"""
Nova-16 Instruction Handler Functions

Pure handler implementations for the parameterized Instruction table in
core/exec.py.  These functions replace the legacy BaseInstruction subclasses
from instructions.py for the converted opcodes.

Each handler receives (cpu, values) where values is a list of resolved
operand values.  Handlers return the computed result (or None for control-flow
instructions that manage pc directly).  Writeback and flag-setting are
handled by the Instruction.execute wrapper.
"""

import math

from core.fetch import calculate_memory_address


# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------

def _operand_width(cpu) -> int:
    """Return 8 if the destination operand is an R register, else 16."""
    if not cpu.operands:
        return 16
    dest = cpu.operands[0]
    if dest.is_register and dest.reg_type == 'R':
        return 8
    return 16


def _write_result(cpu, operand_index: int, value: int,
                  source_size: int = None) -> None:
    """Write a computed result back to the destination operand.

    For memory destinations, the write size is determined by the source
    operand when available (legacy behavior: MOV [mem], imm8 writes a byte,
    MOV [mem], imm16 writes a word).  Register destinations always use the
    register's natural width.
    """
    op = cpu.operands[operand_index]
    if op.is_register:
        # Fast path for R/P — see matching note in core/exec.py's
        # _resolve_single_operand. Masking mirrors RegisterFile's own
        # 'R'/'P' set dispatchers exactly (& 0xFF / & 0xFFFF).
        rt = op.reg_type
        if rt == 'R':
            cpu.Rregisters[op.reg_idx] = value & 0xFF
        elif rt == 'P':
            cpu.Pregisters[op.reg_idx] = value & 0xFFFF
        else:
            cpu.regfile.set(rt, op.reg_idx, value)
    elif op.is_memory:
        addr = calculate_memory_address(op, cpu.regfile)
        if source_size is None:
            # Infer source size from the source operand (operand 1 for binary,
            # operand 0 for unary).  Default to destination width if unavailable.
            src_op = cpu.operands[1] if len(cpu.operands) > 1 else cpu.operands[0]
            if src_op.is_immediate:
                source_size = src_op.size
            elif src_op.is_register and src_op.reg_type == 'R':
                source_size = 8
            else:
                source_size = 16
        # Use fast-path writes for performance (memory writes skip SCB notification overhead)
        if source_size == 8:
            cpu.memory.write_byte_fast(addr, value)
        else:
            cpu.memory.write_word_fast(addr, value)
    else:
        raise RuntimeError(f"Cannot write result to operand type: {op.type}")


def _set_arith_flags(cpu, result: int, op1: int, op2: int, width: int,
                     is_sub: bool = False, is_cmp: bool = False) -> None:
    """Set flags for arithmetic operations."""
    cpu.flags_obj.set_from_operation(result, op1, op2, width=width,
                                     is_subtraction=is_sub, is_cmp=is_cmp)


def _set_logic_flags(cpu, result: int, width: int) -> None:
    """Set flags for logic operations (AND, OR, XOR, NOT)."""
    if width == 8:
        cpu.flags_obj.set_from_8bit(result)
    else:
        cpu.flags_obj.set_from_16bit(result)
    cpu.flags_obj[6] = 0  # Carry
    cpu.flags_obj[2] = 0  # Overflow


def _sign_extend_16(value: int) -> int:
    """Sign-extend a 16-bit value."""
    return value if value < 0x8000 else value - 0x10000


def _to_signed_16(value: int) -> int:
    return value if value < 0x8000 else value - 0x10000


# ------------------------------------------------------------------------------
# Data Movement
# ------------------------------------------------------------------------------

def _mov(cpu, values) -> int:
    """MOV: dst = src."""
    result = values[1]
    _write_result(cpu, 0, result)
    return result


def _movz(cpu, values) -> int:
    """MOVZ: move if zero flag set."""
    if cpu.flags_obj.check_Z():
        result = values[1]
        _write_result(cpu, 0, result)
        _set_logic_flags(cpu, result, _operand_width(cpu))
        return result
    return values[1]


def _movnz(cpu, values) -> int:
    """MOVNZ: move if zero flag clear."""
    if not cpu.flags_obj.check_Z():
        result = values[1]
        _write_result(cpu, 0, result)
        _set_logic_flags(cpu, result, _operand_width(cpu))
        return result
    return values[1]


def _xchng(cpu, values) -> int:
    """XCHNG: swap two operand values."""
    _write_result(cpu, 0, values[1])
    _write_result(cpu, 1, values[0])
    _set_logic_flags(cpu, values[1], _operand_width(cpu))
    return values[1]


def _swap(cpu, values) -> int:
    """SWAP: swap high/low bytes of a 16-bit value."""
    result = ((values[0] & 0xFF) << 8) | ((values[0] >> 8) & 0xFF)
    _write_result(cpu, 0, result)
    _set_logic_flags(cpu, result, 16)
    return result


def _lea(cpu, values) -> int:
    """LEA: load effective address of source operand into destination."""
    op = cpu.operands[1]
    if op.is_memory:
        result = calculate_memory_address(op, cpu.regfile)
    else:
        result = values[1]
    _write_result(cpu, 0, result)
    _set_logic_flags(cpu, result, 16)
    return result


# ------------------------------------------------------------------------------
# Arithmetic
# ------------------------------------------------------------------------------

def _add(cpu, values) -> int:
    """ADD: dst + src."""
    result = values[0] + values[1]
    _write_result(cpu, 0, result)
    width = _operand_width(cpu)
    _set_arith_flags(cpu, result, values[0], values[1], width, is_sub=False)
    return result


def _sub(cpu, values) -> int:
    """SUB: dst - src."""
    result = values[0] - values[1]
    _write_result(cpu, 0, result)
    width = _operand_width(cpu)
    _set_arith_flags(cpu, result, values[0], values[1], width, is_sub=True)
    return result


def _mul(cpu, values) -> int:
    """MUL: dst * src."""
    result = values[0] * values[1]
    _write_result(cpu, 0, result)
    width = _operand_width(cpu)
    _set_arith_flags(cpu, result, values[0], values[1], width, is_sub=False)
    return result


def _div(cpu, values) -> int:
    """DIV: dst / src, remainder stored in P3."""
    if values[1] == 0:
        raise RuntimeError("Division by zero")
    quotient = values[0] // values[1]
    remainder = values[0] % values[1]
    _write_result(cpu, 0, quotient)
    cpu.regfile.set('P', 3, remainder & 0xFFFF)
    width = _operand_width(cpu)
    _set_arith_flags(cpu, quotient, values[0], values[1], width, is_sub=False)
    return quotient


def _mod(cpu, values) -> int:
    """MOD: dst % src."""
    if values[1] == 0:
        raise RuntimeError("Modulo by zero")
    result = values[0] % values[1]
    _write_result(cpu, 0, result)
    width = _operand_width(cpu)
    _set_arith_flags(cpu, result, values[0], values[1], width, is_sub=False)
    return result


def _inc(cpu, values) -> int:
    """INC: dst + 1."""
    result = values[0] + 1
    _write_result(cpu, 0, result)
    width = _operand_width(cpu)
    _set_arith_flags(cpu, result, values[0], 1, width, is_sub=False)
    return result


def _dec(cpu, values) -> int:
    """DEC: dst - 1."""
    result = values[0] - 1
    _write_result(cpu, 0, result)
    width = _operand_width(cpu)
    _set_arith_flags(cpu, result, values[0], 1, width, is_sub=True)
    return result


def _neg(cpu, values) -> int:
    """NEG: -dst."""
    result = -values[0]
    _write_result(cpu, 0, result)
    width = _operand_width(cpu)
    _set_arith_flags(cpu, result, 0, values[0], width, is_sub=True)
    return result


def _abs(cpu, values) -> int:
    """ABS: absolute value."""
    width = _operand_width(cpu)
    if width == 8:
        signed = values[0] if values[0] < 0x80 else values[0] - 0x100
    else:
        signed = _to_signed_16(values[0])
    result = abs(signed)
    _write_result(cpu, 0, result)
    _set_arith_flags(cpu, result, 0, values[0], width, is_sub=False)
    return result


def _adc(cpu, values) -> int:
    """ADC: dst + src + carry.

    The overflow formula in ``set_from_operation`` compares the sign bits of
    op1/op2 to the sign bit of the (unmasked) result. Folding carry into op2
    before that comparison (op2 + carry) can flip op2's sign bit purely from
    the carry addition — e.g. width=8, src=0x7F, carry=1 gives op2=0x80 —
    which corrupts the overflow flag even though the arithmetic result itself
    stays correct. Pass the raw src so only genuine sign bits are compared;
    ``result`` already has carry folded in exactly.
    """
    carry = 1 if cpu.flags_obj.check_C() else 0
    result = values[0] + values[1] + carry
    _write_result(cpu, 0, result)
    width = _operand_width(cpu)
    _set_arith_flags(cpu, result, values[0], values[1], width, is_sub=False)
    return result


