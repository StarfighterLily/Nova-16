"""
Astrid Built-in System Functions
Provides system-level operations and interrupt handling for Nova-16.
"""

from typing import Dict, List, Any
from ..utils.logger import get_logger

logger = get_logger(__name__)


class SystemBuiltins:
    """Built-in system functions for Astrid."""

    def __init__(self):
        self.functions = {
            'enable_interrupts': self._enable_interrupts,
            'disable_interrupts': self._disable_interrupts,
            'set_interrupt_handler': self._set_interrupt_handler,
            'configure_timer': self._configure_timer,
            'read_keyboard': self._read_keyboard,
            'clear_keyboard_buffer': self._clear_keyboard_buffer,
            'get_timer_value': self._get_timer_value,
            'set_timer_match': self._set_timer_match,
            'memory_read': self._memory_read,
            'memory_write': self._memory_write,
            'halt': self._halt,
            'reset': self._reset,
            'vector': self._vector,
            'memory.region': self._memory_region,
            'hardware.reset': self._hardware_reset,
            'memory.initialize_heap': self._memory_initialize_heap,
            'setup_timer_interrupt': self._setup_timer_interrupt,
            'setup_keyboard_interrupt': self._setup_keyboard_interrupt,
            'clear_timer_interrupt': self._clear_timer_interrupt,
            'clear_keyboard_interrupt': self._clear_keyboard_interrupt,
            'software_interrupt': self._software_interrupt,
            'random': self._random,
            'random_range': self._random_range,
        }

    def get_function(self, name: str):
        """Get a built-in function by name."""
        return self.functions.get(name)

    def _enable_interrupts(self) -> str:
        """
        Enable hardware interrupts.

        Returns:
            Assembly code for enabling interrupts
        """
        return """
; Enable interrupts
STI
"""

    def _disable_interrupts(self) -> str:
        """
        Disable hardware interrupts.

        Returns:
            Assembly code for disabling interrupts
        """
        return """
; Disable interrupts
CLI
"""

    def _set_interrupt_handler(self, vector: int, handler_address: int) -> str:
        """
        Set an interrupt handler for the specified vector.

        Args:
            vector: Interrupt vector number (0-7)
            handler_address: Memory address of the handler

        Returns:
            Assembly code for setting the interrupt handler
        """
        vector_address = 0x0100 + (vector * 4)
        return f"""
; Set interrupt handler for vector {vector} to address 0x{handler_address:04X}
MOV P0, 0x{vector_address:04X}    ; Vector table entry
MOV P1, 0x{handler_address:04X}   ; Handler address
MOV [P0], P1                      ; Store handler address
"""

    def _configure_timer(self, match_value: int, speed: int, control: int) -> str:
        """
        Configure the hardware timer.

        Args:
            match_value: Timer match value (0-255)
            speed: Timer speed (0-255)
            control: Timer control flags

        Returns:
            Assembly code for configuring the timer
        """
        return f"""
; Configure timer: match={match_value}, speed={speed}, control={control}
MOV TM, {match_value}    ; Timer match value
MOV TS, {speed}          ; Timer speed
MOV TC, {control}        ; Timer control
"""

    def _read_keyboard(self) -> str:
        """
        Read a key from the keyboard buffer.

        Returns:
            Assembly code for reading keyboard input
        """
        return """
; Read keyboard input
KEYIN R0
"""

    def _clear_keyboard_buffer(self) -> str:
        """
        Clear the keyboard input buffer.

        Returns:
            Assembly code for clearing keyboard buffer
        """
        return """
; Clear keyboard buffer
KEYCLEAR
"""

    def _get_timer_value(self) -> str:
        """
        Get the current timer value.

        Returns:
            Assembly code for reading timer value
        """
        return """
; Get current timer value
MOV R0, TT    ; Timer value register
"""

    def _set_timer_match(self, match_value: int) -> str:
        """
        Set the timer match value.

        Args:
            match_value: Timer match value (0-255)

        Returns:
            Assembly code for setting timer match
        """
        return f"""
; Set timer match to {match_value}
MOV TM, {match_value}
"""

    def _memory_read(self, address: int) -> str:
        """
        Read a byte from memory.

        Args:
            address: Memory address to read from

        Returns:
            Assembly code for memory read
        """
        return f"""
; Read byte from address 0x{address:04X}
MOV P0, 0x{address:04X}
MOV R0, [P0]
"""

    def _memory_write(self, address: int, value: int) -> str:
        """
        Write a byte to memory.

        Args:
            address: Memory address to write to
            value: Value to write (0-255)

        Returns:
            Assembly code for memory write
        """
        return f"""
; Write byte {value} to address 0x{address:04X}
MOV P0, 0x{address:04X}
MOV R0, {value}
MOV [P0], R0
"""

    def _halt(self) -> str:
        """
        Halt the processor.

        Returns:
            Assembly code for halting
        """
        return """
; Halt processor
HLT
"""

    def _reset(self) -> str:
        """
        Reset the system.

        Returns:
            Assembly code for system reset
        """
        return """
; System reset
RESET
"""

    def _vector(self, vector_number: int) -> str:
        """
        Create an interrupt vector reference.

        Args:
            vector_number: Interrupt vector number (0-7)

        Returns:
            Assembly code for interrupt vector initialization
        """
        return f"""
; Initialize interrupt vector {vector_number}
; Vector address: 0x0100 + ({vector_number} * 4)
"""

    def _memory_region(self, start_address: int, size: int) -> str:
        """
        Define a memory region.

        Args:
            start_address: Starting address of the region
            size: Size of the region in bytes

        Returns:
            Assembly code for memory region definition
        """
        return f"""
; Define memory region from 0x{start_address:04X} to 0x{start_address + size - 1:04X}
; Size: {size} bytes
"""

    def _hardware_reset(self) -> str:
        """
        Reset all hardware subsystems.

        Returns:
            Assembly code for hardware reset
        """
        return """
; Hardware reset - reset all subsystems
MOV VM, 0        ; Reset video mode
MOV VL, 0        ; Reset video layer
MOV SA, 0        ; Reset sound address
MOV SF, 0        ; Reset sound frequency
MOV SV, 0        ; Reset sound volume
MOV SW, 0        ; Reset sound waveform
MOV TT, 0        ; Reset timer
MOV TM, 0        ; Reset timer match
MOV TC, 0        ; Reset timer control
MOV TS, 0        ; Reset timer speed
"""

    def _memory_initialize_heap(self, start_address: int, end_address: int) -> str:
        """
        Initialize the heap memory region.

        Args:
            start_address: Start of heap
            end_address: End of heap

        Returns:
            Assembly code for heap initialization
        """
        return f"""
; Initialize heap from 0x{start_address:04X} to 0x{end_address:04X}
; Heap size: {end_address - start_address} bytes
"""

    def _setup_timer_interrupt(self, handler_address: int, timer_value: int, match_value: int, speed: int) -> str:
        """
        Set up timer interrupt with handler and configuration.

        Args:
            handler_address: Address of interrupt handler
            timer_value: Initial timer value (0-255)
            match_value: Timer match value (0-255)
            speed: Timer speed (0-255)

        Returns:
            Assembly code for timer interrupt setup
        """
        return f"""
; Setup timer interrupt
; Set timer interrupt handler (vector 0)
MOV P0, 0x0100                  ; Timer vector address
MOV P1, 0x{handler_address:04X} ; Handler address
MOV [P0], P1                    ; Store handler address
; Configure timer
MOV TT, {timer_value}           ; Timer value
MOV TM, {match_value}           ; Timer match
MOV TS, {speed}                 ; Timer speed
MOV TC, 3                       ; Enable timer and interrupt
"""

    def _setup_keyboard_interrupt(self, handler_address: int) -> str:
        """
        Set up keyboard interrupt with handler.

        Args:
            handler_address: Address of interrupt handler

        Returns:
            Assembly code for keyboard interrupt setup
        """
        return f"""
; Setup keyboard interrupt
; Set keyboard interrupt handler (vector 2)
MOV P0, 0x0108                  ; Keyboard vector address
MOV P1, 0x{handler_address:04X} ; Handler address
MOV [P0], P1                    ; Store handler address
; Enable keyboard interrupt
; (Hardware-specific keyboard setup would go here)
"""

    def _clear_timer_interrupt(self) -> str:
        """
        Clear timer interrupt flag.

        Returns:
            Assembly code for clearing timer interrupt
        """
        return """
; Clear timer interrupt
MOV R0, TC
AND R0, 0xFE                    ; Clear interrupt pending bit
MOV TC, R0
"""

    def _clear_keyboard_interrupt(self) -> str:
        """
        Clear keyboard interrupt flag.

        Returns:
            Assembly code for clearing keyboard interrupt
        """
        return """
; Clear keyboard interrupt
; (Hardware-specific keyboard interrupt clear)
"""

    def _software_interrupt(self, vector: int) -> str:
        """
        Trigger a software interrupt.

        Args:
            vector: Interrupt vector number (0-7)

        Returns:
            Assembly code for software interrupt
        """
        return f"""
; Software interrupt vector {vector}
INT {vector}
"""

    def _random(self) -> str:
        """
        Generate a random 16-bit number (0-65535).

        Returns:
            Assembly code for random number generation
        """
        return """
; Generate random number (0-65535)
RND P0"""

    def _random_range(self, min_val, max_val) -> str:
        """
        Generate a random number within a specified range.

        Args:
            min_val: Minimum value (register or immediate, string or int)
            max_val: Maximum value (register or immediate, string or int)

        Returns:
            Assembly code for ranged random number generation
        """
        # Convert to strings if they're integers
        min_val = str(min_val) if not isinstance(min_val, str) else min_val
        max_val = str(max_val) if not isinstance(max_val, str) else max_val
        
        # Determine if we're using registers or immediates
        min_is_reg = min_val.startswith(('R', 'P'))
        max_is_reg = max_val.startswith(('R', 'P'))
        
        if min_is_reg and max_is_reg:
            # Both are registers
            return f"""
; Generate random number between {min_val} and {max_val}
RNDR P0, {min_val}, {max_val}"""
        elif not min_is_reg and not max_is_reg:
            # Both are immediates - need to determine size
            try:
                min_int = int(min_val, 0) if min_val.startswith('0x') else int(min_val)
                max_int = int(max_val, 0) if max_val.startswith('0x') else int(max_val)
                
                # Use 16-bit immediate if either value is > 255
                # This ensures both operands use the same instruction variant
                if min_int > 255 or max_int > 255:
                    return f"""
; Generate random number between {min_val} and {max_val} (16-bit)
RNDR P0, {min_val}, {max_val}"""
                else:
                    return f"""
; Generate random number between {min_val} and {max_val} (8-bit)
RNDR P0, {min_val}, {max_val}"""
            except ValueError:
                # Fallback to treating as registers
                return f"""
; Generate random number between {min_val} and {max_val}
RNDR P0, {min_val}, {max_val}"""
        else:
            # Mixed registers and immediates - load immediates to temp registers
            # Avoid P8 (stack pointer) - use P6, P7 as temp registers instead
            temp_reg1 = "P6" if min_val != "P6" and max_val != "P6" else "P7"
            temp_reg2 = "P7" if temp_reg1 != "P7" else "P5"
            
            code = ["; Generate random number with mixed reg/immediate"]
            
            if not min_is_reg:
                code.append(f"MOV {temp_reg1}, {min_val}")
                min_val = temp_reg1
                
            if not max_is_reg:
                code.append(f"MOV {temp_reg2}, {max_val}")
                max_val = temp_reg2
                
            code.append(f"RNDR P0, {min_val}, {max_val}")
            
            return "\n".join(code)


# Global instance for use by the compiler
system_builtins = SystemBuiltins()
