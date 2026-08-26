"""
Nova-16 Parameterized Instruction Execution Module

Phase 6 of the reimplantation strategy. Replaces the 199-class OO instruction
hierarchy (instructions.py, ~4092 lines) with a parameterized Instruction
dataclass + pure handler functions.

The Instruction class encapsulates:
    - Instruction name & opcode
    - Number of operands expected
    - Handler function (pure, receives cpu + resolved operand values)
    - Optional flags function (composable flag-setting callback)
    - Operand width hint (8 or 16 bit)

Handler functions are pure arithmetic/logic — they receive the CPU reference
and resolved operand values, compute the result, and optionally write it back.
Flag-setting is handled by composable _flags_* callbacks.

Architecture:
    CPU.step() → fetch opcode → look up INSTRUCTION_TABLE →
    Instruction.execute(cpu) → handler(cpu, resolved_values) → flags_fn(...)

Migration strategy:
    The full 179-opcode INSTRUCTION_TABLE is built from the existing
    instructions.py BaseInstruction subclasses via a compatibility adapter.
    Individual handler functions can replace legacy classes incrementally
    with binary-equivalent behavior verified by the test suite.
"""

from dataclasses import dataclass, field
from typing import Callable, Optional, List, Dict, Any

from core.fetch import calculate_memory_address
from core.exec_handlers import (
    _mov, _movz, _movnz, _xchng, _swap, _lea,
    _add, _sub, _mul, _div, _mod, _inc, _dec, _neg, _abs,
    _adc, _sbc, _mulh, _divh, _min, _max,
    _and, _or, _xor, _not, _shl, _shr, _sar, _sal, _rol, _ror, _rcl, _rcr,
    _btst, _bset, _bclr, _bflip,
    _cmp,
    _push, _pop, _enter, _leave,
    _jmp, _jz, _jnz, _jo, _jno, _jc, _jnc, _js, _jns,
    _jgt, _jlt, _jge, _jle, _br, _brz, _brnz,
    _call, _callz, _callnz, _retn, _loop, _loopz, _while, _int,
    _sed, _cld, _cla, _bcda, _bcds, _bcdcmp, _bcd2bin, _bin2bcd, _bcdadd, _bcdsub,
    _powr, _sqrt, _log, _exp, _sin, _cos, _tan, _atan, _asin, _acos,
    _deg, _rad, _floor, _ceil, _round, _trunc, _frac, _intgr,
    _clz, _ctz, _popcnt,
    _rnd, _rndr,
    _fmul, _fdiv, _ftoi, _itof,
    _itob, _btoi, _itos, _stoi,
    _strcpy, _strcat, _strcmp, _strlen, _strupr, _strlwr, _strrev, _strfind, _strfindi, _strext, _strexti,
    _memcpy, _memset, _memtest, _memmove, _memcmp, _memswap,
    _sblend, _sread, _swrite, _srol, _srot, _sshft, _sflip, _sline, _srect, _scirc, _sinv, _sblit, _sfill,
    _vread, _vwrite, _vblit, _char, _text, _spblit, _spblitall,
    _lswap, _lmove, _lcopy,
    _splay, _sstop, _strig,
    _keyin, _keystat, _keycount, _keyclear, _keyctrl,
    _serin, _serout, _serstat, _serctrl,
    _mousectrl,
    _setbp, _clrbp, _enabrk, _disbrk, _enatrap, _disatrap,
    _sa, _sf, _sv, _sw, _vm, _vl, _tt, _tm, _tc, _ts, _vx, _vy,
)


# ==============================================================================
# Parameterized Instruction
# ==============================================================================

