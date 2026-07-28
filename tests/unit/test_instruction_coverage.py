"""
Coverage tests for Nova-16 opcodes that previously had no direct unit test.

Found via a textual scan of tests/ for each mnemonic in opcodes.py; the
opcodes covered here (MUL, MOD, NEG, ABS, LEA, the full conditional-jump
family, BR/BRZ/BRNZ, LOOP/LOOPZ, PUSHF/POPF, CALLZ/CALLNZ, MEMMOVE/MEMTEST,
the ITOB/BTOI/ITOS/STOI and FMUL/FDIV/FTOI/ITOF conversion families, and the
BCD arithmetic family) had zero prior test coverage despite being core,
reachable instructions.
"""

import pytest

from tests.conftest import run_cpu_cycles, opcode_value, enc


class TestArithmeticCoverage:
    def test_mul_basic(self, cpu, memory):
        program = enc('MOV', ('reg', 'R0'), ('imm8', 6)) + \
            enc('MOV', ('reg', 'R1'), ('imm8', 7)) + \
            enc('MUL', ('reg', 'R0'), ('reg', 'R1')) + \
            enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 4)
        assert cpu.Rregisters[0] == 42
        assert cpu.zero_flag == False

    def test_mul_8bit_overflow_sets_carry(self, cpu, memory):
        program = enc('MOV', ('reg', 'R0'), ('imm8', 0x40)) + \
            enc('MOV', ('reg', 'R1'), ('imm8', 0x04)) + \
            enc('MUL', ('reg', 'R0'), ('reg', 'R1')) + \
            enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 4)
        # 0x40 * 0x04 = 0x100, wraps to 0x00 in an 8-bit register
        assert cpu.Rregisters[0] == 0x00
        assert cpu.flags[6] == 1  # Carry

    def test_mod_basic(self, cpu, memory):
        program = enc('MOV', ('reg', 'R0'), ('imm8', 17)) + \
            enc('MOV', ('reg', 'R1'), ('imm8', 5)) + \
            enc('MOD', ('reg', 'R0'), ('reg', 'R1')) + \
            enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 4)
        assert cpu.Rregisters[0] == 2

    def test_mod_by_zero_raises(self, cpu, memory):
        program = enc('MOV', ('reg', 'R0'), ('imm8', 17)) + \
            enc('MOV', ('reg', 'R1'), ('imm8', 0)) + \
            enc('MOD', ('reg', 'R0'), ('reg', 'R1')) + \
            enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 2)
        with pytest.raises(RuntimeError, match="Modulo by zero"):
            cpu.step()

    def test_neg_basic(self, cpu, memory):
        program = enc('MOV', ('reg', 'P0'), ('imm16', 5)) + \
            enc('NEG', ('reg', 'P0')) + \
            enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 3)
        assert cpu.Pregisters[0] == 0xFFFB  # -5 as 16-bit two's complement

    def test_neg_zero_stays_zero(self, cpu, memory):
        program = enc('MOV', ('reg', 'R0'), ('imm8', 0)) + \
            enc('NEG', ('reg', 'R0')) + \
            enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 3)
        assert cpu.Rregisters[0] == 0
        assert cpu.zero_flag == True

    def test_abs_of_negative(self, cpu, memory):
        program = enc('MOV', ('reg', 'P0'), ('imm16', 0xFFFB)) + \
            enc('ABS', ('reg', 'P0')) + \
            enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 3)
        assert cpu.Pregisters[0] == 5

    def test_abs_of_positive_is_unchanged(self, cpu, memory):
        program = enc('MOV', ('reg', 'P0'), ('imm16', 5)) + \
            enc('ABS', ('reg', 'P0')) + \
            enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 3)
        assert cpu.Pregisters[0] == 5


class TestLea:
    def test_lea_direct_address_not_dereferenced(self, cpu, memory):
        memory.write_word(0x2000, 0xBEEF)  # decoy: LEA must not read this
        program = enc('LEA', ('reg', 'P1'), ('mem_direct', 0x2000)) + enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 1)
        assert cpu.Pregisters[1] == 0x2000

    def test_lea_indexed_address(self, cpu, memory):
        program = enc('MOV', ('reg', 'P0'), ('imm16', 0x3000)) + \
            enc('LEA', ('reg', 'P1'), ('mem_indexed', 'P0', 8)) + \
            enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 2)
        assert cpu.Pregisters[1] == 0x3008