def _sbc(cpu, values) -> int:
    """SBC: dst - src - carry. See _adc for why raw src (not src + carry) is
    passed to the overflow formula."""
    carry = 1 if cpu.flags_obj.check_C() else 0
    result = values[0] - values[1] - carry
    _write_result(cpu, 0, result)
    width = _operand_width(cpu)
    _set_arith_flags(cpu, result, values[0], values[1], width, is_sub=True)
    return result


def _mulh(cpu, values) -> int:
    """MULH: high 16 bits of 32-bit product."""
    result = (values[0] * values[1]) >> 16
    _write_result(cpu, 0, result)
    _set_arith_flags(cpu, result, values[0], values[1], 16, is_sub=False)
    return result


def _divh(cpu, values) -> int:
    """DIVH: 32-bit divide using dest as high word and P3 as low word."""
    if values[1] == 0:
        raise RuntimeError("Division by zero")
    dividend = (values[0] << 16) | (cpu.regfile.get('P', 3) & 0xFFFF)
    quotient = dividend // values[1]
    remainder = dividend % values[1]
    _write_result(cpu, 0, quotient & 0xFFFF)
    cpu.regfile.set('P', 3, remainder & 0xFFFF)
    _set_arith_flags(cpu, quotient & 0xFFFF, values[0], values[1], 16, is_sub=False)
    return quotient & 0xFFFF


def _min(cpu, values) -> int:
    """MIN: minimum of dst and src."""
    result = min(values[0], values[1])
    _write_result(cpu, 0, result)
    _set_arith_flags(cpu, result, values[0], values[1], _operand_width(cpu), is_sub=False)
    return result


def _max(cpu, values) -> int:
    """MAX: maximum of dst and src."""
    result = max(values[0], values[1])
    _write_result(cpu, 0, result)
    _set_arith_flags(cpu, result, values[0], values[1], _operand_width(cpu), is_sub=False)
    return result


# ------------------------------------------------------------------------------
# Bitwise / Shift
# ------------------------------------------------------------------------------

def _and(cpu, values) -> int:
    """AND: dst & src."""
    result = values[0] & values[1]
    _write_result(cpu, 0, result)
    width = _operand_width(cpu)
    _set_logic_flags(cpu, result, width)
    return result


def _or(cpu, values) -> int:
    """OR: dst | src."""
    result = values[0] | values[1]
    _write_result(cpu, 0, result)
    width = _operand_width(cpu)
    _set_logic_flags(cpu, result, width)
    return result


def _xor(cpu, values) -> int:
    """XOR: dst ^ src."""
    result = values[0] ^ values[1]
    _write_result(cpu, 0, result)
    width = _operand_width(cpu)
    _set_logic_flags(cpu, result, width)
    return result


def _not(cpu, values) -> int:
    """NOT: bitwise NOT of dst."""
    width = _operand_width(cpu)
    mask = 0xFF if width == 8 else 0xFFFF
    result = (~values[0]) & mask
    _write_result(cpu, 0, result)
    _set_logic_flags(cpu, result, width)
    return result


def _shl(cpu, values) -> int:
    """SHL: logical shift left."""
    width = _operand_width(cpu)
    mask = 0xFF if width == 8 else 0xFFFF
    shift = values[1] & 0x1F
    result = (values[0] << shift) & mask if shift < width else 0
    _write_result(cpu, 0, result)
    _set_logic_flags(cpu, result, width)
    return result


def _shr(cpu, values) -> int:
    """SHR: logical shift right."""
    width = _operand_width(cpu)
    shift = values[1] & 0x1F
    result = values[0] >> shift if shift < width else 0
    _write_result(cpu, 0, result)
    _set_logic_flags(cpu, result, width)
    return result


def _sar(cpu, values) -> int:
    """SAR: arithmetic shift right."""
    width = _operand_width(cpu)
    shift = values[1] & 0x0F
    if width == 8:
        signed = values[0] if values[0] < 0x80 else values[0] - 0x100
        result = (signed >> shift) & 0xFF
    else:
        signed = _to_signed_16(values[0])
        result = (signed >> shift) & 0xFFFF
    _write_result(cpu, 0, result)
    _set_logic_flags(cpu, result, width)
    return result


def _sal(cpu, values) -> int:
    """SAL: shift arithmetic left (same as SHL)."""
    return _shl(cpu, values)


def _rol(cpu, values) -> int:
    """ROL: rotate left."""
    width = _operand_width(cpu)
    mask = 0xFF if width == 8 else 0xFFFF
    bits = width
    rotate = values[1] & 0x0F
    rotate %= bits if bits else 1
    result = ((values[0] << rotate) | (values[0] >> (bits - rotate))) & mask
    _write_result(cpu, 0, result)
    _set_logic_flags(cpu, result, width)
    return result


def _ror(cpu, values) -> int:
    """ROR: rotate right."""
    width = _operand_width(cpu)
    mask = 0xFF if width == 8 else 0xFFFF
    bits = width
    rotate = values[1] & 0x0F
    rotate %= bits if bits else 1
    result = ((values[0] >> rotate) | (values[0] << (bits - rotate))) & mask
    _write_result(cpu, 0, result)
    _set_logic_flags(cpu, result, width)
    return result


def _rcl(cpu, values) -> int:
    """RCL: rotate left through carry."""
    width = _operand_width(cpu)
    mask = 0xFF if width == 8 else 0xFFFF
    result = values[0]
    rotate = values[1] & 0x0F
    for _ in range(rotate):
        carry_out = (result & (1 << (width - 1))) != 0
        result = ((result << 1) & mask) | cpu.flags_obj[6]
        cpu.flags_obj[6] = 1 if carry_out else 0
    _write_result(cpu, 0, result)
    return result


def _rcr(cpu, values) -> int:
    """RCR: rotate right through carry."""
    width = _operand_width(cpu)
    mask = 0xFF if width == 8 else 0xFFFF
    msb = 1 << (width - 1)
    result = values[0]
    rotate = values[1] & 0x0F
    for _ in range(rotate):
        carry_out = (result & 1) != 0
        result = (result >> 1) | (cpu.flags_obj[6] * msb)
        cpu.flags_obj[6] = 1 if carry_out else 0
    _write_result(cpu, 0, result)
    return result


# ------------------------------------------------------------------------------
# Bit Test / Modify
# ------------------------------------------------------------------------------

def _btst(cpu, values) -> int:
    """BTST: test bit, set zero flag if bit is clear."""
    bit_pos = values[1] & 0x0F
    bit_set = (values[0] & (1 << bit_pos)) != 0
    cpu.flags_obj[7] = 0 if bit_set else 1
    return values[1]


def _bset(cpu, values) -> int:
    """BSET: set bit."""
    bit_pos = values[1] & 0x0F
    result = values[0] | (1 << bit_pos)
    _write_result(cpu, 0, result)
    _set_logic_flags(cpu, result, _operand_width(cpu))
    return result


def _bclr(cpu, values) -> int:
    """BCLR: clear bit."""
    bit_pos = values[1] & 0x0F
    width = _operand_width(cpu)
    mask = 0xFF if width == 8 else 0xFFFF
    result = values[0] & (~(1 << bit_pos) & mask)
    _write_result(cpu, 0, result)
    _set_logic_flags(cpu, result, width)
    return result


def _bflip(cpu, values) -> int:
    """BFLIP: flip bit."""
    bit_pos = values[1] & 0x0F
    result = values[0] ^ (1 << bit_pos)
    _write_result(cpu, 0, result)
    _set_logic_flags(cpu, result, _operand_width(cpu))
    return result


# ------------------------------------------------------------------------------
# Comparison
# ------------------------------------------------------------------------------

def _cmp(cpu, values) -> int:
    """CMP: compare dst and src, set flags only."""
    result = values[0] - values[1]
    width = _operand_width(cpu)
    _set_arith_flags(cpu, result, values[0], values[1], width, is_sub=True, is_cmp=True)
    cpu._last_operation_was_cmp = True
    return result


# ------------------------------------------------------------------------------
# Stack
# ------------------------------------------------------------------------------

def _push_pop_width(op) -> int:
    """Return 8 or 16 — the natural width of a PUSH/POP operand.

    R registers and imm8 are byte-sized; P registers and imm16 are
    word-sized. Memory operands default to word width, matching
    ``_write_result``'s default for single-operand instructions (it infers
    source size from ``cpu.operands[0]`` when there's no second operand).
    """
    if op.is_register:
        return 16 if op.reg_type == 'P' else 8
    if op.is_immediate:
        return op.size
    return 16


def _push(cpu, values) -> int:
    """PUSH: push value onto stack."""
    sp = cpu.regfile.get('P', 8)
    op = cpu.operands[0]
    if _push_pop_width(op) == 16:
        sp = (sp - 2) & 0xFFFF
        cpu.memory.write_word_fast(sp, values[0] & 0xFFFF)
    else:
        sp = (sp - 1) & 0xFFFF
        cpu.memory.write_byte_fast(sp, values[0] & 0xFF)
    cpu.regfile.set('P', 8, sp)
    return values[0]