@dataclass(slots=True)
class Instruction:
    """Parameterized instruction — one instance per opcode family.

    Replaces the BaseInstruction subclass pattern where each opcode needed
    its own class with ~10 lines of boilerplate.

    Attributes:
        name: Human-readable instruction name (e.g., 'ADD', 'MOV').
        opcode: Numeric opcode byte.
        num_operands: Expected operand count (0 for no-operand instructions).
        handler: Callable(cpu, values) -> result, or Callable(cpu) for 0-operand.
        flags_fn: Optional callable(cpu, values, result) to set flags after execution.
        width: Bit-width hint for flag-setting (8 or 16).
        legacy_class: Reference to old instructions.py class during migration.
    """
    name: str
    opcode: int
    num_operands: int = 2
    handler: Optional[Callable] = None
    flags_fn: Optional[Callable] = None
    width: int = 8
    legacy_class: Any = None

    def execute(self, cpu) -> None:
        """Execute this instruction on the given CPU.

        Delegates to self.handler(cpu, resolved_values) if handler is set,
        otherwise falls back to self.legacy_class(cpu).execute(cpu) for
        backward compatibility during migration.
        """
        if self.handler is not None:
            self._execute_handler(cpu)
        elif self.legacy_class is not None:
            self.legacy_class.execute(cpu)
        else:
            raise RuntimeError(
                f"Instruction {self.name} (0x{self.opcode:02X}) has no handler "
                f"and no legacy_class — cannot execute"
            )

    def _execute_handler(self, cpu) -> None:
        """Execute via the handler function.

        Optimized hot path:
        - Local variable bindings to avoid repeated attribute lookups
        - Inline operand resolution to avoid list allocation
        - Pre-sized tuple for 1-4 operand values
        """
        n_ops = self.num_operands
        if n_ops == 0:
            self.handler(cpu)
        elif n_ops == 1:
            v0 = _resolve_single_operand(cpu.operands[0], cpu)
            result = self.handler(cpu, (v0,))
            if self.flags_fn is not None:
                self.flags_fn(cpu, (v0,), result)
        elif n_ops == 2:
            v0 = _resolve_single_operand(cpu.operands[0], cpu)
            v1 = _resolve_single_operand(cpu.operands[1], cpu)
            result = self.handler(cpu, (v0, v1))
            if self.flags_fn is not None:
                self.flags_fn(cpu, (v0, v1), result)
        elif n_ops == 3:
            v0 = _resolve_single_operand(cpu.operands[0], cpu)
            v1 = _resolve_single_operand(cpu.operands[1], cpu)
            v2 = _resolve_single_operand(cpu.operands[2], cpu)
            result = self.handler(cpu, (v0, v1, v2))
            if self.flags_fn is not None:
                self.flags_fn(cpu, (v0, v1, v2), result)
        else:
            # Generic fallback for 4+ operands (rare: STREXT, STREXTI, MEMCMP)
            values = tuple(_resolve_single_operand(op, cpu) for op in cpu.operands)
            result = self.handler(cpu, values)
            if self.flags_fn is not None:
                self.flags_fn(cpu, values, result)

    def __repr__(self) -> str:
        return f"Instruction({self.name}, 0x{self.opcode:02X})"


def _resolve_single_operand(op, cpu) -> int:
    """Resolve a single operand value — inline in the hot path.

    Avoids the list allocation and per-operand method call overhead of
    the old _resolve_operands loop.
    """
    if op.is_register:
        # R and P are the overwhelming majority of register operands and
        # are stored as plain lists on the CPU (cpu.Rregisters/Pregisters
        # alias regfile.R/P) — index directly instead of going through
        # regfile.get()'s dict-dispatch + callable indirection. Every other
        # register type (external/peripheral-backed) still goes through the
        # regular dispatch so callback semantics are unaffected.
        rt = op.reg_type
        if rt == 'R':
            return cpu.Rregisters[op.reg_idx]
        if rt == 'P':
            return cpu.Pregisters[op.reg_idx]
        return cpu.regfile.get(rt, op.reg_idx)
    if op.is_immediate:
        return op.value
    if op.is_memory:
        addr = calculate_memory_address(op, cpu.regfile)
        # Memory read size: byte if dest is R register, otherwise word
        dest_op = cpu.operands[0] if cpu.operands else None
        if dest_op is not None and dest_op.is_register and dest_op.reg_type == 'R':
            return cpu.memory.read_byte_fast(addr)
        return cpu.memory.read_word_fast(addr)
    return 0


# ==============================================================================
# Handler Functions (Pure Arithmetic / Logic)
# ==============================================================================
# Each handler receives (cpu, values) where values is a list of resolved operand
# values. Returns the result (or None for control-flow instructions).
# The caller handles writeback to destination operand and flag-setting.

def _hlt(cpu) -> None:
    """HLT: Halt the CPU."""
    cpu.halted = True


def _nop(cpu) -> None:
    """NOP: No operation."""
    pass


def _ret(cpu) -> None:
    """RET: Return from subroutine. Pop return address from stack."""
    sp = cpu.regfile.get('P', 8)  # SP is P8
    ret_addr = cpu.memory.read_word_fast(sp)
    cpu.regfile.set('P', 8, (sp + 2) & 0xFFFF)
    cpu.pc = ret_addr


