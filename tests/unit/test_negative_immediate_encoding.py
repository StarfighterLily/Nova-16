"""
Regression tests for negative decimal-literal immediate encoding.

OperandClassifier.classify_operand() previously classified a negative decimal
value as IMMEDIATE8 whenever it fit in a signed byte (-128..-1), matching the
same range check used for positive values. IMMEDIATE8 encodes a single raw
byte with no sign-extension step at decode time, so e.g. "MOV P0, -2" wrote
only 0xFE into the instruction stream. When that single byte was loaded into
a 16-bit P register, the missing high byte meant P0 became 254 (0x00FE)
instead of the correct two's-complement 65534 (0xFFFE) - any negative literal
moved into a 16-bit register was silently corrupted.

Register writes already mask down to the destination's actual width, so
always encoding negative literals as IMMEDIATE16 is correct for both 8-bit
(truncates to the same bit pattern) and 16-bit (preserves the sign) targets.
"""

import os
import tempfile

import pytest

from nova_assembler import Assembler, OperandClassifier, OperandType
from opcodes import opcodes as opcode_definitions


class TestOperandClassifier:
    def setup_method(self):
        instruction_set = Assembler().instruction_set
        self.classifier = OperandClassifier(instruction_set)

    @pytest.mark.parametrize("value", ["-1", "-2", "-128"])
    def test_negative_decimal_always_classified_as_immediate16(self, value):
        assert self.classifier.classify_operand(value) == OperandType.IMMEDIATE16

    @pytest.mark.parametrize("value", ["0", "1", "5", "127"])
    def test_small_positive_decimal_still_classified_as_immediate8(self, value):
        assert self.classifier.classify_operand(value) == OperandType.IMMEDIATE8

    def test_large_negative_decimal_still_classified_as_immediate16(self):
        assert self.classifier.classify_operand("-200") == OperandType.IMMEDIATE16


@pytest.mark.assembler
class TestNegativeImmediateAssembly:
    """Assemble and execute MOV with a negative immediate against both an
    8-bit (R) and 16-bit (P) destination to confirm the runtime value is
    correct in both cases."""

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
