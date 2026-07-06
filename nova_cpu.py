import numpy as np
from nova.memory import Memory as mem
import nova_gfx as gpu
import nova_mouse as mouse
import nova_sound as sound
import nova_uart as uart
from core.exec import build_instruction_table, NO_OPERAND_OPCODES
import time
import cProfile
import pstats
from datetime import datetime, timezone
from functools import wraps
from core.flags import Flags
from core.regfile import RegisterFile, REGISTER_CODE_MAP
from core.fetch import decode_operands, calculate_memory_address, Operand

class CPU:
    RTC_EPOCH_UNIX = int(datetime(2018, 7, 17, tzinfo=timezone.utc).timestamp())

    def __init__( self, memory, gfx, keyboard=None, sound_system=None, uart_device=None, mouse_device=None, stack_size = 65535, bus=None, interrupt_controller=None, timer_device=None ):
        self.memory = memory
        self.gfx = gfx
        self.keyboard_device = keyboard
        self.bus = bus
        self.intr_ctrl = interrupt_controller
        self.timer_device = timer_device
        
        # No longer setting circular back-references:
        #   self.memory.cpu = self   -- REMOVED
        #   self.memory.gfx_system = self.gfx  -- REMOVED
        
        # Initialize sound system
        if sound_system is None:
            self.sound = sound.NovaSound()
            # self.sound = None
            # self.sound.set_memory_reference(memory)
        else:
            self.sound = sound_system

        # RegisterFile instance — unified O(1) dispatch for all register types.
        # Rregisters / Pregisters are aliased to regfile.R / regfile.P for
        # backward compatibility with instructions.py and test code.
        self.regfile = RegisterFile()
        self.Rregisters = self.regfile.R  # alias: R0-R9 (8-bit list)
        self.Pregisters = self.regfile.P  # alias: P0-P9 (16-bit array('H'))
        # SP and FP are initialised by RegisterFile (0xFFFF)

        self.pc = 0x0000

        # Flags instance (compact bitfield implementation)
        self.flags_obj = Flags()

        # Flag to track if last operation was CMP for correct carry flag handling
        self._last_operation_was_cmp = False

        self.stack_size = stack_size
        self.stack = []
        
        self.interrupts = [0] * 8  # Interrupt enable flags
        self.interrupts[ 0 ] = 0 # Timer interrupt (T) set to 1 if the Timer interrupt is enabled
        self.interrupts[ 1 ] = 0 # Serial interrupt (S) set to 1 if the Serial interrupt is enabled
        self.interrupts[ 2 ] = 0 # Keyboard interrupt (K) set to 1 if the Keyboard interrupt is enabled
        self.interrupts[ 3 ] = 0 # Mouse interrupt (M) set to 1 if mouse interrupts are enabled
        self.interrupts[ 4 ] = 0 # User interrupt (U1) set to 1 if the User interrupt 1 is enabled

        # Hardware breakpoints
        self.hw_breakpoints = [0] * 4
        self.hw_breakpoint_enabled = [False] * 4

        # Random number generator seed - initialized with system entropy for true randomness
        import random
        self.rng_seed = random.randint(0, 0xFFFF)  # True random seed (0-65535)
        self.rtc_time_source = time.time
        
        self.uart = uart_device if uart_device is not None else uart.NovaUART()
        self.serial = uart.SerialRegisterView(self.uart)  # Legacy serial register compatibility
        self.uart.set_interrupt_callback(self._refresh_pending_interrupt_sources)
        self.mouse = mouse_device if mouse_device is not None else mouse.NovaMouse(self.gfx)
        self.mouse.attach(gfx=self.gfx, cpu_ref=self)
        self.mouse.set_interrupt_callback(self._refresh_pending_interrupt_sources)

        self.keyboard = [0] * 4  # Keyboard data for the keyboard interrupt
        self.keyboard[ 0 ] = 0 # Keyboard data register (D) - current key code
        self.keyboard[ 1 ] = 0 # Keyboard status register (S) - status flags
        self.keyboard[ 2 ] = 0 # Keyboard control register (C) - control flags  
        self.keyboard[ 3 ] = 0 # Keyboard buffer count (B) - number of keys in buffer
        
        self.key_buffer = []  # Circular buffer for keyboard input (max 16 keys)
        self.key_buffer_size = 64

        self.halted = False
        self.cycles = 0  # Total cycles executed
        
        # Pre-computed register lookup table for O(1) access
        self._register_lookup = self._build_register_lookup_table()
        
        # Pre-computed parity lookup table for fast parity calculation
        self._parity_table = self._build_parity_table()
        
        # Interrupt checking optimization
        self.interrupt_check_counter = 0
        self.interrupt_check_frequency = 8  # Check every 8 instructions
        self.last_interrupt_state = 0  # Cache of last interrupt state
        self.has_pending_interrupt_sources = False  # Fast gate for interrupt scan path

        # Breakpoint checking optimization
        self.has_hw_breakpoints = False  # Fast gate for hardware breakpoint scan path

        # Initialize instruction dispatch table (Phase 6: parameterized wrappers)
        self.instruction_table = build_instruction_table()

        # Opcodes that do not use a mode byte / operand parsing
        self.no_operand_opcodes = NO_OPERAND_OPCODES
        
        # Create reverse mapping for profiling (opcode -> name)
        self.opcode_to_name = {}
        for opcode, instruction in self.instruction_table.items():
            self.opcode_to_name[opcode] = instruction.name
        
        # Removed: self.memory.gfx_system = self.gfx  (now uses event bus)

        # Register all external peripheral registers into the RegisterFile
        self._register_externals()

        # ========================================
        # PROFILING SYSTEM
        # ========================================
        self.profiling_enabled = False
        self.profile_data = {
            'total_cycles': 0,
            'instructions_executed': 0,
            'opcode_counts': {},
            'method_times': {},
            'memory_accesses': 0,
            'start_time': None,
            'instruction_start_times': {},
            'cycle_start_time': None
        }

    def enable_profiling(self):
        """Enable CPU profiling"""
        self.profiling_enabled = True
        self.profile_data['start_time'] = time.time()
        print("CPU profiling enabled")

    def disable_profiling(self):
        """Disable CPU profiling"""
        self.profiling_enabled = False
        print("CPU profiling disabled")

    def reset_profile_data(self):
        """Reset all profiling data"""
        self.profile_data = {
            'total_cycles': 0,
            'instructions_executed': 0,
            'opcode_counts': {},
            'method_times': {},
            'memory_accesses': 0,
            'start_time': self.profile_data.get('start_time'),
            'instruction_start_times': {},
            'cycle_start_time': None
        }

    def get_profile_report(self):
        """Generate a profiling report"""
        if not self.profiling_enabled:
            return "Profiling not enabled"

        end_time = time.time()
        total_time = end_time - (self.profile_data['start_time'] or end_time)

        report = []
        report.append("=== CPU Profiling Report ===")
        report.append(f"Total execution time: {total_time:.4f} seconds")
        report.append(f"Instructions executed: {self.profile_data['instructions_executed']}")
        report.append(f"Memory accesses: {self.profile_data['memory_accesses']}")
        report.append(f"Operand parses: {self.profile_data.get('operand_parses', 0)}")
        report.append(f"Operand value gets: {self.profile_data.get('operand_values', 0)}")
        report.append(f"Average IPS: {self.profile_data['instructions_executed'] / total_time:.2f}")

        if self.profile_data['opcode_counts']:
            report.append("\nTop 10 instructions by frequency:")
            sorted_opcodes = sorted(self.profile_data['opcode_counts'].items(),
                                  key=lambda x: x[1], reverse=True)[:10]
            for opcode, count in sorted_opcodes:
                pct = (count / self.profile_data['instructions_executed']) * 100
                name = self.opcode_to_name.get(opcode, f"0x{opcode:02X}")
                report.append(f"  {name}: {count} ({pct:.1f}%)")

        if self.profile_data['method_times']:
            report.append("\nMethod timing (total time spent):")
            sorted_methods = sorted(self.profile_data['method_times'].items(),
                                  key=lambda x: x[1], reverse=True)
            for method, total_time in sorted_methods:
                pct = (total_time / total_time) * 100 if total_time > 0 else 0
                report.append(f"  {method}: {total_time:.6f}s ({pct:.1f}%)")

        return "\n".join(report)

    def profile_method(self, method_name):
        """Decorator to profile a method"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                if self.profiling_enabled:
                    start_time = time.time()
                    result = func(*args, **kwargs)
                    end_time = time.time()
                    elapsed = end_time - start_time

                    if method_name not in self.profile_data['method_times']:
                        self.profile_data['method_times'][method_name] = 0
                    self.profile_data['method_times'][method_name] += elapsed
                    return result
                else:
                    return func(*args, **kwargs)
            return wrapper
        return decorator

    # ========================================
    # FLAGS ACCESS - Backward-compatible property
    # ========================================
    
    @property
    def flags(self):
        """Backward-compatible flags access - returns Flags instance.
        
        Supports both list-style access (flags[7] = 1) and property access
        (flags.zero_flag). Assignment accepts a list to set_state.
        """
        return self.flags_obj
    
    @flags.setter
    def flags(self, value):
        """Allow assignment from a list (backward compatible with tests)."""
        if isinstance(value, (list, tuple)):
            self.flags_obj.set_state(value)
        elif isinstance(value, Flags):
            self.flags_obj = value
        # else: ignore non-list/Flags assignments
    
    # ========================================
    # FLAG PROPERTIES - Delegated to Flags instance
    # ========================================
    
    @property
    def trap_flag(self):
        """Trap flag (T) - bit 0: Enable single-step mode"""
        return self.flags_obj.trap_flag
    
    @trap_flag.setter
    def trap_flag(self, value):
        self.flags_obj.trap_flag = value
    
    @property
    def sign_flag(self):
        """Sign flag (S) - bit 1: Result is negative"""
        return self.flags_obj.sign_flag
    
    @sign_flag.setter
    def sign_flag(self, value):
        self.flags_obj.sign_flag = value
    
    @property
    def overflow_flag(self):
        """Overflow flag (O) - bit 2: Arithmetic overflow occurred"""
        return self.flags_obj.overflow_flag
    
    @overflow_flag.setter
    def overflow_flag(self, value):
        self.flags_obj.overflow_flag = value
    
    @property
    def break_flag(self):
        """Break flag (B) - bit 3: Breakpoint hit"""
        return self.flags_obj.break_flag
    
    @break_flag.setter
    def break_flag(self, value):
        self.flags_obj.break_flag = value
    
    @property
    def decimal_flag(self):
        """Decimal flag (D) - bit 4: BCD mode enabled"""
        return self.flags_obj.decimal_flag
    
    @decimal_flag.setter
    def decimal_flag(self, value):
        self.flags_obj.decimal_flag = value
    
    @property
    def interrupt_flag(self):
        """Interrupt flag (I) - bit 5: Interrupts enabled"""
        return self.flags_obj.interrupt_flag
    
    @interrupt_flag.setter
    def interrupt_flag(self, value):
        self.flags_obj.interrupt_flag = value
    
    @property
    def carry_flag(self):
        """Carry flag (C) - bit 6: Arithmetic carry/borrow occurred"""
        return self.flags_obj.carry_flag
    
    @carry_flag.setter
    def carry_flag(self, value):
        self.flags_obj.carry_flag = value
    
    @property
    def zero_flag(self):
        """Zero flag (Z) - bit 7: Result is zero"""
        return self.flags_obj.zero_flag
    
    @zero_flag.setter
    def zero_flag(self, value):
        self.flags_obj.zero_flag = value
    
    @property
    def parity_flag(self):
        """Parity flag (P) - bit 8: Result has even parity"""
        return self.flags_obj.parity_flag
    
    @parity_flag.setter
    def parity_flag(self, value):
        self.flags_obj.parity_flag = value
    
    @property
    def direction_flag(self):
        """Direction flag (H) - bit 9: CPU runs High to Low"""
        return self.flags_obj.direction_flag
    
    @direction_flag.setter
    def direction_flag(self, value):
        self.flags_obj.direction_flag = value
    
    @property
    def bcd_carry_flag(self):
        """BCD Carry flag (A) - bit 10: BCD operation carry"""
        return self.flags_obj.bcd_carry_flag
    
    @bcd_carry_flag.setter
    def bcd_carry_flag(self, value):
        self.flags_obj.bcd_carry_flag = value
    
    @property
    def hacker_flag(self):
        """Hacker flag (E) - bit 11: User is a hacker (not touched by CPU)"""
        return self.flags_obj.hacker_flag
    
    @hacker_flag.setter
    def hacker_flag(self, value):
        self.flags_obj.hacker_flag = value
    
    @property
    def decimal_mode(self):
        """Decimal mode flag (maps to decimal flag D)"""
        return self.flags_obj.decimal_mode
    
    @decimal_mode.setter
    def decimal_mode(self, value):
        self.flags_obj.decimal_mode = value
    
    @property
    def aux_carry(self):
        """Auxiliary carry flag (maps to BCD carry flag A)"""
        return self.flags_obj.aux_carry
    
    @aux_carry.setter
    def aux_carry(self, value):
        self.flags_obj.aux_carry = value

    # ========================================
    # REGISTER PROPERTIES - Readable Access to Registers
    # ========================================
    
    @property
    def r0(self):
        """R0 register (8-bit)"""
        return int(self.Rregisters[0])
    
    @r0.setter
    def r0(self, value):
        self.Rregisters[0] = int(value) & 0xFF
    
    @property
    def r1(self):
        """R1 register (8-bit)"""
        return int(self.Rregisters[1])
    
    @r1.setter
    def r1(self, value):
        self.Rregisters[1] = int(value) & 0xFF
    
    @property
    def r2(self):
        """R2 register (8-bit)"""
        return int(self.Rregisters[2])
    
    @r2.setter
    def r2(self, value):
        self.Rregisters[2] = int(value) & 0xFF
    
    @property
    def r3(self):
        """R3 register (8-bit)"""
        return int(self.Rregisters[3])
    
    @r3.setter
    def r3(self, value):
        self.Rregisters[3] = int(value) & 0xFF
    
    @property
    def r4(self):
        """R4 register (8-bit)"""
        return int(self.Rregisters[4])
    
    @r4.setter
    def r4(self, value):
        self.Rregisters[4] = int(value) & 0xFF
    
    @property
    def r5(self):
        """R5 register (8-bit)"""
        return int(self.Rregisters[5])
    
    @r5.setter
    def r5(self, value):
        self.Rregisters[5] = int(value) & 0xFF
    
    @property
    def r6(self):
        """R6 register (8-bit)"""
        return int(self.Rregisters[6])
    
    @r6.setter
    def r6(self, value):
        self.Rregisters[6] = int(value) & 0xFF
    
    @property
    def r7(self):
        """R7 register (8-bit)"""
        return int(self.Rregisters[7])
    
    @r7.setter
    def r7(self, value):
        self.Rregisters[7] = int(value) & 0xFF
    
    @property
    def r8(self):
        """R8 register (8-bit)"""
        return int(self.Rregisters[8])
    
    @r8.setter
    def r8(self, value):
        self.Rregisters[8] = int(value) & 0xFF
    
    @property
    def r9(self):
        """R9 register (8-bit)"""
        return int(self.Rregisters[9])
    
    @r9.setter
    def r9(self, value):
        self.Rregisters[9] = int(value) & 0xFF
    
    @property
    def p0(self):
        """P0 register (16-bit)"""
        return int(self.Pregisters[0])
    
    @p0.setter
    def p0(self, value):
        self.Pregisters[0] = int(value) & 0xFFFF
    
    @property
    def p1(self):
        """P1 register (16-bit)"""
        return int(self.Pregisters[1])
    
    @p1.setter
    def p1(self, value):
        self.Pregisters[1] = int(value) & 0xFFFF
    
    @property
    def p2(self):
        """P2 register (16-bit)"""
        return int(self.Pregisters[2])
    
    @p2.setter
    def p2(self, value):
        self.Pregisters[2] = int(value) & 0xFFFF
    
    @property
    def p3(self):
        """P3 register (16-bit)"""
        return int(self.Pregisters[3])
    
    @p3.setter
    def p3(self, value):
        self.Pregisters[3] = int(value) & 0xFFFF
    
    @property
    def p4(self):
        """P4 register (16-bit)"""
        return int(self.Pregisters[4])
    
    @p4.setter
    def p4(self, value):
        self.Pregisters[4] = int(value) & 0xFFFF
    
    @property
    def p5(self):
        """P5 register (16-bit)"""
        return int(self.Pregisters[5])
    
    @p5.setter
    def p5(self, value):
        self.Pregisters[5] = int(value) & 0xFFFF
    
    @property
    def p6(self):
        """P6 register (16-bit)"""
        return int(self.Pregisters[6])
    
    @p6.setter
    def p6(self, value):
        self.Pregisters[6] = int(value) & 0xFFFF
    
    @property
    def p7(self):
        """P7 register (16-bit)"""
        return int(self.Pregisters[7])
    
    @p7.setter
    def p7(self, value):
        self.Pregisters[7] = int(value) & 0xFFFF
    
    @property
    def p8(self):
        """P8 register (16-bit)"""
        return int(self.Pregisters[8])
    
    @p8.setter
    def p8(self, value):
        self.Pregisters[8] = int(value) & 0xFFFF
    
    @property
    def p9(self):
        """P9 register (16-bit)"""
        return int(self.Pregisters[9])
    
    @p9.setter
    def p9(self, value):
        self.Pregisters[9] = int(value) & 0xFFFF
    
    @property
    def sp(self):
        """Stack Pointer register (16-bit) - alias for P8"""
        return int(self.Pregisters[8])
    
    @sp.setter
    def sp(self, value):
        self.Pregisters[8] = int(value) & 0xFFFF
    
    @property
    def fp(self):
        """Frame Pointer register (16-bit) - alias for P9"""
        return int(self.Pregisters[9])
    
    @fp.setter
    def fp(self, value):
        self.Pregisters[9] = int(value) & 0xFFFF

    # ========================================
    # SOUND REGISTER PROPERTIES - Direct access to sound registers
    # ========================================
    
    @property
    def sa(self):
        """SA register - Sound Address (16-bit)"""
        if self.sound:
            return int(self.sound.get_register('SA'))
        return 0
    
    @sa.setter
    def sa(self, value):
        if self.sound:
            self.sound.update_registers(sa=int(value) & 0xFFFF)
    
    @property
    def sf(self):
        """SF register - Sound Frequency (8-bit)"""
        if self.sound:
            return int(self.sound.get_register('SF'))
        return 0
    
    @sf.setter
    def sf(self, value):
        if self.sound:
            self.sound.update_registers(sf=int(value) & 0xFF)
    
    @property
    def sv(self):
        """SV register - Sound Volume (8-bit)"""
        if self.sound:
            return int(self.sound.get_register('SV'))
        return 0
    
    @sv.setter
    def sv(self, value):
        if self.sound:
            self.sound.update_registers(sv=int(value) & 0xFF)
    
    @property
    def sw(self):
        """SW register - Sound Waveform/Control (8-bit)"""
        if self.sound:
            return int(self.sound.get_register('SW'))
        return 0
    
    @sw.setter
    def sw(self, value):
        if self.sound:
            self.sound.update_registers(sw=int(value) & 0xFF)

    @property
    def mx(self):
        """MX register - Mouse X position (16-bit)."""
        return int(self.mouse.x)

    @mx.setter
    def mx(self, value):
        self.mouse.move_to(value, self.mouse.y)

    @property
    def my(self):
        """MY register - Mouse Y position (16-bit)."""
        return int(self.mouse.y)

    @my.setter
    def my(self, value):
        self.mouse.move_to(self.mouse.x, value)

    @property
    def mb(self):
        """MB register - Mouse buttons/status (8-bit)."""
        return int(self.mouse.buttons) & 0xFF

    @mb.setter
    def mb(self, value):
        self.mouse.set_buttons(value)

    @property
    def rtc_seconds(self):
        """Seconds elapsed since the Nova-16 RTC epoch, clamped to 32 bits."""
        elapsed = int(self.rtc_time_source()) - self.RTC_EPOCH_UNIX
        return max(0, elapsed) & 0xFFFFFFFF

    @property
    def c0(self):
        """C0 register - low 16 bits of the RTC seconds counter."""
        return self.rtc_seconds & 0xFFFF

    @c0.setter
    def c0(self, value):
        # RTC registers are read-only hardware state.
        return

    @property
    def c1(self):
        """C1 register - high 16 bits of the RTC seconds counter."""
        return (self.rtc_seconds >> 16) & 0xFFFF

    @c1.setter
    def c1(self, value):
        # RTC registers are read-only hardware state.
        return

    # ========================================
    # BULK OPERATIONS - Maintain numpy efficiency
    # ========================================
    
    def reset_all_flags(self):
        """Reset all flags to 0 - efficient bulk operation"""
        self.flags_obj.reset_all()
    
    def reset_all_registers(self):
        """Reset all registers to 0 - efficient bulk operation"""
        self.Rregisters[:] = [0] * len(self.Rregisters)
        self.Pregisters[:] = [0] * len(self.Pregisters)
        
        # Re-initialize stack pointer and frame pointer
        self.Pregisters[8] = 0xFFFF  # SP
        self.Pregisters[9] = 0xFFFF  # FP
    
    def get_flag_state(self):
        """Get complete flag state as list"""
        return self.flags_obj.get_state()
    
    def set_flag_state(self, flag_array):
        """Set complete flag state from a list"""
        self.flags_obj.set_state(flag_array)
    
    def get_register_state(self):
        """Get complete register state"""
        return {
            'r_registers': self.Rregisters.copy(),
            'p_registers': self.Pregisters.copy()
        }
    
    def set_register_state(self, reg_dict):
        """Set complete register state"""
        if 'r_registers' in reg_dict:
            self.Rregisters[:] = reg_dict['r_registers']
        if 'p_registers' in reg_dict:
            self.Pregisters[:] = reg_dict['p_registers']


    def reinit( self ):
        self.Rregisters[:] = [0] * len(self.Rregisters)
        self.Pregisters[:] = [0] * len(self.Pregisters)
        
        # Re-initialize stack pointer and frame pointer
        self.Pregisters[8] = 0xFFFF  # SP (Stack Pointer)
        self.Pregisters[9] = 0xFFFF  # FP (Frame Pointer)
        
        self.pc = 0x0000
        self.flags_obj.reset_all()
        self.stack = []
        self.interrupts[:] = [0] * len(self.interrupts)
        self.interrupt_check_counter = 0
        self.last_interrupt_state = 0
        self.has_pending_interrupt_sources = False
        self.uart.reset()
        self.keyboard[:] = [0] * len(self.keyboard)
        self.key_buffer = []
        if self.keyboard_device is not None:
            self.keyboard_device.clear_buffer()
        self.halted = False
        self.has_hw_breakpoints = False
        self.memory.reset()
        self.gfx.vram[:] = 0
        self.gfx.screen[:] = 0
        self.gfx.flags[:] = 0
        self.gfx.Vregisters[:] = 0
        self.gfx.vmode = 0
        
        # Reset sound system
        if self.sound:
            self.sound.sstop()  # Stop all sounds
            self.sound.update_registers(sa=0, sf=0, sv=0, sw=0)  # Reset sound registers
        self.mouse.reset()

        # Reset standalone timer peripheral
        if self.timer_device:
            self.timer_device.reset()
        
        # Rebuild register lookup table and re-bind external registers 
        self._register_lookup = self._build_register_lookup_table()

        # Connect keyboard if provided
        if self.keyboard_device is not None:
            self.keyboard_device.cpu = self  # Set back-reference
        self.mouse.attach(gfx=self.gfx, cpu_ref=self)
        self.mouse.set_interrupt_callback(self._refresh_pending_interrupt_sources)

    def _refresh_pending_interrupt_sources(self):
        """Refresh fast interrupt-source gate from current device and interrupt state."""
        self.has_pending_interrupt_sources = bool(
            (self.interrupts[2] == 1 and (self.keyboard[1] & 0x80) != 0) or
            (self.interrupts[1] == 1 and self.uart.pending_interrupt) or
            (self.interrupts[3] == 1 and self.mouse.pending_interrupt) or
            self.interrupts[4] == 1
        )

    def _has_enabled_async_interrupt_sources(self):
        """Return True when step() must rescan device-backed interrupt sources."""
        return bool(
            self.interrupts[1] or
            self.interrupts[2] or
            self.interrupts[3] or
            self.interrupts[4]
        )

    def _refresh_hw_breakpoint_state(self):
        """Refresh fast hardware-breakpoint gate from enabled slots."""
        self.has_hw_breakpoints = bool(
            self.hw_breakpoint_enabled[0] or
            self.hw_breakpoint_enabled[1] or
            self.hw_breakpoint_enabled[2] or
            self.hw_breakpoint_enabled[3]
        )

    # ========================================
    # REGISTER DISPATCH — O(1) via RegisterFile
    # ========================================
    
    def _register_externals(self):
        """Register all external peripheral registers into the RegisterFile.

        Called once at the end of __init__ so all hardware references exist.
        """
        rf = self.regfile
        sound = self.sound
        gfx = self.gfx
        mouse = self.mouse
        timer_dev = self.timer_device

        # Sound registers
        if sound:
            rf.register_external('SA',
                getter=lambda idx: int(sound.get_register('SA')),
                setter=lambda idx, v: sound.update_registers(sa=int(v) & 0xFFFF))
            rf.register_external('SF',
                getter=lambda idx: int(sound.get_register('SF')),
                setter=lambda idx, v: sound.update_registers(sf=int(v) & 0xFF))
            rf.register_external('SV',
                getter=lambda idx: int(sound.get_register('SV')),
                setter=lambda idx, v: sound.update_registers(sv=int(v) & 0xFF))
            rf.register_external('SW',
                getter=lambda idx: int(sound.get_register('SW')),
                setter=lambda idx, v: sound.update_registers(sw=int(v) & 0xFF))
        else:
            rf.register_external('SA', getter=lambda idx: 0)
            rf.register_external('SF', getter=lambda idx: 0)
            rf.register_external('SV', getter=lambda idx: 0)
            rf.register_external('SW', getter=lambda idx: 0)

        # Graphics registers (V — VX/VY/VC/VM)
        rf.register_external('V',
            getter=lambda idx: int(gfx.Vregisters[idx]),
            setter=lambda idx, v: gfx.Vregisters.__setitem__(idx, int(v) & 0xFF))
        rf.register_external('VL',
            getter=lambda idx: int(gfx.VL),
            setter=lambda idx, v: setattr(gfx, 'VL', int(v) & 0xFF))

        # Mouse registers
        rf.register_external('MX',
            getter=lambda idx: int(mouse.x),
            setter=lambda idx, v: mouse.move_to(v, mouse.y))
        rf.register_external('MY',
            getter=lambda idx: int(mouse.y),
            setter=lambda idx, v: mouse.move_to(mouse.x, v))
        rf.register_external('MB',
            getter=lambda idx: int(mouse.buttons) & 0xFF,
            setter=lambda idx, v: mouse.set_buttons(v))

        # RTC registers (read-only)
        rf.register_external('C0', getter=lambda idx: int(self.c0))
        rf.register_external('C1', getter=lambda idx: int(self.c1))

        # Timer registers (delegated to standalone Timer peripheral)
        if timer_dev:
            rf.register_external('TT',
                getter=lambda idx: timer_dev.get_register(0),
                setter=lambda idx, v: timer_dev.set_register(0, v))
            rf.register_external('TM',
                getter=lambda idx: timer_dev.get_register(1),
                setter=lambda idx, v: timer_dev.set_register(1, v))
            rf.register_external('TC',
                getter=lambda idx: timer_dev.get_register(2),
                setter=lambda idx, v: timer_dev.set_register(2, v))
            rf.register_external('TS',
                getter=lambda idx: timer_dev.get_register(3),
                setter=lambda idx, v: timer_dev.set_register(3, v))
        else:
            # Fallback stubs when no timer device is provided
            rf.register_external('TT', getter=lambda idx: 0,
                setter=lambda idx, v: None)
            rf.register_external('TM', getter=lambda idx: 0,
                setter=lambda idx, v: None)
            rf.register_external('TC', getter=lambda idx: 0,
                setter=lambda idx, v: None)
            rf.register_external('TS', getter=lambda idx: 0,
                setter=lambda idx, v: None)
    
    def _get_operand_value( self, type, idx ):
        """Get operand value — delegates core types to regfile, handles special cases."""
        # Fast-path: core and external types served by RegisterFile
        core_types = {'R', 'P', 'P_high', 'P_low', 'SP', 'FP', 'V', 'VL',
                      'TT', 'TM', 'TC', 'TS', 'C0', 'C1', 'MX', 'MY', 'MB',
                      'SA', 'SF', 'SV', 'SW'}
        if type in core_types:
            # SP → ('P', 8), FP → ('P', 9) for the regfile
            if type == 'SP':
                return int(self.regfile.get('P', 8))
            if type == 'FP':
                return int(self.regfile.get('P', 9))
            return int(self.regfile.get(type, idx))
        
        # Sound byte-access (SA:, :SA) — fall through to legacy handling
        if type == 'SA:':
            if self.sound: return int((self.sound.get_register('SA') >> 8) & 0xFF)
            return 0
        if type == ':SA':
            if self.sound: return int(self.sound.get_register('SA') & 0xFF)
            return 0
        
        # Optimized indirect memory access
        if type == 'Rind': return self.memory.read_byte_fast(self.Rregisters[idx])
        if type == 'Pind': return self.memory.read_byte_fast(self.Pregisters[idx])
        if type == 'SPind': return self.memory.read_byte_fast(self.sp)
        if type == 'FPind': return self.memory.read_byte_fast(self.fp)
        if type == 'Vind': return self.memory.read_byte_fast(self.gfx.Vregisters[idx])
        
        # Indexed addressing stubs
        if type == 'Ridx': return self.memory.read_byte_fast(self.Rregisters[idx])
        if type == 'Pidx': return self.memory.read_byte_fast(self.Pregisters[idx])
        if type == 'Vidx': return self.memory.read_byte_fast(self.gfx.Vregisters[idx])
        
        return 0

    def _set_operand_value( self, type, idx, value ):
        """Set operand value — delegates to regfile for core and external types."""
        # Core types + SP/FP aliases
        if type == 'SP':
            self.regfile.set('P', 8, int(value) & 0xFFFF)
            return
        if type == 'FP':
            self.regfile.set('P', 9, int(value) & 0xFFFF)
            return
        
        # Types served by RegisterFile (core + registered externals)
        regfile_types = {'R', 'P', 'P_high', 'P_low', 'V', 'VL',
                         'TT', 'TM', 'TC', 'TS', 'C0', 'C1',
                         'MX', 'MY', 'MB', 'SA', 'SF', 'SV', 'SW'}
        if type in regfile_types:
            try:
                self.regfile.set(type, idx, value)
            except Exception:
                pass  # C0/C1 are read-only; silently ignore
            # Side effects for TC/TS are handled by the registered setter callbacks
            return
        
        # Sound byte-access
        if type == 'SA:':
            if self.sound:
                current_sa = self.sound.get_register('SA')
                new_sa = (current_sa & 0x00FF) | ((int(value) & 0xFF) << 8)
                self.sound.update_registers(sa=new_sa)
            return
        if type == ':SA':
            if self.sound:
                current_sa = self.sound.get_register('SA')
                new_sa = (current_sa & 0xFF00) | (int(value) & 0xFF)
                self.sound.update_registers(sa=new_sa)
            return
        
        # Optimized indirect memory writes
        if type == 'Rind':
            self.write_byte(self.Rregisters[idx], int(value) & 0xFF)
            return
        if type == 'Pind':
            self.write_byte(self.Pregisters[idx], int(value) & 0xFF)
            return
        if type == 'SPind':
            self.write_byte(self.sp, int(value) & 0xFF)
            return
        if type == 'FPind':
            self.write_byte(self.fp, int(value) & 0xFF)
            return
        if type == 'Vind':
            self.write_byte(self.gfx.Vregisters[idx], int(value) & 0xFF)
            return
        
        # Indexed addressing stubs
        if type == 'Ridx':
            self.write_byte(self.Rregisters[idx], int(value) & 0xFF)
            return
        if type == 'Pidx':
            self.write_byte(self.Pregisters[idx], int(value) & 0xFF)
            return
        if type == 'Vidx':
            self.write_byte(self.gfx.Vregisters[idx], int(value) & 0xFF)
            return

    def _set_flags_8bit(self, result, original_result=None):
        """Set flags for 8-bit operations using readable property names"""
        if original_result is None:
            original_result = result
        
        # Zero flag (Z) - result is zero
        self.flags[7] = 1 if (result & 0xFF) == 0 else 0
        
        # Carry flag (C) - for subtraction (CMP), set when borrow occurs (val1 < val2)
        # For other operations, overflow/underflow occurred
        if hasattr(self, '_last_operation_was_cmp') and self._last_operation_was_cmp:
            self.flags[6] = 1 if original_result < 0 else 0  # Borrow occurred
            self._last_operation_was_cmp = False
        else:
            self.flags[6] = 1 if original_result > 0xFF or original_result < 0 else 0
        
        # Sign flag (S) - result is negative (bit 7 set)
        self.flags[1] = 1 if (result & 0x80) != 0 else 0
        
        # Parity flag (P) - even number of 1s in result
        self.flags[8] = self._parity_table[result & 0xFF]

    def _set_flags_16bit(self, result, original_result=None):
        """Set flags for 16-bit operations using readable property names"""
        if original_result is None:
            original_result = result
            
        # Zero flag (Z) - result is zero
        self.flags[7] = 1 if (result & 0xFFFF) == 0 else 0
        
        # Carry flag (C) - for subtraction (CMP), set when borrow occurs (val1 < val2)
        # For other operations, overflow/underflow occurred
        if hasattr(self, '_last_operation_was_cmp') and self._last_operation_was_cmp:
            self.flags[6] = 1 if original_result < 0 else 0  # Borrow occurred
            self._last_operation_was_cmp = False
        else:
            self.flags[6] = 1 if original_result > 0xFFFF or original_result < 0 else 0
        
        # Sign flag (S) - result is negative (bit 15 set)
        self.flags[1] = 1 if (result & 0x8000) != 0 else 0
        
        # Parity flag (P) - even number of 1s in low byte
        self.flags[8] = self._parity_table[result & 0xFF]

    def _set_overflow_flag_8bit(self, op1, op2, result, is_subtraction=False):
        """Set overflow flag for 8-bit operations using readable property name"""
        if is_subtraction:
            # Overflow in subtraction: (pos - neg = neg) or (neg - pos = pos)
            overflow = ((op1 & 0x80) != (op2 & 0x80)) and ((op1 & 0x80) != (result & 0x80))
        else:
            # Overflow in addition: (pos + pos = neg) or (neg + neg = pos)
            overflow = ((op1 & 0x80) == (op2 & 0x80)) and ((op1 & 0x80) != (result & 0x80))
        self.flags[2] = 1 if overflow else 0

    def _set_overflow_flag_16bit(self, op1, op2, result, is_subtraction=False):
        """Set overflow flag for 16-bit operations using readable property name"""
        if is_subtraction:
            # Overflow in subtraction: (pos - neg = neg) or (neg - pos = pos)
            overflow = ((op1 & 0x8000) != (op2 & 0x8000)) and ((op1 & 0x8000) != (result & 0x8000))
        else:
            # Overflow in addition: (pos + pos = neg) or (neg + neg = pos)
            overflow = ((op1 & 0x8000) == (op2 & 0x8000)) and ((op1 & 0x8000) != (result & 0x8000))
        self.flags[2] = 1 if overflow else 0

    # ========================================
    # BCD (Binary Coded Decimal) OPERATIONS
    # ========================================
    
    def _is_valid_bcd(self, value):
        """Check if a value contains valid BCD digits (0-9 in each nibble)"""
        return ((value & 0x0F) <= 9) and (((value & 0xF0) >> 4) <= 9)
    
    def _bcd_to_binary(self, bcd_value):
        """Convert BCD value to binary"""
        if not self._is_valid_bcd(bcd_value):
            return bcd_value  # Invalid BCD, return as-is
        
        low_nibble = bcd_value & 0x0F
        high_nibble = (bcd_value & 0xF0) >> 4
        return high_nibble * 10 + low_nibble
    
    def _binary_to_bcd(self, binary_value):
        """Convert binary value to BCD (max 99)"""
        if binary_value > 99:
            binary_value = binary_value % 100  # Wrap around for values > 99
        
        tens = binary_value // 10
        ones = binary_value % 10
        return (tens << 4) | ones
    
    def _bcd_add(self, val1, val2):
        """Perform BCD addition with proper carry handling"""
        # Convert BCD to binary for arithmetic
        bin1 = self._bcd_to_binary(val1)
        bin2 = self._bcd_to_binary(val2)
        
        # Add with any existing BCD carry
        result = bin1 + bin2 + (1 if self.bcd_carry_flag else 0)
        
        # Handle BCD carry (result > 99)
        bcd_carry = result > 99
        if bcd_carry:
            result = result % 100
        
        # Convert back to BCD
        bcd_result = self._binary_to_bcd(result)
        
        return bcd_result, bcd_carry
    
    def _bcd_sub(self, val1, val2):
        """Perform BCD subtraction with proper borrow handling"""
        # Convert BCD to binary for arithmetic
        bin1 = self._bcd_to_binary(val1)
        bin2 = self._bcd_to_binary(val2)
        
        # Subtract with any existing BCD borrow
        result = bin1 - bin2 - (1 if self.bcd_carry_flag else 0)
        
        # Handle BCD borrow (result < 0)
        bcd_borrow = result < 0
        if bcd_borrow:
            result = result + 100  # Borrow from next digit
        
        # Convert back to BCD
        bcd_result = self._binary_to_bcd(result)
        
        return bcd_result, bcd_borrow
    
    def _set_flags_8bit_bcd(self, result, bcd_carry=False):
        """Set flags for 8-bit BCD operations"""
        # Zero flag (Z) - result is zero
        self.zero_flag = (result & 0xFF) == 0
        
        # BCD Carry flag (A) - BCD operation generated carry/borrow
        self.bcd_carry_flag = bcd_carry
        
        # Regular carry flag is also set for compatibility
        self.carry_flag = bcd_carry
        
        # Sign flag (S) - result is negative (bit 7 set)
        self.sign_flag = (result & 0x80) != 0
        
        # Parity flag (P) - even number of 1s in result
        self.parity_flag = bool(self._parity_table[result & 0xFF])
    
    # Public BCD methods for instructions
    def bcd_add(self, val1, val2):
        """Public BCD add method for instructions"""
        result, carry = self._bcd_add(val1, val2)
        self._set_flags_8bit_bcd(result, carry)
        return result
    
    def bcd_subtract(self, val1, val2):
        """Public BCD subtract method for instructions"""
        result, borrow = self._bcd_sub(val1, val2)
        self._set_flags_8bit_bcd(result, borrow)
        return result
    
    def bcd_compare(self, val1, val2):
        """Public BCD compare method for instructions"""
        result, borrow = self._bcd_sub(val1, val2)
        self._set_flags_8bit_bcd(result, borrow)
        return result
    
    def bcd_to_binary(self, bcd_value):
        """Public BCD to binary conversion for instructions"""
        return self._bcd_to_binary(bcd_value)
    
    def binary_to_bcd(self, binary_value):
        """Public binary to BCD conversion for instructions"""
        return self._binary_to_bcd(binary_value)

    # Keyboard input handling
    def add_key_to_buffer(self, key_code):
        """Add a key press to the keyboard buffer and trigger interrupt if enabled"""
        if self.keyboard_device is not None:
            self.keyboard_device.add_key(key_code)
            # Sync legacy registers from keyboard_device state
            self.keyboard[0] = self.keyboard_device.data_register
            self.keyboard[1] = self.keyboard_device.status_register
            self.keyboard[3] = self.keyboard_device.buffer_count
            # Only set legacy interrupt pending flag if no interrupt controller
            if self.intr_ctrl is None and self.interrupts[2] == 1:
                self.keyboard[1] |= 0x80
                self.has_pending_interrupt_sources = True
            return

        # Legacy path (no keyboard_device)
        if len(self.key_buffer) < self.key_buffer_size:
            self.key_buffer.append(key_code & 0xFF)
            self.keyboard[3] = len(self.key_buffer)  # Update buffer count
            
            # Update keyboard data register with most recent key
            self.keyboard[0] = key_code & 0xFF
            
            # Set status flags
            self.keyboard[1] |= 0x01  # Key available flag
            if len(self.key_buffer) >= self.key_buffer_size:
                self.keyboard[1] |= 0x02  # Buffer full flag
            
            # Trigger keyboard interrupt if enabled
            if self.interrupts[2] == 1:  # Keyboard interrupt enabled
                self.keyboard[1] |= 0x80  # Set interrupt pending flag
                self.has_pending_interrupt_sources = True
                
    def read_key_from_buffer(self):
        """Read and remove the oldest key from the keyboard buffer"""
        if self.keyboard_device is not None:
            key = self.keyboard_device.read_key()
            # Sync legacy registers from keyboard_device state
            self.keyboard[0] = self.keyboard_device.data_register
            self.keyboard[1] = self.keyboard_device.status_register
            self.keyboard[3] = self.keyboard_device.buffer_count
            return key

        # Legacy path
        if self.key_buffer:
            key_code = self.key_buffer.pop(0)
            self.keyboard[3] = len(self.key_buffer)  # Update buffer count
            
            # Update keyboard data register
            if self.key_buffer:
                self.keyboard[0] = self.key_buffer[0]  # Next key in buffer
            else:
                self.keyboard[0] = 0  # No more keys
                self.keyboard[1] = self.keyboard[1] & 0xFE  # Clear key available flag (bit 0)
            
            # Clear buffer full flag if buffer is no longer full
            if len(self.key_buffer) < self.key_buffer_size:
                self.keyboard[1] = self.keyboard[1] & 0xFD  # Clear buffer full flag (bit 1)
                
            return key_code
        else:
            # Buffer is empty - return 0 and ensure correct flags
            self.keyboard[0] = 0
            self.keyboard[3] = 0
            self.keyboard[1] = self.keyboard[1] & 0xFE  # Clear key available flag
            self.keyboard[1] = self.keyboard[1] & 0xFD  # Clear buffer full flag
            return 0
    
    def clear_keyboard_buffer(self):
        """Clear the keyboard buffer and reset status"""
        if self.keyboard_device is not None:
            self.keyboard_device.clear_buffer()
        self.key_buffer = []
        self.keyboard[0] = 0  # Clear data register
        self.keyboard[1] = 0  # Clear status flags
        self.keyboard[3] = 0  # Clear buffer count

    def interrupt(self, interrupt_vector):
        """Public method to trigger an interrupt"""
        if 0 <= interrupt_vector < 8:
            self._trigger_interrupt(interrupt_vector)
        # Invalid vectors are ignored

    def _trigger_interrupt(self, interrupt_vector):
        """Trigger an interrupt if global interrupts are enabled"""
        if int(self.flags[5]) == 1:  # Check if interrupts are globally enabled
            # Check stack bounds before writing (need to push 2 words)
            sp = int(self.Pregisters[8])
            if sp < 0x0124:  # Stack overflow check (protect interrupt vectors)
                raise RuntimeError(f"Stack overflow: SP=0x{sp:04X}")
            
            # Calculate interrupt handler address
            vector_address = 0x0100 + (interrupt_vector * 4)
            handler_address = self.memory.read_word(vector_address)
            
            # Push current PC and flags onto stack in memory
            flags_val = 0
            for i in range(12):
                if int(self.flags[i]) != 0:
                    flags_val |= (1 << i)
            
            self.Pregisters[8] = (int(self.Pregisters[8]) - 2) & 0xFFFF  # Decrement SP
            self.memory.write_word(self.Pregisters[8], flags_val)
            
            self.Pregisters[8] = (int(self.Pregisters[8]) - 2) & 0xFFFF  # Decrement SP
            self.memory.write_word(self.Pregisters[8], self.pc)
            
            # Disable interrupts during interrupt handling
            self.flags[5] = 0
            
            # Jump to interrupt handler
            self.pc = handler_address
    
    def _check_pending_interrupts(self):
        """Optimized interrupt checking with batching and caching"""
        if not self.has_pending_interrupt_sources:
            return False

        # Increment counter and check if we should skip this check
        self.interrupt_check_counter += 1
        if self.interrupt_check_counter < self.interrupt_check_frequency:
            return False
        
        # Reset counter for next batch
        self.interrupt_check_counter = 0
        
        # Fast exit if interrupts are globally disabled
        if self.flags[5] == 0:  # Interrupts disabled
            return False
        
        # Create current interrupt state hash for change detection
        current_state = (
            (self.interrupts[1] << 7) |  # Serial enabled
            (self.interrupts[2] << 6) |  # Keyboard enabled  
            (self.interrupts[3] << 5) |  # Mouse enabled
            (self.interrupts[4] << 4) |  # User1 enabled
            ((self.keyboard[1] & 0x80) >> 3) |  # Keyboard pending
            ((0x80 if self.uart.pending_interrupt else 0) >> 4) |  # Serial pending
            ((0x80 if self.mouse.pending_interrupt else 0) >> 5)  # Mouse pending
        )
        
        # Skip detailed check if state hasn't changed
        if current_state == self.last_interrupt_state and current_state == 0:
            self.has_pending_interrupt_sources = False
            return False
            
        self.last_interrupt_state = current_state
        
        # Explicit loop with early exit instead of generator
        # Check keyboard interrupt first (most common)
        if self.interrupts[2] == 1 and (self.keyboard[1] & 0x80):
            self.keyboard[1] &= 0x7F  # Clear interrupt pending flag
            self._refresh_pending_interrupt_sources()
            self._trigger_interrupt(2)
            return True  # Interrupt was handled
            
        # Check serial interrupt
        if self.interrupts[1] == 1 and self.uart.pending_interrupt:
            self.uart.clear_interrupt()
            self._refresh_pending_interrupt_sources()
            self._trigger_interrupt(1)
            return True

        # Check mouse interrupt
        if self.interrupts[3] == 1 and self.mouse.pending_interrupt:
            self.mouse.clear_interrupt()
            self._refresh_pending_interrupt_sources()
            self._trigger_interrupt(3)
            return True
            
        # Check user interrupts
        if self.interrupts[4] == 1:  # User interrupt 1
            # User interrupt logic would go here
            pass
            
        self._refresh_pending_interrupt_sources()
        return False  # No interrupt handled
    
    def _check_hw_breakpoints(self):
        """Check for hardware breakpoints and single-step trap"""
        if self.flags[0] != 1 and not self.has_hw_breakpoints:
            return

        # Check hardware breakpoints
        any_enabled = False
        for i in range(4):
            if self.hw_breakpoint_enabled[i]:
                any_enabled = True
                if self.pc == self.hw_breakpoints[i]:
                    self.flags[3] = 1  # Set B flag
                    self._trigger_interrupt(7)  # Debug interrupt
                    return

        if not any_enabled:
            self.has_hw_breakpoints = False

        # Check single-step trap
        if self.flags[0] == 1:  # T flag set
                self.flags[3] = 1  # Set B flag
                self._trigger_interrupt(7)  # Debug interrupt
    
    def _build_register_lookup_table(self):
        """Build optimized lookup table for register access - O(1) performance"""
        lookup = {}

        # Real-time clock registers
        lookup[0xC3] = (0, 'C0')  # RTC seconds low word
        lookup[0xC4] = (0, 'C1')  # RTC seconds high word

        # Mouse registers
        lookup[0xC5] = (0, 'MX')  # Mouse X
        lookup[0xC6] = (0, 'MY')  # Mouse Y
        lookup[0xC7] = (0, 'MB')  # Mouse buttons
        
        # Sound registers
        lookup[0xDD] = (0, 'SA')  # Sound Address
        lookup[0xDE] = (0, 'SF')  # Sound Frequency
        lookup[0xDF] = (0, 'SV')  # Sound Volume
        lookup[0xE0] = (0, 'SW')  # Sound Waveform/Control
        
        # P register byte access (0xC9-0xD2 for high bytes, 0xD3-0xDC for low bytes)
        for i in range(10):
            lookup[0xC9 + i] = (i, 'P_high')  # P0: to P9: (high bytes)
            lookup[0xD3 + i] = (i, 'P_low')   # :P0 to :P9 (low bytes)
        
        # Video registers
        lookup[0xE1] = (2, 'V')   # VM register - Vregisters[2]
        lookup[0xE2] = (0, 'VL')  # Video Layer register
        lookup[0xC8] = (3, 'V')   # VC register - Vregisters[3] - moved to 0xC8
        
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
        lookup[0xFB] = (8, 'P')  # SP = P8
        lookup[0xFC] = (9, 'P')  # FP = P9
            
        # V registers (0xFD-0xFE) - VX, VY
        lookup[0xFD] = (0, 'V')  # VX
        lookup[0xFE] = (1, 'V')  # VY
        
        return lookup
    
    def _build_parity_table(self):
        """Build parity lookup table for fast parity flag calculation"""
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

    # Optimized register lookup - O(1) performance
    def reg_index(self, reg_code):
        """Fast register lookup using pre-computed dictionary"""
        try:
            return self._register_lookup[reg_code]
        except KeyError:
            if reg_code == 0x00:
                return 0, 'R'  # Treat 0x00 as R0
            raise Exception(f"Unknown register code: {reg_code:02X}")

    def fetch( self, bytes=1 ):
        if bytes == 1:
            data = self.memory.read( self.pc, 1 )
            self.pc = (self.pc + 1) & 0xFFFF
            return data[0]
        elif bytes == 2:
            data = self.memory.read( self.pc, 2 )
            self.pc = (self.pc + 2) & 0xFFFF
            return (int(data[0]) << 8) | int(data[1])  # Convert to int first for proper bit operations
        else:
            data = self.memory.read( self.pc, bytes )
            self.pc = (self.pc + bytes) & 0xFFFF
            return [ int( b ) for b in data ]
    
    def fetch_byte(self):
        """Fetch single byte directly from memory (no caching)."""
        if self.profiling_enabled:
            self.profile_data['memory_accesses'] += 1
        
        value = self.memory.read_byte_fast(self.pc)
        self.pc = (self.pc + 1) & 0xFFFF
        return int(value)
    
    def fetch_word(self):
        """Fetch 16-bit word directly from memory (big-endian for Nova-16)."""
        high = self.fetch_byte()
        low = self.fetch_byte()
        return (int(high) << 8) | int(low)

    def fetch_bytes(self, count):
        """Fetch multiple bytes directly from memory."""
        result = [self.memory.read_byte_fast((self.pc + i) & 0xFFFF) for i in range(count)]
        self.pc = (self.pc + count) & 0xFFFF
        return result
    
    def write_memory(self, address, value, bytes=1):
        """Write to memory (no cache invalidation needed)."""
        self.memory.write(address, value, bytes)
    
    def write_byte(self, address, value):
        """Write single byte to memory (no cache invalidation needed)."""
        self.memory.write_byte_fast(address, value)
    
    def write_word(self, address, value):
        """Write 16-bit word to memory (no cache invalidation needed)."""
        self.memory.write_word_fast(address, value)
    
    # ========================================
    # LEGACY COMPATIBILITY STUBS
    # ========================================
    
    def invalidate_prefetch(self):
        """Legacy stub — prefetch cache eliminated in Phase 4."""
        pass

    # ========================================
    # NEW PREFIXED OPERAND METHODS
    # ========================================
    
    def fetch_operand_by_mode(self, mode_bits):
        """Fetch operand based on 2-bit mode encoding"""
        if mode_bits == 0:  # Register direct
            reg_code = self.fetch_byte()
            idx, typ = self.reg_index(reg_code)
            return self._get_operand_value(typ, idx)
        elif mode_bits == 1:  # Immediate 8-bit
            return self.fetch_byte()
        elif mode_bits == 2:  # Immediate 16-bit
            return self.fetch_word()
        elif mode_bits == 3:  # Memory reference
            # Check flags for interpretation
            indexed = (self._current_mode_byte & (1 << 6)) != 0
            direct = (self._current_mode_byte & (1 << 7)) != 0
            
            if direct and not indexed:
                # Direct memory address
                addr = self.fetch_word()
                return self.memory.read_word(addr)
            elif not direct and not indexed:
                # Register indirect
                reg_code = self.fetch_byte()
                idx, typ = self.reg_index(reg_code)
                if typ == 'P':
                    addr = self.Pregisters[idx]
                elif typ == 'R':
                    addr = self.Rregisters[idx]
                else:
                    raise Exception(f"Invalid register type {typ} for indirect addressing")
                return self.memory.read_word(addr & 0xFFFF)
            elif not direct and indexed:
                # Register indexed
                reg_code = self.fetch_byte()
                index = self.fetch_byte()
                idx, typ = self.reg_index(reg_code)
                if typ == 'P':
                    base_addr = self.Pregisters[idx]
                elif typ == 'R':
                    base_addr = self.Rregisters[idx]
                else:
                    raise Exception(f"Invalid register type {typ} for indexed addressing")
                
                # FP (P9) and SP (P8) use signed offset for stack-relative addressing
                # Convert unsigned byte to signed (-128 to +127)
                if idx in [8, 9]:  # SP or FP
                    signed_offset = index if index < 128 else index - 256
                    addr = (base_addr + signed_offset) & 0xFFFF
                else:
                    addr = (base_addr + index) & 0xFFFF
                return self.memory.read_word(addr)
            elif direct and indexed:
                # Direct indexed
                addr = self.fetch_word()
                index = self.fetch_byte()
                final_addr = (addr + index) & 0xFFFF
                return self.memory.read_word(final_addr)
        else:
            raise Exception(f"Invalid mode bits: {mode_bits}")
    
    def parse_operands(self, num_operands):
        """Parse operands based on current mode byte for prefixed operand instructions"""
        if self.profiling_enabled:
            self.profile_data['operand_parses'] = self.profile_data.get('operand_parses', 0) + 1
        
        operands = []
        for i in range(num_operands):
            mode_bits = (self._current_mode_byte >> (i * 2)) & 0x3
            operand = {'mode': mode_bits}
            
            if mode_bits == 0:  # Register direct
                reg_code = self.fetch_byte()
                idx, typ = self.reg_index(reg_code)
                operand['type'] = 'register'
                operand['reg_type'] = typ
                operand['reg_idx'] = idx
            elif mode_bits == 1:  # Immediate 8-bit
                operand['type'] = 'immediate'
                operand['value'] = self.fetch_byte()
                operand['size'] = 8
            elif mode_bits == 2:  # Immediate 16-bit
                operand['type'] = 'immediate'
                operand['value'] = self.fetch_word()
                operand['size'] = 16
            elif mode_bits == 3:  # Memory reference
                indexed = (self._current_mode_byte & (1 << 6)) != 0
                direct = (self._current_mode_byte & (1 << 7)) != 0
                operand['type'] = 'memory'
                operand['indexed'] = indexed
                operand['direct'] = direct
                if direct and not indexed:
                    # Direct memory address
                    operand['address'] = self.fetch_word()
                elif not direct and not indexed:
                    # Register indirect
                    reg_code = self.fetch_byte()
                    idx, typ = self.reg_index(reg_code)
                    if typ not in ['P', 'R']:
                        raise Exception(f"Invalid register type {typ} for indirect addressing")
                    operand['indirect'] = True
                    operand['reg_type'] = typ
                    operand['reg_idx'] = idx
                elif not direct and indexed:
                    # Register indexed
                    reg_code = self.fetch_byte()
                    index = self.fetch_byte()
                    idx, typ = self.reg_index(reg_code)
                    if typ not in ['P', 'R']:
                        raise Exception(f"Invalid register type {typ} for indexed addressing")
                    operand['indexed'] = True
                    operand['reg_type'] = typ
                    operand['reg_idx'] = idx
                    operand['index'] = index
                elif direct and indexed:
                    # Direct indexed
                    addr = self.fetch_word()
                    index = self.fetch_byte()
                    operand['address'] = (addr + index) & 0xFFFF
                    operand['index'] = index
            operands.append(operand)
        
        return operands

    def get_operand_value(self, operand, dest_operand=None):
        """Get value from operand"""
        if self.profiling_enabled:
            self.profile_data['operand_values'] = self.profile_data.get('operand_values', 0) + 1
        
        if operand['type'] == 'register':
            # Check cache first
            # cache_key = (operand['reg_type'], operand['reg_idx'])
            # if cache_key in self.register_cache:
            #     return self.register_cache[cache_key]
            
            value = self._get_operand_value(operand['reg_type'], operand['reg_idx'])
            
            # Cache the value
            # if len(self.register_cache) < self.register_cache_size:
            #     self.register_cache[cache_key] = value
            # elif len(self.register_cache) >= self.register_cache_size:
            #     # Simple LRU
            #     oldest_key = next(iter(self.register_cache))
            #     del self.register_cache[oldest_key]
            #     self.register_cache[cache_key] = value
            
            return value
        elif operand['type'] == 'immediate':
            return operand['value']
        elif operand['type'] == 'memory':
            # Calculate address at access time
            if 'address' in operand:
                address = operand['address']
            elif 'indirect' in operand:
                address = self.Pregisters[operand['reg_idx']] if operand['reg_type'] == 'P' else self.Rregisters[operand['reg_idx']]
            elif 'indexed' in operand:
                base = self.Pregisters[operand['reg_idx']] if operand['reg_type'] == 'P' else self.Rregisters[operand['reg_idx']]
                address = (base + operand['index']) & 0xFFFF
            else:
                raise Exception("Invalid memory operand")
            
            # Determine read size based on destination operand
            if dest_operand and dest_operand['type'] == 'register':
                if dest_operand['reg_type'] == 'R':
                    return self.memory.read_byte(address)
                else:  # P register
                    return self.memory.read_word(address)
            else:
                # Default to word for backward compatibility
                return self.memory.read_word(address)
        else:
            raise Exception(f"Unknown operand type: {operand['type']}")

    def set_operand_value(self, operand, value, source_operand=None):
        """Set value to operand"""
        if operand['type'] == 'register':
            self._set_operand_value(operand['reg_type'], operand['reg_idx'], value)
            # Invalidate register cache for this register
            # cache_key = (operand['reg_type'], operand['reg_idx'])
            # if cache_key in self.register_cache:
            #     del self.register_cache[cache_key]
        elif operand['type'] == 'memory':
            # Calculate address at access time
            if 'address' in operand:
                address = operand['address']
            elif 'indirect' in operand:
                address = self.Pregisters[operand['reg_idx']] if operand['reg_type'] == 'P' else self.Rregisters[operand['reg_idx']]
            elif 'indexed' in operand:
                base = self.Pregisters[operand['reg_idx']] if operand['reg_type'] == 'P' else self.Rregisters[operand['reg_idx']]
                address = (base + operand['index']) & 0xFFFF
            else:
                raise Exception("Invalid memory operand")
            
            # Determine write size based on source operand or value size
            if source_operand and source_operand['type'] == 'immediate':
                if source_operand.get('size') == 8:
                    self.write_byte(address, value)
                else:  # 16-bit or unknown
                    self.write_memory(address, value, bytes=2)
            elif source_operand and source_operand['type'] == 'register':
                if source_operand['reg_type'] == 'R':
                    self.write_byte(address, value)
                else:  # P register or other
                    self.write_memory(address, value, bytes=2)
            else:
                # Default to word for backward compatibility
                self.write_memory(address, value, bytes=2)
        else:
            raise Exception(f"Cannot set value for operand type: {operand['type']}")

    def get_register_value(self, reg_num):
        """Get register value by number (0-22)"""
        if 0 <= reg_num <= 9:  # R0-R9
            return self.Rregisters[reg_num]
        elif 10 <= reg_num <= 19:  # P0-P9
            return self.Pregisters[reg_num - 10]
        elif reg_num == 20:  # VX
            return self.gfx.Vregisters[0]
        elif reg_num == 21:  # VY
            return self.gfx.Vregisters[1]
        elif reg_num == 22:  # VC
            return self.gfx.Vregisters[3]
        else:
            raise Exception(f"Invalid register number: {reg_num}")
    
    def set_register_value(self, reg_num, value):
        """Set register value by number (0-21)"""
        if 0 <= reg_num <= 9:  # R0-R9
            self.Rregisters[reg_num] = value & 0xFF
        elif 10 <= reg_num <= 19:  # P0-P9
            self.Pregisters[reg_num - 10] = value & 0xFFFF
        elif reg_num == 20:  # VX
            self.gfx.Vregisters[0] = value & 0xFF
        elif reg_num == 21:  # VY
            self.gfx.Vregisters[1] = value & 0xFF
        elif reg_num == 22:  # VC
            self.gfx.Vregisters[3] = value & 0xFF
        else:
            raise Exception(f"Invalid register number: {reg_num}")
    
    def get_operand_address(self, mode_bits):
        """Get address for memory write operations"""
        if mode_bits == 0:  # Register direct - not an address
            raise Exception("Cannot get address for register direct mode")
        elif mode_bits == 1:  # Immediate 8-bit - not an address
            raise Exception("Cannot get address for immediate 8-bit mode")
        elif mode_bits == 2:  # Immediate 16-bit - not an address
            raise Exception("Cannot get address for immediate 16-bit mode")
        elif mode_bits == 3:  # Memory reference
            indexed = (self._current_mode_byte & (1 << 6)) != 0
            direct = (self._current_mode_byte & (1 << 7)) != 0
            
            if direct and not indexed:
                # Direct memory address
                return self.fetch_word()
            elif not direct and not indexed:
                # Register indirect
                reg_code = self.fetch_byte()
                idx, typ = self.reg_index(reg_code)
                if typ == 'P':
                    return self.Pregisters[idx] & 0xFFFF
                elif typ == 'R':
                    return self.Rregisters[idx] & 0xFFFF
                else:
                    raise Exception(f"Invalid register type {typ} for indirect addressing")
            elif not direct and indexed:
                # Register indexed
                reg_code = self.fetch_byte()
                index = self.fetch_byte()
                idx, typ = self.reg_index(reg_code)
                if typ == 'P':
                    base_addr = self.Pregisters[idx]
                elif typ == 'R':
                    base_addr = self.Rregisters[idx]
                else:
                    raise Exception(f"Invalid register type {typ} for indexed addressing")
                
                # FP (P9) and SP (P8) use signed offset for stack-relative addressing
                # Convert unsigned byte to signed (-128 to +127)
                if idx in [8, 9]:  # SP or FP
                    signed_offset = index if index < 128 else index - 256
                    return (base_addr + signed_offset) & 0xFFFF
                else:
                    return (base_addr + index) & 0xFFFF
            elif direct and indexed:
                # Direct indexed
                addr = self.fetch_word()
                index = self.fetch_byte()
                return (addr + index) & 0xFFFF
        else:
            raise Exception(f"Invalid mode bits: {mode_bits}")

    def step( self ):
        if self.halted:
            return
        
        self.cycles += 1  # Increment cycle counter
        
        # Publish tick event at start of step (timer ticks before instruction execution)
        if self.bus:
            self.bus.publish('cpu.tick', self.cycles)
        
        if self.profiling_enabled:
            if self.profile_data['cycle_start_time'] is None:
                self.profile_data['cycle_start_time'] = time.time()
            self.profile_data['total_cycles'] += 1
        
        # Poll UART host bridge so RX data can trigger interrupts.
        self.uart.poll_host_bridge()
        
        # Fetch opcode with caching for hot-path optimization
        opcode = self.memory.fetch_opcode(self.pc)
        self.pc = (self.pc + 1) & 0xFFFF
        self._execute_instruction(opcode)
        
        # Publish post-step event (interrupt check, etc.)
        if self.bus:
            self.bus.publish('cpu.post_step', self)
        
        # Refresh only when async interrupt sources are enabled but the fast gate is stale.
        if self.has_pending_interrupt_sources:
            self._check_pending_interrupts()
        elif self._has_enabled_async_interrupt_sources():
            self._refresh_pending_interrupt_sources()
            if self.has_pending_interrupt_sources:
                self._check_pending_interrupts()

    def _execute_instruction(self, opcode):
        """Execute a single instruction by opcode (no caching)."""
        if self.profiling_enabled:
            self.profile_data['instructions_executed'] += 1
            if opcode not in self.profile_data['opcode_counts']:
                self.profile_data['opcode_counts'][opcode] = 0
            self.profile_data['opcode_counts'][opcode] += 1
        
        instruction = self.instruction_table.get(opcode)
        if instruction:
            # Check if this is a no-operand instruction
            if opcode in self.no_operand_opcodes:
                # No-operand instructions don't have mode byte
                self._current_mode_byte = 0
                self.operands = []
                instruction.execute(self)
                self._check_hw_breakpoints()
            else:
                # All other instructions use prefixed operand format
                # Fetch mode byte with caching
                mode_byte = self.memory.fetch_opcode(self.pc)
                self._current_mode_byte = mode_byte
                self.pc = (self.pc + 1) & 0xFFFF

                if instruction.handler is not None:
                    # Handler-based instruction: decode operands with the new
                    # standalone decoder and advance PC past operand bytes.
                    # decode_operands() returns (operands, byte_length) — use it!
                    self.operands, byte_length = decode_operands(
                        self.memory, self.pc, mode_byte, instruction.num_operands,
                        self.regfile.decode_register_code
                    )
                    self.pc = (self.pc + byte_length) & 0xFFFF
                else:
                    # Legacy class-based instruction: it will call parse_operands()
                    # internally and advance PC itself. Provide an empty operands
                    # list in case a handler fallback is ever triggered.
                    self.operands = []

                instruction.execute(self)
                self._check_hw_breakpoints()
                # Release operands back to pool after handler-based execution
                if instruction.handler is not None and hasattr(self, 'operands'):
                    from core.fetch import release_operands
                    release_operands(self.operands)
        else:
            raise Exception(f"Unknown opcode: {opcode:02X}")

    def execute(self, opcode):
        """Execute instruction using dispatch table (legacy method for compatibility)"""
        self._execute_instruction(opcode)

if __name__ == "__main__":
    print("Nova-16")