"""Unit tests for the BANK register (bank-switched memory expansion)."""

from nova_assembler import Assembler
from nova_disassembler import create_reverse_maps, disassemble_instruction_new
from tests.conftest import opcode_value


def test_bank_register_code_mapping(cpu):
    assert cpu.reg_index(opcode_value('BANK')) == (0, 'BANK')


def test_mov_bank_immediate(cpu):
    # MOV BANK, 3  (dest=register mode, src=imm8 mode)
    cpu.memory.write_byte(0x0000, 0x06)              # MOV
    cpu.memory.write_byte(0x0001, 0x04)               # mode byte: op1=register, op2=imm8
    cpu.memory.write_byte(0x0002, opcode_value('BANK'))
    cpu.memory.write_byte(0x0003, 3)
    cpu.memory.write_byte(0x0004, 0x00)               # HLT

    cpu.step()
    assert cpu.memory.current_bank == 3


def test_mov_bank_from_register(cpu):
    # MOV R0, 7 ; MOV BANK, R0
    cpu.memory.write_byte(0x0000, 0x06)               # MOV
    cpu.memory.write_byte(0x0001, 0x04)               # op1=register, op2=imm8
    cpu.memory.write_byte(0x0002, opcode_value('R0'))
    cpu.memory.write_byte(0x0003, 7)

    cpu.memory.write_byte(0x0004, 0x06)               # MOV
    cpu.memory.write_byte(0x0005, 0x00)               # op1=register, op2=register
    cpu.memory.write_byte(0x0006, opcode_value('BANK'))
    cpu.memory.write_byte(0x0007, opcode_value('R0'))
    cpu.memory.write_byte(0x0008, 0x00)               # HLT

    cpu.step()
    cpu.step()
    assert cpu.memory.current_bank == 7


def test_mov_reads_bank_register(cpu):
    cpu.memory.set_bank(9)

    # MOV R0, BANK
    cpu.memory.write_byte(0x0000, 0x06)               # MOV
    cpu.memory.write_byte(0x0001, 0x00)               # op1=register, op2=register
    cpu.memory.write_byte(0x0002, opcode_value('R0'))
    cpu.memory.write_byte(0x0003, opcode_value('BANK'))
    cpu.memory.write_byte(0x0004, 0x00)               # HLT

    cpu.step()
    assert cpu.Rregisters[0] == 9


def test_bank_clamps_above_range(cpu):
    # MOV BANK, 200 -- imm8 can't exceed 255, but 200 alone still clamps to 15
    cpu.memory.write_byte(0x0000, 0x06)               # MOV
    cpu.memory.write_byte(0x0001, 0x04)               # op1=register, op2=imm8
    cpu.memory.write_byte(0x0002, opcode_value('BANK'))
    cpu.memory.write_byte(0x0003, 200)
    cpu.memory.write_byte(0x0004, 0x00)               # HLT

    cpu.step()
    assert cpu.memory.current_bank == 15


def test_bank_register_assembles_and_disassembles(tmp_path):
    source = tmp_path / "bank_register.asm"
    source.write_text(
        "ORG 0x1000\n"
        "MOV BANK, 5\n"
        "MOV R0, BANK\n"
        "NOP\n"
        "HLT\n",
        encoding='ascii',
    )

    assembler = Assembler()
    assert assembler.assemble(str(source)) is True

    binary = source.with_suffix('.bin').read_bytes()
    assert opcode_value('BANK') in binary

    opcode_map, register_map = create_reverse_maps()

    mnemonic0, operands0, size0 = disassemble_instruction_new(binary, 0, opcode_map, register_map)
    assert (mnemonic0, operands0) == ('MOV', ['BANK', '0x05'])

    mnemonic1, operands1, size1 = disassemble_instruction_new(binary, size0, opcode_map, register_map)
    assert (mnemonic1, operands1) == ('MOV', ['R0', 'BANK'])

    # Regression check: BANK now sits at 0xC2, well clear of NOP's 0xFF,
    # so NOP disassembly must be completely unaffected.
    offset = size0 + size1
    mnemonic2, operands2, size2 = disassemble_instruction_new(binary, offset, opcode_map, register_map)
    assert (mnemonic2, operands2) == ('NOP', [])