class TestConditionalJumpFamily:
    """Each of these was previously untested. All follow the same
    build-a-condition-then-branch-or-fall-through shape: run 3 instructions
    (set flags, jump, marker) and check whether the jump landed."""

    def _run_jump(self, cpu, memory, setup, jump_mnemonic, taken: bool):
        target = 0x0100
        program = setup + enc(jump_mnemonic, ('imm16', target)) + \
            enc('MOV', ('reg', 'R9'), ('imm8', 0xAA))  # marker: only if NOT taken
        memory.load_program(program)
        memory.write_byte(target, opcode_value('HLT'))
        cpu.pc = 0
        while not cpu.halted:
            cpu.step()
            if cpu.pc >= target and taken:
                break
        if taken:
            assert cpu.pc == target
        else:
            assert cpu.Rregisters[9] == 0xAA

    def test_jc_taken_when_carry_set(self, cpu, memory):
        # ADD that overflows a byte sets carry
        setup = enc('MOV', ('reg', 'R0'), ('imm8', 0xFF)) + \
            enc('ADD', ('reg', 'R0'), ('imm8', 1))
        self._run_jump(cpu, memory, setup, 'JC', taken=True)

    def test_jnc_taken_when_no_carry(self, cpu, memory):
        setup = enc('MOV', ('reg', 'R0'), ('imm8', 1)) + \
            enc('ADD', ('reg', 'R0'), ('imm8', 1))
        self._run_jump(cpu, memory, setup, 'JNC', taken=True)

    def test_jo_taken_on_signed_overflow(self, cpu, memory):
        # 0x7F + 1 signed-overflows an 8-bit register (127 -> -128)
        setup = enc('MOV', ('reg', 'R0'), ('imm8', 0x7F)) + \
            enc('ADD', ('reg', 'R0'), ('imm8', 1))
        self._run_jump(cpu, memory, setup, 'JO', taken=True)

    def test_jno_taken_without_overflow(self, cpu, memory):
        setup = enc('MOV', ('reg', 'R0'), ('imm8', 1)) + \
            enc('ADD', ('reg', 'R0'), ('imm8', 1))
        self._run_jump(cpu, memory, setup, 'JNO', taken=True)

    def test_js_taken_on_negative_result(self, cpu, memory):
        setup = enc('MOV', ('reg', 'R0'), ('imm8', 1)) + \
            enc('SUB', ('reg', 'R0'), ('imm8', 2))
        self._run_jump(cpu, memory, setup, 'JS', taken=True)

    def test_jns_taken_on_nonnegative_result(self, cpu, memory):
        setup = enc('MOV', ('reg', 'R0'), ('imm8', 5)) + \
            enc('SUB', ('reg', 'R0'), ('imm8', 2))
        self._run_jump(cpu, memory, setup, 'JNS', taken=True)

    def test_jgt_taken_when_signed_greater(self, cpu, memory):
        setup = enc('MOV', ('reg', 'R0'), ('imm8', 5)) + \
            enc('CMP', ('reg', 'R0'), ('imm8', 3))
        self._run_jump(cpu, memory, setup, 'JGT', taken=True)

    def test_jgt_not_taken_when_equal(self, cpu, memory):
        setup = enc('MOV', ('reg', 'R0'), ('imm8', 3)) + \
            enc('CMP', ('reg', 'R0'), ('imm8', 3))
        self._run_jump(cpu, memory, setup, 'JGT', taken=False)

    def test_jge_taken_when_equal(self, cpu, memory):
        setup = enc('MOV', ('reg', 'R0'), ('imm8', 3)) + \
            enc('CMP', ('reg', 'R0'), ('imm8', 3))
        self._run_jump(cpu, memory, setup, 'JGE', taken=True)

    def test_jle_taken_when_equal(self, cpu, memory):
        setup = enc('MOV', ('reg', 'R0'), ('imm8', 3)) + \
            enc('CMP', ('reg', 'R0'), ('imm8', 3))
        self._run_jump(cpu, memory, setup, 'JLE', taken=True)

    def test_jle_not_taken_when_greater(self, cpu, memory):
        setup = enc('MOV', ('reg', 'R0'), ('imm8', 5)) + \
            enc('CMP', ('reg', 'R0'), ('imm8', 3))
        self._run_jump(cpu, memory, setup, 'JLE', taken=False)


