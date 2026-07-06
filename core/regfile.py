"""
Nova-16 Register File

Unified register file with O(1) dispatch tables for core registers (R0-R9, P0-P9)
and callback-based delegation for external registers (sound, mouse, timer, RTC, graphics).

Phase 1 of the reimplantation strategy - extracts register management from the
monolithic CPU class into a focused, testable module.

Phase 4 (Performance): Replaced if/elif chains with dict-based dispatch.
"""

from array import array
from typing import Callable, Optional


def _build_register_code_map() -> dict[int, tuple[int, str]]:
    """Build the register code → (idx, reg_type) lookup table.

    Matches the original CPU._build_register_lookup_table() mapping exactly.
    """
    lookup: dict[int, tuple[int, str]] = {}

    # Real-time clock registers
    lookup[0xC3] = (0, 'C0')
    lookup[0xC4] = (0, 'C1')

    # Mouse registers
    lookup[0xC5] = (0, 'MX')
    lookup[0xC6] = (0, 'MY')
    lookup[0xC7] = (0, 'MB')

    # VC register (moved to 0xC8)
    lookup[0xC8] = (3, 'V')

    # P register byte access (0xC9-0xD2 for high bytes, 0xD3-0xDC for low bytes)
    for i in range(10):
        lookup[0xC9 + i] = (i, 'P_high')  # P0: to P9: (high bytes)
        lookup[0xD3 + i] = (i, 'P_low')   # :P0 to :P9 (low bytes)

    # Sound registers
    lookup[0xDD] = (0, 'SA')
    lookup[0xDE] = (0, 'SF')
    lookup[0xDF] = (0, 'SV')
    lookup[0xE0] = (0, 'SW')

    # Video registers
    lookup[0xE1] = (2, 'V')   # VM register - Vregisters[2]
    lookup[0xE2] = (0, 'VL')  # Video Layer register

    # Timer registers
    lookup[0xE3] = (0, 'TT')  # Timer Time/Counter
    lookup[0xE4] = (1, 'TM')  # Timer Modulo
    lookup[0xE5] = (2, 'TC')  # Timer Control
    lookup[0xE6] = (3, 'TS')  # Timer Speed

    # R registers (0xE7-0xF0)
    for i in range(10):
        lookup[0xE7 + i] = (i, 'R')

    # P registers (0xF1-0xFA)
    for i in range(10):
        lookup[0xF1 + i] = (i, 'P')

    # SP and FP (same as P8, P9)
    lookup[0xFB] = (8, 'P')   # SP = P8
    lookup[0xFC] = (9, 'P')   # FP = P9

    # V registers (0xFD-0xFE) - VX, VY
    lookup[0xFD] = (0, 'V')   # VX
    lookup[0xFE] = (1, 'V')   # VY

    return lookup


REGISTER_CODE_MAP: dict[int, tuple[int, str]] = _build_register_code_map()


