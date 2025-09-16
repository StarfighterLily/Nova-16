import numpy as np
import nova_memory as mem
import nova_gfx as gpu
import nova_sound as sound
from instructions import create_instruction_table

class CPU:
    def __init__( self, memory, gfx, keyboard=None, sound_system=None, stack_size = 65535 ):
        self.memory = memory
        self.gfx = gfx
        self.keyboard_device = keyboard
        
        # Initialize sound system
        if sound_system is None:
            self.sound = sound.NovaSound()
            self.sound.set_memory_reference(memory)
        else:
            self.sound = sound_system

        self.Rregisters = [0] * 10  # R registers (8-bit)
        self.Pregisters = [0] * 10  # P registers (16-bit)

        # Initialize stack pointer and frame pointer
        self.Pregisters[8] = 0xFFFF  # SP (Stack Pointer)
        self.Pregisters[9] = 0xFFFF  # FP (Frame Pointer)

        self.pc = 0x0000

        # Internal flag array for bulk operations and compatibility
        self._flags = [0] * 12  # CPU flags
        self._flags[ 11 ] = 0 # Hacker flag (E), set to 1 if the user is a hacker (not touched by the CPU)
        self._flags[ 10 ] = 0 # BCD Carry flag (A), set to 1 if the result of an operation is greater than 9
        self._flags[ 9 ] = 0 # Direction flag (H), set to 1 if the CPU runs High to Low
        self._flags[ 8 ] = 0 # Parity flag (P), set to 1 if the result of an operation is even
        self._flags[ 7 ] = 0 # Zero flag (Z), set to 1 if the result of an operation is 0
        self._flags[ 6 ] = 0 # Carry flag (C), set to 1 if the result of an operation is greater than 255
        self._flags[ 5 ] = 0 # Interrupt flag (I), set to 1 if interrupts are enabled
        self._flags[ 4 ] = 0 # Decimal flag (D), set to 1 if BCD mode is enabled
        self._flags[ 3 ] = 0 # Break flag (B), set to 1 if a breakpoint is hit
        self._flags[ 2 ] = 0 # Overflow flag (O), set to 1 if the result of an operation overflows
        self._flags[ 1 ] = 0 # Sign flag (S), set to 1 if the result of an operation is negative
        self._flags[ 0 ] = 0 # Trap flag (T), set to 1 to enable stepping
        
        # Legacy compatibility - points to internal array
        self.flags = self._flags

        # Flag to track if last operation was CMP for correct carry flag handling
        self._last_operation_was_cmp = False

        self.stack_size = stack_size
        self.stack = []
        
        self.interrupts = [0] * 8  # Interrupt enable flags
        self.interrupts[ 0 ] = 0 # Timer interrupt (T) set to 1 if the Timer interrupt is enabled
        self.interrupts[ 1 ] = 0 # Serial interrupt (S) set to 1 if the Serial interrupt is enabled
        self.interrupts[ 2 ] = 0 # Keyboard interrupt (K) set to 1 if the Keyboard interrupt is enabled
        self.interrupts[ 3 ] = 0 # User interrupt (U1) set to 1 if the User interrupt 1 is enabled
        self.interrupts[ 4 ] = 0 # User interrupt (U2) set to 1 if the User interrupt 2 is enabled

        self.timer = [0] * 4  # Timer registers # Timers for the timer interrupt
        self.timer[ 0 ] = 0 # Timer counter (T)
        self.timer[ 1 ] = 0 # Timer modulo (M)
        self.timer[ 2 ] = 0 # Timer control (C)
        self.timer[ 3 ] = 0 # Timer speed (S)
        
        # Timer internal state
        self.timer_cycles = 0  # Cycle counter for timer
        self.timer_enabled = False  # Timer enable state
        
        self.serial = [0] * 2  # Serial data for the serial interrupt
        self.serial[ 0 ] = 0 # Serial data register (S)
        self.serial[ 1 ] = 0 # Serial control register (C)

        self.keyboard = [0] * 4  # Keyboard data for the keyboard interrupt
        self.keyboard[ 0 ] = 0 # Keyboard data register (D) - current key code
        self.keyboard[ 1 ] = 0 # Keyboard status register (S) - status flags
        self.keyboard[ 2 ] = 0 # Keyboard control register (C) - control flags  
        self.keyboard[ 3 ] = 0 # Keyboard buffer count (B) - number of keys in buffer
        
        self.key_buffer = []  # Circular buffer for keyboard input (max 16 keys)
        self.key_buffer_size = 16

        self.halted = False
        
        # Pre-computed register lookup table for O(1) access
        self._register_lookup = self._build_register_lookup_table()
        
        # Interrupt checking optimization
        self.interrupt_check_counter = 0
        self.interrupt_check_frequency = 8  # Check every 8 instructions
        self.last_interrupt_state = 0  # Cache of last interrupt state
        
        # Memory prefetch optimization
        self.prefetch_buffer = np.zeros(16, dtype=np.uint8)  # 16-byte prefetch buffer
        self.prefetch_pc = 0  # PC when buffer was loaded
        self.prefetch_valid = False  # Is the buffer valid?
        
        # Timer optimization
        self.timer_update_counter = 0
        self.timer_update_frequency = 4  # Update timer every 4 cycles instead of every cycle
        
        # Initialize instruction dispatch table
        self.instruction_table = create_instruction_table()
        
        # Connect memory system to graphics for sprite memory-mapping
        self.memory.gfx_system = self.gfx

    # ========================================
    # FLAG PROPERTIES - Readable Access to CPU Flags
    # ========================================
    
    @property
    def trap_flag(self):
        """Trap flag (T) - bit 0: Enable single-step mode"""
        return bool(self._flags[0])
    
    @trap_flag.setter
    def trap_flag(self, value):
        self._flags[0] = int(bool(value))
    
    @property
    def sign_flag(self):
        """Sign flag (S) - bit 1: Result is negative"""
        return bool(self._flags[1])
    
    @sign_flag.setter
    def sign_flag(self, value):
        self._flags[1] = int(bool(value))
    
    @property
    def overflow_flag(self):
        """Overflow flag (O) - bit 2: Arithmetic overflow occurred"""
        return bool(self._flags[2])
    
    @overflow_flag.setter
    def overflow_flag(self, value):
        self._flags[2] = int(bool(value))
    
    @property
    def break_flag(self):
        """Break flag (B) - bit 3: Breakpoint hit"""
        return bool(self._flags[3])
    
    @break_flag.setter
    def break_flag(self, value):
        self._flags[3] = int(bool(value))
    
    @property
    def decimal_flag(self):
        """Decimal flag (D) - bit 4: BCD mode enabled"""
        return bool(self._flags[4])
    
    @decimal_flag.setter
    def decimal_flag(self, value):
        self._flags[4] = int(bool(value))
    
    @property
    def interrupt_flag(self):
        """Interrupt flag (I) - bit 5: Interrupts enabled"""
        return bool(self._flags[5])
    
    @interrupt_flag.setter
    def interrupt_flag(self, value):
        self._flags[5] = int(bool(value))
    
    @property
    def carry_flag(self):
        """Carry flag (C) - bit 6: Arithmetic carry/borrow occurred"""
        return bool(self._flags[6])
    
    @carry_flag.setter
    def carry_flag(self, value):
        self._flags[6] = int(bool(value))
    
    @property
    def zero_flag(self):
        """Zero flag (Z) - bit 7: Result is zero"""
        return bool(self._flags[7])
    
    @zero_flag.setter
    def zero_flag(self, value):
        self._flags[7] = int(bool(value))
    
    @property
    def parity_flag(self):
        """Parity flag (P) - bit 8: Result has even parity"""
        return bool(self._flags[8])
    
    @parity_flag.setter
    def parity_flag(self, value):
        self._flags[8] = int(bool(value))
    
    @property
    def direction_flag(self):
        """Direction flag (H) - bit 9: CPU runs High to Low"""
        return bool(self._flags[9])
    
    @direction_flag.setter
    def direction_flag(self, value):
        self._flags[9] = int(bool(value))
    
    @property
    def bcd_carry_flag(self):
        """BCD Carry flag (A) - bit 10: BCD operation carry"""
        return bool(self._flags[10])
    
    @bcd_carry_flag.setter
    def bcd_carry_flag(self, value):
        self._flags[10] = int(bool(value))
    
    @property
    def hacker_flag(self):
        """Hacker flag (E) - bit 11: User is a hacker (not touched by CPU)"""
        return bool(self._flags[11])
    
    @hacker_flag.setter
    def hacker_flag(self, value):
        self._flags[11] = int(bool(value))

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
        return int(self.sound.get_register('SA'))
    
    @sa.setter
    def sa(self, value):
        self.sound.update_registers(sa=int(value) & 0xFFFF)
    
    @property
    def sf(self):
        """SF register - Sound Frequency (8-bit)"""
        return int(self.sound.get_register('SF'))
    
    @sf.setter
    def sf(self, value):
        self.sound.update_registers(sf=int(value) & 0xFF)
    
    @property
    def sv(self):
        """SV register - Sound Volume (8-bit)"""
        return int(self.sound.get_register('SV'))
    
    @sv.setter
    def sv(self, value):
        self.sound.update_registers(sv=int(value) & 0xFF)
    
    @property
    def sw(self):
        """SW register - Sound Waveform/Control (8-bit)"""
        return int(self.sound.get_register('SW'))
    
    @sw.setter
    def sw(self, value):
        self.sound.update_registers(sw=int(value) & 0xFF)

    # ========================================
    # BULK OPERATIONS - Maintain numpy efficiency
    # ========================================
    
    def reset_all_flags(self):
        """Reset all flags to 0 - efficient bulk operation"""
        self._flags[:] = 0
    
    def reset_all_registers(self):
        """Reset all registers to 0 - efficient bulk operation"""
        self.Rregisters[:] = 0
        self.Pregisters[:] = 0
        
        # Re-initialize stack pointer and frame pointer
        self.Pregisters[8] = 0xFFFF  # SP
        self.Pregisters[9] = 0xFFFF  # FP
    
    def get_flag_state(self):
        """Get complete flag state as numpy array"""
        return self._flags.copy()
    
    def set_flag_state(self, flag_array):
        """Set complete flag state from numpy array"""
        self._flags[:] = flag_array
    
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
        self.Rregisters[:] = 0
        self.Pregisters[:] = 0
        self.pc = 0x0000
        self._flags[:] = 0  # Use internal flag array
        self.stack = []
        self.interrupts[:] = 0
        self.timer[:] = 0
        self.timer_cycles = 0
        self.timer_enabled = False
        self.serial[:] = 0
        self.keyboard[:] = 0
        self.key_buffer = []
        self.halted = False
        self.memory.memory[:] = 0
        self.gfx.vram[:] = 0
        self.gfx.screen[:] = 0
        self.gfx.flags[:] = 0
        self.gfx.Vregisters[:] = 0
        self.gfx.vmode = 0
        
        # Reset sound system
        self.sound.sstop()  # Stop all sounds
        self.sound.update_registers(sa=0, sf=0, sv=0, sw=0)  # Reset sound registers
        
        # Rebuild register lookup table 
        self._register_lookup = self._build_register_lookup_table()

        # Connect keyboard if provided
        if self.keyboard_device is not None:
            self.keyboard_device.cpu = self  # Set back-reference

    def _get_operand_value( self, type, idx ):
        if type == 'R': return int( self.Rregisters[ idx ] )
        if type == 'P': return int( self.Pregisters[ idx ] )
        if type == 'V': return int( self.gfx.Vregisters[ idx ] )
        if type == 'SP': return int( self.SP )
        if type == 'FP': return int( self.FP )
        if type == 'T': return int( self.timer[ idx ] )  # Generic timer register access
        if type == 'TT': return int( self.timer[ 0 ] )  # Timer Time/Counter
        if type == 'TM': return int( self.timer[ 1 ] )  # Timer Modulo
        if type == 'TC': return int( self.timer[ 2 ] )  # Timer Control
        if type == 'TS': return int( self.timer[ 3 ] )  # Timer Speed
        if type == 'VL': return int( self.gfx.VL )  # Graphics Layer register
        
        # Sound registers
        if type == 'SA': return int( self.sound.get_register('SA') )  # Sound Address
        if type == 'SF': return int( self.sound.get_register('SF') )  # Sound Frequency
        if type == 'SV': return int( self.sound.get_register('SV') )  # Sound Volume
        if type == 'SW': return int( self.sound.get_register('SW') )  # Sound Waveform
        if type == 'SA:': return int( (self.sound.get_register('SA') >> 8) & 0xFF )  # Sound Address high byte
        if type == ':SA': return int( self.sound.get_register('SA') & 0xFF )  # Sound Address low byte
        
        # Optimized indirect memory access - Phase 3
        if type == 'Rind': return self.memory.read_byte( self.Rregisters[ idx ] )
        if type == 'Pind': return self.memory.read_byte( self.Pregisters[ idx ] )
        if type == 'SPind': return self.memory.read_byte( self.SP )
        if type == 'FPind': return self.memory.read_byte( self.FP )
        if type == 'Vind': return self.memory.read_byte( self.gfx.Vregisters[ idx ] )
        
        # NOTE: Indexed addressing (Ridx, Pidx, etc.) should not be used in _get_operand_value
        # because they require an offset parameter that must be fetched by individual instructions.
        # The following are kept for compatibility but may not work correctly:
        if type == 'Ridx': return self.memory.read_byte( self.Rregisters[ idx ] )
        if type == 'Pidx': return self.memory.read_byte( self.Pregisters[ idx ] )
        if type == 'Vidx': return self.memory.read_byte( self.gfx.Vregisters[ idx ] )
        return 0

    def _set_operand_value( self, type, idx, value ):
        """Set value to operand based on type"""
        if type == 'R': 
            self.Rregisters[ idx ] = int(value) & 0xFF
        elif type == 'P': 
            self.Pregisters[ idx ] = int(value) & 0xFFFF
        elif type == 'SP':
            self.SP = int(value) & 0xFFFF
        elif type == 'FP':
            self.FP = int(value) & 0xFFFF
        elif type == 'V': 
            self.gfx.Vregisters[ idx ] = int(value) & 0xFFFF
        elif type == 'T':
            self.timer[ idx ] = int(value) & 0xFF
            # Update timer enabled state when control register (idx=2) is written
            if idx == 2:
                self.set_timer_control(self.timer[ 2 ])
        elif type == 'TT': 
            self.timer[ 0 ] = int(value) & 0xFF
        elif type == 'TM': 
            self.timer[ 1 ] = int(value) & 0xFF
        elif type == 'TC': 
            self.timer[ 2 ] = int(value) & 0xFF
            # Update timer enabled state when control register is written
            self.set_timer_control(self.timer[ 2 ])
        elif type == 'TS': 
            self.timer[ 3 ] = int(value) & 0xFF
        elif type == 'VL': 
            self.gfx.VL = int(value) & 0xFF
            
        # Sound registers
        elif type == 'SA': 
            self.sound.update_registers(sa=int(value) & 0xFFFF)
        elif type == 'SF': 
            self.sound.update_registers(sf=int(value) & 0xFF)
        elif type == 'SV': 
            self.sound.update_registers(sv=int(value) & 0xFF)
        elif type == 'SW': 
            self.sound.update_registers(sw=int(value) & 0xFF)
        elif type == 'SA:':  # Sound Address high byte
            current_sa = self.sound.get_register('SA')
            new_sa = (current_sa & 0x00FF) | ((int(value) & 0xFF) << 8)
            self.sound.update_registers(sa=new_sa)
        elif type == ':SA':  # Sound Address low byte
            current_sa = self.sound.get_register('SA')
            new_sa = (current_sa & 0xFF00) | (int(value) & 0xFF)
            self.sound.update_registers(sa=new_sa)
        
        # Optimized indirect memory writes - Phase 3
        elif type == 'Rind': 
            self.write_byte( self.Rregisters[ idx ], int(value) & 0xFF )
        elif type == 'Pind': 
            self.write_byte( self.Pregisters[ idx ], int(value) & 0xFF )
        elif type == 'SPind':
            self.write_byte( self.SP, int(value) & 0xFF )
        elif type == 'FPind':
            self.write_byte( self.FP, int(value) & 0xFF )
        elif type == 'Vind': 
            self.write_byte( self.gfx.Vregisters[ idx ], int(value) & 0xFF )
        
        # NOTE: Indexed addressing (Ridx, Pidx, etc.) should not be used in _set_operand_value
        # because they require an offset parameter that must be fetched by individual instructions.
        # The following are kept for compatibility but may not work correctly:
        elif type == 'Ridx': 
            self.write_byte( self.Rregisters[ idx ], int(value) & 0xFF )
        elif type == 'Pidx': 
            self.write_byte( self.Pregisters[ idx ], int(value) & 0xFF )
        elif type == 'Vidx': 
            self.write_byte( self.gfx.Vregisters[ idx ], int(value) & 0xFF )

    def _set_flags_8bit(self, result, original_result=None):
        """Set flags for 8-bit operations using readable property names"""
        if original_result is None:
            original_result = result
        
        # Zero flag (Z) - result is zero
        self.zero_flag = (result & 0xFF) == 0
        
        # Carry flag (C) - for subtraction (CMP), set when borrow occurs (val1 < val2)
        # For other operations, overflow/underflow occurred
        if hasattr(self, '_last_operation_was_cmp') and self._last_operation_was_cmp:
            self.carry_flag = original_result < 0  # Borrow occurred
            self._last_operation_was_cmp = False
        else:
            self.carry_flag = original_result > 0xFF or original_result < 0
        
        # Sign flag (S) - result is negative (bit 7 set)
        self.sign_flag = (result & 0x80) != 0
        
        # Parity flag (P) - even number of 1s in result
        parity = bin(result & 0xFF).count('1') % 2
        self.parity_flag = parity == 0

    def _set_flags_16bit(self, result, original_result=None):
        """Set flags for 16-bit operations using readable property names"""
        if original_result is None:
            original_result = result
            
        # Zero flag (Z) - result is zero
        self.zero_flag = (result & 0xFFFF) == 0
        
        # Carry flag (C) - for subtraction (CMP), set when borrow occurs (val1 < val2)
        # For other operations, overflow/underflow occurred
        if hasattr(self, '_last_operation_was_cmp') and self._last_operation_was_cmp:
            self.carry_flag = original_result < 0  # Borrow occurred
            self._last_operation_was_cmp = False
        else:
            self.carry_flag = original_result > 0xFFFF or original_result < 0
        
        # Sign flag (S) - result is negative (bit 15 set)
        self.sign_flag = (result & 0x8000) != 0
        
        # Parity flag (P) - even number of 1s in low byte
        parity = bin(result & 0xFF).count('1') % 2
        self.parity_flag = parity == 0

    def _set_overflow_flag_8bit(self, op1, op2, result, is_subtraction=False):
        """Set overflow flag for 8-bit operations using readable property name"""
        if is_subtraction:
            # Overflow in subtraction: (pos - neg = neg) or (neg - pos = pos)
            overflow = ((op1 & 0x80) != (op2 & 0x80)) and ((op1 & 0x80) != (result & 0x80))
        else:
            # Overflow in addition: (pos + pos = neg) or (neg + neg = pos)
            overflow = ((op1 & 0x80) == (op2 & 0x80)) and ((op1 & 0x80) != (result & 0x80))
        self.overflow_flag = overflow

    def _set_overflow_flag_16bit(self, op1, op2, result, is_subtraction=False):
        """Set overflow flag for 16-bit operations using readable property name"""
        if is_subtraction:
            # Overflow in subtraction: (pos - neg = neg) or (neg - pos = pos)
            overflow = ((op1 & 0x8000) != (op2 & 0x8000)) and ((op1 & 0x8000) != (result & 0x8000))
        else:
            # Overflow in addition: (pos + pos = neg) or (neg + neg = pos)
            overflow = ((op1 & 0x8000) == (op2 & 0x8000)) and ((op1 & 0x8000) != (result & 0x8000))
        self.overflow_flag = overflow

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
        parity = bin(result & 0xFF).count('1') % 2
        self.parity_flag = parity == 0

    # Keyboard input handling
    def add_key_to_buffer(self, key_code):
        """Add a key press to the keyboard buffer and trigger interrupt if enabled"""
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
                
    def read_key_from_buffer(self):
        """Read and remove the oldest key from the keyboard buffer"""
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
        self.key_buffer = []
        self.keyboard[0] = 0  # Clear data register
        self.keyboard[1] = 0  # Clear status flags
        self.keyboard[3] = 0  # Clear buffer count

    def _trigger_interrupt(self, interrupt_vector):
        """Trigger an interrupt if global interrupts are enabled"""
        if int(self._flags[5]) == 1:  # Check if interrupts are globally enabled
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
                if int(self._flags[i]) != 0:
                    flags_val |= (1 << i)
            
            self.Pregisters[8] = (int(self.Pregisters[8]) - 2) & 0xFFFF  # Decrement SP
            self.memory.write_word(self.Pregisters[8], flags_val)
            
            self.Pregisters[8] = (int(self.Pregisters[8]) - 2) & 0xFFFF  # Decrement SP
            self.memory.write_word(self.Pregisters[8], self.pc)
            
            # Disable interrupts during interrupt handling
            self._flags[5] = 0
            
            # Jump to interrupt handler
            self.pc = handler_address
            
            # Invalidate prefetch buffer after jump
            self.invalidate_prefetch()
    
    def _check_pending_interrupts(self):
        """Optimized interrupt checking with batching and caching"""
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
            (self.interrupts[3] << 5) |  # User1 enabled
            (self.interrupts[4] << 4) |  # User2 enabled
            ((self.keyboard[1] & 0x80) >> 3) |  # Keyboard pending
            ((self.serial[1] & 0x80) >> 4)      # Serial pending
        )
        
        # Skip detailed check if state hasn't changed
        if current_state == self.last_interrupt_state and current_state == 0:
            return False
            
        self.last_interrupt_state = current_state
        
        # Explicit loop with early exit instead of generator
        # Check keyboard interrupt first (most common)
        if self.interrupts[2] == 1 and (self.keyboard[1] & 0x80):
            self.keyboard[1] &= 0x7F  # Clear interrupt pending flag
            self._trigger_interrupt(2)
            return True  # Interrupt was handled
            
        # Check serial interrupt
        if self.interrupts[1] == 1 and (self.serial[1] & 0x80):
            self.serial[1] &= 0x7F  # Clear interrupt pending flag
            self._trigger_interrupt(1)
            return True
            
        # Check user interrupts
        if self.interrupts[3] == 1:  # User interrupt 1
            # User interrupt logic would go here
            pass
            
        if self.interrupts[4] == 1:  # User interrupt 2
            # User interrupt logic would go here
            pass
            
        return False  # No interrupt handled
    
    def _check_timer_interrupt(self):
        """Check if timer interrupt should be triggered"""
        if not self.timer_enabled:
            return False
            
        # Check if timer has reached or exceeded modulo value
        if self.timer[1] > 0 and self.timer[0] >= self.timer[1]:
            return True
            
        return False
    
    def update_timer(self):
        """Optimized timer update - batched for better performance"""
        # Fast exit if timer is disabled
        if not self.timer_enabled:
            return
            
        # Batch timer updates for better performance
        self.timer_update_counter += 1
        if self.timer_update_counter < self.timer_update_frequency:
            return
        
        # Reset counter and process batched cycles
        cycles_to_process = self.timer_update_counter
        self.timer_update_counter = 0
        
        # Increment cycle counter by batch amount
        self.timer_cycles += cycles_to_process
        
        # Check if we should increment timer based on speed setting
        # Speed controls how many cycles per timer increment:
        # Speed 0 = every cycle, 1 = every 2 cycles, 2 = every 4 cycles, etc.
        # Use linear scaling instead of exponential for more reasonable control
        speed_value = int(self.timer[3]) & 0xFF
        if speed_value == 0:
            speed_divisor = 1  # Every cycle
        else:
            # Linear scaling: speed 1 = 2 cycles, speed 4 = 5 cycles, speed 16 = 17 cycles, etc.
            speed_divisor = speed_value + 1
        
        if self.timer_cycles >= speed_divisor:
            timer_increments = self.timer_cycles // speed_divisor
            self.timer_cycles = self.timer_cycles % speed_divisor
            
            # Clamp timer increments to prevent overflow
            # Limit to reasonable increments to avoid numpy overflow warnings
            timer_increments = min(timer_increments, 255)
            
            # Increment timer counter by calculated amount (use Python int to avoid numpy overflow warnings)
            new_timer_value = (int(self.timer[0]) + int(timer_increments)) & 0xFF
            self.timer[0] = new_timer_value
            
            # Check for timer interrupt after incrementing
            if self.interrupts[0] == 1 and self.timer[1] > 0 and self.timer[0] >= self.timer[1]:
                # Reset timer counter when interrupt is triggered
                self.timer[0] = 0
                self._trigger_interrupt(0)
    
    def set_timer_control(self, control_value):
        """Set timer control register and update timer state"""
        self.timer[2] = control_value & 0xFF
        
        # Bit 0: Timer enable
        self.timer_enabled = bool(control_value & 0x01)
        
        # Bit 1: Timer interrupt enable
        self.interrupts[0] = int(bool(control_value & 0x02))
        
        # If timer is disabled, reset internal state
        if not self.timer_enabled:
            self.timer_cycles = 0
            self.timer[0] = 0
    
    def get_timer_status(self):
        """Get timer status for debugging/monitoring"""
        return {
            'counter': self.timer[0],
            'modulo': self.timer[1], 
            'control': self.timer[2],
            'speed': self.timer[3],
            'enabled': self.timer_enabled,
            'cycles': self.timer_cycles,
            'interrupt_enabled': bool(self.interrupts[0])
        }

    def _build_register_lookup_table(self):
        """Build optimized lookup table for register access - O(1) performance"""
        lookup = {}
        
        # Sound registers
        lookup[0xDD] = (0, 'SA')  # Sound Address
        lookup[0xDE] = (0, 'SF')  # Sound Frequency
        lookup[0xDF] = (0, 'SV')  # Sound Volume
        lookup[0xE0] = (0, 'SW')  # Sound Waveform/Control
        
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
        lookup[0xFB] = (8, 'P')  # SP = P8
        lookup[0xFC] = (9, 'P')  # FP = P9
            
        # V registers (0xFD-0xFE) - VX, VY
        lookup[0xFD] = (0, 'V')  # VX
        lookup[0xFE] = (1, 'V')  # VY
        
        return lookup

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
            self.pc += 1
            return data[0]
        elif bytes == 2:
            data = self.memory.read( self.pc, 2 )
            self.pc += 2
            return (int(data[0]) << 8) | int(data[1])  # Convert to int first for proper bit operations
        else:
            data = self.memory.read( self.pc, bytes )
            self.pc += bytes
            return [ int( b ) for b in data ]
    
    # ========================================
    # OPTIMIZED FETCH METHODS - Phase 2
    # ========================================
    
    def fetch_byte(self):
        """Optimized single byte fetch with prefetching"""
        # Disable prefetch optimization temporarily for debugging
        value = self.memory.read_byte(self.pc)
        self.pc += 1
        return int(value)
    
    def _fill_prefetch_buffer(self):
        """Fill the prefetch buffer with 16 bytes starting from current PC"""
        self.prefetch_pc = self.pc
        end_addr = min(self.pc + 16, len(self.memory.memory))
        buffer_size = end_addr - self.pc
        
        # Fill buffer with available bytes
        self.prefetch_buffer[:buffer_size] = self.memory.memory[self.pc:end_addr]
        # Zero out unused buffer space
        if buffer_size < 16:
            self.prefetch_buffer[buffer_size:] = 0
        self.prefetch_valid = True
    
    def invalidate_prefetch(self):
        """Invalidate prefetch buffer when PC changes unexpectedly (jumps, branches, etc.)"""
        self.prefetch_valid = False
        
    def write_memory(self, address, value, bytes=1):
        """Write to memory and invalidate prefetch buffer if necessary"""
        self.memory.write(address, value, bytes)
        
        # Invalidate prefetch buffer if writing to area that might be prefetched
        if (self.prefetch_valid and 
            address < self.prefetch_pc + 16 and 
            address + bytes > self.prefetch_pc):
            self.prefetch_valid = False
            
    def write_byte(self, address, value):
        """Write single byte to memory and invalidate prefetch buffer if necessary"""
        self.memory.write_byte(address, value)
        
        # Invalidate prefetch buffer if writing to area that might be prefetched
        if (self.prefetch_valid and 
            address < self.prefetch_pc + 16 and 
            address + 1 > self.prefetch_pc):
            self.prefetch_valid = False
    
    def fetch_word(self):
        """Optimized 16-bit fetch with prefetching (big-endian for Nova-16)"""
        # Temporarily disable prefetch for debugging
        # Check if we can fetch both bytes from prefetch buffer
        # if (self.prefetch_valid and 
        #     self.pc >= self.prefetch_pc and 
        #     self.pc + 1 < self.prefetch_pc + 16):
        #     offset = self.pc - self.prefetch_pc
        #     high = self.prefetch_buffer[offset]
        #     low = self.prefetch_buffer[offset + 1]
        #     self.pc += 2
        #     return (int(high) << 8) | int(low)
        
        # Use individual byte fetches with prefetching
        high = self.fetch_byte()
        low = self.fetch_byte()
        return (int(high) << 8) | int(low)
    

    def fetch_bytes(self, count):
        """Optimized multi-byte fetch returning list of ints"""
        result = [int(self.memory.memory[self.pc + i]) for i in range(count)]
        self.pc += count
        return result

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
    
    def get_register_value(self, reg_num):
        """Get register value by number (0-19)"""
        if 0 <= reg_num <= 9:  # R0-R9
            return self.Rregisters[reg_num]
        elif 10 <= reg_num <= 19:  # P0-P9
            return self.Pregisters[reg_num - 10]
        elif reg_num == 20:  # VX
            return self.gfx.Vregisters[0]
        elif reg_num == 21:  # VY
            return self.gfx.Vregisters[1]
        else:
            raise Exception(f"Invalid register number: {reg_num}")
    
    def set_register_value(self, reg_num, value):
        """Set register value by number (0-21)"""
        if 0 <= reg_num <= 9:  # R0-R9
            self.Rregisters[reg_num] = value & 0xFF
        elif 10 <= reg_num <= 19:  # P0-P9
            self.Pregisters[reg_num - 10] = value & 0xFFFF
        elif reg_num == 20:  # VX
            self.gfx.Vregisters[0] = value & 0xFFFF
        elif reg_num == 21:  # VY
            self.gfx.Vregisters[1] = value & 0xFFFF
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
        
        # Update timer first (so timer interrupt can happen before instruction execution)
        self.update_timer()
        
        #prefetchpc = self.pc
        opcode = self.fetch_byte()  # Use optimized fetch for single byte opcodes
        #print( f"pre-fetch pc: {prefetchpc:04x} opcode: {opcode:04x}" )
        self.execute( opcode )
        
        # Check for other pending interrupts (keyboard, serial, etc.)
        self._check_pending_interrupts()

    def execute(self, opcode):
        """Execute instruction using dispatch table"""
        instruction = self.instruction_table.get(opcode)
        if instruction:
            # Check if this is a no-operand instruction
            if opcode in [0x00, 0xFF, 0x01, 0x02, 0x03, 0x04, 0x1A, 0x1B, 0x1C, 0x1D]:  # HLT, NOP, RET, IRET, CLI, STI, PUSHF, POPF, PUSHA, POPA
                # No-operand instructions don't have mode byte
                instruction.execute(self)
            else:
                # All other instructions use prefixed operand format
                self._current_mode_byte = self.fetch_byte()
                instruction.execute(self)
        else:
            raise Exception(f"Unknown opcode: {opcode:02X}")

if __name__ == "__main__":
    print("Nova-16")