class TestRelativeBranches:
    def test_br_unconditional(self, cpu, memory):
        br_instr = enc('BR', ('imm16', 6))
        program = br_instr + enc('MOV', ('reg', 'R9'), ('imm8', 0xAA)) + enc('HLT')
        memory.load_program(program)
        cpu.pc = 0
        run_cpu_cycles(cpu, 1)
        # offset is relative to PC right after the BR instruction (opcode +
        # mode byte + 2-byte imm16 = 4 bytes)
        assert cpu.pc == len(br_instr) + 6

    def test_brz_taken_when_zero(self, cpu, memory):
        program = enc('MOV', ('reg', 'R0'), ('imm8', 0)) + \
            enc('CMP', ('reg', 'R0'), ('imm8', 0)) + \
            enc('BRZ', ('imm16', 4)) + \
            enc('MOV', ('reg', 'R9'), ('imm8', 0xAA)) + \
            enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 3)
        assert cpu.Rregisters[9] == 0  # jump skipped the marker MOV

    def test_brnz_taken_when_not_zero(self, cpu, memory):
        program = enc('MOV', ('reg', 'R0'), ('imm8', 1)) + \
            enc('CMP', ('reg', 'R0'), ('imm8', 0)) + \
            enc('BRNZ', ('imm16', 4)) + \
            enc('MOV', ('reg', 'R9'), ('imm8', 0xAA)) + \
            enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 3)
        assert cpu.Rregisters[9] == 0


class TestLoop:
    def test_loop_decrements_and_repeats(self, cpu, memory):
        # P0 = 3; loop body increments R0; LOOP P0, body until P0 == 0
        program = enc('MOV', ('reg', 'P0'), ('imm16', 3)) + \
            enc('MOV', ('reg', 'R0'), ('imm8', 0))            # addr 3
        loop_top = len(program)
        program += enc('INC', ('reg', 'R0')) + \
            enc('LOOP', ('reg', 'P0'), ('imm16', loop_top)) + \
            enc('HLT')
        memory.load_program(program)
        cpu.pc = 0
        for _ in range(200):
            if cpu.halted:
                break
            cpu.step()
        assert cpu.Rregisters[0] == 3
        assert cpu.Pregisters[0] == 0

    def test_loopz_stops_when_zero_flag_clear(self, cpu, memory):
        # Counter starts at 3; CMP makes Z=0 every iteration, so LOOPZ should
        # never branch even though the counter hasn't reached zero.
        program = enc('MOV', ('reg', 'P0'), ('imm16', 3)) + \
            enc('MOV', ('reg', 'R0'), ('imm8', 1))
        loop_top = len(program)
        program += enc('CMP', ('reg', 'R0'), ('imm8', 0)) + \
            enc('LOOPZ', ('reg', 'P0'), ('imm16', loop_top)) + \
            enc('HLT')
        memory.load_program(program)
        cpu.pc = 0
        for _ in range(50):
            if cpu.halted:
                break
            cpu.step()
        # Counter still decrements each pass even though it never branches
        assert cpu.Pregisters[0] == 2
        assert cpu.halted