class RegisterFile:
    """Unified register file with O(1) dispatch tables.

    Core registers (R0-R9, P0-P9) are stored directly in compact arrays.
    External registers (sound, mouse, timer, etc.) are accessed via registered
    getter/setter callbacks, keeping the register file decoupled from peripherals.

    Usage:
        regfile = RegisterFile()
        regfile.get('R', 0)       # Read R0
        regfile.set('P', 3, 42)   # Write P3
        regfile.get('P_high', 1)  # High byte of P1
        regfile.set('P_low', 2, 0xFF)  # Low byte of P2
    """

    # Class-level constant (built once at module load)
    REGISTER_CODE_MAP: dict[int, tuple[int, str]] = REGISTER_CODE_MAP

    def __init__(self):
        """Initialize register file with default values."""
        # R registers (8-bit)
        self.R = [0] * 10  # R0-R9 (list for backward compatibility with code
                            # that assigns values > 255; Rregisters[i] = value
                            # should not raise ValueError, even though
                            # architectural width is 8 bits -- masking
                            # is applied by the register property setters)

        # P registers (16-bit) - plain list for full backward compatibility
        # (tests and legacy code use list.copy(), slice assignment, etc.)
        self.P = [0] * 10  # P0-P9
        self.P[8] = 0xFFFF  # SP (Stack Pointer)
        self.P[9] = 0xFFFF  # FP (Frame Pointer)

        # External register getter/setter callbacks
        # Maps reg_type → getter callable: getter(idx) → int
        # Maps reg_type → setter callable: setter(idx, value) → None
        self._external_getters: dict[str, Callable[[int], int]] = {}
        self._external_setters: dict[str, Callable[[int, int], None]] = {}

        # Dict-based dispatch tables for core register types
        # Avoids if/elif chain overhead in the hot get()/set() path
        self._get_dispatchers: dict[str, Callable[[int], int]] = {
            'R': lambda idx: self.R[idx],
            'P': lambda idx: self.P[idx],
            'P_high': lambda idx: (self.P[idx] >> 8) & 0xFF,
            'P_low': lambda idx: self.P[idx] & 0xFF,
        }
        self._set_dispatchers: dict[str, Callable[[int, int], None]] = {
            'R': lambda idx, val: self.R.__setitem__(idx, val & 0xFF),
            'P': lambda idx, val: self.P.__setitem__(idx, val & 0xFFFF),
            'P_high': lambda idx, val: self.P.__setitem__(
                idx, (self.P[idx] & 0x00FF) | ((val & 0xFF) << 8)),
            'P_low': lambda idx, val: self.P.__setitem__(
                idx, (self.P[idx] & 0xFF00) | (val & 0xFF)),
        }

    # ---- External register registration ----

    def register_external(self, reg_type: str,
                          getter: Callable[[int], int],
                          setter: Optional[Callable[[int, int], None]] = None):
        """Register an external register type with getter/setter callbacks.

        External registers are those not stored directly in the RegisterFile
        but proxied to other subsystems (e.g., sound SA/SF/SV/SW, mouse MX/MY/MB,
        timer TT/TM/TC/TS, RTC C0/C1, graphics VX/VY/VC/VM/VL).

        Args:
            reg_type: The register type string (e.g., 'V', 'SA', 'MX', 'TT').
            getter: Callable(idx) → int to read register value.
            setter: Optional callable(idx, value) to write register value.
                    Set to None for read-only registers.
        """
        self._external_getters[reg_type] = getter
        if setter is not None:
            self._external_setters[reg_type] = setter
        elif reg_type in self._external_setters:
            del self._external_setters[reg_type]

    # ---- Core register dispatch ----

    def get(self, reg_type: str, idx: int) -> int:
        """Get register value by type and index. O(1) dispatch.

        Args:
            reg_type: One of 'R', 'P', 'P_high', 'P_low', or an external type.
            idx: Register index (0-9 for core registers).

        Returns:
            Register value as int.

        Raises:
            ValueError: If the register type is unknown.
        """
        # Dict dispatch for core types (faster than if/elif chain)
        dispatcher = self._get_dispatchers.get(reg_type)
        if dispatcher is not None:
            return dispatcher(idx)
        # Fall through to external getters
        if reg_type in self._external_getters:
            return self._external_getters[reg_type](idx)
        raise ValueError(f"Unknown register type: {reg_type}")

    def set(self, reg_type: str, idx: int, value: int):
        """Set register value by type and index. O(1) dispatch.

        Args:
            reg_type: One of 'R', 'P', 'P_high', 'P_low', or an external type.
            idx: Register index (0-9 for core registers).
            value: New value (will be masked to appropriate bit width).

        Raises:
            ValueError: If the register type is unknown or read-only.
        """
        # Dict dispatch for core types (faster than if/elif chain)
        dispatcher = self._set_dispatchers.get(reg_type)
        if dispatcher is not None:
            dispatcher(idx, value)
            return
        # Fall through to external setters
        if reg_type in self._external_setters:
            self._external_setters[reg_type](idx, value)
        elif reg_type in self._external_getters:
            raise ValueError(f"Register type '{reg_type}' is read-only")
        else:
            raise ValueError(f"Unknown register type: {reg_type}")

    # ---- Register code lookup ----

    def lookup(self, reg_code: int) -> tuple[int, str]:
        """Look up register by opcode byte. Returns (idx, reg_type) tuple.

        Args:
            reg_code: The opcode byte (0x00-0xFF).

        Returns:
            Tuple of (register_index, register_type).

        Raises:
            KeyError: If the register code is unknown.
        """
        try:
            return self.REGISTER_CODE_MAP[reg_code]
        except KeyError:
            # Backward compatibility: treat 0x00 as R0
            if reg_code == 0x00:
                return (0, 'R')
            raise KeyError(f"Unknown register code: 0x{reg_code:02X}")

    def decode_register_code(self, reg_code: int) -> tuple[int, str]:
        """Alias for lookup() used by the standalone operand decoder.

        Returns:
            Tuple of (register_index, register_type).
        """
        return self.lookup(reg_code)

    # ---- Bulk operations ----

    def reset_all(self):
        """Reset all core registers to their default values."""
        self.R[:] = [0] * 10
        # array('H') doesn't support slice assignment from list directly
        self.P = array('H', [0] * 10)
        self.P[8] = 0xFFFF  # SP
        self.P[9] = 0xFFFF  # FP

    def get_state(self) -> dict:
        """Get complete register state for debugging/profiling.

        Returns:
            dict with 'r_registers' (list of ints) and 'p_registers' (list of ints).
        """
        return {
            'r_registers': list(self.R),
            'p_registers': list(self.P),
        }

    def set_state(self, state: dict):
        """Set complete register state from a state dict.

        Args:
            state: dict with optional 'r_registers' and 'p_registers' keys.
        """
        if 'r_registers' in state:
            for i in range(min(10, len(state['r_registers']))):
                self.R[i] = state['r_registers'][i] & 0xFF
        if 'p_registers' in state:
            for i in range(min(10, len(state['p_registers']))):
                self.P[i] = state['p_registers'][i] & 0xFFFF

    def __repr__(self) -> str:
        """String representation for debugging."""
        r_str = ' '.join(f'R{i}=0x{r:02X}' for i, r in enumerate(self.R))
        p_str = ' '.join(f'P{i}=0x{p:04X}' for i, p in enumerate(self.P))
        return f"RegisterFile({r_str} | {p_str})"