def _iret(cpu) -> None:
    """IRET: Return from interrupt. Restore PC and flags.

    Legacy interrupt entry pushes PC first, then flags, so the stack layout
    at the handler is (top -> bottom): flags, PC.  IRET therefore pops PC
    first and flags second.
    """
    sp = cpu.regfile.get('P', 8)

    # Match legacy behavior: require at least 4 bytes on the stack.
    if sp > 0xFFFB:
        raise RuntimeError(
            f"Stack underflow in IRET: SP=0x{sp:04X}, insufficient data on stack"
        )

    # Pop return address first (it was pushed last by _trigger_interrupt)
    ret_addr = cpu.memory.read_word_fast(sp)
    sp = (sp + 2) & 0xFFFF

    # Pop flags second (pushed first)
    flags_val = cpu.memory.read_word_fast(sp)
    sp = (sp + 2) & 0xFFFF

    cpu.regfile.set('P', 8, sp)
    cpu.flags_obj.set_state(
        [(flags_val >> i) & 1 for i in range(12)]
    )
    cpu.pc = ret_addr


def _cli(cpu) -> None:
    """CLI: Clear interrupt flag."""
    cpu.flags_obj[5] = 0


def _sti(cpu) -> None:
    """STI: Set interrupt flag."""
    cpu.flags_obj[5] = 1


def _pushf(cpu) -> None:
    """PUSHF: Push flags onto stack."""
    sp = cpu.regfile.get('P', 8)
    sp = (sp - 2) & 0xFFFF
    flags_packed = cpu.flags_obj.pack()
    cpu.memory.write_word_fast(sp, flags_packed)
    cpu.regfile.set('P', 8, sp)


def _popf(cpu) -> None:
    """POPF: Pop flags from stack."""
    sp = cpu.regfile.get('P', 8)
    flags_packed = cpu.memory.read_word_fast(sp)
    cpu.flags_obj.set_state(
        [(flags_packed >> i) & 1 for i in range(12)]
    )
    cpu.regfile.set('P', 8, (sp + 2) & 0xFFFF)


def _pusha(cpu) -> None:
    """PUSHA: Push all registers onto stack as 16-bit words.

    Legacy layout (top -> bottom): VC, VY, VX, P9..P0, R9..R0.
    Total: 23 words = 46 bytes.
    """
    sp = cpu.regfile.get('P', 8)
    regs = []
    regs.extend(cpu.regfile.R)          # R0-R9
    regs.extend(cpu.regfile.P)          # P0-P9
    regs.append(cpu.gfx.Vregisters[0])  # VX
    regs.append(cpu.gfx.Vregisters[1])  # VY
    regs.append(cpu.gfx.Vregisters[3])  # VC

    for value in reversed(regs):
        sp = (sp - 2) & 0xFFFF
        cpu.memory.write_word_fast(sp, value)
    cpu.regfile.set('P', 8, sp)


def _popa(cpu) -> None:
    """POPA: Pop all registers from stack as 16-bit words.

    Reverse of PUSHA. SP is restored last so P8 doesn't corrupt the walk.
    If the stack is exhausted (fewer than 46 bytes present), the missing
    registers are restored to zero rather than raising -- this keeps a
    standalone popa() from crashing the emulator, matching the
    Defense-in-Depth principle that a single bad call must not corrupt
    the whole system.
    """
    sp = cpu.regfile.get('P', 8)
    values = []
    for _ in range(23):
        if sp >= 0xFFFE:
            values.append(0)
        else:
            values.append(cpu.memory.read_word_fast(sp))
            sp = (sp + 2) & 0xFFFF

    # Restore R0-R9
    for i in range(10):
        cpu.regfile.set('R', i, values[i] & 0xFF)
    # Restore P0-P9
    for i in range(10):
        cpu.regfile.set('P', i, values[10 + i] & 0xFFFF)
    # Restore VX, VY, VC
    cpu.gfx.Vregisters[0] = values[20] & 0xFF
    cpu.gfx.Vregisters[1] = values[21] & 0xFF
    cpu.gfx.Vregisters[3] = values[22] & 0xFF

    cpu.regfile.set('P', 8, sp)


# ==============================================================================
# Flag-Setting Callbacks
# ==============================================================================

def _flags_arith_8bit(cpu, values, result):
    """Set flags for 8-bit arithmetic (ADD, SUB, ADC, SBC, INC, DEC)."""
    op1 = values[0] if len(values) > 0 else 0
    op2 = values[1] if len(values) > 1 else 1
    cpu.flags_obj.set_from_operation(result, op1, op2, width=8,
                                     is_subtraction=False)


def _flags_arith_16bit(cpu, values, result):
    """Set flags for 16-bit arithmetic."""
    op1 = values[0] if len(values) > 0 else 0
    op2 = values[1] if len(values) > 1 else 1
    cpu.flags_obj.set_from_operation(result, op1, op2, width=16,
                                     is_subtraction=False)


