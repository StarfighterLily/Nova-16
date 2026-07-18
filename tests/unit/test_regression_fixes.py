"""
Regression tests for bugs found and fixed during the Nova-16 system audit.

Each test class documents a real bug that was confirmed by tracing the code
and reproducing the wrong behavior against the live CPU, then fixed. These
tests pin the fix down so the bug class can't silently come back.
"""

import inspect
import re

import pytest

from tests.conftest import run_cpu_cycles, opcode_value, enc
from opcodes import opcodes as opcode_definitions
from core.exec import HANDLER_INSTRUCTIONS


def write_cstring(memory, addr, s):
    for i, ch in enumerate(s):
        memory.write_byte(addr + i, ord(ch))
    memory.write_byte(addr + len(s), 0)


class TestOpcodeMetadataConsistency:
    """Regression for the BCDA/BCDS/BCDCMP/BCDADD/BCDSUB disassembler desync.

    opcodes.py declared these as 1-operand instructions while the runtime
    handlers (core/exec_handlers.py) and core/exec.py's HANDLER_INSTRUCTIONS
    table actually use 2 operands. Since the disassembler (nova_disassembler.py)
    and the assembler's opcode table both key off opcodes.py's declared count,
    any mismatch with the runtime desyncs disassembly (and would desync
    execution too, for any code path that trusted opcodes.py's count instead
    of the assembled operand bytes). This test asserts every handler-based
    opcode's declared operand count in opcodes.py agrees with its real
    num_operands in HANDLER_INSTRUCTIONS, so this whole bug class can't
    silently reappear for any opcode.
    """

    def test_opcodes_py_matches_handler_instructions_operand_counts(self):
        declared = {int(hexcode, 16): (name, nops) for name, hexcode, nops in opcode_definitions}

        mismatches = []
        for code, inst in HANDLER_INSTRUCTIONS.items():
            if code not in declared:
                continue
            name, nops = declared[code]
            if nops != inst.num_operands:
                mismatches.append(
                    f"0x{code:02X} {name}: opcodes.py says {nops}, "
                    f"HANDLER_INSTRUCTIONS says {inst.num_operands}"
                )

        assert not mismatches, "Operand count mismatches:\n" + "\n".join(mismatches)

    def test_disassembler_stays_aligned_across_bcd_instruction(self, cpu, memory):
        """A BCDA in the middle of a program must not desync disassembly of
        the instruction that follows it (this is exactly how the bug was
        first discovered: BCDA's second operand byte got swallowed and
        interpreted as the start of a bogus following instruction)."""
        from nova_disassembler import create_reverse_maps, disassemble_instruction_new

        program = enc('MOV', ('reg', 'R0'), ('imm8', 0x12)) + \
            enc('MOV', ('reg', 'R1'), ('imm8', 0x34)) + \
            enc('BCDA', ('reg', 'R0'), ('reg', 'R1')) + \
            enc('MOV', ('reg', 'R2'), ('imm8', 0x99)) + \
            enc('HLT')
        data = bytes(program)

        opcode_map, register_map = create_reverse_maps()
        pc = 0
        mnemonics = []
        while pc < len(data):
            mnemonic, operands, size = disassemble_instruction_new(data, pc, opcode_map, register_map)
            mnemonics.append(mnemonic)
            pc += size

        assert mnemonics == ['MOV', 'MOV', 'BCDA', 'MOV', 'HLT']


