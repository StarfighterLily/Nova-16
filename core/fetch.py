"""
Nova-16 Operand Decoder Module

Standalone operand decoder that parses the prefixed-mode instruction format
without any CPU state dependency. Pure functions produce structured Operand
namedtuples ready for execution.

Phase 6.1 of the reimplantation strategy.

Phase 3 (Performance): Added operand object pooling to reduce allocation overhead.

Operand encoding (prefixed-mode format):
    Mode byte layout (1 byte):
        Bits 1-0: operand 1 mode (if applicable)
        Bits 3-2: operand 2 mode (if applicable)  
        Bits 5-4: operand 3 mode (if applicable)
        Bit 6:    indexed flag (for memory references)
        Bit 7:    direct flag (for memory references)

    Mode values:
        0 = Register direct  → followed by 1 byte register code
        1 = Immediate 8-bit  → followed by 1 byte value
        2 = Immediate 16-bit → followed by 2 bytes (big-endian)
        3 = Memory reference → interpretation depends on bits 6 & 7

    Memory reference types (mode=3):
        direct=0, indexed=0 → Register indirect [reg]     → 1 byte reg code
        direct=0, indexed=1 → Register indexed [reg+offs]  → 1 byte reg code + 1 byte offset
        direct=1, indexed=0 → Direct memory [addr16]       → 2 byte address
        direct=1, indexed=1 → Direct indexed [addr16+offs] → 2 byte address + 1 byte offset
"""

from typing import List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class Operand:
    """Structured operand descriptor produced by OperandDecoder.
    
    Attributes:
        mode: Raw 2-bit mode encoding (0=register, 1=imm8, 2=imm16, 3=memory).
        type: One of 'register', 'immediate', 'memory'.
        reg_type: For register operands: 'R', 'P', 'V', 'TT', 'SA', etc.
        reg_idx: For register operands: index within register group.
        value: For immediate operands: the literal value.
        size: For immediate operands: bit width (8 or 16).
        address: For memory-direct operands: the 16-bit address.
        indirect: For memory-indirect operands: whether [reg] addressing.
        indexed: For memory-indexed operands: whether [reg+offset] or [addr+offset].
        index: Offset byte for indexed addressing.
        is_register: Pre-computed boolean for fast access (avoids property overhead).
        is_immediate: Pre-computed boolean for fast access.
        is_memory: Pre-computed boolean for fast access.
    """
    mode: int
    type: str = ''
    reg_type: str = ''
    reg_idx: int = 0
    value: int = 0
    size: int = 0
    address: int = 0
    indirect: bool = False
    indexed: bool = False
    index: int = 0
    is_register: bool = False
    is_immediate: bool = False
    is_memory: bool = False

    def reset(self):
        """Minimal reset for pool reuse — only fields that may hold stale values."""
        self.mode = 0
        self.value = 0
        self.size = 0
        self.address = 0
        self.indirect = False
        self.indexed = False
        self.index = 0
        self.is_register = False
        self.is_immediate = False
        self.is_memory = False
        # type, reg_type, reg_idx are always set by every decode branch
        # and do not need clearing for pool reuse

    @classmethod
    def register(cls, reg_type: str, reg_idx: int) -> 'Operand':
        """Create a register operand."""
        return cls(mode=0, type='register', reg_type=reg_type, reg_idx=reg_idx)

    @classmethod
    def immediate(cls, value: int, size: int = 8) -> 'Operand':
        """Create an immediate operand."""
        mode = 1 if size == 8 else 2
        return cls(mode=mode, type='immediate', value=value, size=size)

    @classmethod
    def memory_direct(cls, address: int) -> 'Operand':
        """Create a direct memory operand [imm16]."""
        return cls(mode=3, type='memory', address=address, indirect=False, indexed=False)

    @classmethod
    def memory_indirect(cls, reg_type: str, reg_idx: int) -> 'Operand':
        """Create a register-indirect memory operand [reg]."""
        return cls(mode=3, type='memory', indirect=True, indexed=False,
                   reg_type=reg_type, reg_idx=reg_idx)

    @classmethod
    def memory_indexed(cls, reg_type: str, reg_idx: int, offset: int) -> 'Operand':
        """Create a register-indexed memory operand [reg+offset]."""
        return cls(mode=3, type='memory', indirect=False, indexed=True,
                   reg_type=reg_type, reg_idx=reg_idx, index=offset)

    @classmethod
    def memory_direct_indexed(cls, address: int, offset: int) -> 'Operand':
        """Create a direct-indexed memory operand [imm16+offset]."""
        return cls(mode=3, type='memory', address=address, indirect=False, indexed=True,
                   index=offset)


