import pytest
import os
import tempfile
from nova_assembler import Assembler, InstructionSet


@pytest.mark.assembler
def test_include_directive():
    """Test INCLUDE directive"""
    assembler = Assembler()
    success = assembler.assemble("tests/integration/include_test.asm")
    assert success
    assert os.path.exists("tests/integration/include_test.bin")
    assert os.path.exists("tests/integration/include_test.sym")

    # Check symbol table contains symbols from included file
    with open("tests/integration/include_test.sym", 'r') as f:
        sym_content = f.read()
        assert "SUB_DATA" in sym_content
        assert "SUB_LABEL" in sym_content
        assert "MAIN_DATA" in sym_content


@pytest.mark.assembler
def test_conditional_assembly():
    """Test conditional assembly directives"""
    assembler = Assembler()
    success = assembler.assemble("tests/integration/conditional_test.asm")
    assert success
    assert os.path.exists("tests/integration/conditional_test.bin")

    # Check that DEBUG_MSG is included since DEBUG is defined
    with open("tests/integration/conditional_test.sym", 'r') as f:
        sym_content = f.read()
        assert "DEBUG_MSG" in sym_content
        assert "TEST_DATA" in sym_content  # Since RELEASE not defined


@pytest.mark.assembler
def test_ds_directive():
    """Test DS directive for defining space"""
    assembler = Assembler()
    success = assembler.assemble("tests/integration/ds_test.asm")
    assert success
    assert os.path.exists("tests/integration/ds_test.bin")

    # Check binary size: 10 (DS) + 3 (DB) + 5 (DS) + 5 (MOV R0, BUFFER) + 1 (HLT) = 24 bytes
    with open("tests/integration/ds_test.bin", 'rb') as f:
        data = f.read()
        assert len(data) == 24
        # First 10 bytes should be 0 (DS 10)
        assert data[:10] == b'\x00' * 10
        # Next 3 bytes: 1,2,3
        assert data[10:13] == b'\x01\x02\x03'
        # Next 5 bytes: 0 (DS 5)
        assert data[13:18] == b'\x00' * 5