class TestSoftwareInterruptRoundTrip:
    """Regression for the INT/IRET push-order bug.

    core/exec_handlers.py::_int pushed PC then flags, while
    nova_cpu.py::_trigger_interrupt (used for hardware/async interrupts)
    pushes flags then PC. IRET only unwinds the hardware order, so a
    software INT followed by IRET returned to the wrong PC and restored
    garbage flags. Fixed by making _int push in the same order as
    _trigger_interrupt.
    """

    def _setup_vector(self, cpu, memory, vector, handler_addr):
        memory.write_word(0x0100 + vector * 4, handler_addr)

    def test_int_then_iret_returns_to_correct_pc(self, cpu, memory):
        self._setup_vector(cpu, memory, 0, 0x2000)
        sti_and_int = enc('STI') + enc('INT', ('imm8', 0))
        program = sti_and_int + enc('HLT')
        memory.load_program(program)
        memory.write_byte(0x2000, opcode_value('IRET'))

        return_addr = len(sti_and_int)  # address right after INT, where HLT sits

        cpu.pc = 0
        run_cpu_cycles(cpu, 2)  # STI, INT
        assert cpu.pc == 0x2000, "INT should jump to the vector's handler"

        run_cpu_cycles(cpu, 1)  # IRET
        assert cpu.pc == return_addr, "IRET must return to the instruction after INT"
        assert cpu.Pregisters[8] == 0xFFFF, "SP must be fully restored"

    def test_int_then_iret_preserves_flags(self, cpu, memory):
        self._setup_vector(cpu, memory, 0, 0x2000)
        program = enc('STI') + enc('INT', ('imm8', 0)) + enc('HLT')
        memory.load_program(program)
        memory.write_byte(0x2000, opcode_value('IRET'))

        cpu.pc = 0
        run_cpu_cycles(cpu, 2)
        run_cpu_cycles(cpu, 1)

        # After IRET, the only flag guaranteed set is I (interrupts were
        # enabled by STI before the INT captured the flag snapshot).
        assert cpu.flags[5] == 1  # Interrupt flag
        assert cpu.flags[2] == 0  # Overflow should not be spuriously set

    def test_nested_software_interrupts_return_correctly(self, cpu, memory):
        self._setup_vector(cpu, memory, 0, 0x2000)
        self._setup_vector(cpu, memory, 1, 0x3000)

        program = enc('STI') + enc('INT', ('imm8', 0)) + enc('HLT')
        memory.load_program(program)

        handler0 = enc('INT', ('imm8', 1)) + enc('IRET')
        memory.load_program(handler0, 0x2000)

        handler1 = enc('IRET')
        memory.load_program(handler1, 0x3000)

        cpu.pc = 0
        while not cpu.halted:
            run_cpu_cycles(cpu, 1)
            if cpu.pc == len(program) - 1:  # about to execute HLT
                break

        assert cpu.pc == len(program) - 1
        assert cpu.Pregisters[8] == 0xFFFF, "Stack must fully unwind after nested INT/IRET"


class TestPushPopWidth:
    """Regression: PUSH/POP decided byte-vs-word width solely from
    ``operand.is_register and reg_type == 'P'``, ignoring immediate/memory
    operand size. PUSH of a 16-bit immediate or memory value silently
    dropped the high byte and only moved SP by 1; POP into a memory
    destination only consumed 1 byte off the stack while writing a
    (zero-extended) 16-bit result, permanently desyncing SP.
    """

    def test_push_imm16_moves_sp_by_two_and_round_trips(self, cpu, memory):
        program = enc('PUSH', ('imm16', 0x1234)) + enc('POP', ('reg', 'P0')) + enc('HLT')
        memory.load_program(program)
        sp0 = cpu.Pregisters[8]

        cpu.pc = 0
        run_cpu_cycles(cpu, 1)  # PUSH
        assert sp0 - cpu.Pregisters[8] == 2, "PUSH of a 16-bit immediate must move SP by 2"

        run_cpu_cycles(cpu, 1)  # POP
        assert cpu.Pregisters[0] == 0x1234
        assert cpu.Pregisters[8] == sp0

    def test_push_imm8_moves_sp_by_one(self, cpu, memory):
        program = enc('PUSH', ('imm8', 0x42)) + enc('POP', ('reg', 'R0')) + enc('HLT')
        memory.load_program(program)
        sp0 = cpu.Pregisters[8]

        cpu.pc = 0
        run_cpu_cycles(cpu, 1)  # PUSH
        assert sp0 - cpu.Pregisters[8] == 1

        run_cpu_cycles(cpu, 1)  # POP
        assert cpu.Rregisters[0] == 0x42
        assert cpu.Pregisters[8] == sp0

    def test_push_memory_word_round_trips_through_pop_memory(self, cpu, memory):
        memory.write_word(0x3000, 0xCAFE)
        program = enc('PUSH', ('mem_direct', 0x3000)) + \
            enc('POP', ('mem_direct', 0x4000)) + \
            enc('HLT')
        memory.load_program(program)
        sp0 = cpu.Pregisters[8]

        cpu.pc = 0
        run_cpu_cycles(cpu, 1)  # PUSH [0x3000]
        assert sp0 - cpu.Pregisters[8] == 2, "PUSH of a memory word must move SP by 2"

        run_cpu_cycles(cpu, 1)  # POP [0x4000]
        assert cpu.Pregisters[8] == sp0, "POP into memory must fully restore SP"
        assert memory.read_word(0x4000) == 0xCAFE