def _flags_sub_8bit(cpu, values, result):
    """Set flags for 8-bit subtraction (SUB, CMP, SBC, DEC)."""
    op1 = values[0] if len(values) > 0 else 0
    op2 = values[1] if len(values) > 1 else 1
    cpu.flags_obj.set_from_operation(result, op1, op2, width=8,
                                     is_subtraction=True)


def _flags_sub_16bit(cpu, values, result):
    """Set flags for 16-bit subtraction."""
    op1 = values[0] if len(values) > 0 else 0
    op2 = values[1] if len(values) > 1 else 1
    cpu.flags_obj.set_from_operation(result, op1, op2, width=16,
                                     is_subtraction=True)


def _flags_cmp_8bit(cpu, values, result):
    """Set flags for 8-bit comparison (CMP)."""
    op1 = values[0] if len(values) > 0 else 0
    op2 = values[1] if len(values) > 1 else 1
    cpu.flags_obj.set_from_operation(result, op1, op2, width=8,
                                     is_subtraction=True, is_cmp=True)


def _flags_cmp_16bit(cpu, values, result):
    """Set flags for 16-bit comparison."""
    op1 = values[0] if len(values) > 0 else 0
    op2 = values[1] if len(values) > 1 else 1
    cpu.flags_obj.set_from_operation(result, op1, op2, width=16,
                                     is_subtraction=True, is_cmp=True)


def _flags_logic_8bit(cpu, values, result):
    """Set flags for 8-bit logic (AND, OR, XOR, NOT, SHL, SHR)."""
    cpu.flags_obj.set_from_8bit(result)
    # Clear carry and overflow for logic operations
    cpu.flags_obj[6] = 0  # Carry
    cpu.flags_obj[2] = 0  # Overflow


def _flags_logic_16bit(cpu, values, result):
    """Set flags for 16-bit logic."""
    cpu.flags_obj.set_from_16bit(result)
    cpu.flags_obj[6] = 0
    cpu.flags_obj[2] = 0


# ==============================================================================
# Instruction Table Builder
# ==============================================================================

def build_instruction_table() -> Dict[int, Instruction]:
    """Build the complete instruction dispatch table.

    During Phase 6 migration, this creates parameterized Instruction wrappers
    around the existing instructions.py BaseInstruction classes.  As individual
    instructions are converted to pure handler functions, their entries are
    replaced with handler-based Instruction instances.

    Returns:
        Dict mapping opcode (int) -> Instruction.
    """
    import instructions as inst_module
    from instructions import BaseInstruction

    table: Dict[int, Instruction] = {}

    # Build from all classes in instructions.py that inherit from BaseInstruction
    for name in dir(inst_module):
        obj = getattr(inst_module, name)
        if not isinstance(obj, type):
            continue
        if not issubclass(obj, BaseInstruction) or obj is BaseInstruction:
            continue
        try:
            inst = obj()  # Instantiate to get opcode + name
            if hasattr(inst, 'opcode') and hasattr(inst, 'name'):
                table[inst.opcode] = Instruction(
                    name=inst.name,
                    opcode=inst.opcode,
                    num_operands=getattr(inst, 'num_operands', 2),
                    legacy_class=inst,
                )
        except Exception:
            continue

    # Start from handler-based instructions so converted opcodes take precedence.
    table.update(HANDLER_INSTRUCTIONS)

    # Call the original create_instruction_table to ensure all opcodes covered
    from instructions import create_instruction_table as legacy_create
    legacy_table = legacy_create()
    for opcode, legacy_inst in legacy_table.items():
        if opcode not in table:
            table[opcode] = Instruction(
                name=legacy_inst.name,
                opcode=opcode,
                num_operands=getattr(legacy_inst, 'num_operands', 2),
                legacy_class=legacy_inst,
            )

    return table


# ==============================================================================
# No-Operand Opcode Set
# ==============================================================================

NO_OPERAND_OPCODES: set = {
    0x00,  # HLT
    0xFF,  # NOP
    0x01,  # RET
    0x02,  # IRET
    0x03,  # CLI
    0x04,  # STI
    0x1A,  # PUSHF
    0x1B,  # POPF
    0x1C,  # PUSHA
    0x1D,  # POPA
    0x3B,  # SINV
    0x3C,  # SBLIT
    0x40,  # VBLIT
    0x56,  # SPBLITALL
    0x57,  # SPLAY
    0x58,  # SSTOP
    0xA8,  # ENABRK
    0xA9,  # DISBRK
    0xAA,  # ENATRAP
    0xAB,  # DISATRAP
    0x46,  # KEYCLEAR
    0x4B,  # SED
    0x4C,  # CLD
    0x4D,  # CLA
    0x9C,  # LEAVE
}