@pytest.mark.assembler
class TestDualPurposeRegisterInstructions:
    """Regression: InstructionSet._load_opcodes() classified every mnemonic
    that also serves as a register code (SA, SF, SV, SW, VM, VL, TT, TM, TC,
    TS, VX, VY, plus register-only names like BANK/C0/C1/MX/MY/MB/SP/FP/VC)
    as register-only, never populating self.instructions for any of them --
    even though opcodes.py, core/exec.py's HANDLER_INSTRUCTIONS, and
    core/exec_handlers.py all implement SA/SF/SV/SW/VM/VL/TT/TM/TC/TS/VX/VY
    as genuine, documented one-operand instructions (see
    docs/nova16_instruction_reference.md).

    Assembler.first_pass/second_pass then unconditionally skipped any line
    whose instruction name appeared in InstructionSet.registers, regardless
    of whether it had operands. So a line like ``SW 5`` used as a standalone
    instruction (as opposed to a MOV target, e.g. ``MOV SW, 5``) was
    silently dropped -- zero bytes emitted, zero error reported, and the
    rest of the program shifted underneath it with no warning.

    Fixed by tracking which register-code mnemonics also have a real CPU
    handler (InstructionSet.DUAL_PURPOSE_INSTRUCTIONS) and only treating a
    line as a no-op register reference when the mnemonic has no such
    handler-backed instruction form.
    """

    def test_special_register_mnemonics_are_not_silently_dropped(self, tmp_path):
        asm_path = tmp_path / "special_regs.asm"
        asm_path.write_text(
            "ORG 0x0000\n"
            "SA 0x1234\n"
            "SF 5\n"
            "SV 6\n"
            "SW 7\n"
            "VM 1\n"
            "VL 2\n"
            "VX 10\n"
            "VY 20\n"
            "TT 1\n"
            "TM 2\n"
            "TC 3\n"
            "TS 4\n"
            "HLT\n"
        )
        assembler = Assembler(log=None)
        success = assembler.assemble(str(asm_path))
        assert success, f"Assembly failed: {assembler.errors}"

        bin_path = tmp_path / "special_regs.bin"
        data = bin_path.read_bytes()
        # SA's operand (0x1234) needs a 16-bit immediate (opcode+mode+2 bytes = 4);
        # the other 11 instructions take an 8-bit immediate (opcode+mode+1 byte = 3);
        # HLT is a single opcode byte with no operand.
        assert len(data) == 4 + 11 * 3 + 1, (
            f"Expected all 12 special-register instructions to be emitted, got {len(data)} bytes: {data.hex()}"
        )
        # Every opcode byte must appear in program order with nothing dropped.
        expected_opcodes = [0xDD, 0xDE, 0xDF, 0xE0, 0xE1, 0xE2, 0xFD, 0xFE, 0xE3, 0xE4, 0xE5, 0xE6, 0x00]
        actual_opcodes = []
        i = 0
        sizes = {0xDD: 4, 0xDE: 3, 0xDF: 3, 0xE0: 3, 0xE1: 3, 0xE2: 3, 0xFD: 3, 0xFE: 3,
                 0xE3: 3, 0xE4: 3, 0xE5: 3, 0xE6: 3, 0x00: 1}
        while i < len(data):
            op = data[i]
            actual_opcodes.append(op)
            i += sizes[op]
        assert actual_opcodes == expected_opcodes

    def test_special_register_opcode_form_executes_correctly_on_cpu(self, tmp_path):
        """End-to-end: text assembly -> binary -> real CPU execution must
        agree with the register-code ("MOV SW, 5") form's effect."""
        import nova_memory as mem
        import nova_cpu as cpu_mod
        import nova_gfx as gpu
        import nova_sound as sound
        import nova_keyboard as keyboard

        asm_path = tmp_path / "special_regs2.asm"
        asm_path.write_text(
            "ORG 0x0000\n"
            "SW 0x42\n"
            "VY 100\n"
            "HLT\n"
        )
        assembler = Assembler(log=None)
        assert assembler.assemble(str(asm_path))

        data = (tmp_path / "special_regs2.bin").read_bytes()

        memory = mem.Memory()
        graphics = gpu.GFX()
        sound_system = sound.NovaSound()
        keyboard_device = keyboard.NovaKeyboard()
        cpu = cpu_mod.CPU(memory, graphics, keyboard_device, sound_system)
        memory.load_program(list(data))
        for _ in range(10):
            if cpu.halted:
                break
            cpu.step()

        assert cpu.sound.SW == 0x42
        assert cpu.gfx.Vregisters[1] == 100

    def test_register_only_mnemonics_without_a_cpu_handler_still_skipped(self, tmp_path):
        """Sanity check: BANK/C0/C1/MX/MY/MB/SP/FP/VC have no standalone
        opcode handler in core/exec.py's HANDLER_INSTRUCTIONS -- unlike the
        SA/SW/etc. family -- so they must remain register-only and keep
        being skipped as bare instruction lines rather than emitting bytes
        for an opcode the CPU can't execute."""
        instruction_set = InstructionSet()
        for name in ("BANK", "C0", "C1", "MX", "MY", "MB", "SP", "FP", "VC"):
            assert name in instruction_set.registers
            assert instruction_set.get_instruction_info(name) is None

    def test_dual_purpose_mnemonics_are_registered_both_ways(self, tmp_path):
        instruction_set = InstructionSet()
        for name in sorted(InstructionSet.DUAL_PURPOSE_INSTRUCTIONS):
            assert name in instruction_set.registers, f"{name} should still be usable as a register operand"
            assert instruction_set.get_instruction_info(name) is not None, f"{name} should also be a standalone instruction"