class TestPushfPopf:
    def test_pushf_popf_round_trip(self, cpu, memory):
        program = enc('MOV', ('reg', 'R0'), ('imm8', 0)) + \
            enc('CMP', ('reg', 'R0'), ('imm8', 0)) + \
            enc('PUSHF') + \
            enc('MOV', ('reg', 'R0'), ('imm8', 5)) + \
            enc('CMP', ('reg', 'R0'), ('imm8', 0)) + \
            enc('POPF') + \
            enc('HLT')
        memory.load_program(program)
        sp0 = cpu.Pregisters[8]
        run_cpu_cycles(cpu, 2)
        assert cpu.zero_flag == True

        run_cpu_cycles(cpu, 1)  # PUSHF
        assert sp0 - cpu.Pregisters[8] == 2

        run_cpu_cycles(cpu, 2)  # MOV, CMP -> zero_flag becomes False
        assert cpu.zero_flag == False

        run_cpu_cycles(cpu, 1)  # POPF restores the earlier Z=1 state
        assert cpu.zero_flag == True
        assert cpu.Pregisters[8] == sp0


class TestCallzCallnz:
    def test_callnz_taken_when_not_zero(self, cpu, memory):
        program = enc('MOV', ('reg', 'R0'), ('imm8', 1)) + \
            enc('CMP', ('reg', 'R0'), ('imm8', 0)) + \
            enc('CALLNZ', ('imm16', 0x0100)) + \
            enc('HLT')
        memory.load_program(program)
        memory.write_byte(0x0100, opcode_value('RET'))
        cpu.pc = 0
        run_cpu_cycles(cpu, 3)
        assert cpu.pc == 0x0100
        run_cpu_cycles(cpu, 1)  # RET
        assert cpu.pc == len(program) - 1  # back at the HLT

    def test_callnz_not_taken_when_zero(self, cpu, memory):
        program = enc('MOV', ('reg', 'R0'), ('imm8', 0)) + \
            enc('CMP', ('reg', 'R0'), ('imm8', 0)) + \
            enc('CALLNZ', ('imm16', 0x0100)) + \
            enc('MOV', ('reg', 'R9'), ('imm8', 0xAA)) + \
            enc('HLT')
        memory.load_program(program)
        memory.write_byte(0x0100, opcode_value('RET'))
        run_cpu_cycles(cpu, 4)
        assert cpu.Rregisters[9] == 0xAA
        assert cpu.pc != 0x0100

    def test_callz_taken_when_zero(self, cpu, memory):
        program = enc('MOV', ('reg', 'R0'), ('imm8', 0)) + \
            enc('CMP', ('reg', 'R0'), ('imm8', 0)) + \
            enc('CALLZ', ('imm16', 0x0100)) + \
            enc('HLT')
        memory.load_program(program)
        memory.write_byte(0x0100, opcode_value('RET'))
        run_cpu_cycles(cpu, 3)
        assert cpu.pc == 0x0100


class TestMemmoveAndMemtest:
    def test_memmove_no_overlap(self, cpu, memory):
        for i in range(8):
            memory.write_byte(0x1000 + i, i + 1)
        program = enc('MEMMOVE', ('imm16', 0x2000), ('imm16', 0x1000), ('imm16', 8)) + enc('HLT')
        memory.load_program(program, 0x5000)
        cpu.pc = 0x5000
        run_cpu_cycles(cpu, 1)
        assert [memory.read_byte(0x2000 + i) for i in range(8)] == list(range(1, 9))

    def test_memmove_forward_overlap(self, cpu, memory):
        # dest > source, ranges overlap: classic memmove hazard for a naive
        # forward copy.
        for i in range(8):
            memory.write_byte(0x1000 + i, i + 1)
        program = enc('MEMMOVE', ('imm16', 0x1004), ('imm16', 0x1000), ('imm16', 8)) + enc('HLT')
        memory.load_program(program, 0x5000)
        cpu.pc = 0x5000
        run_cpu_cycles(cpu, 1)
        assert [memory.read_byte(0x1004 + i) for i in range(8)] == list(range(1, 9))

    def test_memtest_match_sets_zero_flag(self, cpu, memory):
        for i in range(4):
            memory.write_byte(0x1000 + i, 0x55)
            memory.write_byte(0x2000 + i, 0x55)
        program = enc('MEMTEST', ('imm16', 0x1000), ('imm16', 0x2000), ('imm16', 4)) + enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 1)
        assert cpu.zero_flag == True

    def test_memtest_mismatch_clears_zero_flag(self, cpu, memory):
        for i in range(4):
            memory.write_byte(0x1000 + i, 0x55)
            memory.write_byte(0x2000 + i, 0x55)
        memory.write_byte(0x2002, 0x99)
        program = enc('MEMTEST', ('imm16', 0x1000), ('imm16', 0x2000), ('imm16', 4)) + enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 1)
        assert cpu.zero_flag == False