# ── Operand object pool ────────────────────────────────────────────────
# Reduces allocation overhead by reusing Operand instances.

_operand_pool: List[Operand] = []


def _acquire_operand() -> Operand:
    """Get an Operand from the pool, or create a new one if the pool is empty."""
    if _operand_pool:
        op = _operand_pool.pop()
        op.reset()
        return op
    return Operand(mode=0)


def _release_operand(op: Operand):
    """Return an Operand to the pool for reuse."""
    _operand_pool.append(op)


# ── Decoding functions ─────────────────────────────────────────────────


def decode_operands(memory, pc: int, mode_byte: int, num_operands: int,
                    reg_index_fn) -> Tuple[List[Operand], int]:
    """Decode operands from instruction stream starting at pc.
    
    Pure function — no CPU state dependency beyond memory and reg_index_fn.
    
    Args:
        memory: Memory object with read_byte(addr).
        pc: Current program counter (byte address in memory).
        mode_byte: The mode byte following the opcode.
        num_operands: Expected number of operands (0 for no-operand instructions).
        reg_index_fn: Callable(reg_code) → (idx, reg_type) for register lookup.
    
    Returns:
        (operands_list, total_byte_length) where total_byte_length is the
        number of bytes consumed by operand data (NOT including the mode byte).
    """
    operands: List[Operand] = []
    addr = pc
    direct_bit = (mode_byte >> 7) & 1
    indexed_bit = (mode_byte >> 6) & 1

    # Cache commonly used methods locally for hot-path access
    read_byte = memory.read_byte_fast

    for i in range(num_operands):
        mode = (mode_byte >> (i * 2)) & 0x3

        if mode == 0:  # Register direct
            reg_code = read_byte(addr)
            addr = (addr + 1) & 0xFFFF
            idx, typ = reg_index_fn(reg_code)
            op = _acquire_operand()
            op.mode = 0
            op.type = 'register'
            op.reg_type = typ
            op.reg_idx = idx
            op.is_register = True
            operands.append(op)

        elif mode == 1:  # Immediate 8-bit
            value = read_byte(addr)
            addr = (addr + 1) & 0xFFFF
            op = _acquire_operand()
            op.mode = 1
            op.type = 'immediate'
            op.value = value
            op.size = 8
            op.is_immediate = True
            operands.append(op)

        elif mode == 2:  # Immediate 16-bit
            high = read_byte(addr)
            low = read_byte((addr + 1) & 0xFFFF)
            addr = (addr + 2) & 0xFFFF
            op = _acquire_operand()
            op.mode = 2
            op.type = 'immediate'
            op.value = (high << 8) | low
            op.size = 16
            op.is_immediate = True
            operands.append(op)

        elif mode == 3:  # Memory reference
            operand = _decode_memory_ref(memory, addr, direct_bit, indexed_bit,
                                         reg_index_fn)
            operands.append(operand)
            # Advance PC past the memory reference bytes
            byte_len = _memory_ref_byte_length(direct_bit, indexed_bit)
            addr = (addr + byte_len) & 0xFFFF
        else:
            raise ValueError(f"Invalid operand mode: {mode}")

    byte_length = (addr - pc) & 0xFFFF
    return operands, byte_length