def _pop(cpu, values) -> int:
    """POP: pop value from stack."""
    sp = cpu.regfile.get('P', 8)
    op = cpu.operands[0]
    if _push_pop_width(op) == 16:
        if sp >= 0xFFFE:
            raise RuntimeError(f"Stack underflow: SP=0x{sp:04X}")
        value = cpu.memory.read_word_fast(sp)
        sp = (sp + 2) & 0xFFFF
    else:
        if sp >= 0xFFFF:
            raise RuntimeError(f"Stack underflow: SP=0x{sp:04X}")
        value = cpu.memory.read_byte_fast(sp)
        sp = (sp + 1) & 0xFFFF
    cpu.regfile.set('P', 8, sp)
    _write_result(cpu, 0, value)
    return value


def _enter(cpu, values) -> int:
    """ENTER: create stack frame."""
    sp = cpu.regfile.get('P', 8)
    sp = (sp - 2) & 0xFFFF
    cpu.memory.write_word_fast(sp, cpu.regfile.get('P', 9))
    cpu.regfile.set('P', 9, sp)
    sp = (sp - values[0]) & 0xFFFF
    cpu.regfile.set('P', 8, sp)
    return sp


def _leave(cpu) -> int:
    """LEAVE: destroy stack frame."""
    fp = cpu.regfile.get('P', 9)
    old_fp = cpu.memory.read_word_fast(fp)
    cpu.regfile.set('P', 8, (fp + 2) & 0xFFFF)
    cpu.regfile.set('P', 9, old_fp)
    return old_fp


# ------------------------------------------------------------------------------
# Control Flow
# ------------------------------------------------------------------------------

def _jmp(cpu, values) -> None:
    """JMP: unconditional jump."""
    cpu.pc = values[0] & 0xFFFF


def _jz(cpu, values) -> None:
    """JZ: jump if zero."""
    if cpu.flags_obj.check_Z():
        cpu.pc = values[0] & 0xFFFF


def _jnz(cpu, values) -> None:
    """JNZ: jump if not zero."""
    if not cpu.flags_obj.check_Z():
        cpu.pc = values[0] & 0xFFFF


def _jo(cpu, values) -> None:
    """JO: jump if overflow."""
    if cpu.flags_obj.check_O():
        cpu.pc = values[0] & 0xFFFF


def _jno(cpu, values) -> None:
    """JNO: jump if no overflow."""
    if not cpu.flags_obj.check_O():
        cpu.pc = values[0] & 0xFFFF


def _jc(cpu, values) -> None:
    """JC: jump if carry."""
    if cpu.flags_obj.check_C():
        cpu.pc = values[0] & 0xFFFF


def _jnc(cpu, values) -> None:
    """JNC: jump if no carry."""
    if not cpu.flags_obj.check_C():
        cpu.pc = values[0] & 0xFFFF


def _js(cpu, values) -> None:
    """JS: jump if sign."""
    if cpu.flags_obj.check_S():
        cpu.pc = values[0] & 0xFFFF


def _jns(cpu, values) -> None:
    """JNS: jump if no sign."""
    if not cpu.flags_obj.check_S():
        cpu.pc = values[0] & 0xFFFF


def _jgt(cpu, values) -> None:
    """JGT: jump if signed greater than."""
    lt = cpu.flags_obj.check_O() != cpu.flags_obj.check_S()
    if not lt and not cpu.flags_obj.check_Z():
        cpu.pc = values[0] & 0xFFFF


def _jlt(cpu, values) -> None:
    """JLT: jump if signed less than."""
    lt = cpu.flags_obj.check_O() != cpu.flags_obj.check_S()
    if lt:
        cpu.pc = values[0] & 0xFFFF


def _jge(cpu, values) -> None:
    """JGE: jump if signed greater or equal."""
    lt = cpu.flags_obj.check_O() != cpu.flags_obj.check_S()
    if not lt:
        cpu.pc = values[0] & 0xFFFF


def _jle(cpu, values) -> None:
    """JLE: jump if signed less or equal."""
    lt = cpu.flags_obj.check_O() != cpu.flags_obj.check_S()
    if cpu.flags_obj.check_Z() or lt:
        cpu.pc = values[0] & 0xFFFF


def _br(cpu, values) -> None:
    """BR: relative branch."""
    offset = values[1] if len(values) > 1 else values[0]
    if offset & 0x8000:
        offset -= 0x10000
    cpu.pc = (cpu.pc + offset) & 0xFFFF


def _brz(cpu, values) -> None:
    """BRZ: relative branch if zero."""
    if cpu.flags_obj.check_Z():
        offset = values[0]
        if offset & 0x8000:
            offset -= 0x10000
        cpu.pc = (cpu.pc + offset) & 0xFFFF


def _brnz(cpu, values) -> None:
    """BRNZ: relative branch if not zero."""
    if not cpu.flags_obj.check_Z():
        offset = values[0]
        if offset & 0x8000:
            offset -= 0x10000
        cpu.pc = (cpu.pc + offset) & 0xFFFF


def _call(cpu, values) -> None:
    """CALL: call subroutine."""
    sp = cpu.regfile.get('P', 8)
    sp = (sp - 2) & 0xFFFF
    cpu.memory.write_word(sp, cpu.pc)
    cpu.regfile.set('P', 8, sp)
    cpu.pc = values[0] & 0xFFFF


def _callz(cpu, values) -> None:
    """CALLZ: call if zero."""
    if cpu.flags_obj.check_Z():
        sp = cpu.regfile.get('P', 8)
        sp = (sp - 2) & 0xFFFF
        cpu.memory.write_word(sp, cpu.pc)
        cpu.regfile.set('P', 8, sp)
        cpu.pc = values[0] & 0xFFFF


def _callnz(cpu, values) -> None:
    """CALLNZ: call if not zero."""
    if not cpu.flags_obj.check_Z():
        sp = cpu.regfile.get('P', 8)
        sp = (sp - 2) & 0xFFFF
        cpu.memory.write_word(sp, cpu.pc)
        cpu.regfile.set('P', 8, sp)
        cpu.pc = values[0] & 0xFFFF


def _retn(cpu, values) -> int:
    """RETN: return with value in R0/P0."""
    result = values[1] if len(values) > 1 else values[0]
    cpu.regfile.set('R', 0, result & 0xFF)
    cpu.regfile.set('P', 0, result & 0xFFFF)
    _set_arith_flags(cpu, result & 0xFFFF, 0, 0, 16, is_sub=False)
    sp = cpu.regfile.get('P', 8)
    if sp >= 0xFFFF:
        raise RuntimeError(f"Stack underflow: SP=0x{sp:04X}")
    cpu.pc = cpu.memory.read_word(sp)
    cpu.regfile.set('P', 8, (sp + 2) & 0xFFFF)
    return result


def _loop(cpu, values) -> int:
    """LOOP: decrement counter and jump if not zero."""
    new_value = (values[0] - 1) & 0xFFFF
    _write_result(cpu, 0, new_value)
    if new_value != 0:
        cpu.pc = values[1] & 0xFFFF
    return new_value


def _loopz(cpu, values) -> int:
    """LOOPZ: loop while counter != 0 and zero flag set."""
    new_value = (values[0] - 1) & 0xFFFF
    _write_result(cpu, 0, new_value)
    if new_value != 0 and cpu.flags_obj.check_Z():
        cpu.pc = values[1] & 0xFFFF
    return new_value


def _while(cpu, values) -> int:
    """WHILE: set flags from condition value."""
    _set_arith_flags(cpu, values[0], 0, 0, 16, is_sub=False)
    return values[0]


def _int(cpu, values) -> None:
    """INT: software interrupt."""
    if not cpu.flags_obj.check_I():
        return
    flags_value = cpu.flags_obj.pack()
    sp = cpu.regfile.get('P', 8)
    sp = (sp - 2) & 0xFFFF
    cpu.memory.write_word(sp, flags_value)
    sp = (sp - 2) & 0xFFFF
    cpu.memory.write_word(sp, cpu.pc)
    cpu.regfile.set('P', 8, sp)
    cpu.flags_obj[5] = 0
    vector_addr = 0x0100 + (values[0] * 4)
    cpu.pc = cpu.memory.read_word(vector_addr)


# ------------------------------------------------------------------------------
# BCD / Flag Instructions
# ------------------------------------------------------------------------------

def _sed(cpu) -> None:
    """SED: set decimal flag."""
    cpu.flags_obj[4] = 1


def _cld(cpu) -> None:
    """CLD: clear decimal flag."""
    cpu.flags_obj[4] = 0


def _cla(cpu) -> None:
    """CLA: clear BCD adjust flag (alias for BCD carry flag A)."""
    cpu.flags_obj[10] = 0


