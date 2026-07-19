"""
Regression tests for negative decimal-literal immediate encoding in the
newer token-based assembler package (nova/assembler/).

nova/assembler/__init__.py explicitly advertises itself as a drop-in,
API-compatible replacement for the legacy nova_assembler.py (see
tests/unit/test_negative_immediate_encoding.py for the original bug this
mirrors). Its codegen.classify_operand() re-derived the imm8/imm16 decimal
cutoff as a plain "-128..127 -> imm8" range check instead of copying the
legacy assembler's explicit "any negative value -> imm16" rule, so e.g.
"SROL 0, -1" encoded the second operand as a raw 0xFF byte instead of the
two's-complement 0xFFFF word. Any negative literal moved into a 16-bit
context (or read directly as a raw immediate by handlers that don't mask,
like SROL/SROT/SSHFT's roll/shift amount) was silently corrupted.

Register writes already mask down to the destination's actual width, so
always encoding negative literals as IMMEDIATE16 is correct for both 8-bit
and 16-bit targets, exactly as in the legacy assembler.
"""

import glob
import os
import shutil
import tempfile

import pytest

from nova.assembler.codegen import classify_operand, OperandType
from nova.assembler import Assembler
from nova_assembler import Assembler as LegacyAssembler


class TestClassifyOperand:
    @pytest.mark.parametrize("value", ["-1", "-2", "-128", "-200"])
    def test_negative_decimal_always_classified_as_immediate16(self, value):
        assert classify_operand(value, {}) == OperandType.IMMEDIATE16

    @pytest.mark.parametrize("value", ["0", "1", "5", "127"])
    def test_small_positive_decimal_still_classified_as_immediate8(self, value):
        assert classify_operand(value, {}) == OperandType.IMMEDIATE8

    def test_large_positive_decimal_classified_as_immediate16(self):
        assert classify_operand("200", {}) == OperandType.IMMEDIATE16


@pytest.mark.assembler
class TestNegativeImmediateAssembly:
    """Assemble and execute against both an 8-bit (R) and 16-bit (P)
    destination to confirm the runtime value is correct in both cases."""

    def _assemble_and_load(self, memory, source: str):
        with tempfile.TemporaryDirectory() as tmpdir:
            asm_path = os.path.join(tmpdir, "prog.asm")
            with open(asm_path, "w") as f:
                f.write(source)
            assembler = Assembler(log=None)
            assert assembler.assemble(asm_path)
            with open(os.path.join(tmpdir, "prog.bin"), "rb") as f:
                machine_code = f.read()
        for offset, byte in enumerate(machine_code):
            memory.write_byte(offset, byte)

    def test_negative_immediate_into_16bit_register_preserves_sign(self, cpu, memory):
        self._assemble_and_load(memory, "MOV P0, -2\nHLT\n")
        cpu.pc = 0
        while not cpu.halted:
            cpu.step()
        assert cpu.Pregisters[0] == 0xFFFE

    def test_negative_immediate_into_8bit_register_matches_byte_pattern(self, cpu, memory):
        self._assemble_and_load(memory, "MOV R0, -2\nHLT\n")
        cpu.pc = 0
        while not cpu.halted:
            cpu.step()
        assert cpu.Rregisters[0] == 0xFE

    def test_srol_negative_amount_encodes_as_word_immediate(self, tmp_path):
        """SROL 0, -1 must encode its second operand as a 2-byte imm16
        (0xFFFF), matching nova_assembler.py byte-for-byte, not a 1-byte
        imm8 (0xFF)."""
        asm_path = tmp_path / "prog.asm"
        asm_path.write_text("SROL 0, -1\nHLT\n")
        assembler = Assembler(log=None)
        assert assembler.assemble(str(asm_path))
        with open(tmp_path / "prog.bin", "rb") as f:
            new_bytes = f.read()

        legacy_path = tmp_path / "prog_legacy.asm"
        legacy_path.write_text("SROL 0, -1\nHLT\n")
        legacy = LegacyAssembler(log=None)
        assert legacy.assemble(str(legacy_path))
        with open(tmp_path / "prog_legacy.bin", "rb") as f:
            legacy_bytes = f.read()

        assert new_bytes == legacy_bytes