class TestStrcmpNullTerminator:
    """Regression: STRCMP compared bytes for the full ``length`` argument
    even past a shared null terminator, so two equal, null-terminated
    strings could compare unequal if the caller passed a generous/buffer
    sized length and the bytes beyond the terminator happened to differ.
    """

    def test_equal_strings_compare_equal_despite_trailing_buffer_garbage(self, cpu, memory):
        write_cstring(memory, 0x4000, "AB")
        write_cstring(memory, 0x4100, "AB")
        # garbage past each string's null terminator
        memory.write_byte(0x4003, ord('Z'))
        memory.write_byte(0x4103, ord('Q'))

        program = enc('STRCMP', ('imm16', 0x4000), ('imm16', 0x4100), ('imm8', 8)) + enc('HLT')
        memory.load_program(program)
        cpu.pc = 0
        run_cpu_cycles(cpu, 1)

        assert cpu.Rregisters[0] == 0

    def test_different_strings_still_detected(self, cpu, memory):
        write_cstring(memory, 0x4000, "AB")
        write_cstring(memory, 0x4100, "AC")

        program = enc('STRCMP', ('imm16', 0x4000), ('imm16', 0x4100), ('imm8', 8)) + enc('HLT')
        memory.load_program(program)
        cpu.pc = 0
        run_cpu_cycles(cpu, 1)

        assert cpu.Rregisters[0] != 0


class TestMemmoveWraparound:
    """Regression: MEMMOVE picked its copy direction from a raw
    ``dest < source`` comparison, which ignores the 64KB address-space
    wraparound. A move whose destination range overlaps the source only
    because it wraps past 0xFFFF/0x0000 picked the wrong direction and
    corrupted data. Fixed by staging through a temporary buffer so no
    direction choice is needed.
    """

    def test_move_wrapping_across_address_boundary_is_correct(self, cpu, memory):
        # Source: 0x0000..0x001F holds a known pattern.
        for i in range(0x20):
            memory.write_byte(i, i + 1)  # 1..32, all non-zero so overlap is visible

        # Destination wraps from 0xFFF0 through 0xFFFF back to 0x000F,
        # overlapping the tail of the source range across the seam. The
        # program itself is loaded well away from both ranges so it doesn't
        # clobber the source pattern.
        program = enc('MEMMOVE', ('imm16', 0xFFF0), ('imm16', 0x0000), ('imm16', 0x20)) + enc('HLT')
        memory.load_program(program, 0x5000)
        cpu.pc = 0x5000
        run_cpu_cycles(cpu, 1)

        expected = [(i + 1) & 0xFF for i in range(0x20)]
        actual = [memory.read_byte((0xFFF0 + i) & 0xFFFF) for i in range(0x20)]
        assert actual == expected