def _bcda(cpu, values) -> int:
    """BCDA: BCD adjust after addition."""
    result = values[0] + values[1]
    if not cpu.flags_obj[4] and cpu.flags_obj[10]:
        result += 1
    if cpu.flags_obj[4]:
        if (result & 0x0F) > 9:
            result += 0x06
        if ((result >> 4) & 0x0F) > 9:
            result += 0x60
    # Carry check must run BEFORE masking to 8 bits — result may be 3 digits
    carry = result > 0x99
    result &= 0xFF
    _write_result(cpu, 0, result)
    cpu.flags_obj.set_from_bcd(result, carry)
    return result


def _bcds(cpu, values) -> int:
    """BCDS: BCD subtract with borrow."""
    result = values[0] - values[1]
    if not cpu.flags_obj[4] and cpu.flags_obj[10]:
        result -= 1
    if cpu.flags_obj[4]:
        if (result & 0x0F) > 9:
            result -= 0x06
        if ((result >> 4) & 0x0F) > 9:
            result -= 0x60
    # Borrow check must run BEFORE masking to 8 bits — result may be negative
    borrow = result < 0
    result &= 0xFF
    _write_result(cpu, 0, result)
    cpu.flags_obj.set_from_bcd(result, borrow)
    return result


def _bcdcmp(cpu, values) -> int:
    """BCDCMP: compare BCD values (dst vs src)."""
    bcd1, bcd2 = values[0], values[1]
    if bcd1 == bcd2:
        cpu.flags_obj[7] = 1
        cpu.flags_obj[1] = 0
        cpu.flags_obj[6] = 0
    elif bcd1 < bcd2:
        cpu.flags_obj[7] = 0
        cpu.flags_obj[1] = 1
        cpu.flags_obj[6] = 1
    else:
        cpu.flags_obj[7] = 0
        cpu.flags_obj[1] = 0
        cpu.flags_obj[6] = 0
    cpu.flags_obj[2] = 0
    return bcd1 - bcd2


def _bcd2bin(cpu, values) -> int:
    """BCD2BIN: convert BCD to binary."""
    bcd = values[0]
    valid = True
    for i in range(4):
        digit = (bcd >> (i * 4)) & 0x0F
        if digit > 9:
            valid = False
            break
    if valid:
        result = 0
        for i in range(4):
            digit = (bcd >> (i * 4)) & 0x0F
            result += digit * (10 ** i)
    else:
        result = bcd
    _write_result(cpu, 0, result & 0xFFFF)
    _set_logic_flags(cpu, result & 0xFFFF, 16)
    return result & 0xFFFF