class TestConversionCoverage:
    def test_itob_btoi_round_trip(self, cpu, memory):
        program = enc('MOV', ('reg', 'P0'), ('imm16', 0x2000)) + \
            enc('ITOB', ('reg', 'P0'), ('imm8', 13)) + \
            enc('BTOI', ('reg', 'R0'), ('reg', 'P0')) + \
            enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 3)
        # 13 = 0b1101
        s = bytearray()
        i = 0
        while True:
            b = memory.read_byte(0x2000 + i)
            if b == 0:
                break
            s.append(b)
            i += 1
        assert bytes(s) == b"1101"
        assert cpu.Rregisters[0] == 13

    def test_itos_stoi_round_trip(self, cpu, memory):
        program = enc('MOV', ('reg', 'P1'), ('imm16', 1234)) + \
            enc('ITOS', ('reg', 'P0'), ('reg', 'P1')) + \
            enc('STOI', ('reg', 'P2'), ('reg', 'P0')) + \
            enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 3)
        assert cpu.Pregisters[0] == 0xA000  # ITOS writes to the fixed buffer
        s = bytearray()
        i = 0
        while True:
            b = memory.read_byte(0xA000 + i)
            if b == 0:
                break
            s.append(b)
            i += 1
        assert bytes(s) == b"1234"
        assert cpu.Pregisters[2] == 1234


class TestFixedPointCoverage:
    def test_itof_ftoi_round_trip(self, cpu, memory):
        program = enc('MOV', ('reg', 'P0'), ('imm16', 5)) + \
            enc('ITOF', ('reg', 'P0')) + \
            enc('FTOI', ('reg', 'P0')) + \
            enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 3)
        assert cpu.Pregisters[0] == 5

    def test_fmul_identity(self, cpu, memory):
        # 2.0 (Q8.8 = 0x0200) * 3.0 (0x0300) = 6.0 (0x0600)
        program = enc('MOV', ('reg', 'P0'), ('imm16', 0x0200)) + \
            enc('MOV', ('reg', 'P1'), ('imm16', 0x0300)) + \
            enc('FMUL', ('reg', 'P0'), ('reg', 'P1')) + \
            enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 3)
        assert cpu.Pregisters[0] == 0x0600

    def test_fdiv_basic(self, cpu, memory):
        # 6.0 / 3.0 = 2.0
        program = enc('MOV', ('reg', 'P0'), ('imm16', 0x0600)) + \
            enc('MOV', ('reg', 'P1'), ('imm16', 0x0300)) + \
            enc('FDIV', ('reg', 'P0'), ('reg', 'P1')) + \
            enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 3)
        assert cpu.Pregisters[0] == 0x0200

    def test_fdiv_by_zero_raises(self, cpu, memory):
        program = enc('MOV', ('reg', 'P0'), ('imm16', 0x0600)) + \
            enc('MOV', ('reg', 'P1'), ('imm16', 0)) + \
            enc('FDIV', ('reg', 'P0'), ('reg', 'P1')) + \
            enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 2)
        with pytest.raises(RuntimeError, match="Division by zero"):
            cpu.step()