class TestIndexedAddressingSignedOffset:
    """Regression: core/fetch.py::calculate_memory_address only sign-extended
    the offset byte of a register-indexed operand ([reg+offset]) for P8 (SP)
    and P9 (FP), treating the same byte as an unsigned 0..255 offset for
    every other register.

    Both assemblers (nova_assembler.py::encode_operand and
    nova/assembler/codegen.py::_encode_operand) encode a negative decimal
    offset like ``[P0-4]`` identically to ``[FP-4]`` -- as a two's-complement
    byte, for any P or R register, not just SP/FP -- and nova_disassembler.py
    decodes that byte as signed universally too (``format_indexed_register``,
    and the inline offset formatting around disassemble_instruction_new).
    Only the CPU's runtime address calculation singled out P8/P9, so
    ``[P0-4]`` assembled correctly and disassembled back to ``[P0-4]``, but
    executing it computed ``base + 252`` instead of ``base - 4`` -- a silent
    wrong-address bug for any negative-offset indexed addressing on a
    non-stack register.
    """

    def test_lea_negative_offset_on_general_register(self, cpu, memory):
        program = enc('MOV', ('reg', 'P0'), ('imm16', 0x3000)) + \
            enc('LEA', ('reg', 'P1'), ('mem_indexed', 'P0', -4)) + \
            enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 2)
        assert cpu.Pregisters[1] == 0x2FFC

    def test_mov_read_through_negative_offset_on_general_register(self, cpu, memory):
        memory.write_byte(0x2FFC, 0x77)
        program = enc('MOV', ('reg', 'P0'), ('imm16', 0x3000)) + \
            enc('MOV', ('reg', 'R0'), ('mem_indexed', 'P0', -4)) + \
            enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 2)
        assert cpu.Rregisters[0] == 0x77

    def test_mov_write_through_negative_offset_on_general_register(self, cpu, memory):
        program = enc('MOV', ('reg', 'P0'), ('imm16', 0x3000)) + \
            enc('MOV', ('reg', 'R1'), ('imm8', 0x99)) + \
            enc('MOV', ('mem_indexed', 'P0', -4), ('reg', 'R1')) + \
            enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 3)
        assert memory.read_byte(0x2FFC) == 0x99
        assert memory.read_byte(0x3000) == 0, "must not have written at the unsigned +252 address"

    def test_negative_offset_matches_fp_relative_addressing(self, cpu, memory):
        """[P9-4] (P9 is FP) and the FP-specific encoding must resolve to the
        same address, since the CPU distinguishes them only by register
        index, not by which assembler syntax produced the operand."""
        program = enc('MOV', ('reg', 'P9'), ('imm16', 0x4000)) + \
            enc('LEA', ('reg', 'P0'), ('mem_indexed', 'P9', -10)) + \
            enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 2)
        assert cpu.Pregisters[0] == 0x3FF6

    def test_negative_offset_wraps_below_zero_address(self, cpu, memory):
        program = enc('MOV', ('reg', 'P0'), ('imm16', 0x0002)) + \
            enc('LEA', ('reg', 'P1'), ('mem_indexed', 'P0', -4)) + \
            enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 2)
        assert cpu.Pregisters[1] == 0xFFFE


class TestDirectIndexedZeroPageAddressing:
    """Regression: core/fetch.py::calculate_memory_address distinguished a
    direct-indexed operand ([addr16+offset]) from a register-indexed operand
    ([reg+offset]) by checking ``if operand.address:`` -- truthiness, not
    ``is not None``. Zero-page base addresses (e.g. ``[0x0000+4]``) are a
    documented fast path (see docs/NOVA_PROFILER_README.md) and legitimately
    leave ``operand.address == 0``, so the check misfired and fell into the
    register-indexed branch instead.

    Worse, ``core/fetch.py::_decode_memory_ref`` never cleared
    ``reg_type``/``reg_idx`` on direct/direct-indexed operands, relying on a
    stated invariant ("every decode branch sets them") that was false for
    those two branches. Operand objects are pooled and reused
    (``_acquire_operand``/``_release_operand``), so a direct-indexed operand
    decoded right after a register-indexed one inherited that operand's
    stale reg_type/reg_idx. Combined with the truthiness bug, a zero-page
    direct-indexed reference silently computed its address from whatever
    register a *prior, unrelated* instruction happened to index through,
    instead of from the literal address in the instruction stream.

    Fixed by keying the branch off ``operand.indirect``/``operand.indexed``/
    ``operand.reg_type`` (never truthy-ambiguous) and by explicitly clearing
    reg_type/reg_idx in the direct decode branches.
    """

    # Programs are loaded away from address 0x0000 so the zero-page trap/
    # target bytes under test can't be clobbered by the program bytes
    # themselves (the default load address is 0x0000).
    LOAD_ADDR = 0x0200

    def _load(self, cpu, memory, program):
        memory.load_program(program, self.LOAD_ADDR)
        cpu.pc = self.LOAD_ADDR

    def test_zero_page_direct_indexed_ignores_stale_pooled_register(self, cpu, memory):
        # Trap value at the address the bug would wrongly compute
        # (P0=0x1234, so the old code would resolve [0x0000+4] as [P0+4] = 0x1238).
        memory.write_byte(0x1238, 0xAA)
        # Correct target: literal zero-page address 0x0000 + offset 4.
        memory.write_byte(0x0004, 0x99)

        program = enc('MOV', ('reg', 'P0'), ('imm16', 0x1234)) + \
            enc('MOV', ('reg', 'R0'), ('mem_indexed', 'P0', 4)) + \
            enc('MOV', ('reg', 'R1'), ('mem_direct_indexed', 0x0000, 4)) + \
            enc('HLT')
        self._load(cpu, memory, program)
        run_cpu_cycles(cpu, 3)

        assert cpu.Rregisters[1] == 0x99, (
            "MOV R1, [0x0000+4] must read the literal zero-page address, "
            "not a stale register-indexed address left in the operand pool"
        )

    def test_zero_page_direct_indexed_write_targets_literal_address(self, cpu, memory):
        memory.write_byte(0x0000, 0)
        program = enc('MOV', ('reg', 'P0'), ('imm16', 0x1234)) + \
            enc('MOV', ('reg', 'R0'), ('mem_indexed', 'P0', 4)) + \
            enc('MOV', ('reg', 'R1'), ('imm8', 0x55)) + \
            enc('MOV', ('mem_direct_indexed', 0x0000, 0), ('reg', 'R1')) + \
            enc('HLT')
        self._load(cpu, memory, program)
        run_cpu_cycles(cpu, 4)

        assert memory.read_byte(0x0000) == 0x55
        assert memory.read_byte(0x1234) == 0, "must not have written through the stale P0-based address"

    def test_plain_direct_zero_page_still_correct(self, cpu, memory):
        """Sanity check: [0x0000] with no offset must still resolve to address 0."""
        memory.write_byte(0x0000, 0x77)
        program = enc('MOV', ('reg', 'R0'), ('mem_direct', 0x0000)) + \
            enc('HLT')
        self._load(cpu, memory, program)
        run_cpu_cycles(cpu, 1)
        assert cpu.Rregisters[0] == 0x77

    def test_direct_indexed_nonzero_base_unaffected(self, cpu, memory):
        """Sanity check: non-zero-page direct-indexed addressing still works."""
        memory.write_byte(0x2008, 0x42)
        program = enc('MOV', ('reg', 'R0'), ('mem_direct_indexed', 0x2000, 8)) + \
            enc('HLT')
        self._load(cpu, memory, program)
        run_cpu_cycles(cpu, 1)
        assert cpu.Rregisters[0] == 0x42


