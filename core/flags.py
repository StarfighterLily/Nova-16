"""
Nova-16 Flags Module

Compact 12-bit flag management using bitfield operations instead of a list.
Provides O(1) flag read/write, parity table, and flag-setting methods for
8-bit, 16-bit, and BCD operations.

Phase 2 of the reimplantation strategy - extracts flag management from the
monolithic CPU class into a focused, testable module.
"""

from typing import Union


def _build_parity_table() -> list:
    """Build parity lookup table for fast parity flag calculation.

    Returns a list of 256 bools where table[i] is True if i has even parity.
    """
    table = [0] * 256
    for i in range(256):
        # Count number of 1 bits using efficient method
        count = 0
        n = i
        while n:
            count += n & 1
            n >>= 1
        table[i] = (count % 2) == 0  # True if even parity
    return table


# Module-level parity table (built once at import time)
PARITY_TABLE: list = _build_parity_table()


class Flags:
    """Compact 12-bit flag register - bitwise operations only.

    Replaces the 12-element list + 24 property methods + 5 flag-setting methods
    with a single integer bitfield and O(1) bitwise operations.

    Supports backward-compatible list-style access via __getitem__/__setitem__
    so that existing code like ``cpu.flags[7] = 1`` continues to work.

    Bit positions:
        0 (T): Trap         - Enable single-step mode
        1 (S): Sign         - Result is negative
        2 (O): Overflow     - Arithmetic overflow occurred
        3 (B): Break        - Breakpoint hit
        4 (D): Decimal      - BCD mode enabled
        5 (I): Interrupt    - Interrupts enabled
        6 (C): Carry        - Arithmetic carry/borrow occurred
        7 (Z): Zero         - Result is zero
        8 (P): Parity       - Result has even parity
        9 (H): Direction    - CPU runs High to Low
       10 (A): BCD Carry    - BCD operation carry
       11 (E): Hacker       - User is a hacker (not touched by CPU)
    """

    # Bit position constants
    T = 0   # Trap
    S = 1   # Sign
    O = 2   # Overflow
    B = 3   # Break
    D = 4   # Decimal
    I = 5   # Interrupt
    C = 6   # Carry
    Z = 7   # Zero
    P = 8   # Parity
    H = 9   # Direction
    A = 10  # BCD Carry
    E = 11  # Hacker

    # Mask for valid flag bits (12 bits)
    FLAGS_MASK = 0xFFF

    # Pre-computed bit masks for hot-path flag checks (avoid repeated shift operations)
    # Used for frequently-checked flags: I (interrupt), Z (zero), C (carry)
    _INTERRUPT_MASK = 1 << 5   # 0x20
    _ZERO_MASK = 1 << 7       # 0x80
    _CARRY_MASK = 1 << 6      # 0x40
    _SIGN_MASK = 1 << 1       # 0x02
    _OVERFLOW_MASK = 1 << 2   # 0x04

    # Module-level parity table reference (built once)
    PARITY_TABLE = PARITY_TABLE

    # Human-readable flag names (index order)
    FLAG_NAMES = ['T', 'S', 'O', 'B', 'D', 'I', 'C', 'Z', 'P', 'H', 'A', 'E']

    def __init__(self):
        """Initialize all flags to 0."""
        self._bits: int = 0

    # ---- Fast-path flag checks (inline cache-friendly, no property overhead) ----
    # These methods are optimized for the hot path where I, Z, C flags are checked
    # frequently in instruction handlers and interrupt processing.

    def check_I(self) -> bool:
        """Fast check for Interrupt flag - no property overhead."""
        return (self._bits & self._INTERRUPT_MASK) != 0

    def check_Z(self) -> bool:
        """Fast check for Zero flag - no property overhead."""
        return (self._bits & self._ZERO_MASK) != 0

    def check_C(self) -> bool:
        """Fast check for Carry flag - no property overhead."""
        return (self._bits & self._CARRY_MASK) != 0

    def check_S(self) -> bool:
        """Fast check for Sign flag - no property overhead."""
        return (self._bits & self._SIGN_MASK) != 0

    def check_O(self) -> bool:
        """Fast check for Overflow flag - no property overhead."""
        return (self._bits & self._OVERFLOW_MASK) != 0

    # ---- List-style access (backward compatible) ----

    def __getitem__(self, bit: int) -> int:
        """O(1) flag read - supports ``flags[7]`` access pattern.

        Args:
            bit: Flag bit index (0-11).

        Returns:
            1 if the flag is set, 0 otherwise.
        """
        return (self._bits >> bit) & 1

    def __setitem__(self, bit: int, value: Union[bool, int]):
        """O(1) flag write - supports ``flags[7] = 1`` access pattern.

        Args:
            bit: Flag bit index (0-11).
            value: Truthy value to set (True/1) or clear (False/0).
        """
        mask = 1 << bit
        if value:
            self._bits |= mask
        else:
            self._bits &= ~mask

    # ---- Properties ----

    @property
    def trap_flag(self) -> bool:
        """Trap flag (T) - bit 0: Enable single-step mode"""
        return bool(self._bits & (1 << self.T))

    @trap_flag.setter
    def trap_flag(self, value: Union[bool, int]):
        if value:
            self._bits |= (1 << self.T)
        else:
            self._bits &= ~(1 << self.T)

    @property
    def sign_flag(self) -> bool:
        """Sign flag (S) - bit 1: Result is negative"""
        return bool(self._bits & (1 << self.S))

    @sign_flag.setter
    def sign_flag(self, value: Union[bool, int]):
        if value:
            self._bits |= (1 << self.S)
        else:
            self._bits &= ~(1 << self.S)

    @property
    def overflow_flag(self) -> bool:
        """Overflow flag (O) - bit 2: Arithmetic overflow occurred"""
        return bool(self._bits & (1 << self.O))

    @overflow_flag.setter
    def overflow_flag(self, value: Union[bool, int]):
        if value:
            self._bits |= (1 << self.O)
        else:
            self._bits &= ~(1 << self.O)

    @property
    def break_flag(self) -> bool:
        """Break flag (B) - bit 3: Breakpoint hit"""
        return bool(self._bits & (1 << self.B))

    @break_flag.setter
    def break_flag(self, value: Union[bool, int]):
        if value:
            self._bits |= (1 << self.B)
        else:
            self._bits &= ~(1 << self.B)

    @property
    def decimal_flag(self) -> bool:
        """Decimal flag (D) - bit 4: BCD mode enabled"""
        return bool(self._bits & (1 << self.D))

    @decimal_flag.setter
    def decimal_flag(self, value: Union[bool, int]):
        if value:
            self._bits |= (1 << self.D)
        else:
            self._bits &= ~(1 << self.D)

    @property
    def interrupt_flag(self) -> bool:
        """Interrupt flag (I) - bit 5: Interrupts enabled"""
        return bool(self._bits & (1 << self.I))

    @interrupt_flag.setter
    def interrupt_flag(self, value: Union[bool, int]):
        if value:
            self._bits |= (1 << self.I)
        else:
            self._bits &= ~(1 << self.I)

    @property
    def carry_flag(self) -> bool:
        """Carry flag (C) - bit 6: Arithmetic carry/borrow occurred"""
        return bool(self._bits & (1 << self.C))

    @carry_flag.setter
    def carry_flag(self, value: Union[bool, int]):
        if value:
            self._bits |= (1 << self.C)
        else:
            self._bits &= ~(1 << self.C)

    @property
    def zero_flag(self) -> bool:
        """Zero flag (Z) - bit 7: Result is zero"""
        return bool(self._bits & (1 << self.Z))

    @zero_flag.setter
    def zero_flag(self, value: Union[bool, int]):
        if value:
            self._bits |= (1 << self.Z)
        else:
            self._bits &= ~(1 << self.Z)

    @property
    def parity_flag(self) -> bool:
        """Parity flag (P) - bit 8: Result has even parity"""
        return bool(self._bits & (1 << self.P))

    @parity_flag.setter
    def parity_flag(self, value: Union[bool, int]):
        if value:
            self._bits |= (1 << self.P)
        else:
            self._bits &= ~(1 << self.P)

    @property
    def direction_flag(self) -> bool:
        """Direction flag (H) - bit 9: CPU runs High to Low"""
        return bool(self._bits & (1 << self.H))

    @direction_flag.setter
    def direction_flag(self, value: Union[bool, int]):
        if value:
            self._bits |= (1 << self.H)
        else:
            self._bits &= ~(1 << self.H)

    @property
    def bcd_carry_flag(self) -> bool:
        """BCD Carry flag (A) - bit 10: BCD operation carry"""
        return bool(self._bits & (1 << self.A))

    @bcd_carry_flag.setter
    def bcd_carry_flag(self, value: Union[bool, int]):
        if value:
            self._bits |= (1 << self.A)
        else:
            self._bits &= ~(1 << self.A)

    @property
    def hacker_flag(self) -> bool:
        """Hacker flag (E) - bit 11: User is a hacker (not touched by CPU)"""
        return bool(self._bits & (1 << self.E))

    @hacker_flag.setter
    def hacker_flag(self, value: Union[bool, int]):
        if value:
            self._bits |= (1 << self.E)
        else:
            self._bits &= ~(1 << self.E)

    # ---- Aliases ----

    @property
    def decimal_mode(self) -> bool:
        """Decimal mode flag (maps to decimal flag D)"""
        return self.decimal_flag

    @decimal_mode.setter
    def decimal_mode(self, value: Union[bool, int]):
        self.decimal_flag = value

    @property
    def aux_carry(self) -> bool:
        """Auxiliary carry flag (maps to BCD carry flag A)"""
        return self.bcd_carry_flag

    @aux_carry.setter
    def aux_carry(self, value: Union[bool, int]):
        self.bcd_carry_flag = value

    # ---- Bulk operations ----

    def reset_all(self):
        """Reset all flags to 0."""
        self._bits = 0

    def get_state(self) -> list:
        """Get complete flag state as a list of 12 ints (0 or 1).

        Returns:
            List of 12 flag values in index order.
        """
        return [(self._bits >> i) & 1 for i in range(12)]

    def set_state(self, flag_list: list):
        """Set complete flag state from a list of 12 ints or bools.

        Args:
            flag_list: List of 12 flag values (truthy/falsy) in index order.
        """
        self._bits = 0
        for i in range(min(12, len(flag_list))):
            if flag_list[i]:
                self._bits |= (1 << i)

    def pack(self) -> int:
        """Pack flags into a 12-bit integer (for interrupt push).

        Returns:
            12-bit integer with flag bits set.
        """
        return self._bits & self.FLAGS_MASK

    @staticmethod
    def pack_flags(flag_bits: int) -> int:
        """Pack flags from a 12-bit integer (class method variant).

        Args:
            flag_bits: 12-bit integer with flag bits.

        Returns:
            Masked 12-bit value.
        """
        return flag_bits & Flags.FLAGS_MASK

    # ---- Flag-setting methods ----

    def set_from_8bit(self, result: int, original_result: int = None,
                      is_cmp: bool = False,
                      last_operation_was_cmp: bool = False) -> None:
        """Set Z, C, S, P flags from an 8-bit result.

        Matches the original CPU._set_flags_8bit behavior exactly.

        Args:
            result: Masked result value (low 8 bits used).
            original_result: Full result before masking (for carry calculation).
                             If None, uses result.
            is_cmp: If True, this is a CMP operation (sets carry differently).
            last_operation_was_cmp: State tracking from CPU for CMP carry handling.
        """
        if original_result is None:
            original_result = result

        r = result & 0xFF
        orig = original_result

        # Zero flag (Z) - result is zero
        if r == 0:
            self._bits |= (1 << self.Z)
        else:
            self._bits &= ~(1 << self.Z)

        # Carry flag (C) - for subtraction (CMP), set when borrow occurs
        # For other operations, overflow/underflow occurred
        if is_cmp or last_operation_was_cmp:
            if orig < 0:
                self._bits |= (1 << self.C)
            else:
                self._bits &= ~(1 << self.C)
        else:
            if orig > 0xFF or orig < 0:
                self._bits |= (1 << self.C)
            else:
                self._bits &= ~(1 << self.C)

        # Sign flag (S) - result is negative (bit 7 set)
        if r & 0x80:
            self._bits |= (1 << self.S)
        else:
            self._bits &= ~(1 << self.S)

        # Parity flag (P) - even number of 1s in result
        if self.PARITY_TABLE[r]:
            self._bits |= (1 << self.P)
        else:
            self._bits &= ~(1 << self.P)

    def set_from_16bit(self, result: int, original_result: int = None,
                       is_cmp: bool = False,
                       last_operation_was_cmp: bool = False) -> None:
        """Set Z, C, S, P flags from a 16-bit result.

        Matches the original CPU._set_flags_16bit behavior exactly.

        Args:
            result: Masked result value (low 16 bits used).
            original_result: Full result before masking (for carry calculation).
                             If None, uses result.
            is_cmp: If True, this is a CMP operation (sets carry differently).
            last_operation_was_cmp: State tracking from CPU for CMP carry handling.
        """
        if original_result is None:
            original_result = result

        r = result & 0xFFFF
        orig = original_result

        # Zero flag (Z) - result is zero
        if r == 0:
            self._bits |= (1 << self.Z)
        else:
            self._bits &= ~(1 << self.Z)

        # Carry flag (C) 
        if is_cmp or last_operation_was_cmp:
            if orig < 0:
                self._bits |= (1 << self.C)
            else:
                self._bits &= ~(1 << self.C)
        else:
            if orig > 0xFFFF or orig < 0:
                self._bits |= (1 << self.C)
            else:
                self._bits &= ~(1 << self.C)

        # Sign flag (S) - result is negative (bit 15 set)
        if r & 0x8000:
            self._bits |= (1 << self.S)
        else:
            self._bits &= ~(1 << self.S)

        # Parity flag (P) - even number of 1s in low byte
        if self.PARITY_TABLE[r & 0xFF]:
            self._bits |= (1 << self.P)
        else:
            self._bits &= ~(1 << self.P)

    def set_overflow_8bit(self, op1: int, op2: int, result: int,
                          is_subtraction: bool = False) -> None:
        """Set overflow flag for 8-bit operations.

        Args:
            op1: First operand (destination).
            op2: Second operand (source).
            result: Result of the operation.
            is_subtraction: True if this is a subtraction operation.
        """
        if is_subtraction:
            overflow = ((op1 ^ op2) & 0x80) != 0 and ((op1 ^ result) & 0x80) != 0
        else:
            overflow = ((op1 ^ op2) & 0x80) == 0 and ((op1 ^ result) & 0x80) != 0

        if overflow:
            self._bits |= (1 << self.O)
        else:
            self._bits &= ~(1 << self.O)

    def set_overflow_16bit(self, op1: int, op2: int, result: int,
                           is_subtraction: bool = False) -> None:
        """Set overflow flag for 16-bit operations.

        Args:
            op1: First operand (destination).
            op2: Second operand (source).
            result: Result of the operation.
            is_subtraction: True if this is a subtraction operation.
        """
        if is_subtraction:
            overflow = ((op1 ^ op2) & 0x8000) != 0 and ((op1 ^ result) & 0x8000) != 0
        else:
            overflow = ((op1 ^ op2) & 0x8000) == 0 and ((op1 ^ result) & 0x8000) != 0

        if overflow:
            self._bits |= (1 << self.O)
        else:
            self._bits &= ~(1 << self.O)

    def set_from_operation(self, result: int, op1: int, op2: int,
                           width: int = 16, is_subtraction: bool = False,
                           is_cmp: bool = False) -> None:
        """Unified flag-setting for arithmetic/logic operations.

        Convenience method that combines set_from_{8bit,16bit} and
        set_overflow_{8bit,16bit} into a single call.  Reduces the
        common 8-line flag pattern in instruction handlers to 1-2 lines.

        Args:
            result: Full (unmasked) result of the operation.
            op1: First operand (destination before operation).
            op2: Second operand (source).
            width: Bit width of the operation (8 or 16).
            is_subtraction: True for SUB/CMP, False for ADD/ADC.
            is_cmp: True if this is a CMP (comparison, no writeback).
        """
        if width == 8:
            masked = result & 0xFF
            mask = 0xFF
            sign_bit = 0x80
        else:
            masked = result & 0xFFFF
            mask = 0xFFFF
            sign_bit = 0x8000

        if is_cmp or is_subtraction:
            # Overflow: (signs differ between op1 and op2) AND (sign differs from result)
            overflow = ((op1 ^ op2) & sign_bit) and ((op1 ^ result) & sign_bit)
        else:
            # Overflow: (signs same between op1 and op2) AND (sign differs from result)
            overflow = not ((op1 ^ op2) & sign_bit) and ((op1 ^ result) & sign_bit)

        # Zero (Z), Sign (S), Parity (P), Carry (C)
        self._bits &= ~((1 << self.Z) | (1 << self.S) | (1 << self.P) | (1 << self.C))

        if masked == 0:
            self._bits |= (1 << self.Z)
        if masked & sign_bit:
            self._bits |= (1 << self.S)
        if self.PARITY_TABLE[masked & 0xFF]:
            self._bits |= (1 << self.P)
        if is_cmp:
            if result < 0:
                self._bits |= (1 << self.C)
        else:
            if result > mask or result < 0:
                self._bits |= (1 << self.C)

        # Overflow (O)
        self._bits &= ~(1 << self.O)
        if overflow:
            self._bits |= (1 << self.O)

    def set_from_bcd(self, result: int, bcd_carry: bool = False) -> None:
        """Set flags for 8-bit BCD operations.

        Matches original CPU._set_flags_8bit_bcd behavior exactly.

        Args:
            result: BCD result value (low 8 bits).
            bcd_carry: True if BCD operation generated carry/borrow.
        """
        r = result & 0xFF

        # Zero flag (Z) - result is zero
        if r == 0:
            self._bits |= (1 << self.Z)
        else:
            self._bits &= ~(1 << self.Z)

        # BCD Carry flag (A)
        if bcd_carry:
            self._bits |= (1 << self.A)
        else:
            self._bits &= ~(1 << self.A)

        # Regular carry flag is also set for compatibility
        if bcd_carry:
            self._bits |= (1 << self.C)
        else:
            self._bits &= ~(1 << self.C)

        # Sign flag (S) - result is negative (bit 7 set)
        if r & 0x80:
            self._bits |= (1 << self.S)
        else:
            self._bits &= ~(1 << self.S)

        # Parity flag (P) - even number of 1s in result
        if self.PARITY_TABLE[r]:
            self._bits |= (1 << self.P)
        else:
            self._bits &= ~(1 << self.P)

    # ---- Utility ----

    def __repr__(self) -> str:
        """String representation for debugging."""
        names = self.FLAG_NAMES
        set_flags = [names[i] for i in range(12) if self._bits & (1 << i)]
        if set_flags:
            return f"Flags({','.join(set_flags)})"
        return "Flags(none)"

    def __eq__(self, other) -> bool:
        """Compare two Flags objects or a Flags with a list."""
        if isinstance(other, Flags):
            return self._bits == other._bits
        elif isinstance(other, (list, tuple)):
            return self.get_state() == list(other)
        return NotImplemented

    def copy(self) -> 'Flags':
        """Create a deep copy of this Flags object."""
        f = Flags()
        f._bits = self._bits
        return f