class TestBcdArithmetic:
    """BCDA/BCDS/BCDCMP/BCDADD/BCDSUB had zero prior coverage, and their
    declared operand count in opcodes.py was wrong until this audit (see
    tests/unit/test_regression_fixes.py::TestOpcodeMetadataConsistency)."""

    def test_bcdadd_no_carry(self, cpu, memory):
        # 15 + 27 = 42 in BCD
        program = enc('SED') + \
            enc('MOV', ('reg', 'R0'), ('imm8', 0x15)) + \
            enc('MOV', ('reg', 'R1'), ('imm8', 0x27)) + \
            enc('BCDADD', ('reg', 'R0'), ('reg', 'R1')) + \
            enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 4)
        assert cpu.Rregisters[0] == 0x42

    def test_bcdsub_basic(self, cpu, memory):
        # 42 - 15 = 27 in BCD
        program = enc('SED') + \
            enc('MOV', ('reg', 'R0'), ('imm8', 0x42)) + \
            enc('MOV', ('reg', 'R1'), ('imm8', 0x15)) + \
            enc('BCDSUB', ('reg', 'R0'), ('reg', 'R1')) + \
            enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 4)
        assert cpu.Rregisters[0] == 0x27

    def test_bcda_matches_bcdadd_without_pending_carry(self, cpu, memory):
        program = enc('SED') + \
            enc('CLA') + \
            enc('MOV', ('reg', 'R0'), ('imm8', 0x15)) + \
            enc('MOV', ('reg', 'R1'), ('imm8', 0x27)) + \
            enc('BCDA', ('reg', 'R0'), ('reg', 'R1')) + \
            enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 5)
        assert cpu.Rregisters[0] == 0x42

    def test_bcdcmp_equal_sets_zero(self, cpu, memory):
        program = enc('MOV', ('reg', 'R0'), ('imm8', 0x42)) + \
            enc('MOV', ('reg', 'R1'), ('imm8', 0x42)) + \
            enc('BCDCMP', ('reg', 'R0'), ('reg', 'R1')) + \
            enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 3)
        assert cpu.zero_flag == True

    def test_bcdcmp_less_sets_carry(self, cpu, memory):
        program = enc('MOV', ('reg', 'R0'), ('imm8', 0x15)) + \
            enc('MOV', ('reg', 'R1'), ('imm8', 0x42)) + \
            enc('BCDCMP', ('reg', 'R0'), ('reg', 'R1')) + \
            enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 3)
        assert cpu.zero_flag == False
        assert cpu.flags[6] == 1  # Carry (borrow)

    def test_bcdadd_sets_bcd_carry_on_overflow(self, cpu, memory):
        # 95 + 38 = 133 decimal: masking to a byte must not suppress the
        # BCD carry flag (regression for masking-before-check ordering bug).
        program = enc('SED') + \
            enc('MOV', ('reg', 'R0'), ('imm8', 0x95)) + \
            enc('MOV', ('reg', 'R1'), ('imm8', 0x38)) + \
            enc('BCDADD', ('reg', 'R0'), ('reg', 'R1')) + \
            enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 4)
        assert cpu.Rregisters[0] == 0x33
        assert cpu.flags_obj[10] == 1  # A (BCD carry)

    def test_bcda_sets_bcd_carry_on_overflow(self, cpu, memory):
        program = enc('SED') + \
            enc('CLA') + \
            enc('MOV', ('reg', 'R0'), ('imm8', 0x95)) + \
            enc('MOV', ('reg', 'R1'), ('imm8', 0x38)) + \
            enc('BCDA', ('reg', 'R0'), ('reg', 'R1')) + \
            enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 5)
        assert cpu.Rregisters[0] == 0x33
        assert cpu.flags_obj[10] == 1  # A (BCD carry)

    def test_bcdsub_sets_bcd_borrow_on_underflow(self, cpu, memory):
        # 15 - 42: a genuine borrow, must not be masked away to C=0.
        program = enc('SED') + \
            enc('MOV', ('reg', 'R0'), ('imm8', 0x15)) + \
            enc('MOV', ('reg', 'R1'), ('imm8', 0x42)) + \
            enc('BCDSUB', ('reg', 'R0'), ('reg', 'R1')) + \
            enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 4)
        assert cpu.flags_obj[10] == 1  # A (BCD borrow)

    def test_bcds_sets_bcd_borrow_on_underflow(self, cpu, memory):
        program = enc('SED') + \
            enc('CLA') + \
            enc('MOV', ('reg', 'R0'), ('imm8', 0x15)) + \
            enc('MOV', ('reg', 'R1'), ('imm8', 0x42)) + \
            enc('BCDS', ('reg', 'R0'), ('reg', 'R1')) + \
            enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 5)
        assert cpu.flags_obj[10] == 1  # A (BCD borrow)