class TestStrextNeedleLongerThanMaxLen:
    """Regression: STREXT/STREXTI's inner matching loop was bounded by
    ``max_len`` and treated hitting that cap as a successful match, even
    when the needle actually continues past max_len and the full needle
    isn't present in the haystack at all. Fixed by requiring the loop to
    have reached the needle's own null terminator for a match to count.
    """

    def test_needle_longer_than_max_len_is_not_a_false_positive_match(self, cpu, memory):
        write_cstring(memory, 0x3000, "HELLO!")
        write_cstring(memory, 0x3100, "HELLOWORLD")
        memory.write_byte(0x3200, 0xAA)  # poison the destination buffer

        program = enc('STREXT', ('imm16', 0x3200), ('imm16', 0x3000),
                      ('imm16', 0x3100), ('imm8', 5)) + enc('HLT')
        memory.load_program(program)
        cpu.pc = 0
        run_cpu_cycles(cpu, 1)

        assert memory.read_byte(0x3200) == 0, "no genuine match should be found"

    def test_needle_shorter_than_max_len_still_matches(self, cpu, memory):
        write_cstring(memory, 0x3000, "SAY HELLO THERE")
        write_cstring(memory, 0x3100, "HELLO")
        memory.write_byte(0x3200, 0xAA)

        # max_len bounds how many characters get copied out of the haystack
        # starting at the match, not the needle's own length — so with
        # max_len=5 the extracted text is exactly "HELLO".
        program = enc('STREXT', ('imm16', 0x3200), ('imm16', 0x3000),
                      ('imm16', 0x3100), ('imm8', 5)) + enc('HLT')
        memory.load_program(program)
        cpu.pc = 0
        run_cpu_cycles(cpu, 1)

        result = bytearray()
        i = 0
        while True:
            b = memory.read_byte(0x3200 + i)
            if b == 0:
                break
            result.append(b)
            i += 1
        assert bytes(result) == b"HELLO"


