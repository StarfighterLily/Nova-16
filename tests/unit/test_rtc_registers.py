"""Unit tests for RTC register support across CPU, assembler, and disassembler."""

from nova_assembler import Assembler
from nova_disassembler import create_reverse_maps, disassemble_instruction_new


def test_rtc_registers_round_trip_through_cpu_and_tooling(cpu, monkeypatch, tmp_path):
    rtc_seconds = 0x12345678
    monkeypatch.setattr(cpu, "rtc_time_source", lambda: cpu.RTC_EPOCH_UNIX + rtc_seconds)

    assert cpu.reg_index(0xBE) == (0, 'C0')
    assert cpu.reg_index(0xBF) == (0, 'C1')
    assert cpu.c0 == 0x5678
    assert cpu.c1 == 0x1234
    assert cpu._get_operand_value('C0', 0) == 0x5678
    assert cpu._get_operand_value('C1', 0) == 0x1234

    cpu._set_operand_value('C0', 0, 0xAAAA)
    cpu._set_operand_value('C1', 0, 0xBBBB)
    assert cpu.c0 == 0x5678
    assert cpu.c1 == 0x1234

    cpu.memory.write_byte(0x0000, 0x06)  # MOV
    cpu.memory.write_byte(0x0001, 0x00)  # reg, reg
    cpu.memory.write_byte(0x0002, 0xF1)  # P0
    cpu.memory.write_byte(0x0003, 0xBE)  # C0
    cpu.memory.write_byte(0x0004, 0x06)  # MOV
    cpu.memory.write_byte(0x0005, 0x00)  # reg, reg
    cpu.memory.write_byte(0x0006, 0xF2)  # P1
    cpu.memory.write_byte(0x0007, 0xBF)  # C1
    cpu.memory.write_byte(0x0008, 0x00)  # HLT

    cpu.step()
    cpu.step()
    assert cpu.Pregisters[0] == 0x5678
    assert cpu.Pregisters[1] == 0x1234

    source = tmp_path / "rtc_registers.asm"
    source.write_text(
        "ORG 0x1000\n"
        "MOV P0, C0\n"
        "MOV P1, C1\n"
        "HLT\n",
        encoding='ascii',
    )

    assembler = Assembler()
    assert assembler.assemble(str(source)) is True

    binary = source.with_suffix('.bin').read_bytes()
    assert 0xBE in binary
    assert 0xBF in binary

    opcode_map, register_map = create_reverse_maps()
    mnemonic0, operands0, size0 = disassemble_instruction_new(binary, 0, opcode_map, register_map)
    mnemonic1, operands1, size1 = disassemble_instruction_new(binary, size0, opcode_map, register_map)

    assert (mnemonic0, operands0) == ('MOV', ['P0', 'C0'])
    assert (mnemonic1, operands1) == ('MOV', ['P1', 'C1'])
    assert size1 > 0