class TestSblendAppliesToDrawing:
    """SBLEND previously decoded and stored a blend mode that no drawing
    primitive ever consulted (docs/TODO item 4) -- SWRITE and every SLINE/
    SRECT/SCIRC/CHAR/SFILL draw always overwrote raw, unblended values.
    These exercise the real opcode path end-to-end and confirm the active
    blend mode (additive, mode 1) is now actually applied by each primitive,
    while mode 0 (the default) still overwrites exactly as before."""

    def test_sblend_default_mode_still_overwrites(self, cpu, memory):
        program = enc('VX', ('imm8', 10)) + enc('VY', ('imm8', 10)) + \
            enc('SWRITE', ('imm8', 100)) + \
            enc('SWRITE', ('imm8', 50)) + \
            enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 4)
        assert cpu.gfx.screen[10, 10] == 50

    def test_sblend_additive_mode_applies_to_swrite(self, cpu, memory):
        # existing=100, new=50, alpha=255 -> 100 + ((50*255+127)//255) = 150
        program = enc('VX', ('imm8', 10)) + enc('VY', ('imm8', 10)) + \
            enc('SWRITE', ('imm8', 100)) + \
            enc('SBLEND', ('imm8', 1)) + \
            enc('SWRITE', ('imm8', 50)) + \
            enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 5)
        assert cpu.gfx.screen[10, 10] == 150

    def test_sblend_additive_mode_applies_to_sfill(self, cpu, memory):
        program = enc('VL', ('imm8', 1)) + \
            enc('SFILL', ('imm8', 64)) + \
            enc('SBLEND', ('imm8', 1)) + \
            enc('SFILL', ('imm8', 16)) + \
            enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 4)
        layer1 = cpu.gfx.get_layer_buffer_by_num(1)
        assert bool((layer1 == 80).all())

    def test_sblend_additive_mode_applies_to_sline(self, cpu, memory):
        program = enc('VX', ('imm8', 5)) + enc('VY', ('imm8', 5)) + \
            enc('MOV', ('reg', 'VC'), ('imm8', 100)) + \
            enc('SLINE', ('imm8', 5), ('imm8', 5)) + \
            enc('SBLEND', ('imm8', 1)) + \
            enc('MOV', ('reg', 'VC'), ('imm8', 50)) + \
            enc('SLINE', ('imm8', 5), ('imm8', 5)) + \
            enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 7)
        assert cpu.gfx.screen[5, 5] == 150

    def test_sblend_additive_mode_applies_to_srect(self, cpu, memory):
        program = enc('VX', ('imm8', 5)) + enc('VY', ('imm8', 5)) + \
            enc('MOV', ('reg', 'VC'), ('imm8', 100)) + \
            enc('SRECT', ('imm8', 8), ('imm8', 8), ('imm8', 1)) + \
            enc('SBLEND', ('imm8', 1)) + \
            enc('MOV', ('reg', 'VC'), ('imm8', 50)) + \
            enc('SRECT', ('imm8', 8), ('imm8', 8), ('imm8', 1)) + \
            enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 7)
        assert cpu.gfx.screen[6, 6] == 150

    def test_sblend_additive_mode_applies_to_scirc(self, cpu, memory):
        program = enc('VX', ('imm8', 20)) + enc('VY', ('imm8', 20)) + \
            enc('MOV', ('reg', 'VC'), ('imm8', 100)) + \
            enc('SCIRC', ('imm8', 4), ('imm8', 1)) + \
            enc('SBLEND', ('imm8', 1)) + \
            enc('MOV', ('reg', 'VC'), ('imm8', 50)) + \
            enc('SCIRC', ('imm8', 4), ('imm8', 1)) + \
            enc('HLT')
        memory.load_program(program)
        run_cpu_cycles(cpu, 7)
        # The midpoint circle-fill algorithm can touch the same pixel more
        # than once per draw, so an exact additive sum isn't guaranteed --
        # but a raw (unblended) overwrite would leave this at exactly 50.
        # Additive blending only ever moves a pixel up toward 255.
        assert cpu.gfx.screen[20, 20] > 100