class TestHandlerOperandIndexBounds:
    """Regression for SW/VY (see TestSpecialRegisterOpcodes below): both
    handlers unconditionally indexed ``values[1]`` despite their opcode
    being declared ``num_operands=1`` in HANDLER_INSTRUCTIONS, so every
    execution raised IndexError. ``_execute_handler`` in core/exec.py only
    ever builds a ``values`` tuple of exactly ``num_operands`` entries (see
    the ``n_ops == 1``/``n_ops == 2``/etc. branches), so any handler that
    reads ``values[N]`` unconditionally with N >= num_operands is always
    broken, not just in some edge case.

    This scans every handler's source for literal ``values[N]`` indexing
    (skipping uses already guarded by an explicit ``len(values) > N`` check,
    which several variadic-looking handlers use legitimately) and fails if
    any unguarded index falls outside the opcode's declared operand count,
    so this whole bug class can't silently reappear for any opcode.
    """

    def test_no_handler_indexes_values_beyond_its_declared_operand_count(self):
        violations = []
        for opcode, inst in sorted(HANDLER_INSTRUCTIONS.items()):
            if inst.handler is None or inst.handler.__module__ != 'core.exec_handlers':
                continue
            try:
                src = inspect.getsource(inst.handler)
            except (TypeError, OSError):
                continue

            # Drop any 'values[N] if len(values) > M else ...' branch text
            # from consideration on the guarded side; the ternary's fallback
            # (post-'else') is what actually executes when len(values) is
            # small, so only *that* side needs to stay in bounds. Rather
            # than parse the ternary precisely, conservatively treat any
            # values[N] textually preceded on the same line by a matching
            # 'len(values) > N' guard as safe, and flag everything else.
            for lineno, line in enumerate(src.splitlines(), start=1):
                guarded_indices = {int(m) for m in re.findall(r'len\(values\)\s*>\s*(\d+)', line)}
                for m in re.finditer(r'values\[(\d+)\]', line):
                    idx = int(m.group(1))
                    if idx in guarded_indices:
                        continue
                    if idx >= inst.num_operands:
                        violations.append(
                            f"0x{opcode:02X} {inst.name} ({inst.handler.__name__}): "
                            f"unguarded values[{idx}] but num_operands={inst.num_operands} "
                            f"(line {lineno}: {line.strip()!r})"
                        )

        assert not violations, "Handlers indexing values[] out of bounds:\n" + "\n".join(violations)


class TestSpecialRegisterOpcodes:
    """Regression + first-ever coverage for the dedicated single-operand
    special-register opcodes (SA/SF/SV/SW/VM/VL/VX/VY/TT/TM/TC/TS). None of
    these had any test exercising the *opcode* form (as opposed to using
    the register name as a MOV operand, e.g. ``MOV TT, 42``), which is why
    two independent bugs went unnoticed:

    - SW (0xE0) and VY (0xFE) handlers indexed ``values[1]`` on a
      1-operand instruction, raising IndexError on every execution
      (see TestHandlerOperandIndexBounds).
    - TT/TM/TC/TS (0xE3-0xE6) wrote to ``cpu.timer[...]``, a list
      attribute that was never defined anywhere on the CPU class (the
      real timer state lives in ``cpu.timer_device``, an optional
      peripheral only wired up via the ``cpu_with_timer`` fixture / a
      real event bus), so these opcodes raised AttributeError
      unconditionally -- even when no timer was attached, since the
      crash happened before any None-check could apply.
    """

    def test_sw_opcode_sets_sound_waveform_register(self, cpu, memory):
        program = enc('SW', ('imm8', 0x85)) + enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 1)
        assert cpu.sound.SW == 0x85

    def test_vy_opcode_sets_video_y_register(self, cpu, memory):
        program = enc('VY', ('imm8', 100)) + enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 1)
        assert cpu.gfx.Vregisters[1] == 100

    def test_vx_opcode_sets_video_x_register(self, cpu, memory):
        program = enc('VX', ('imm8', 50)) + enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 1)
        assert cpu.gfx.Vregisters[0] == 50

    def test_sa_sf_sv_opcodes_set_sound_registers(self, cpu, memory):
        program = enc('SA', ('imm16', 0x1234)) + \
            enc('SF', ('imm8', 0x42)) + \
            enc('SV', ('imm8', 0x07)) + \
            enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 3)
        assert cpu.sound.SA == 0x1234
        assert cpu.sound.SF == 0x42
        assert cpu.sound.SV == 0x07

    def test_vm_vl_opcodes_set_graphics_mode_registers(self, cpu, memory):
        program = enc('VM', ('imm8', 1)) + \
            enc('VL', ('imm8', 3)) + \
            enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 2)
        assert cpu.gfx.VM == 1
        assert cpu.gfx.VL == 3

    def test_tt_tm_tc_ts_opcodes_do_not_crash_without_timer_device(self, cpu, memory):
        """Without a wired timer peripheral, these must be safe no-ops --
        matching the register-code path's documented no-op behavior in
        CPU._register_externals when timer_device is None -- not crash."""
        program = enc('TT', ('imm8', 1)) + \
            enc('TM', ('imm8', 2)) + \
            enc('TC', ('imm8', 3)) + \
            enc('TS', ('imm8', 4)) + \
            enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 4)
        assert cpu.pc != 0  # executed past all four without raising

    def test_tt_tm_ts_opcodes_write_through_to_timer_device(self, cpu_with_timer, memory):
        """TC is checked separately: enabling it resets the counter (see
        Timer._set_control), which would make TT's written value
        unobservable if both were checked together after running."""
        cpu = cpu_with_timer
        program = enc('TT', ('imm8', 10)) + \
            enc('TM', ('imm8', 20)) + \
            enc('TS', ('imm8', 4)) + \
            enc('HLT')
        memory.load_program(program)
        cpu.pc = 0
        run_cpu_cycles(cpu, 3)
        assert cpu.timer_device.regs[0] == 10
        assert cpu.timer_device.regs[1] == 20
        assert cpu.timer_device.regs[3] == 4

    def test_tc_opcode_writes_through_and_enables_timer(self, cpu_with_timer, memory):
        cpu = cpu_with_timer
        program = enc('TC', ('imm8', 3)) + enc('HLT')  # enable + interrupt-enable
        memory.load_program(program)
        cpu.pc = 0
        run_cpu_cycles(cpu, 1)
        assert cpu.timer_device.regs[2] == 3
        assert cpu.timer_device._enabled is True
        assert cpu.timer_device._interrupt_enabled is True