@pytest.mark.assembler
class TestDualPurposeStandaloneInstructions:
    """Regression tests for a silent-drop bug in the new assembler's parser:
    SA/SF/SV/SW/VM/VL/TT/TM/TC/TS/VX/VY are simultaneously register operand
    tokens ("MOV SA, 5") and standalone one-operand instructions with real
    opcodes ("SA 5"). The lexer classified these as TokenKind.REGISTER
    unconditionally, so a standalone instruction line hit the parser's
    "must be a mnemonic" fallback and was silently discarded -- no error,
    the instruction just vanished from the assembled binary."""

    @pytest.mark.parametrize("mnemonic,operand", [
        ("SA", "0x1234"), ("SF", "0x1234"), ("SV", "5"), ("SW", "5"),
        ("VM", "1"), ("VL", "2"), ("TT", "5"), ("TM", "5"), ("TC", "5"),
        ("TS", "5"), ("VX", "5"), ("VY", "5"),
    ])
    def test_standalone_dual_purpose_instruction_not_dropped(self, tmp_path, mnemonic, operand):
        asm_path = tmp_path / "prog.asm"
        asm_path.write_text(f"{mnemonic} {operand}\nHLT\n")

        new = Assembler(log=None)
        assert new.assemble(str(asm_path))
        with open(tmp_path / "prog.bin", "rb") as f:
            new_bytes = f.read()

        legacy_path = tmp_path / "prog_legacy.asm"
        legacy_path.write_text(f"{mnemonic} {operand}\nHLT\n")
        legacy = LegacyAssembler(log=None)
        assert legacy.assemble(str(legacy_path))
        with open(tmp_path / "prog_legacy.bin", "rb") as f:
            legacy_bytes = f.read()

        # The instruction must actually be encoded (more than just the
        # trailing HLT byte), and must match the legacy assembler exactly.
        assert len(new_bytes) > 1
        assert new_bytes == legacy_bytes


@pytest.mark.assembler
class TestUnimplementedOpcodeRejected:
    """SMIX/SECHO/SREVERB/SFILTER have opcode bytes reserved in opcodes.py
    but no CPU handler (core/exec.py's HANDLER_INSTRUCTIONS has no entry for
    them). They must be rejected at assembly time with a clear error rather
    than either (a) silently vanishing from the output with no diagnostic,
    or (b) assembling successfully and crashing the CPU with a raw
    "Unknown opcode" exception at execution time."""

    @pytest.mark.parametrize("mnemonic", ["SMIX", "SECHO", "SREVERB", "SFILTER"])
    def test_rejected_at_assembly_time(self, tmp_path, mnemonic):
        asm_path = tmp_path / "prog.asm"
        asm_path.write_text(f"{mnemonic} R0\nHLT\n")

        new = Assembler(log=None)
        assert not new.assemble(str(asm_path))

        legacy_path = tmp_path / "prog_legacy.asm"
        legacy_path.write_text(f"{mnemonic} R0\nHLT\n")
        legacy = LegacyAssembler(log=None)
        assert not legacy.assemble(str(legacy_path))
        assert any("not implemented" in e for e in legacy.errors)


@pytest.mark.assembler
class TestAssemblerCorpusParity:
    """Differential test: every hand-written .asm program in asm/ that the
    legacy assembler can build must produce byte-identical output from the
    new nova/assembler package, since it claims API/behavioral compatibility.
    Catches any future drift between the two implementations, not just the
    negative-immediate case above."""

    @staticmethod
    def _asm_corpus():
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return sorted(glob.glob(os.path.join(repo_root, "asm", "*.asm")))

    @pytest.mark.parametrize("asm_file", _asm_corpus.__func__())
    def test_matches_legacy_assembler_output(self, asm_file, tmp_path):
        base = os.path.splitext(os.path.basename(asm_file))[0]
        legacy_copy = tmp_path / f"{base}_legacy.asm"
        new_copy = tmp_path / f"{base}_new.asm"
        shutil.copy(asm_file, legacy_copy)
        shutil.copy(asm_file, new_copy)

        legacy = LegacyAssembler(log=None)
        try:
            legacy_ok = legacy.assemble(str(legacy_copy))
        except Exception:
            legacy_ok = False
        if not legacy_ok:
            pytest.skip("legacy assembler cannot build this program (pre-existing, unrelated)")

        new = Assembler(log=None)
        new_ok = new.assemble(str(new_copy))
        assert new_ok, f"new assembler failed where legacy succeeded: {new.errors}"

        with open(legacy_copy.with_suffix(".bin"), "rb") as f:
            legacy_bytes = f.read()
        with open(new_copy.with_suffix(".bin"), "rb") as f:
            new_bytes = f.read()
        assert new_bytes == legacy_bytes