def _decode_memory_ref(memory, addr: int, direct: int, indexed: int,
                       reg_index_fn) -> Operand:
    """Decode a single memory reference operand."""
    op = _acquire_operand()
    op.mode = 3
    op.type = 'memory'
    op.is_memory = True

    if direct and not indexed:
        # Direct memory address [imm16]
        high = memory.read_byte_fast(addr)
        low = memory.read_byte_fast((addr + 1) & 0xFFFF)
        op.address = (high << 8) | low
        op.indirect = False
        op.indexed = False

    elif not direct and not indexed:
        # Register indirect [reg]
        reg_code = memory.read_byte_fast(addr)
        idx, typ = reg_index_fn(reg_code)
        if typ not in ('P', 'R'):
            _release_operand(op)
            raise ValueError(f"Invalid register type '{typ}' for indirect addressing")
        op.indirect = True
        op.indexed = False
        op.reg_type = typ
        op.reg_idx = idx

    elif not direct and indexed:
        # Register indexed [reg + offset]
        reg_code = memory.read_byte_fast(addr)
        offset = memory.read_byte_fast((addr + 1) & 0xFFFF)
        idx, typ = reg_index_fn(reg_code)
        if typ not in ('P', 'R'):
            _release_operand(op)
            raise ValueError(f"Invalid register type '{typ}' for indexed addressing")
        op.indirect = False
        op.indexed = True
        op.reg_type = typ
        op.reg_idx = idx
        op.index = offset

    elif direct and indexed:
        # Direct indexed [imm16 + offset]
        high = memory.read_byte_fast(addr)
        low = memory.read_byte_fast((addr + 1) & 0xFFFF)
        offset = memory.read_byte_fast((addr + 2) & 0xFFFF)
        base_addr = (high << 8) | low
        op.address = base_addr
        op.indirect = False
        op.indexed = True
        op.index = offset

    return op


def _memory_ref_byte_length(direct: int, indexed: int) -> int:
    """Return the number of bytes consumed by a memory reference operand."""
    if direct and not indexed:
        return 2  # [imm16]
    elif not direct and not indexed:
        return 1  # [reg]
    elif not direct and indexed:
        return 2  # [reg + offset]
    elif direct and indexed:
        return 3  # [imm16 + offset]
    return 0


def calculate_memory_address(operand: Operand, regfile) -> int:
    """Calculate the effective address for a memory operand.
    
    Pure function — resolves the address from an Operand using register values.
    
    Args:
        operand: An Operand with type='memory'.
        regfile: Object with .get(reg_type, idx) method for register values.
    
    Returns:
        16-bit effective address.
    """
    if operand.type != 'memory':
        raise ValueError(f"Cannot calculate address for operand type '{operand.type}'")

    if operand.address and not operand.indexed:
        # Direct memory [imm16]
        return operand.address & 0xFFFF

    elif operand.indirect:
        # Register indirect [reg]
        base = regfile.get(operand.reg_type, operand.reg_idx)
        return base & 0xFFFF

    elif operand.indexed:
        if operand.address:
            # Direct indexed [imm16 + offset]
            return (operand.address + operand.index) & 0xFFFF
        else:
            # Register indexed [reg + offset]. Both assemblers
            # (nova_assembler.py, nova/assembler/codegen.py) encode this
            # offset byte as a signed two's-complement displacement for
            # every register, not just SP/FP -- e.g. [P0-4] assembles the
            # same way as [FP-4] -- and nova_disassembler.py decodes it as
            # signed universally too. The offset must be sign-extended here
            # to match, for every register.
            base = regfile.get(operand.reg_type, operand.reg_idx)
            signed_offset = operand.index if operand.index < 128 else operand.index - 256
            return (base + signed_offset) & 0xFFFF

    return 0


def release_operands(operands: List[Operand]):
    """Release a list of operands back to the pool after instruction execution."""
    for op in operands:
        _release_operand(op)