# ==============================================================================
# Handler-Based Instruction Table (Work in Progress — Phase 6 Migration)
# ==============================================================================
# As instructions are converted from legacy classes to handler functions,
# add them here. The build_instruction_table() function will prefer handler-based
# entries over legacy_class entries.

HANDLER_INSTRUCTIONS: Dict[int, Instruction] = {
    # No-operand instructions
    0x00: Instruction('HLT', 0x00, num_operands=0, handler=_hlt),
    0xFF: Instruction('NOP', 0xFF, num_operands=0, handler=_nop),
    0x01: Instruction('RET', 0x01, num_operands=0, handler=_ret),
    0x02: Instruction('IRET', 0x02, num_operands=0, handler=_iret),
    0x03: Instruction('CLI', 0x03, num_operands=0, handler=_cli),
    0x04: Instruction('STI', 0x04, num_operands=0, handler=_sti),
    0x1A: Instruction('PUSHF', 0x1A, num_operands=0, handler=_pushf),
    0x1B: Instruction('POPF', 0x1B, num_operands=0, handler=_popf),
    0x1C: Instruction('PUSHA', 0x1C, num_operands=0, handler=_pusha),
    0x1D: Instruction('POPA', 0x1D, num_operands=0, handler=_popa),
    0x3B: Instruction('SINV', 0x3B, num_operands=0, handler=_sinv),
    0x3C: Instruction('SBLIT', 0x3C, num_operands=0, handler=_sblit),
    0x40: Instruction('VBLIT', 0x40, num_operands=0, handler=_vblit),
    0x56: Instruction('SPBLITALL', 0x56, num_operands=0, handler=_spblitall),
    0x57: Instruction('SPLAY', 0x57, num_operands=0, handler=_splay),
    0x58: Instruction('SSTOP', 0x58, num_operands=0, handler=_sstop),
    0xA8: Instruction('ENABRK', 0xA8, num_operands=0, handler=_enabrk),
    0xA9: Instruction('DISBRK', 0xA9, num_operands=0, handler=_disbrk),
    0xAA: Instruction('ENATRAP', 0xAA, num_operands=0, handler=_enatrap),
    0xAB: Instruction('DISATRAP', 0xAB, num_operands=0, handler=_disatrap),
    0x46: Instruction('KEYCLEAR', 0x46, num_operands=0, handler=_keyclear),

    # Data movement (2 operands)
    0x06: Instruction('MOV', 0x06, num_operands=2, handler=_mov),
    0x96: Instruction('MOVZ', 0x96, num_operands=2, handler=_movz),
    0x97: Instruction('MOVNZ', 0x97, num_operands=2, handler=_movnz),
    0x95: Instruction('XCHNG', 0x95, num_operands=2, handler=_xchng),
    0x94: Instruction('SWAP', 0x94, num_operands=1, handler=_swap),
    0x98: Instruction('LEA', 0x98, num_operands=2, handler=_lea),

    # Arithmetic (2 operands)
    0x07: Instruction('ADD', 0x07, num_operands=2, handler=_add),
    0x08: Instruction('SUB', 0x08, num_operands=2, handler=_sub),
    0x09: Instruction('MUL', 0x09, num_operands=2, handler=_mul),
    0x0A: Instruction('DIV', 0x0A, num_operands=2, handler=_div),
    0x0D: Instruction('MOD', 0x0D, num_operands=2, handler=_mod),
    0x0B: Instruction('INC', 0x0B, num_operands=1, handler=_inc),
    0x0C: Instruction('DEC', 0x0C, num_operands=1, handler=_dec),
    0x0E: Instruction('NEG', 0x0E, num_operands=1, handler=_neg),
    0x0F: Instruction('ABS', 0x0F, num_operands=1, handler=_abs),
    0x87: Instruction('ADC', 0x87, num_operands=2, handler=_adc),
    0x88: Instruction('SBC', 0x88, num_operands=2, handler=_sbc),
    0x89: Instruction('MULH', 0x89, num_operands=2, handler=_mulh),
    0x8A: Instruction('DIVH', 0x8A, num_operands=2, handler=_divh),
    0x8B: Instruction('MIN', 0x8B, num_operands=2, handler=_min),
    0x8C: Instruction('MAX', 0x8C, num_operands=2, handler=_max),

    # Bitwise / shift (2 operands)
    0x10: Instruction('AND', 0x10, num_operands=2, handler=_and),
    0x11: Instruction('OR', 0x11, num_operands=2, handler=_or),
    0x12: Instruction('XOR', 0x12, num_operands=2, handler=_xor),
    0x13: Instruction('NOT', 0x13, num_operands=1, handler=_not),
    0x14: Instruction('SHL', 0x14, num_operands=2, handler=_shl),
    0x15: Instruction('SHR', 0x15, num_operands=2, handler=_shr),
    0x90: Instruction('SAR', 0x90, num_operands=2, handler=_sar),
    0x91: Instruction('SAL', 0x91, num_operands=2, handler=_sal),
    0x16: Instruction('ROL', 0x16, num_operands=2, handler=_rol),
    0x17: Instruction('ROR', 0x17, num_operands=2, handler=_ror),
    0x92: Instruction('RCL', 0x92, num_operands=2, handler=_rcl),
    0x93: Instruction('RCR', 0x93, num_operands=2, handler=_rcr),

    # Bit test / modify (2 operands)
    0x6D: Instruction('BTST', 0x6D, num_operands=2, handler=_btst),
    0x6E: Instruction('BSET', 0x6E, num_operands=2, handler=_bset),
    0x6F: Instruction('BCLR', 0x6F, num_operands=2, handler=_bclr),
    0x70: Instruction('BFLIP', 0x70, num_operands=2, handler=_bflip),

    # Comparison (2 operands)
    0x2E: Instruction('CMP', 0x2E, num_operands=2, handler=_cmp),

    # Stack (1 operand)
    0x18: Instruction('PUSH', 0x18, num_operands=1, handler=_push),
    0x19: Instruction('POP', 0x19, num_operands=1, handler=_pop),
    0x9B: Instruction('ENTER', 0x9B, num_operands=1, handler=_enter),
    0x9C: Instruction('LEAVE', 0x9C, num_operands=0, handler=_leave),

    # Control flow (1 operand)
    0x1E: Instruction('JMP', 0x1E, num_operands=1, handler=_jmp),
    0x1F: Instruction('JZ', 0x1F, num_operands=1, handler=_jz),
    0x20: Instruction('JNZ', 0x20, num_operands=1, handler=_jnz),
    0x21: Instruction('JO', 0x21, num_operands=1, handler=_jo),
    0x22: Instruction('JNO', 0x22, num_operands=1, handler=_jno),
    0x23: Instruction('JC', 0x23, num_operands=1, handler=_jc),
    0x24: Instruction('JNC', 0x24, num_operands=1, handler=_jnc),
    0x25: Instruction('JS', 0x25, num_operands=1, handler=_js),
    0x26: Instruction('JNS', 0x26, num_operands=1, handler=_jns),
    0x27: Instruction('JGT', 0x27, num_operands=1, handler=_jgt),
    0x28: Instruction('JLT', 0x28, num_operands=1, handler=_jlt),
    0x29: Instruction('JGE', 0x29, num_operands=1, handler=_jge),
    0x2A: Instruction('JLE', 0x2A, num_operands=1, handler=_jle),
    0x2B: Instruction('BR', 0x2B, num_operands=1, handler=_br),
    0x2C: Instruction('BRZ', 0x2C, num_operands=1, handler=_brz),
    0x2D: Instruction('BRNZ', 0x2D, num_operands=1, handler=_brnz),
    0x2F: Instruction('CALL', 0x2F, num_operands=1, handler=_call),
    0x9D: Instruction('CALLZ', 0x9D, num_operands=1, handler=_callz),
    0x9E: Instruction('CALLNZ', 0x9E, num_operands=1, handler=_callnz),
    0x9F: Instruction('RETN', 0x9F, num_operands=1, handler=_retn),
    0x30: Instruction('INT', 0x30, num_operands=1, handler=_int),

    # Loop (2 operands)
    0x5A: Instruction('LOOP', 0x5A, num_operands=2, handler=_loop),
    0xA0: Instruction('LOOPZ', 0xA0, num_operands=2, handler=_loopz),
    0xA1: Instruction('WHILE', 0xA1, num_operands=1, handler=_while),

    # BCD / flag (0-2 operands)
    0x4B: Instruction('SED', 0x4B, num_operands=0, handler=_sed),
    0x4C: Instruction('CLD', 0x4C, num_operands=0, handler=_cld),
    0x4D: Instruction('CLA', 0x4D, num_operands=0, handler=_cla),
    0x4E: Instruction('BCDA', 0x4E, num_operands=2, handler=_bcda),
    0x4F: Instruction('BCDS', 0x4F, num_operands=2, handler=_bcds),
    0x50: Instruction('BCDCMP', 0x50, num_operands=2, handler=_bcdcmp),
    0x51: Instruction('BCD2BIN', 0x51, num_operands=1, handler=_bcd2bin),
    0x52: Instruction('BIN2BCD', 0x52, num_operands=1, handler=_bin2bcd),
    0x53: Instruction('BCDADD', 0x53, num_operands=2, handler=_bcdadd),
    0x54: Instruction('BCDSUB', 0x54, num_operands=2, handler=_bcdsub),

    # Math functions (1-2 operands)
    0x5B: Instruction('POWR', 0x5B, num_operands=2, handler=_powr),
    0x5C: Instruction('SQRT', 0x5C, num_operands=1, handler=_sqrt),
    0x5D: Instruction('LOG', 0x5D, num_operands=1, handler=_log),
    0x5E: Instruction('EXP', 0x5E, num_operands=1, handler=_exp),
    0x5F: Instruction('SIN', 0x5F, num_operands=1, handler=_sin),
    0x60: Instruction('COS', 0x60, num_operands=1, handler=_cos),
    0x61: Instruction('TAN', 0x61, num_operands=1, handler=_tan),
    0x62: Instruction('ATAN', 0x62, num_operands=1, handler=_atan),
    0x63: Instruction('ASIN', 0x63, num_operands=1, handler=_asin),
    0x64: Instruction('ACOS', 0x64, num_operands=1, handler=_acos),
    0x65: Instruction('DEG', 0x65, num_operands=1, handler=_deg),
    0x66: Instruction('RAD', 0x66, num_operands=1, handler=_rad),
    0x67: Instruction('FLOOR', 0x67, num_operands=1, handler=_floor),
    0x68: Instruction('CEIL', 0x68, num_operands=1, handler=_ceil),
    0x69: Instruction('ROUND', 0x69, num_operands=1, handler=_round),
    0x6A: Instruction('TRUNC', 0x6A, num_operands=1, handler=_trunc),
    0x6B: Instruction('FRAC', 0x6B, num_operands=1, handler=_frac),
    0x6C: Instruction('INTGR', 0x6C, num_operands=1, handler=_intgr),

    # Count / leading/trailing zeros (1-2 operands)
    0x8D: Instruction('CLZ', 0x8D, num_operands=1, handler=_clz),
    0x8E: Instruction('CTZ', 0x8E, num_operands=1, handler=_ctz),
    0x8F: Instruction('POPCNT', 0x8F, num_operands=1, handler=_popcnt),

    # Random (1-3 operands)
    0x48: Instruction('RND', 0x48, num_operands=1, handler=_rnd),
    0x49: Instruction('RNDR', 0x49, num_operands=3, handler=_rndr),

    # Fixed-point (2 operands)
    0xAC: Instruction('FMUL', 0xAC, num_operands=2, handler=_fmul),
    0xAD: Instruction('FDIV', 0xAD, num_operands=2, handler=_fdiv),
    0xAE: Instruction('FTOI', 0xAE, num_operands=1, handler=_ftoi),
    0xAF: Instruction('ITOF', 0xAF, num_operands=1, handler=_itof),

    # Integer/string conversion (2 operands)
    0x83: Instruction('ITOB', 0x83, num_operands=2, handler=_itob),
    0x84: Instruction('BTOI', 0x84, num_operands=2, handler=_btoi),
    0x85: Instruction('ITOS', 0x85, num_operands=2, handler=_itos),
    0x86: Instruction('STOI', 0x86, num_operands=2, handler=_stoi),

    # String operations (1-4 operands)
    0x71: Instruction('STRCPY', 0x71, num_operands=2, handler=_strcpy),
    0x72: Instruction('STRCAT', 0x72, num_operands=2, handler=_strcat),
    0x73: Instruction('STRCMP', 0x73, num_operands=3, handler=_strcmp),
    0x74: Instruction('STRLEN', 0x74, num_operands=1, handler=_strlen),
    0x77: Instruction('STRUPR', 0x77, num_operands=1, handler=_strupr),
    0x78: Instruction('STRLWR', 0x78, num_operands=1, handler=_strlwr),
    0x79: Instruction('STRREV', 0x79, num_operands=1, handler=_strrev),
    0x7A: Instruction('STRFIND', 0x7A, num_operands=2, handler=_strfind),
    0x7B: Instruction('STRFINDI', 0x7B, num_operands=2, handler=_strfindi),
    0x75: Instruction('STREXT', 0x75, num_operands=4, handler=_strext),
    0x76: Instruction('STREXTI', 0x76, num_operands=4, handler=_strexti),

    # Memory operations (2-4 operands)
    0x4A: Instruction('MEMCPY', 0x4A, num_operands=3, handler=_memcpy),
    0x7C: Instruction('MEMSET', 0x7C, num_operands=3, handler=_memset),
    0x7D: Instruction('MEMTEST', 0x7D, num_operands=3, handler=_memtest),
    0x7E: Instruction('MEMMOVE', 0x7E, num_operands=3, handler=_memmove),
    0x99: Instruction('MEMCMP', 0x99, num_operands=4, handler=_memcmp),
    0x9A: Instruction('MEMSWAP', 0x9A, num_operands=3, handler=_memswap),

    # Graphics / sprite (1-3 operands)
    0x31: Instruction('SBLEND', 0x31, num_operands=1, handler=_sblend),
    0x32: Instruction('SREAD', 0x32, num_operands=1, handler=_sread),
    0x33: Instruction('SWRITE', 0x33, num_operands=1, handler=_swrite),
    0x34: Instruction('SROL', 0x34, num_operands=2, handler=_srol),
    0x35: Instruction('SROT', 0x35, num_operands=2, handler=_srot),
    0x36: Instruction('SSHFT', 0x36, num_operands=2, handler=_sshft),
    0x37: Instruction('SFLIP', 0x37, num_operands=1, handler=_sflip),
    0x38: Instruction('SLINE', 0x38, num_operands=2, handler=_sline),
    0x39: Instruction('SRECT', 0x39, num_operands=3, handler=_srect),
    0x3A: Instruction('SCIRC', 0x3A, num_operands=2, handler=_scirc),
    0x3D: Instruction('SFILL', 0x3D, num_operands=1, handler=_sfill),
    0x3E: Instruction('VREAD', 0x3E, num_operands=1, handler=_vread),
    0x3F: Instruction('VWRITE', 0x3F, num_operands=1, handler=_vwrite),
    0x41: Instruction('CHAR', 0x41, num_operands=1, handler=_char),
    0x42: Instruction('TEXT', 0x42, num_operands=1, handler=_text),
    0x55: Instruction('SPBLIT', 0x55, num_operands=1, handler=_spblit),

    # Layer operations (1 operand)
    0xB0: Instruction('LSWAP', 0xB0, num_operands=1, handler=_lswap),
    0xB1: Instruction('LMOVE', 0xB1, num_operands=1, handler=_lmove),
    0xB2: Instruction('LCOPY', 0xB2, num_operands=1, handler=_lcopy),

    # Sound (1 operand)
    0x59: Instruction('STRIG', 0x59, num_operands=1, handler=_strig),

    # Keyboard (1 operand)
    0x43: Instruction('KEYIN', 0x43, num_operands=1, handler=_keyin),
    0x44: Instruction('KEYSTAT', 0x44, num_operands=1, handler=_keystat),
    0x45: Instruction('KEYCOUNT', 0x45, num_operands=1, handler=_keycount),
    0x47: Instruction('KEYCTRL', 0x47, num_operands=1, handler=_keyctrl),

    # Serial (1 operand)
    0xA2: Instruction('SERIN', 0xA2, num_operands=1, handler=_serin),
    0xA3: Instruction('SEROUT', 0xA3, num_operands=1, handler=_serout),
    0xA4: Instruction('SERSTAT', 0xA4, num_operands=1, handler=_serstat),
    0xA5: Instruction('SERCTRL', 0xA5, num_operands=1, handler=_serctrl),

    # Mouse / hardware debug (1-2 operands)
    0xB3: Instruction('MOUSECTRL', 0xB3, num_operands=1, handler=_mousectrl),
    0xA6: Instruction('SETBP', 0xA6, num_operands=2, handler=_setbp),
    0xA7: Instruction('CLRBP', 0xA7, num_operands=1, handler=_clrbp),

    # Special register access (1 operand)
    0xDD: Instruction('SA', 0xDD, num_operands=1, handler=_sa),
    0xDE: Instruction('SF', 0xDE, num_operands=1, handler=_sf),
    0xDF: Instruction('SV', 0xDF, num_operands=1, handler=_sv),
    0xE0: Instruction('SW', 0xE0, num_operands=1, handler=_sw),
    0xE1: Instruction('VM', 0xE1, num_operands=1, handler=_vm),
    0xE2: Instruction('VL', 0xE2, num_operands=1, handler=_vl),
    0xE3: Instruction('TT', 0xE3, num_operands=1, handler=_tt),
    0xE4: Instruction('TM', 0xE4, num_operands=1, handler=_tm),
    0xE5: Instruction('TC', 0xE5, num_operands=1, handler=_tc),
    0xE6: Instruction('TS', 0xE6, num_operands=1, handler=_ts),
    0xFD: Instruction('VX', 0xFD, num_operands=1, handler=_vx),
    0xFE: Instruction('VY', 0xFE, num_operands=1, handler=_vy),
}