def _bin2bcd(cpu, values) -> int:
    """BIN2BCD: convert binary to BCD."""
    result = 0
    for i in range(4):
        digit = (values[0] // (10 ** i)) % 10
        result |= (digit << (i * 4))
    _write_result(cpu, 0, result & 0xFFFF)
    _set_logic_flags(cpu, result & 0xFFFF, 16)
    return result & 0xFFFF


def _bcdadd(cpu, values) -> int:
    """BCDADD: add BCD values."""
    result = values[0] + values[1]
    if cpu.flags_obj[4]:
        if (result & 0x0F) > 9:
            result += 0x06
        if ((result >> 4) & 0x0F) > 9:
            result += 0x60
    # Carry check must run BEFORE masking to 8 bits — result may be 3 digits
    carry = result > 0x99
    result &= 0xFF
    _write_result(cpu, 0, result)
    cpu.flags_obj.set_from_bcd(result, carry)
    return result


def _bcdsub(cpu, values) -> int:
    """BCDSUB: subtract BCD values."""
    result = values[0] - values[1]
    if cpu.flags_obj[4]:
        if (result & 0x0F) > 9:
            result -= 0x06
        if ((result >> 4) & 0x0F) > 9:
            result -= 0x60
    # Borrow check must run BEFORE masking to 8 bits — result may be negative
    borrow = result < 0
    result &= 0xFF
    _write_result(cpu, 0, result)
    cpu.flags_obj.set_from_bcd(result, borrow)
    return result


# ------------------------------------------------------------------------------
# Math Functions
# ------------------------------------------------------------------------------

def _powr(cpu, values) -> int:
    """POWR: integer power."""
    try:
        result = int(math.pow(values[0], values[1]))
    except Exception:
        result = 0
    _write_result(cpu, 0, result & 0xFFFF)
    _set_arith_flags(cpu, result & 0xFFFF, values[0], values[1], 16, is_sub=False)
    return result & 0xFFFF


def _sqrt(cpu, values) -> int:
    """SQRT: square root."""
    signed = _to_signed_16(values[0])
    if signed < 0:
        result = 0
    else:
        result = int(math.sqrt(signed))
    _write_result(cpu, 0, result & 0xFFFF)
    _set_arith_flags(cpu, result & 0xFFFF, 0, values[0], 16, is_sub=False)
    return result & 0xFFFF


def _log(cpu, values) -> int:
    """LOG: natural logarithm (fixed-point)."""
    v = _to_signed_16(values[0])
    if v <= 0:
        result = 0
    else:
        result = int(math.log(v / 256.0) * 256)
    _write_result(cpu, 0, result & 0xFFFF)
    _set_arith_flags(cpu, result & 0xFFFF, 0, values[0], 16, is_sub=False)
    return result & 0xFFFF


def _exp(cpu, values) -> int:
    """EXP: exponential (fixed-point)."""
    v = _to_signed_16(values[0])
    try:
        result = int(math.exp(v / 256.0) * 256)
    except Exception:
        result = 0xFFFF
    _write_result(cpu, 0, result & 0xFFFF)
    _set_arith_flags(cpu, result & 0xFFFF, 0, values[0], 16, is_sub=False)
    return result & 0xFFFF


def _sin(cpu, values) -> int:
    """SIN: sine (fixed-point radians)."""
    v = _to_signed_16(values[0])
    result = int(math.sin(v / 256.0) * 256)
    _write_result(cpu, 0, result & 0xFFFF)
    _set_arith_flags(cpu, result & 0xFFFF, 0, values[0], 16, is_sub=False)
    return result & 0xFFFF


def _cos(cpu, values) -> int:
    """COS: cosine (fixed-point radians)."""
    v = _to_signed_16(values[0])
    result = int(math.cos(v / 256.0) * 256)
    _write_result(cpu, 0, result & 0xFFFF)
    _set_arith_flags(cpu, result & 0xFFFF, 0, values[0], 16, is_sub=False)
    return result & 0xFFFF


def _tan(cpu, values) -> int:
    """TAN: tangent (scaled by 1000)."""
    v = _to_signed_16(values[0])
    try:
        result = int(math.tan(v) * 1000)
    except Exception:
        result = 0
    _write_result(cpu, 0, result & 0xFFFF)
    _set_arith_flags(cpu, result & 0xFFFF, 0, values[0], 16, is_sub=False)
    return result & 0xFFFF


def _atan(cpu, values) -> int:
    """ATAN: arctangent (fixed-point)."""
    v = _to_signed_16(values[0])
    result = int(math.atan(v / 256.0) * 256)
    _write_result(cpu, 0, result & 0xFFFF)
    _set_arith_flags(cpu, result & 0xFFFF, 0, values[0], 16, is_sub=False)
    return result & 0xFFFF


def _asin(cpu, values) -> int:
    """ASIN: arcsine (fixed-point)."""
    v = _to_signed_16(values[0])
    try:
        result = int(math.asin(v / 256.0) * 256)
    except Exception:
        result = 0
    _write_result(cpu, 0, result & 0xFFFF)
    _set_arith_flags(cpu, result & 0xFFFF, 0, values[0], 16, is_sub=False)
    return result & 0xFFFF


def _acos(cpu, values) -> int:
    """ACOS: arccosine (fixed-point)."""
    v = _to_signed_16(values[0])
    try:
        result = int(math.acos(v / 256.0) * 256)
    except Exception:
        result = 0
    _write_result(cpu, 0, result & 0xFFFF)
    _set_arith_flags(cpu, result & 0xFFFF, 0, values[0], 16, is_sub=False)
    return result & 0xFFFF


def _deg(cpu, values) -> int:
    """DEG: degrees to radians (fixed-point)."""
    v = _to_signed_16(values[0])
    result = int((v * math.pi / 180.0) * 256)
    _write_result(cpu, 0, result & 0xFFFF)
    _set_arith_flags(cpu, result & 0xFFFF, 0, values[0], 16, is_sub=False)
    return result & 0xFFFF


def _rad(cpu, values) -> int:
    """RAD: radians to degrees."""
    v = _to_signed_16(values[0])
    result = int((v / 256.0) * 180.0 / math.pi)
    _write_result(cpu, 0, result & 0xFFFF)
    _set_arith_flags(cpu, result & 0xFFFF, 0, values[0], 16, is_sub=False)
    return result & 0xFFFF


def _floor(cpu, values) -> int:
    """FLOOR: floor of fixed-point value."""
    v = _to_signed_16(values[0])
    result = int(math.floor(v / 256.0))
    _write_result(cpu, 0, result & 0xFFFF)
    _set_arith_flags(cpu, result & 0xFFFF, 0, values[0], 16, is_sub=False)
    return result & 0xFFFF


def _ceil(cpu, values) -> int:
    """CEIL: ceiling of fixed-point value."""
    v = _to_signed_16(values[0])
    result = int(math.ceil(v / 256.0))
    _write_result(cpu, 0, result & 0xFFFF)
    _set_arith_flags(cpu, result & 0xFFFF, 0, values[0], 16, is_sub=False)
    return result & 0xFFFF


def _round(cpu, values) -> int:
    """ROUND: round fixed-point value."""
    v = _to_signed_16(values[0])
    result = int(round(v / 256.0))
    _write_result(cpu, 0, result & 0xFFFF)
    _set_arith_flags(cpu, result & 0xFFFF, 0, values[0], 16, is_sub=False)
    return result & 0xFFFF


def _trunc(cpu, values) -> int:
    """TRUNC: truncate fixed-point value toward zero."""
    v = _to_signed_16(values[0])
    result = int(v / 256.0)
    _write_result(cpu, 0, result & 0xFFFF)
    _set_arith_flags(cpu, result & 0xFFFF, 0, values[0], 16, is_sub=False)
    return result & 0xFFFF


def _frac(cpu, values) -> int:
    """FRAC: fractional part of fixed-point value (same sign as the input,
    i.e. consistent with TRUNC: v == TRUNC(v) * 256 + FRAC(v))."""
    v = _to_signed_16(values[0])
    result = int(math.fmod(v, 256))
    _write_result(cpu, 0, result & 0xFFFF)
    _set_arith_flags(cpu, result & 0xFFFF, 0, values[0], 16, is_sub=False)
    return result & 0xFFFF


def _intgr(cpu, values) -> int:
    """INTGR: integer part of fixed-point value toward zero (alias of TRUNC)."""
    v = _to_signed_16(values[0])
    result = int(v / 256.0)
    _write_result(cpu, 0, result & 0xFFFF)
    _set_arith_flags(cpu, result & 0xFFFF, 0, values[0], 16, is_sub=False)
    return result & 0xFFFF


# ------------------------------------------------------------------------------
# Count / Leading/Trailing Zeros
# ------------------------------------------------------------------------------

def _clz(cpu, values) -> int:
    """CLZ: count leading zeros."""
    value = values[1] if len(values) > 1 else values[0]
    if value == 0:
        result = 16
    else:
        result = 0
        while (value & 0x8000) == 0 and result < 16:
            value <<= 1
            result += 1
    _write_result(cpu, 0, result)
    _set_arith_flags(cpu, result, 0, value, 16, is_sub=False)
    return result


def _ctz(cpu, values) -> int:
    """CTZ: count trailing zeros."""
    value = values[1] if len(values) > 1 else values[0]
    if value == 0:
        result = 16
    else:
        result = 0
        while (value & 0x0001) == 0 and result < 16:
            value >>= 1
            result += 1
    _write_result(cpu, 0, result)
    _set_arith_flags(cpu, result, 0, value, 16, is_sub=False)
    return result


def _popcnt(cpu, values) -> int:
    """POPCNT: population count."""
    value = values[1] if len(values) > 1 else values[0]
    result = bin(value).count('1')
    _write_result(cpu, 0, result)
    _set_arith_flags(cpu, result, 0, value, 16, is_sub=False)
    return result


# ------------------------------------------------------------------------------
# Random
# ------------------------------------------------------------------------------

def _next_random_word(cpu) -> int:
    """Advance the CPU RNG and return next 16-bit word."""
    seed = cpu.rng_seed & 0xFFFF
    if seed == 0:
        seed = 0xACE1
    seed ^= (seed << 7) & 0xFFFF
    seed ^= seed >> 9
    seed ^= (seed << 8) & 0xFFFF
    cpu.rng_seed = seed & 0xFFFF
    return cpu.rng_seed


def _rnd(cpu, values) -> int:
    """RND: random number."""
    result = _next_random_word(cpu)
    _write_result(cpu, 0, result)
    _set_arith_flags(cpu, result, 0, 0, 16, is_sub=False)
    return result


def _rndr(cpu, values) -> int:
    """RNDR: random number in range [min, max]."""
    min_value = values[1]
    max_value = values[2]
    if max_value < min_value:
        result = min_value
    else:
        result = min_value + (_next_random_word(cpu) % (max_value - min_value + 1))
    _write_result(cpu, 0, result)
    _set_arith_flags(cpu, result, min_value, max_value, 16, is_sub=False)
    return result


# ------------------------------------------------------------------------------
# Fixed-Point Conversion
# ------------------------------------------------------------------------------

def _fmul(cpu, values) -> int:
    """FMUL: Q8.8 fixed-point multiply."""
    dest_signed = _to_signed_16(values[0])
    src_signed = _to_signed_16(values[1])
    result_signed = (dest_signed * src_signed) >> 8
    result = result_signed & 0xFFFF
    _write_result(cpu, 0, result)
    _set_arith_flags(cpu, result, values[0], values[1], 16, is_sub=False)
    return result


def _fdiv(cpu, values) -> int:
    """FDIV: Q8.8 fixed-point divide."""
    if values[1] == 0:
        raise RuntimeError("Division by zero")
    dest_signed = _to_signed_16(values[0])
    src_signed = _to_signed_16(values[1])
    result_signed = (dest_signed << 8) // src_signed
    result = result_signed & 0xFFFF
    _write_result(cpu, 0, result)
    _set_arith_flags(cpu, result, values[0], values[1], 16, is_sub=False)
    return result


def _ftoi(cpu, values) -> int:
    """FTOI: Q8.8 fixed-point to integer."""
    signed = _to_signed_16(values[0])
    result = signed >> 8
    result_unsigned = result & 0xFFFF
    _write_result(cpu, 0, result_unsigned)
    _set_arith_flags(cpu, result_unsigned, 0, values[0], 16, is_sub=False)
    return result_unsigned


def _itof(cpu, values) -> int:
    """ITOF: integer to Q8.8 fixed-point."""
    signed = _to_signed_16(values[0])
    result = signed << 8
    result_unsigned = result & 0xFFFF
    _write_result(cpu, 0, result_unsigned)
    _set_arith_flags(cpu, result_unsigned, 0, values[0], 16, is_sub=False)
    return result_unsigned


# ------------------------------------------------------------------------------
# Integer/String Conversion
# ------------------------------------------------------------------------------

def _itob(cpu, values) -> int:
    """ITOB: integer to binary string."""
    dest_addr = values[0]
    value = values[1]
    if value == 0:
        binary_str = "0"
    else:
        binary_str = ""
        temp = value
        while temp > 0:
            binary_str = str(temp & 1) + binary_str
            temp >>= 1
    for i, char in enumerate(binary_str):
        cpu.memory.write_byte((dest_addr + i) & 0xFFFF, ord(char))
    cpu.memory.write_byte((dest_addr + len(binary_str)) & 0xFFFF, 0)
    return dest_addr


def _btoi(cpu, values) -> int:
    """BTOI: binary string to integer."""
    source_addr = values[1]
    binary_str = ""
    i = 0
    while True:
        char = cpu.memory.read_byte((source_addr + i) & 0xFFFF)
        if char == 0 or char not in (48, 49):
            break
        binary_str += chr(char)
        i += 1
    result = 0
    for char in binary_str:
        result = (result << 1) | (1 if char == '1' else 0)
    _write_result(cpu, 0, result)
    _set_arith_flags(cpu, result, 0, 0, 16, is_sub=False)
    return result


def _itos(cpu, values) -> int:
    """ITOS: integer to decimal string at static buffer 0xA000."""
    value = values[1]
    if value > 32767:
        value -= 65536
    buffer_addr = 0xA000
    decimal_str = str(value)
    for i, char in enumerate(decimal_str):
        cpu.memory.write_byte((buffer_addr + i) & 0xFFFF, ord(char))
    cpu.memory.write_byte((buffer_addr + len(decimal_str)) & 0xFFFF, 0)
    _write_result(cpu, 0, buffer_addr)
    _set_arith_flags(cpu, buffer_addr, 0, value, 16, is_sub=False)
    return buffer_addr


def _stoi(cpu, values) -> int:
    """STOI: decimal string to integer."""
    source_addr = values[1]
    decimal_str = ""
    i = 0
    while True:
        char = cpu.memory.read_byte((source_addr + i) & 0xFFFF)
        if char == 0:
            break
        decimal_str += chr(char)
        i += 1
    try:
        result = int(decimal_str)
    except ValueError:
        result = 0
    _write_result(cpu, 0, result)
    _set_arith_flags(cpu, result, 0, 0, 16, is_sub=False)
    return result


# ------------------------------------------------------------------------------
# String Operations
# ------------------------------------------------------------------------------

def _strcpy(cpu, values) -> int:
    """STRCPY: copy null-terminated string."""
    src = values[1]
    dest = values[0]
    while True:
        char = cpu.memory.read_byte(src)
        cpu.memory.write_byte(dest, char)
        if char == 0:
            break
        src = (src + 1) & 0xFFFF
        dest = (dest + 1) & 0xFFFF
    return dest


def _strcat(cpu, values) -> int:
    """STRCAT: concatenate source to destination."""
    src = values[1]
    dest = values[0]
    while cpu.memory.read_byte(dest) != 0:
        dest = (dest + 1) & 0xFFFF
    while True:
        char = cpu.memory.read_byte(src)
        cpu.memory.write_byte(dest, char)
        if char == 0:
            break
        src = (src + 1) & 0xFFFF
        dest = (dest + 1) & 0xFFFF
    return dest


def _strcmp(cpu, values) -> int:
    """STRCMP: compare two strings up to length, stopping at a shared null terminator."""
    str1 = values[0]
    str2 = values[1]
    length = values[2]
    result = 0
    for i in range(length):
        char1 = cpu.memory.read_byte((str1 + i) & 0xFFFF)
        char2 = cpu.memory.read_byte((str2 + i) & 0xFFFF)
        if char1 != char2:
            result = -1 if char1 < char2 else 1
            break
        if char1 == 0:
            break
    cpu.regfile.set('R', 0, result & 0xFF)
    _set_arith_flags(cpu, result & 0xFFFF, 0, 0, 16, is_sub=False)
    return result & 0xFFFF


def _strlen(cpu, values) -> int:
    """STRLEN: length of null-terminated string."""
    src = values[0]
    length = 0
    while cpu.memory.read_byte((src + length) & 0xFFFF) != 0:
        length = (length + 1) & 0xFFFF
    cpu.regfile.set('R', 0, length & 0xFF)
    _set_arith_flags(cpu, length, 0, 0, 16, is_sub=False)
    return length


def _strupr(cpu, values) -> int:
    """STRUPR: convert string to uppercase in-place."""
    addr = values[0]
    while True:
        char = cpu.memory.read_byte(addr)
        if char == 0:
            break
        if 97 <= char <= 122:
            char -= 32
        cpu.memory.write_byte(addr, char)
        addr = (addr + 1) & 0xFFFF
    return addr


def _strlwr(cpu, values) -> int:
    """STRLWR: convert string to lowercase in-place."""
    addr = values[0]
    while True:
        char = cpu.memory.read_byte(addr)
        if char == 0:
            break
        if 65 <= char <= 90:
            char += 32
        cpu.memory.write_byte(addr, char)
        addr = (addr + 1) & 0xFFFF
    return addr


def _strrev(cpu, values) -> int:
    """STRREV: reverse string in-place."""
    src = values[0]
    length = 0
    while cpu.memory.read_byte((src + length) & 0xFFFF) != 0:
        length += 1
    for i in range(length // 2):
        left = (src + i) & 0xFFFF
        right = (src + length - 1 - i) & 0xFFFF
        left_char = cpu.memory.read_byte(left)
        right_char = cpu.memory.read_byte(right)
        cpu.memory.write_byte(left, right_char)
        cpu.memory.write_byte(right, left_char)
    return src


def _strfind(cpu, values) -> int:
    """STRFIND: return 1 if needle found in haystack, else 0."""
    haystack = values[0]
    needle = values[1]
    haystack_pos = 0
    while cpu.memory.read_byte((haystack + haystack_pos) & 0xFFFF) != 0:
        needle_pos = 0
        match = True
        while cpu.memory.read_byte((needle + needle_pos) & 0xFFFF) != 0:
            h = cpu.memory.read_byte((haystack + haystack_pos + needle_pos) & 0xFFFF)
            n = cpu.memory.read_byte((needle + needle_pos) & 0xFFFF)
            if h != n:
                match = False
                break
            needle_pos += 1
        if match:
            cpu.regfile.set('R', 0, 1)
            _set_arith_flags(cpu, 1, 0, 0, 16, is_sub=False)
            return 1
        haystack_pos += 1
    cpu.regfile.set('R', 0, 0)
    _set_arith_flags(cpu, 0, 0, 0, 16, is_sub=False)
    return 0


def _strfindi(cpu, values) -> int:
    """STRFINDI: case-insensitive substring find, return 1 if found else 0."""
    haystack = values[0]
    needle = values[1]
    haystack_pos = 0
    while cpu.memory.read_byte((haystack + haystack_pos) & 0xFFFF) != 0:
        needle_pos = 0
        match = True
        while cpu.memory.read_byte((needle + needle_pos) & 0xFFFF) != 0:
            h = cpu.memory.read_byte((haystack + haystack_pos + needle_pos) & 0xFFFF)
            n = cpu.memory.read_byte((needle + needle_pos) & 0xFFFF)
            if chr(h).upper() != chr(n).upper():
                match = False
                break
            needle_pos += 1
        if match:
            cpu.regfile.set('R', 0, 1)
            _set_arith_flags(cpu, 1, 0, 0, 16, is_sub=False)
            return 1
        haystack_pos += 1
    cpu.regfile.set('R', 0, 0)
    _set_arith_flags(cpu, 0, 0, 0, 16, is_sub=False)
    return 0


def _strext(cpu, values) -> int:
    """STREXT: extract substring from haystack into dest."""
    dest = values[0]
    haystack = values[1]
    needle = values[2]
    max_len = values[3]
    haystack_pos = 0
    found = False
    while cpu.memory.read_byte((haystack + haystack_pos) & 0xFFFF) != 0:
        needle_pos = 0
        match = True
        while needle_pos < max_len and cpu.memory.read_byte((needle + needle_pos) & 0xFFFF) != 0:
            h = cpu.memory.read_byte((haystack + haystack_pos + needle_pos) & 0xFFFF)
            n = cpu.memory.read_byte((needle + needle_pos) & 0xFFFF)
            if h != n:
                match = False
                break
            needle_pos += 1
        # A needle longer than max_len must not count as matched just because
        # the comparison loop hit the max_len cap — only a genuine match up
        # to the needle's own null terminator counts.
        if match and cpu.memory.read_byte((needle + needle_pos) & 0xFFFF) != 0:
            match = False
        if match:
            found = True
            break
        haystack_pos += 1
    if found:
        i = 0
        while i < max_len:
            char = cpu.memory.read_byte((haystack + haystack_pos + i) & 0xFFFF)
            cpu.memory.write_byte((dest + i) & 0xFFFF, char)
            if char == 0:
                break
            i += 1
    else:
        cpu.memory.write_byte(dest, 0)
    return dest


def _strexti(cpu, values) -> int:
    """STREXTI: case-insensitive extract substring."""
    dest = values[0]
    haystack = values[1]
    needle = values[2]
    max_len = values[3]
    haystack_pos = 0
    found = False
    while cpu.memory.read_byte((haystack + haystack_pos) & 0xFFFF) != 0:
        needle_pos = 0
        match = True
        while needle_pos < max_len and cpu.memory.read_byte((needle + needle_pos) & 0xFFFF) != 0:
            h = cpu.memory.read_byte((haystack + haystack_pos + needle_pos) & 0xFFFF)
            n = cpu.memory.read_byte((needle + needle_pos) & 0xFFFF)
            if chr(h).upper() != chr(n).upper():
                match = False
                break
            needle_pos += 1
        if match and cpu.memory.read_byte((needle + needle_pos) & 0xFFFF) != 0:
            match = False
        if match:
            found = True
            break
        haystack_pos += 1
    if found:
        i = 0
        while i < max_len:
            char = cpu.memory.read_byte((haystack + haystack_pos + i) & 0xFFFF)
            cpu.memory.write_byte((dest + i) & 0xFFFF, char)
            if char == 0:
                break
            i += 1
    else:
        cpu.memory.write_byte(dest, 0)
    return dest


# ------------------------------------------------------------------------------
# Memory Operations
# ------------------------------------------------------------------------------

def _memcpy(cpu, values) -> int:
    """MEMCPY: copy memory block."""
    dest = values[0]
    source = values[1]
    length = values[2]
    for i in range(length):
        data = cpu.memory.read_byte((source + i) & 0xFFFF)
        cpu.memory.write_byte((dest + i) & 0xFFFF, data)
    return dest


def _memset(cpu, values) -> int:
    """MEMSET: fill memory block."""
    dest = values[0]
    fill_value = values[1]
    length = values[2]
    for i in range(length):
        cpu.memory.write_byte((dest + i) & 0xFFFF, fill_value)
    return dest


def _memtest(cpu, values) -> int:
    """MEMTEST: compare two memory regions and set zero flag."""
    addr1 = values[0]
    addr2 = values[1]
    length = values[2]
    match = True
    for i in range(length):
        byte1 = cpu.memory.read_byte((addr1 + i) & 0xFFFF)
        byte2 = cpu.memory.read_byte((addr2 + i) & 0xFFFF)
        if byte1 != byte2:
            match = False
            break
    cpu.flags_obj[7] = 1 if match else 0
    cpu.flags_obj[1] = 0
    cpu.flags_obj[2] = 0
    cpu.flags_obj[6] = 0
    return 1 if match else 0


def _memmove(cpu, values) -> int:
    """MEMMOVE: copy memory block handling overlap.

    Stages through a temporary buffer rather than picking a copy direction
    from a raw ``dest < source`` comparison — that comparison ignores the
    64KB address-space wraparound, so ranges that overlap only because they
    wrap past 0xFFFF/0x0000 would pick the wrong direction and corrupt data.
    """
    dest = values[0]
    source = values[1]
    length = values[2]
    data = [cpu.memory.read_byte((source + i) & 0xFFFF) for i in range(length)]
    for i, byte in enumerate(data):
        cpu.memory.write_byte((dest + i) & 0xFFFF, byte)
    return dest


def _memcmp(cpu, values) -> int:
    """MEMCMP: compare two memory regions."""
    addr1 = values[1]
    addr2 = values[2]
    length = values[3]
    result = 0
    for i in range(length):
        byte1 = cpu.memory.read_byte((addr1 + i) & 0xFFFF)
        byte2 = cpu.memory.read_byte((addr2 + i) & 0xFFFF)
        if byte1 != byte2:
            result = 1 if byte1 > byte2 else -1
            break
    _write_result(cpu, 0, result & 0xFFFF)
    _set_arith_flags(cpu, result & 0xFFFF, 0, 0, 16, is_sub=False)
    return result & 0xFFFF


def _memswap(cpu, values) -> int:
    """MEMSWAP: swap two memory regions."""
    addr1 = values[0]
    addr2 = values[1]
    length = values[2]
    for i in range(length):
        byte1 = cpu.memory.read_byte((addr1 + i) & 0xFFFF)
        byte2 = cpu.memory.read_byte((addr2 + i) & 0xFFFF)
        cpu.memory.write_byte((addr1 + i) & 0xFFFF, byte2)
        cpu.memory.write_byte((addr2 + i) & 0xFFFF, byte1)
    return addr1


# ------------------------------------------------------------------------------
# Graphics / Sprite / Layer Operations
# ------------------------------------------------------------------------------

def _sblend(cpu, values) -> int:
    """SBLEND: set blend mode."""
    cpu.gfx.set_blend_mode(values[0])
    return values[0]


def _sread(cpu, values) -> int:
    """SREAD: read pixel at (VX, VY)."""
    color = cpu.gfx.get_screen_val()
    _write_result(cpu, 0, color)
    return color


def _swrite(cpu, values) -> int:
    """SWRITE: write pixel at (VX, VY)."""
    cpu.gfx.set_screen_val(values[0])
    return values[0]


def _srol(cpu, values) -> int:
    """SROL: roll screen."""
    axis = values[0]
    amount = values[1]
    if axis == 0:
        cpu.gfx.roll_x(-amount)
    elif axis == 1:
        cpu.gfx.roll_y(-amount)
    else:
        raise ValueError(f"Invalid axis for SROL: {axis}")
    return values[0]


def _srot(cpu, values) -> int:
    """SROT: rotate screen."""
    direction = values[0]
    amount = values[1]
    if direction == 0:
        cpu.gfx.rotate_left(amount)
    elif direction == 1:
        cpu.gfx.rotate_right(amount)
    else:
        raise ValueError(f"Invalid direction for SROT: {direction}")
    return values[0]


def _sshft(cpu, values) -> int:
    """SSHFT: shift screen.

    The shift amount is a SIGNED 16-bit value: the assembler encodes
    negative amounts as two's-complement imm16 (see
    tests/unit/test_new_assembler_negative_immediate.py), so a raw
    0xFFF8 means "shift up by 8", not "+65528".  Without the sign
    extension, numpy executes the huge positive shift as "copy an
    empty slice, then zero the whole layer" -- wiping the active
    layer instead of scrolling it (StarSys1 console scrolling relies
    on exactly this negative-amount behavior).
    """
    axis = values[0]
    amount = values[1]
    if amount & 0x8000:
        amount -= 0x10000
    if axis == 0:
        cpu.gfx.shift_x(amount)
    elif axis == 1:
        cpu.gfx.shift_y(amount)
    else:
        raise ValueError(f"Invalid axis for SSHFT: {axis}")
    return values[0]


def _sflip(cpu, values) -> int:
    """SFLIP: flip screen."""
    axis = values[0]
    if axis == 0:
        cpu.gfx.flip_x()
    elif axis == 1:
        cpu.gfx.flip_y()
    else:
        raise ValueError(f"Invalid axis for SFLIP: {axis}")
    return values[0]


def _sline(cpu, values) -> int:
    """SLINE: draw line."""
    x1 = cpu.gfx.Vregisters[0]
    y1 = cpu.gfx.Vregisters[1]
    color = cpu.gfx.Vregisters[3]
    cpu.gfx.draw_line(x1, y1, values[0], values[1], color)
    return values[0]


def _srect(cpu, values) -> int:
    """SRECT: draw rectangle."""
    x1 = cpu.gfx.Vregisters[0]
    y1 = cpu.gfx.Vregisters[1]
    color = cpu.gfx.Vregisters[3]
    cpu.gfx.draw_rectangle(x1, y1, values[0], values[1], color, values[2] != 0)
    return values[0]


def _scirc(cpu, values) -> int:
    """SCIRC: draw circle."""
    x = cpu.gfx.Vregisters[0]
    y = cpu.gfx.Vregisters[1]
    color = cpu.gfx.Vregisters[3]
    cpu.gfx.draw_circle(x, y, values[0], color, values[1] != 0)
    return values[0]


def _sinv(cpu) -> None:
    """SINV: invert screen colors."""
    cpu.gfx.invert_colors()


def _sblit(cpu) -> None:
    """SBLIT: blit VRAM to active layer."""
    cpu.gfx.blit()


def _sfill(cpu, values) -> int:
    """SFILL: fill active layer."""
    cpu.gfx.fill_layer(values[1] if len(values) > 1 else values[0])
    return values[0]


def _vread(cpu, values) -> int:
    """VREAD: read VRAM at linear address."""
    addr = values[0]
    if 0 <= addr < 65536:
        x = addr % 256
        y = addr // 256
        value = int(cpu.gfx.vram[y, x])
        _write_result(cpu, 0, value)
        return value
    raise IndexError(f"VRAM address out of range: {addr}")


def _vwrite(cpu, values) -> int:
    """VWRITE: write VRAM at (VX, VY)."""
    cpu.gfx.set_vram_val(values[0])
    return values[0]


def _vblit(cpu) -> None:
    """VBLIT: blit screen to VRAM."""
    cpu.gfx.blit_vram()


def _char(cpu, values) -> int:
    """CHAR: draw character."""
    color = cpu.gfx.Vregisters[3]
    x = int(cpu.gfx.Vregisters[0])
    y = int(cpu.gfx.Vregisters[1])
    cpu.gfx.draw_char(values[0], x, y, color)
    cpu.gfx.Vregisters[0] = (x + 8) % 256
    return values[0]


def _text(cpu, values) -> int:
    """TEXT: draw text string."""
    color = cpu.gfx.Vregisters[3]
    x = int(cpu.gfx.Vregisters[0])
    y = int(cpu.gfx.Vregisters[1])
    final_x, final_y = cpu.gfx.draw_text(x, y, color, values[0], cpu.memory)
    cpu.gfx.Vregisters[0] = int(final_x) % 256
    cpu.gfx.Vregisters[1] = int(final_y) % 256
    return values[0]


def _spblit(cpu, values) -> int:
    """SPBLIT: blit a sprite."""
    cpu.gfx.blit_sprite(values[0], cpu.memory)
    return values[0]


def _spblitall(cpu) -> None:
    """SPBLITALL: blit all sprites."""
    cpu.gfx.blit_all_sprites(cpu.memory)


def _lswap(cpu, values) -> int:
    """LSWAP: swap current layer with target layer."""
    target_layer = values[0]
    current_layer = int(cpu.gfx.VL)
    if not (0 <= target_layer <= 8):
        raise ValueError(f"Invalid target layer for LSWAP: {target_layer}")
    if target_layer == current_layer:
        return values[0]
    current_buffer = _get_layer_buffer(cpu.gfx, current_layer)
    target_buffer = _get_layer_buffer(cpu.gfx, target_layer)
    if current_buffer is None or target_buffer is None:
        raise ValueError(f"Invalid layer for LSWAP: current={current_layer}, target={target_layer}")
    temp = current_buffer.copy()
    current_buffer[:] = target_buffer
    target_buffer[:] = temp
    cpu.gfx.layers_dirty = True
    return values[0]


def _lmove(cpu, values) -> int:
    """LMOVE: move current layer to target and clear current."""
    target_layer = values[0]
    current_layer = int(cpu.gfx.VL)
    if not (0 <= target_layer <= 8):
        raise ValueError(f"Invalid target layer for LMOVE: {target_layer}")
    if target_layer == current_layer:
        return values[0]
    current_buffer = _get_layer_buffer(cpu.gfx, current_layer)
    target_buffer = _get_layer_buffer(cpu.gfx, target_layer)
    if current_buffer is None or target_buffer is None:
        raise ValueError(f"Invalid layer for LMOVE: current={current_layer}, target={target_layer}")
    target_buffer[:] = current_buffer
    current_buffer.fill(0)
    cpu.gfx.layers_dirty = True
    return values[0]


def _lcopy(cpu, values) -> int:
    """LCOPY: copy current layer to target."""
    target_layer = values[0]
    current_layer = int(cpu.gfx.VL)
    if not (0 <= target_layer <= 8):
        raise ValueError(f"Invalid target layer for LCOPY: {target_layer}")
    if target_layer == current_layer:
        return values[0]
    current_buffer = _get_layer_buffer(cpu.gfx, current_layer)
    target_buffer = _get_layer_buffer(cpu.gfx, target_layer)
    if current_buffer is None or target_buffer is None:
        raise ValueError(f"Invalid layer for LCOPY: current={current_layer}, target={target_layer}")
    target_buffer[:] = current_buffer
    cpu.gfx.layers_dirty = True
    return values[0]


def _get_layer_buffer(gfx, layer_num):
    """Return backing buffer for layer number 0-8."""
    if layer_num == 0:
        return gfx.layer_0
    if 1 <= layer_num <= 4:
        return gfx.background_layers[layer_num - 1]
    if 5 <= layer_num <= 8:
        return gfx.sprite_layers[layer_num - 5]
    return None


# ------------------------------------------------------------------------------
# Sound Operations
# ------------------------------------------------------------------------------

def _splay(cpu) -> int:
    """SPLAY: play sound on channel from SW bits 3-5.

    SW layout: bits 0-2 waveform, bits 3-5 channel, bit 6 loop, bit 7 enable.
    Bits 0-2 are the WAVEFORM, not the channel -- masking SW & 0x07 here would
    select the channel from the waveform field (e.g. MOV SW, 0x87 = waveform 7
    on channel 0 would wrongly play on channel 7).
    """
    channel = (cpu.sound.SW >> 3) & 0x07
    return cpu.sound.splay(channel)


def _sstop(cpu) -> int:
    """SSTOP: stop sound on channel from SW bits 3-5 (see _splay for layout)."""
    channel = (cpu.sound.SW >> 3) & 0x07
    return cpu.sound.sstop(channel)


def _strig(cpu, values) -> int:
    """STRIG: trigger sound effect."""
    return cpu.sound.strig(values[0])


# ------------------------------------------------------------------------------
# Keyboard Operations
# ------------------------------------------------------------------------------

def _keyin(cpu, values) -> int:
    """KEYIN: read key from buffer."""
    key = cpu.read_key_from_buffer()
    _write_result(cpu, 0, key)
    return key


def _keystat(cpu, values) -> int:
    """KEYSTAT: check if key is available."""
    if cpu.keyboard_device is not None:
        status = 1 if (cpu.keyboard_device.status_register & 0x01) else 0
    else:
        status = 1 if (cpu.keyboard[1] & 0x01) else 0
    _write_result(cpu, 0, status)
    return status


def _keycount(cpu, values) -> int:
    """KEYCOUNT: number of keys in buffer."""
    if cpu.keyboard_device is not None:
        count = cpu.keyboard_device.buffer_count
    else:
        count = cpu.keyboard[3]
    _write_result(cpu, 0, count)
    return count


def _keyclear(cpu) -> None:
    """KEYCLEAR: clear keyboard buffer."""
    cpu.clear_keyboard_buffer()


def _keyctrl(cpu, values) -> int:
    """KEYCTRL: set keyboard control register."""
    control = values[0]
    cpu.keyboard[2] = control
    cpu.interrupts[2] = control
    if cpu.keyboard_device is not None:
        cpu.keyboard_device.control_register = control
    cpu._refresh_pending_interrupt_sources()
    return control


# ------------------------------------------------------------------------------
# Serial Operations
# ------------------------------------------------------------------------------

def _serin(cpu, values) -> int:
    """SERIN: read serial data."""
    data = cpu.uart.read_data()
    _write_result(cpu, 0, data)
    return data


def _serout(cpu, values) -> int:
    """SEROUT: write serial data."""
    cpu.uart.write_data(values[0])
    return values[0]


def _serstat(cpu, values) -> int:
    """SERSTAT: read serial status."""
    status = cpu.uart.read_status_flags()
    _write_result(cpu, 0, status)
    return status


def _serctrl(cpu, values) -> int:
    """SERCTRL: write serial control."""
    control = values[0]
    cpu.uart.write_control(control)
    cpu.interrupts[1] = control & 0x01
    cpu._refresh_pending_interrupt_sources()
    return control


# ------------------------------------------------------------------------------
# Mouse / Hardware Debug
# ------------------------------------------------------------------------------

def _mousectrl(cpu, values) -> int:
    """MOUSECTRL: enable/disable mouse input and interrupts."""
    control = values[0] & 0xFF
    cpu.mouse.write_control(control)
    cpu.interrupts[3] = control & 0x01
    cpu._refresh_pending_interrupt_sources()
    return control


def _setbp(cpu, values) -> int:
    """SETBP: set hardware breakpoint."""
    index = values[0]
    address = values[1]
    if 0 <= index < 4:
        cpu.hw_breakpoints[index] = address
        cpu.hw_breakpoint_enabled[index] = True
        cpu.has_hw_breakpoints = True
    return index


def _clrbp(cpu, values) -> int:
    """CLRBP: clear hardware breakpoint."""
    index = values[0]
    if 0 <= index < 4:
        cpu.hw_breakpoint_enabled[index] = False
        cpu._refresh_hw_breakpoint_state()
    return index


def _enabrk(cpu) -> None:
    """ENABRK: enable all set hardware breakpoints."""
    for i in range(4):
        if cpu.hw_breakpoints[i] != 0:
            cpu.hw_breakpoint_enabled[i] = True
    cpu._refresh_hw_breakpoint_state()


def _disbrk(cpu) -> None:
    """DISBRK: disable all hardware breakpoints."""
    for i in range(4):
        cpu.hw_breakpoint_enabled[i] = False
    cpu.has_hw_breakpoints = False


def _enatrap(cpu) -> None:
    """ENATRAP: enable single-step trap."""
    cpu.flags_obj[0] = 1


def _disatrap(cpu) -> None:
    """DISATRAP: disable single-step trap."""
    cpu.flags_obj[0] = 0


# ------------------------------------------------------------------------------
# Special Register Access
# ------------------------------------------------------------------------------

def _sa(cpu, values) -> int:
    """SA: sound address register."""
    cpu.sound.SA = values[0] & 0xFFFF
    return values[0]


def _sf(cpu, values) -> int:
    """SF: sound frequency register."""
    cpu.sound.SF = values[0] & 0xFFFF
    return values[0]


def _sv(cpu, values) -> int:
    """SV: sound volume register."""
    cpu.sound.SV = values[0] & 0xFF
    return values[0]


def _sw(cpu, values) -> int:
    """SW: sound waveform/control register."""
    cpu.sound.SW = values[0] & 0xFF
    return values[0]


def _vm(cpu, values) -> int:
    """VM: video mode register."""
    cpu.gfx.VM = values[0] & 0xFF
    return values[0]


def _vl(cpu, values) -> int:
    """VL: video layer register."""
    cpu.gfx.VL = values[0] & 0xFF
    return values[0]


def _tt(cpu, values) -> int:
    """TT: timer counter register.

    Routed through cpu.timer_device (the real backing store, also used by
    the register-code path for ``MOV TT, ...``) rather than a ``cpu.timer``
    list attribute, which was never defined on CPU and made this opcode
    raise AttributeError unconditionally. Matches _register_externals'
    no-op-when-unwired behavior when no timer peripheral is attached.
    """
    if cpu.timer_device is not None:
        cpu.timer_device.set_register(0, values[0])
    return values[0]


def _tm(cpu, values) -> int:
    """TM: timer match register."""
    if cpu.timer_device is not None:
        cpu.timer_device.set_register(1, values[0])
    return values[0]


def _tc(cpu, values) -> int:
    """TC: timer control register."""
    if cpu.timer_device is not None:
        cpu.timer_device.set_register(2, values[0])
    return values[0]


def _ts(cpu, values) -> int:
    """TS: timer speed register."""
    if cpu.timer_device is not None:
        cpu.timer_device.set_register(3, values[0])
    return values[0]


def _vx(cpu, values) -> int:
    """VX: video X coordinate register."""
    cpu.gfx.Vregisters[0] = values[0] & 0xFF
    return values[0]


def _vy(cpu, values) -> int:
    """VY: video Y coordinate register."""
    cpu.gfx.Vregisters[1] = values[0] & 0xFF
    return values[0]