class TestDirectIndexedOffsetSignedness:
    """Regression: core/fetch.py::calculate_memory_address sign-extended the
    offset byte of a register-indexed operand ([reg+offset]) for every
    register (see TestIndexedAddressingSignedOffset above) but treated the
    *identical* offset byte as an unsigned 0..255 value for the
    direct-indexed form ([addr16+offset]) specifically.

    nova_disassembler.py decodes the direct-indexed offset as signed
    two's-complement (``if offset > 127: offset -= 256``) for both forms
    uniformly, so a direct-indexed operand with offset byte 0xFC disassembles
    as ``[0x2000-4]`` but, before this fix, actually computed
    ``0x2000 + 0xFC = 0x20FC`` instead of ``0x2000 - 4 = 0x1FFC`` --
    the same "disassembly says signed, execution says unsigned" mismatch
    already fixed once for the register-indexed case.
    """

    def test_direct_indexed_negative_offset_reads_correct_address(self, cpu, memory):
        memory.write_byte(0x1FFC, 0x77)
        memory.write_byte(0x20FC, 0xAA)  # trap value at the old, wrong address
        program = enc('MOV', ('reg', 'R0'), ('mem_direct_indexed', 0x2000, -4)) + \
            enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 1)
        assert cpu.Rregisters[0] == 0x77

    def test_direct_indexed_negative_offset_write_targets_correct_address(self, cpu, memory):
        program = enc('MOV', ('reg', 'R1'), ('imm8', 0x99)) + \
            enc('MOV', ('mem_direct_indexed', 0x2000, -4), ('reg', 'R1')) + \
            enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 2)
        assert memory.read_byte(0x1FFC) == 0x99
        assert memory.read_byte(0x20FC) == 0, "must not have written at the unsigned +252 address"

    def test_direct_indexed_positive_offset_unaffected(self, cpu, memory):
        """Sanity check: small positive direct-indexed offsets (the only
        form the primary assembler/NoBASIC codegen currently emit) must
        still resolve exactly as before."""
        memory.write_byte(0x2008, 0x42)
        program = enc('MOV', ('reg', 'R0'), ('mem_direct_indexed', 0x2000, 8)) + \
            enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 1)
        assert cpu.Rregisters[0] == 0x42
