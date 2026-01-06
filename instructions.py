from opcodes import opcodes
import math

class BaseInstruction:
    """Base class for all instructions"""
    def __init__(self, name, opcode):
        self.name = name
        self.opcode = opcode
    
    def __repr__(self):
        return self.name.lower()
    
    def execute(self, cpu):
        raise NotImplementedError("Subclasses must implement execute method")

# No-operand instructions
class Hlt(BaseInstruction):
    def __init__(self):
        opcode_val = 0x00  # HLT
        super().__init__("HLT", opcode_val)
    
    def execute(self, cpu):
        cpu.halted = True

class Nop(BaseInstruction):
    def __init__(self):
        opcode_val = 0xFF  # NOP
        super().__init__("NOP", opcode_val)
    
    def execute(self, cpu):
        pass

class Ret(BaseInstruction):
    def __init__(self):
        opcode_val = 0x01  # RET
        super().__init__("RET", opcode_val)
    
    def execute(self, cpu):
        # Check stack bounds before reading - when RET executes there should be a return address
        # CALL pushes 2-byte return address, so valid SP values are 0x0000 to 0xFFFD
        # SP=0xFFFE means 1 byte on stack (invalid for 2-byte return address)
        # SP=0xFFFF means empty stack (no return address)
        if cpu.Pregisters[8] >= 0xFFFF:  # Not enough bytes for return address
            raise RuntimeError(f"Stack underflow: SP=0x{cpu.Pregisters[8]:04X}")
        
        # Pop PC from stack in memory
        cpu.pc = cpu.memory.read_word(cpu.Pregisters[8])
        
        # Use standardized SP manipulation
        sp = int(cpu.Pregisters[8])
        sp = (sp + 2) & 0xFFFF
        cpu.Pregisters[8] = sp
        
        # Invalidate prefetch buffer after jump
        cpu.invalidate_prefetch()
        # Invalidate instruction cache after return
        cpu.invalidate_instruction_cache()

class IRet(BaseInstruction):
    def __init__(self):
        opcode_val = 0x02  # IRET
        super().__init__("IRET", opcode_val)
    
    def execute(self, cpu):
        # Check if there's actually data on the stack for IRET
        sp = int(cpu.Pregisters[8])
        if sp == 0xFFFF:  # Stack is at initial position - nothing was pushed
            raise RuntimeError(f"Stack underflow in IRET: SP=0x{sp:04X}, no interrupt context to restore")
        if sp > 0xFFFB:  # Not enough space for both PC and flags (4 bytes total)
            raise RuntimeError(f"Stack underflow in IRET: SP=0x{sp:04X}, insufficient data on stack")
        
        # Restore PC first (it was pushed last, so it's at the bottom)
        pc_value = cpu.memory.read_word(cpu.Pregisters[8])
        cpu.pc = pc_value
        sp = int(cpu.Pregisters[8])
        sp = (sp + 2) & 0xFFFF
        cpu.Pregisters[8] = sp
        
        # Restore flags second (they were pushed first, so they're at the top)
        flags_val = cpu.memory.read_word(cpu.Pregisters[8])
        sp = int(cpu.Pregisters[8])
        sp = (sp + 2) & 0xFFFF
        cpu.Pregisters[8] = sp
        
        #print(f"IRET: Restored PC=0x{cpu.pc:04X}, SP=0x{cpu.Pregisters[8]:04X}")
        
        # Convert flags value back to array with proper type conversion
        for i in range(12):
            bit_set = (flags_val & (1 << i)) != 0
            # Ensure explicit type conversion to avoid numpy overflow
            flag_value = 1 if bit_set else 0
            cpu.flags[i] = int(flag_value) & 0xFF
        
        # Re-enable interrupts after restoring context
        cpu._flags[5] = 1
        
        # Invalidate prefetch buffer after jump
        cpu.invalidate_prefetch()
        # Invalidate instruction cache after return from interrupt
        cpu.invalidate_instruction_cache()

class Cli(BaseInstruction):
    def __init__(self):
        opcode_val = 0x03  # CLI
        super().__init__("CLI", opcode_val)
    
    def execute(self, cpu):
        cpu.flags[5] = 0  # Clear interrupt flag

class Sti(BaseInstruction):
    def __init__(self):
        opcode_val = 0x04  # STI
        super().__init__("STI", opcode_val)
    
    def execute(self, cpu):
        cpu.flags[5] = 1  # Set interrupt flag

# STC, CLC, CMC removed - conflicts with RETN (0x9F), LOOPZ (0xA0), WHILE (0xA1)

# Data movement
class Mov(BaseInstruction):
    """MOV instruction for prefixed operand system"""
    def __init__(self):
        opcode_val = 0x06  # MOV
        super().__init__("MOV", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        source_value = cpu.get_operand_value(operands[1], operands[0])
        cpu.set_operand_value(operands[0], source_value, operands[1])

# Arithmetic operations
class Add(BaseInstruction):
    """ADD instruction for prefixed operand system"""
    def __init__(self):
        opcode_val = 0x07  # ADD
        super().__init__("ADD", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        dest_value = cpu.get_operand_value(operands[0])
        source_value = cpu.get_operand_value(operands[1], operands[0])
        result = dest_value + source_value
        cpu.set_operand_value(operands[0], result)
        # Set flags based on destination operand type and masked result
        if operands[0]['type'] == 'register' and operands[0]['reg_type'] == 'R':
            masked_result = result & 0xFF
            cpu._set_overflow_flag_8bit(dest_value, source_value, result, is_subtraction=False)
            cpu._set_flags_8bit(masked_result, result)
        else:
            masked_result = result & 0xFFFF
            cpu._set_overflow_flag_16bit(dest_value, source_value, result, is_subtraction=False)
            cpu._set_flags_16bit(masked_result, result)

class Sub(BaseInstruction):
    """SUB instruction for prefixed operand system"""
    def __init__(self):
        opcode_val = 0x08  # SUB
        super().__init__("SUB", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        dest_value = cpu.get_operand_value(operands[0])
        source_value = cpu.get_operand_value(operands[1], operands[0])
        result = dest_value - source_value
        cpu.set_operand_value(operands[0], result)
        # Set flags based on destination operand type and masked result
        if operands[0]['type'] == 'register' and operands[0]['reg_type'] == 'R':
            masked_result = result & 0xFF
            cpu._set_overflow_flag_8bit(dest_value, source_value, result, is_subtraction=True)
            cpu._set_flags_8bit(masked_result, result)
        else:
            masked_result = result & 0xFFFF
            cpu._set_overflow_flag_16bit(dest_value, source_value, result, is_subtraction=True)
            cpu._set_flags_16bit(masked_result, result)

class Mul(BaseInstruction):
    """MUL instruction for prefixed operand system"""
    def __init__(self):
        opcode_val = 0x09  # MUL
        super().__init__("MUL", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        dest_value = cpu.get_operand_value(operands[0])
        source_value = cpu.get_operand_value(operands[1])
        result = dest_value * source_value
        cpu.set_operand_value(operands[0], result)
        cpu._set_flags_16bit(result, result)

class Div(BaseInstruction):
    """DIV instruction for prefixed operand system"""
    def __init__(self):
        opcode_val = 0x0A  # DIV
        super().__init__("DIV", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        dest_value = cpu.get_operand_value(operands[0])
        source_value = cpu.get_operand_value(operands[1])
        
        if source_value == 0:
            raise RuntimeError("Division by zero")
        
        quotient = dest_value // source_value
        remainder = dest_value % source_value
        
        cpu.set_operand_value(operands[0], quotient)
        # Store remainder in P3
        cpu.Pregisters[3] = remainder & 0xFFFF

class Inc(BaseInstruction):
    """INC instruction for prefixed operand system"""
    def __init__(self):
        opcode_val = 0x0B  # INC
        super().__init__("INC", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        value = cpu.get_operand_value(operands[0])
        result = value + 1
        cpu.set_operand_value(operands[0], result)
        cpu._set_flags_16bit(result, result)

class Dec(BaseInstruction):
    """DEC instruction for prefixed operand system"""
    def __init__(self):
        opcode_val = 0x0C  # DEC
        super().__init__("DEC", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        value = cpu.get_operand_value(operands[0])
        result = value - 1
        cpu.set_operand_value(operands[0], result)
        cpu._set_flags_16bit(result, result)

class Mod(BaseInstruction):
    """MOD instruction for prefixed operand system"""
    def __init__(self):
        opcode_val = 0x0D  # MOD
        super().__init__("MOD", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        dest_value = cpu.get_operand_value(operands[0])
        source_value = cpu.get_operand_value(operands[1])
        
        if source_value == 0:
            raise RuntimeError("Modulo by zero")
        
        result = dest_value % source_value
        cpu.set_operand_value(operands[0], result)
        cpu._set_flags_16bit(result, result)

class Neg(BaseInstruction):
    """NEG instruction for prefixed operand system"""
    def __init__(self):
        opcode_val = 0x0E  # NEG
        super().__init__("NEG", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        value = cpu.get_operand_value(operands[0])
        result = -value
        cpu.set_operand_value(operands[0], result)
        cpu._set_flags_16bit(result, result)

class Abs(BaseInstruction):
    """ABS instruction for prefixed operand system"""
    def __init__(self):
        opcode_val = 0x0F  # ABS
        super().__init__("ABS", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        value = cpu.get_operand_value(operands[0])
        result = abs(value)
        cpu.set_operand_value(operands[0], result)
        cpu._set_flags_16bit(result, result)

# Enhanced arithmetic operations
class Adc(BaseInstruction):
    """ADC instruction for prefixed operand system - Add with Carry"""
    def __init__(self):
        opcode_val = 0x87  # ADC
        super().__init__("ADC", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        dest_value = cpu.get_operand_value(operands[0])
        source_value = cpu.get_operand_value(operands[1])
        carry = 1 if cpu.carry_flag else 0
        result = dest_value + source_value + carry
        cpu.set_operand_value(operands[0], result)
        # Set flags based on destination operand type and masked result
        if operands[0]['type'] == 'register' and operands[0]['reg_type'] == 'R':
            masked_result = result & 0xFF
            cpu._set_overflow_flag_8bit(dest_value, source_value + carry, result, is_subtraction=False)
            cpu._set_flags_8bit(masked_result, result)
        else:
            masked_result = result & 0xFFFF
            cpu._set_overflow_flag_16bit(dest_value, source_value + carry, result, is_subtraction=False)
            cpu._set_flags_16bit(masked_result, result)

class Sbc(BaseInstruction):
    """SBC instruction for prefixed operand system - Subtract with Carry"""
    def __init__(self):
        opcode_val = 0x88  # SBC
        super().__init__("SBC", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        dest_value = cpu.get_operand_value(operands[0])
        source_value = cpu.get_operand_value(operands[1])
        carry = 1 if cpu.carry_flag else 0
        result = dest_value - source_value - carry
        cpu.set_operand_value(operands[0], result)
        # Set flags based on destination operand type and masked result
        if operands[0]['type'] == 'register' and operands[0]['reg_type'] == 'R':
            masked_result = result & 0xFF
            cpu._set_overflow_flag_8bit(dest_value, source_value + carry, result, is_subtraction=True)
            cpu._set_flags_8bit(masked_result, result)
        else:
            masked_result = result & 0xFFFF
            cpu._set_overflow_flag_16bit(dest_value, source_value + carry, result, is_subtraction=True)
            cpu._set_flags_16bit(masked_result, result)

class Mulh(BaseInstruction):
    """MULH instruction for prefixed operand system - Multiply High"""
    def __init__(self):
        opcode_val = 0x89  # MULH
        super().__init__("MULH", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        dest_value = cpu.get_operand_value(operands[0])
        source_value = cpu.get_operand_value(operands[1], operands[0])
        result = dest_value * source_value
        # Store high 16 bits of 32-bit result
        high_result = (result >> 16) & 0xFFFF
        cpu.set_operand_value(operands[0], high_result)
        cpu._set_flags_16bit(high_result, result)

class Divh(BaseInstruction):
    """DIVH instruction for prefixed operand system - Divide High"""
    def __init__(self):
        opcode_val = 0x8A  # DIVH
        super().__init__("DIVH", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        dest_value = cpu.get_operand_value(operands[0])
        source_value = cpu.get_operand_value(operands[1], operands[0])
        
        if source_value == 0:
            raise RuntimeError("Division by zero")
        
        # Combine dest (high) and P3 (low) for 32-bit dividend
        dividend = (dest_value << 16) | (cpu.Pregisters[3] & 0xFFFF)
        quotient = dividend // source_value
        remainder = dividend % source_value
        
        cpu.set_operand_value(operands[0], quotient & 0xFFFF)
        # Store remainder in P3
        cpu.Pregisters[3] = remainder & 0xFFFF

class Min(BaseInstruction):
    """MIN instruction for prefixed operand system - Minimum"""
    def __init__(self):
        opcode_val = 0x8B  # MIN
        super().__init__("MIN", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        dest_value = cpu.get_operand_value(operands[0])
        source_value = cpu.get_operand_value(operands[1], operands[0])
        result = min(dest_value, source_value)
        cpu.set_operand_value(operands[0], result)
        cpu._set_flags_16bit(result, result)

class Max(BaseInstruction):
    """MAX instruction for prefixed operand system - Maximum"""
    def __init__(self):
        opcode_val = 0x8C  # MAX
        super().__init__("MAX", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        dest_value = cpu.get_operand_value(operands[0])
        source_value = cpu.get_operand_value(operands[1], operands[0])
        result = max(dest_value, source_value)
        cpu.set_operand_value(operands[0], result)
        cpu._set_flags_16bit(result, result)

class Clz(BaseInstruction):
    """CLZ instruction for prefixed operand system - Count Leading Zeros"""
    def __init__(self):
        opcode_val = 0x8D  # CLZ
        super().__init__("CLZ", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        value = cpu.get_operand_value(operands[0])
        if value == 0:
            result = 16  # 16 bits for 16-bit values
        else:
            result = 0
            while (value & 0x8000) == 0 and result < 16:
                value <<= 1
                result += 1
        cpu.set_operand_value(operands[0], result)
        cpu._set_flags_16bit(result, result)

class Ctz(BaseInstruction):
    """CTZ instruction for prefixed operand system - Count Trailing Zeros"""
    def __init__(self):
        opcode_val = 0x8E  # CTZ
        super().__init__("CTZ", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        value = cpu.get_operand_value(operands[0])
        if value == 0:
            result = 16  # 16 bits for 16-bit values
        else:
            result = 0
            while (value & 0x0001) == 0 and result < 16:
                value >>= 1
                result += 1
        cpu.set_operand_value(operands[0], result)
        cpu._set_flags_16bit(result, result)

class Popcnt(BaseInstruction):
    """POPCNT instruction for prefixed operand system - Population Count"""
    def __init__(self):
        opcode_val = 0x8F  # POPCNT
        super().__init__("POPCNT", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        value = cpu.get_operand_value(operands[0])
        result = bin(value).count('1')
        cpu.set_operand_value(operands[0], result)
        cpu._set_flags_16bit(result, result)

# Enhanced bitwise operations
class Sar(BaseInstruction):
    """SAR instruction for prefixed operand system - Shift Arithmetic Right"""
    def __init__(self):
        opcode_val = 0x90  # SAR
        super().__init__("SAR", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        dest_value = cpu.get_operand_value(operands[0])
        shift_amount = cpu.get_operand_value(operands[1]) & 0x0F  # Limit to 0-15
        if shift_amount > 0:
            # Check if sign bit is set
            sign_bit = (dest_value & 0x8000) != 0
            result = dest_value >> shift_amount
            if sign_bit:
                # Fill the leftmost bits with 1s
                mask = ((1 << shift_amount) - 1) << (16 - shift_amount)
                result |= mask
            result &= 0xFFFF
        else:
            result = dest_value
        cpu.set_operand_value(operands[0], result)
        cpu._set_flags_16bit(result, result)

class Sal(BaseInstruction):
    """SAL instruction for prefixed operand system - Shift Arithmetic Left"""
    def __init__(self):
        opcode_val = 0x91  # SAL
        super().__init__("SAL", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        dest_value = cpu.get_operand_value(operands[0])
        shift_amount = cpu.get_operand_value(operands[1]) & 0x0F  # Limit to 0-15
        result = (dest_value << shift_amount) & 0xFFFF
        cpu.set_operand_value(operands[0], result)
        cpu._set_flags_16bit(result, result)

class Rcl(BaseInstruction):
    """RCL instruction for prefixed operand system - Rotate through Carry Left"""
    def __init__(self):
        opcode_val = 0x92  # RCL
        super().__init__("RCL", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        dest_value = cpu.get_operand_value(operands[0])
        rotate_amount = cpu.get_operand_value(operands[1]) & 0x0F  # Limit to 0-15
        result = dest_value
        for _ in range(rotate_amount):
            carry_out = (result & 0x8000) != 0
            result = ((result << 1) & 0xFFFF) | (1 if cpu.carry_flag else 0)
            cpu.carry_flag = carry_out
        cpu.set_operand_value(operands[0], result)
        # Don't call _set_flags_16bit as it would override the carry flag we just set

class Rcr(BaseInstruction):
    """RCR instruction for prefixed operand system - Rotate through Carry Right"""
    def __init__(self):
        opcode_val = 0x93  # RCR
        super().__init__("RCR", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        dest_value = cpu.get_operand_value(operands[0])
        rotate_amount = cpu.get_operand_value(operands[1]) & 0x0F  # Limit to 0-15
        result = dest_value
        for _ in range(rotate_amount):
            carry_out = (result & 0x0001) != 0
            result = (result >> 1) | (0x8000 if cpu.carry_flag else 0)
            cpu.carry_flag = carry_out
        cpu.set_operand_value(operands[0], result)
        # Don't call _set_flags_16bit as it would override the carry flag we just set

# Bitwise operations
class And(BaseInstruction):
    """AND instruction for prefixed operand system"""
    def __init__(self):
        opcode_val = 0x10  # AND
        super().__init__("AND", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        dest_value = cpu.get_operand_value(operands[0])
        source_value = cpu.get_operand_value(operands[1], operands[0])
        result = dest_value & source_value
        cpu.set_operand_value(operands[0], result)
        cpu._set_flags_16bit(result, result)

class Or(BaseInstruction):
    """OR instruction for prefixed operand system"""
    def __init__(self):
        opcode_val = 0x11  # OR
        super().__init__("OR", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        dest_value = cpu.get_operand_value(operands[0])
        source_value = cpu.get_operand_value(operands[1], operands[0])
        result = dest_value | source_value
        cpu.set_operand_value(operands[0], result)
        cpu._set_flags_16bit(result, result)

class Xor(BaseInstruction):
    """XOR instruction for prefixed operand system"""
    def __init__(self):
        opcode_val = 0x12  # XOR
        super().__init__("XOR", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        dest_value = cpu.get_operand_value(operands[0])
        source_value = cpu.get_operand_value(operands[1], operands[0])
        result = dest_value ^ source_value
        cpu.set_operand_value(operands[0], result)
        cpu._set_flags_16bit(result, result)

class Not(BaseInstruction):
    """NOT instruction for prefixed operand system"""
    def __init__(self):
        opcode_val = 0x13  # NOT
        super().__init__("NOT", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        value = cpu.get_operand_value(operands[0])
        result = (~value) & 0xFFFF  # Mask to 16 bits
        cpu.set_operand_value(operands[0], result)
        cpu._set_flags_16bit(result, result)

class Shl(BaseInstruction):
    """SHL instruction for prefixed operand system"""
    def __init__(self):
        opcode_val = 0x14  # SHL
        super().__init__("SHL", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        dest_value = cpu.get_operand_value(operands[0])
        shift_amount = cpu.get_operand_value(operands[1]) & 0x1F  # Mask to 0-31
        
        # Determine if this is an 8-bit or 16-bit operation based on destination register type
        if operands[0]['type'] == 'register' and operands[0]['reg_type'] == 'R':
            # 8-bit shift for R registers
            bit_width = 8
            mask = 0xFF
        else:
            # 16-bit shift for P registers and memory
            bit_width = 16
            mask = 0xFFFF
        
        if shift_amount >= bit_width:  # Shifts >= bit_width should result in 0
            result = 0
        else:
            result = (dest_value << shift_amount) & mask
        cpu.set_operand_value(operands[0], result)
        cpu._set_flags_16bit(result, result)

class Shr(BaseInstruction):
    """SHR instruction for prefixed operand system"""
    def __init__(self):
        opcode_val = 0x15  # SHR
        super().__init__("SHR", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        dest_value = cpu.get_operand_value(operands[0])
        shift_amount = cpu.get_operand_value(operands[1]) & 0x1F  # Mask to 0-31
        
        # Determine if this is an 8-bit or 16-bit operation based on destination register type
        if operands[0]['type'] == 'register' and operands[0]['reg_type'] == 'R':
            # 8-bit shift for R registers
            bit_width = 8
            mask = 0xFF
        else:
            # 16-bit shift for P registers and memory
            bit_width = 16
            mask = 0xFFFF
        
        if shift_amount >= bit_width:  # Shifts >= bit_width should result in 0
            result = 0
        else:
            result = dest_value >> shift_amount
        cpu.set_operand_value(operands[0], result)
        cpu._set_flags_16bit(result, result)

class Rol(BaseInstruction):
    """ROL instruction for prefixed operand system"""
    def __init__(self):
        opcode_val = 0x16  # ROL
        super().__init__("ROL", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        dest_value = cpu.get_operand_value(operands[0])
        rotate_amount = cpu.get_operand_value(operands[1]) & 0x0F  # Mask to 0-15
        
        # Determine if this is an 8-bit or 16-bit operation based on destination register type
        if operands[0]['type'] == 'register' and operands[0]['reg_type'] == 'R':
            # 8-bit rotate for R registers
            bit_width = 8
            mask = 0xFF
        else:
            # 16-bit rotate for P registers and memory
            bit_width = 16
            mask = 0xFFFF
        
        # Perform rotate
        result = ((dest_value << rotate_amount) | (dest_value >> (bit_width - rotate_amount))) & mask
        cpu.set_operand_value(operands[0], result)
        cpu._set_flags_16bit(result, result)

class Ror(BaseInstruction):
    """ROR instruction for prefixed operand system"""
    def __init__(self):
        opcode_val = 0x17  # ROR
        super().__init__("ROR", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        dest_value = cpu.get_operand_value(operands[0])
        rotate_amount = cpu.get_operand_value(operands[1]) & 0x0F  # Mask to 0-15
        
        # Determine if this is an 8-bit or 16-bit operation based on destination register type
        if operands[0]['type'] == 'register' and operands[0]['reg_type'] == 'R':
            # 8-bit rotate for R registers
            bit_width = 8
            mask = 0xFF
        else:
            # 16-bit rotate for P registers and memory
            bit_width = 16
            mask = 0xFFFF
        
        # Perform rotate
        result = ((dest_value >> rotate_amount) | (dest_value << (bit_width - rotate_amount))) & mask
        cpu.set_operand_value(operands[0], result)
        cpu._set_flags_16bit(result, result)

# Bit test and modify
class Btst(BaseInstruction):
    """BTST instruction for prefixed operand system - test bit"""
    def __init__(self):
        opcode_val = 0x6D  # BTST
        super().__init__("BTST", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        dest_value = cpu.get_operand_value(operands[0])
        bit_pos = cpu.get_operand_value(operands[1]) & 0x0F  # 0-15 bits
        bit_mask = 1 << bit_pos
        bit_set = (dest_value & bit_mask) != 0
        # Set zero flag: Z=1 if bit is 0, Z=0 if bit is 1
        cpu._flags[7] = 0 if bit_set else 1  # Direct flag access for BTST
        # For BTST, we don't modify the destination, just test the bit

class Bset(BaseInstruction):
    """BSET instruction for prefixed operand system - set bit"""
    def __init__(self):
        opcode_val = 0x6E  # BSET
        super().__init__("BSET", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        dest_value = cpu.get_operand_value(operands[0])
        bit_pos = cpu.get_operand_value(operands[1]) & 0x0F  # 0-15 bits
        bit_mask = 1 << bit_pos
        result = dest_value | bit_mask
        cpu.set_operand_value(operands[0], result)
        cpu._set_flags_16bit(result, result)

class Bclr(BaseInstruction):
    """BCLR instruction for prefixed operand system - clear bit"""
    def __init__(self):
        opcode_val = 0x6F  # BCLR
        super().__init__("BCLR", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        dest_value = cpu.get_operand_value(operands[0])
        bit_pos = cpu.get_operand_value(operands[1]) & 0x0F  # 0-15 bits
        bit_mask = ~(1 << bit_pos) & 0xFFFF
        result = dest_value & bit_mask
        cpu.set_operand_value(operands[0], result)
        cpu._set_flags_16bit(result, result)

class Bflip(BaseInstruction):
    """BFLIP instruction for prefixed operand system - flip bit"""
    def __init__(self):
        opcode_val = 0x70  # BFLIP
        super().__init__("BFLIP", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        dest_value = cpu.get_operand_value(operands[0])
        bit_pos = cpu.get_operand_value(operands[1]) & 0x0F  # 0-15 bits
        bit_mask = 1 << bit_pos
        result = dest_value ^ bit_mask
        cpu.set_operand_value(operands[0], result)
        cpu._set_flags_16bit(result, result)

# String operations
class Strcpy(BaseInstruction):
    """STRCPY instruction - copy string from source to destination"""
    def __init__(self):
        opcode_val = 0x71  # STRCPY
        super().__init__("STRCPY", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        src_addr = cpu.get_operand_value(operands[1])
        dest_addr = cpu.get_operand_value(operands[0])
        # Copy null-terminated string
        while True:
            char = cpu.memory.read_byte(src_addr)
            cpu.memory.write_byte(dest_addr, char)
            if char == 0:
                break
            src_addr = (src_addr + 1) & 0xFFFF
            dest_addr = (dest_addr + 1) & 0xFFFF

class Strcat(BaseInstruction):
    """STRCAT instruction - concatenate string from source to end of destination"""
    def __init__(self):
        opcode_val = 0x72  # STRCAT
        super().__init__("STRCAT", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        src_addr = cpu.get_operand_value(operands[1])
        dest_addr = cpu.get_operand_value(operands[0])
        # Find end of destination string
        while cpu.memory.read_byte(dest_addr) != 0:
            dest_addr = (dest_addr + 1) & 0xFFFF
        # Copy source string to end
        while True:
            char = cpu.memory.read_byte(src_addr)
            cpu.memory.write_byte(dest_addr, char)
            if char == 0:
                break
            src_addr = (src_addr + 1) & 0xFFFF
            dest_addr = (dest_addr + 1) & 0xFFFF

class Strcmp(BaseInstruction):
    """STRCMP instruction - compare two strings for length"""
    def __init__(self):
        opcode_val = 0x73  # STRCMP
        super().__init__("STRCMP", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(3)
        str1_addr = cpu.get_operand_value(operands[0])
        str2_addr = cpu.get_operand_value(operands[1])
        length = cpu.get_operand_value(operands[2])
        # Compare strings byte by byte up to length
        result = 0
        for i in range(length):
            char1 = cpu.memory.read_byte((str1_addr + i) & 0xFFFF)
            char2 = cpu.memory.read_byte((str2_addr + i) & 0xFFFF)
            if char1 != char2:
                result = -1 if char1 < char2 else 1
                break
        # Set flags based on result
        cpu._set_flags_16bit(result, result)

class Strlen(BaseInstruction):
    """STRLEN instruction - get length of null-terminated string"""
    def __init__(self):
        opcode_val = 0x74  # STRLEN
        super().__init__("STRLEN", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        src_addr = cpu.get_operand_value(operands[0])
        # Count characters until null terminator
        length = 0
        while cpu.memory.read_byte((src_addr + length) & 0xFFFF) != 0:
            length = (length + 1) & 0xFFFF
        # Store result in R0
        cpu.Rregisters[0] = length & 0xFF
        cpu._set_flags_16bit(length, length)

class Strext(BaseInstruction):
    """STREXT instruction - extract substring from haystack"""
    def __init__(self):
        opcode_val = 0x75  # STREXT
        super().__init__("STREXT", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(4)
        dest_addr = cpu.get_operand_value(operands[0])
        haystack_addr = cpu.get_operand_value(operands[1])
        needle_addr = cpu.get_operand_value(operands[2])
        max_len = cpu.get_operand_value(operands[3])
        # Find needle in haystack
        found = False
        haystack_pos = 0
        while cpu.memory.read_byte((haystack_addr + haystack_pos) & 0xFFFF) != 0:
            needle_pos = 0
            match = True
            while needle_pos < max_len and cpu.memory.read_byte((needle_addr + needle_pos) & 0xFFFF) != 0:
                if cpu.memory.read_byte((haystack_addr + haystack_pos + needle_pos) & 0xFFFF) != cpu.memory.read_byte((needle_addr + needle_pos) & 0xFFFF):
                    match = False
                    break
                needle_pos += 1
            if match:
                # Copy found substring to destination
                for i in range(needle_pos):
                    char = cpu.memory.read_byte((haystack_addr + haystack_pos + i) & 0xFFFF)
                    cpu.memory.write_byte((dest_addr + i) & 0xFFFF, char)
                cpu.memory.write_byte((dest_addr + needle_pos) & 0xFFFF, 0)  # Null terminate
                found = True
                break
            haystack_pos += 1
        if not found:
            cpu.memory.write_byte(dest_addr, 0)  # Empty string
        cpu.zero_flag = 1 if found else 0

class Strexti(BaseInstruction):
    """STREXTI instruction - extract substring case-insensitive"""
    def __init__(self):
        opcode_val = 0x76  # STREXTI
        super().__init__("STREXTI", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(4)
        dest_addr = cpu.get_operand_value(operands[0])
        haystack_addr = cpu.get_operand_value(operands[1])
        needle_addr = cpu.get_operand_value(operands[2])
        max_len = cpu.get_operand_value(operands[3])
        # Find needle in haystack (case-insensitive)
        found = False
        haystack_pos = 0
        while cpu.memory.read_byte((haystack_addr + haystack_pos) & 0xFFFF) != 0:
            needle_pos = 0
            match = True
            while needle_pos < max_len and cpu.memory.read_byte((needle_addr + needle_pos) & 0xFFFF) != 0:
                h_char = cpu.memory.read_byte((haystack_addr + haystack_pos + needle_pos) & 0xFFFF)
                n_char = cpu.memory.read_byte((needle_addr + needle_pos) & 0xFFFF)
                if chr(h_char).upper() != chr(n_char).upper():
                    match = False
                    break
                needle_pos += 1
            if match:
                # Copy found substring to destination
                for i in range(needle_pos):
                    char = cpu.memory.read_byte((haystack_addr + haystack_pos + i) & 0xFFFF)
                    cpu.memory.write_byte((dest_addr + i) & 0xFFFF, char)
                cpu.memory.write_byte((dest_addr + needle_pos) & 0xFFFF, 0)  # Null terminate
                found = True
                break
            haystack_pos += 1
        if not found:
            cpu.memory.write_byte(dest_addr, 0)  # Empty string
        cpu.zero_flag = 1 if found else 0

class Strupr(BaseInstruction):
    """STRUPR instruction - convert string to uppercase"""
    def __init__(self):
        opcode_val = 0x77  # STRUPR
        super().__init__("STRUPR", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        src_addr = cpu.get_operand_value(operands[0])
        # Convert string to uppercase in-place
        addr = src_addr
        while True:
            char = cpu.memory.read_byte(addr)
            if char == 0:
                break
            if 97 <= char <= 122:  # a-z
                char = char - 32  # Convert to uppercase
            cpu.memory.write_byte(addr, char)
            addr = (addr + 1) & 0xFFFF

class Strlwr(BaseInstruction):
    """STRLWR instruction - convert string to lowercase"""
    def __init__(self):
        opcode_val = 0x78  # STRLWR
        super().__init__("STRLWR", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        src_addr = cpu.get_operand_value(operands[0])
        # Convert string to lowercase in-place
        addr = src_addr
        while True:
            char = cpu.memory.read_byte(addr)
            if char == 0:
                break
            if 65 <= char <= 90:  # A-Z
                char = char + 32  # Convert to lowercase
            cpu.memory.write_byte(addr, char)
            addr = (addr + 1) & 0xFFFF

class Strrev(BaseInstruction):
    """STRREV instruction - reverse a string"""
    def __init__(self):
        opcode_val = 0x79  # STRREV
        super().__init__("STRREV", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        src_addr = cpu.get_operand_value(operands[0])
        # Find string length
        length = 0
        while cpu.memory.read_byte((src_addr + length) & 0xFFFF) != 0:
            length += 1
        # Reverse the string in-place
        for i in range(length // 2):
            left = src_addr + i
            right = src_addr + length - 1 - i
            left_char = cpu.memory.read_byte(left & 0xFFFF)
            right_char = cpu.memory.read_byte(right & 0xFFFF)
            cpu.memory.write_byte(left & 0xFFFF, right_char)
            cpu.memory.write_byte(right & 0xFFFF, left_char)

class Strfind(BaseInstruction):
    """STRFIND instruction - find substring in string"""
    def __init__(self):
        opcode_val = 0x7A  # STRFIND
        super().__init__("STRFIND", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        haystack_addr = cpu.get_operand_value(operands[0])
        needle_addr = cpu.get_operand_value(operands[1])
        # Find needle in haystack
        result = 0  # Position, 1-indexed (0 if not found)
        position = 1
        haystack_pos = 0
        while cpu.memory.read_byte((haystack_addr + haystack_pos) & 0xFFFF) != 0:
            needle_pos = 0
            match = True
            while cpu.memory.read_byte((needle_addr + needle_pos) & 0xFFFF) != 0:
                if cpu.memory.read_byte((haystack_addr + haystack_pos + needle_pos) & 0xFFFF) != cpu.memory.read_byte((needle_addr + needle_pos) & 0xFFFF):
                    match = False
                    break
                needle_pos += 1
            if match:
                result = position
                break
            haystack_pos += 1
            position += 1
        # Store result in R0
        cpu.Rregisters[0] = result & 0xFF
        cpu._set_flags_16bit(result, result)

class Strfindi(BaseInstruction):
    """STRFINDI instruction - find substring case-insensitive"""
    def __init__(self):
        opcode_val = 0x7B  # STRFINDI
        super().__init__("STRFINDI", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        haystack_addr = cpu.get_operand_value(operands[0])
        needle_addr = cpu.get_operand_value(operands[1])
        # Find needle in haystack (case-insensitive)
        result = 0  # Position, 1-indexed (0 if not found)
        position = 1
        haystack_pos = 0
        while cpu.memory.read_byte((haystack_addr + haystack_pos) & 0xFFFF) != 0:
            needle_pos = 0
            match = True
            while cpu.memory.read_byte((needle_addr + needle_pos) & 0xFFFF) != 0:
                h_char = cpu.memory.read_byte((haystack_addr + haystack_pos + needle_pos) & 0xFFFF)
                n_char = cpu.memory.read_byte((needle_addr + needle_pos) & 0xFFFF)
                if chr(h_char).upper() != chr(n_char).upper():
                    match = False
                    break
                needle_pos += 1
            if match:
                result = position
                break
            haystack_pos += 1
            position += 1
        # Store result in R0
        cpu.Rregisters[0] = result & 0xFF
        cpu._set_flags_16bit(result, result)

# Enhanced data movement
class Swap(BaseInstruction):
    """SWAP instruction for prefixed operand system - Swap nibbles"""
    def __init__(self):
        opcode_val = 0x94  # SWAP
        super().__init__("SWAP", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        value = cpu.get_operand_value(operands[0])
        # Swap high and low nibbles (4 bits each)
        # For 16-bit: ABCD EFGH -> EFGH ABCD
        high_nibble = (value >> 8) & 0xFF
        low_nibble = value & 0xFF
        result = (low_nibble << 8) | high_nibble
        cpu.set_operand_value(operands[0], result)
        cpu._set_flags_16bit(result, result)

class Xchng(BaseInstruction):
    """XCHNG instruction for prefixed operand system - Exchange operands"""
    def __init__(self):
        opcode_val = 0x95  # XCHNG
        super().__init__("XCHNG", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        value1 = cpu.get_operand_value(operands[0])
        value2 = cpu.get_operand_value(operands[1])
        cpu.set_operand_value(operands[0], value2)
        cpu.set_operand_value(operands[1], value1)
        # Set flags based on the first operand after exchange
        cpu._set_flags_16bit(value2, value2)

class Movz(BaseInstruction):
    """MOVZ instruction for prefixed operand system - Move if zero"""
    def __init__(self):
        opcode_val = 0x96  # MOVZ
        super().__init__("MOVZ", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        if cpu.zero_flag:
            source_value = cpu.get_operand_value(operands[1], operands[0])
            cpu.set_operand_value(operands[0], source_value, operands[1])
            cpu._set_flags_16bit(source_value, source_value)
        # If not zero, do nothing and don't change flags

class Movnz(BaseInstruction):
    """MOVNZ instruction for prefixed operand system - Move if not zero"""
    def __init__(self):
        opcode_val = 0x97  # MOVNZ
        super().__init__("MOVNZ", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        if not cpu.zero_flag:
            source_value = cpu.get_operand_value(operands[1], operands[0])
            cpu.set_operand_value(operands[0], source_value, operands[1])
            cpu._set_flags_16bit(source_value, source_value)
        # If zero, do nothing and don't change flags

class Lea(BaseInstruction):
    """LEA instruction for prefixed operand system - Load effective address"""
    def __init__(self):
        opcode_val = 0x98  # LEA
        super().__init__("LEA", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        # Calculate effective address from the source operand
        # This is typically used with memory operands that have displacement/offset
        # For now, treat it like a MOV that loads the address instead of the value
        if operands[1]['type'] == 'memory':
            # If source is memory, load the address
            address = cpu.calculate_memory_address(operands[1])
            cpu.set_operand_value(operands[0], address)
            cpu._set_flags_16bit(address, address)
        else:
            # If source is not memory, treat like MOV
            source_value = cpu.get_operand_value(operands[1], operands[0])
            cpu.set_operand_value(operands[0], source_value, operands[1])
            cpu._set_flags_16bit(source_value, source_value)

# Stack operations
class Push(BaseInstruction):
    """PUSH instruction for prefixed operand system"""
    def __init__(self):
        opcode_val = 0x18  # PUSH
        super().__init__("PUSH", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        value = cpu.get_operand_value(operands[0])
        
        # Push to stack (stack grows downward)
        # Size depends on register type: P registers are 16-bit, R registers are 8-bit
        sp = int(cpu.Pregisters[8])
        if operands[0]['type'] == 'register' and operands[0]['reg_type'] == 'P':
            # Push 16-bit value for P registers
            sp = (sp - 2) & 0xFFFF
            cpu.memory.write_word(sp, value)
        else:
            # Push 8-bit value for R registers and other types
            sp = (sp - 1) & 0xFFFF
            cpu.memory.write_byte(sp, value & 0xFF)
        cpu.Pregisters[8] = sp

class Pop(BaseInstruction):
    """POP instruction for prefixed operand system"""
    def __init__(self):
        opcode_val = 0x19  # POP
        super().__init__("POP", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        
        # Check stack bounds
        sp = int(cpu.Pregisters[8])
        if operands[0]['type'] == 'register' and operands[0]['reg_type'] == 'P':
            # Pop 16-bit value for P registers
            if sp >= 0xFFFE:
                raise RuntimeError(f"Stack underflow: SP=0x{sp:04X}, need 2 bytes for P register")
            value = cpu.memory.read_word(sp)
            sp = (sp + 2) & 0xFFFF
        else:
            # Pop 8-bit value for R registers and other types
            if sp >= 0xFFFF:
                raise RuntimeError(f"Stack underflow: SP=0x{sp:04X}")
            value = cpu.memory.read_byte(sp)
            sp = (sp + 1) & 0xFFFF
        cpu.Pregisters[8] = sp
        
        cpu.set_operand_value(operands[0], value)

class Pushf(BaseInstruction):
    """PUSHF instruction - push flags"""
    def __init__(self):
        opcode_val = 0x1A  # PUSHF
        super().__init__("PUSHF", opcode_val)
    
    def execute(self, cpu):
        # Convert flags array to 16-bit value
        flags_value = 0
        for i in range(12):
            if cpu.flags[i]:
                flags_value |= (1 << i)
        
        # Push flags to stack
        sp = int(cpu.Pregisters[8])
        sp = (sp - 2) & 0xFFFF
        cpu.Pregisters[8] = sp
        cpu.memory.write_word(sp, flags_value)

class Popf(BaseInstruction):
    """POPF instruction - pop flags"""
    def __init__(self):
        opcode_val = 0x1B  # POPF
        super().__init__("POPF", opcode_val)
    
    def execute(self, cpu):
        # Check stack bounds
        sp = int(cpu.Pregisters[8])
        if sp >= 0xFFFF:
            raise RuntimeError(f"Stack underflow: SP=0x{sp:04X}")
        
        # Pop flags from stack
        flags_value = cpu.memory.read_word(sp)
        sp = (sp + 2) & 0xFFFF
        cpu.Pregisters[8] = sp
        
        # Convert flags value back to array
        for i in range(12):
            bit_set = (flags_value & (1 << i)) != 0
            cpu.flags[i] = 1 if bit_set else 0

class Pusha(BaseInstruction):
    """PUSHA instruction - push all registers"""
    def __init__(self):
        opcode_val = 0x1C  # PUSHA
        super().__init__("PUSHA", opcode_val)
    
    def execute(self, cpu):
        # Push all registers (R0-R9, P0-P9, VX, VY, VC) to stack
        registers = []
        registers.extend(cpu.Rregisters)  # R0-R9
        registers.extend(cpu.Pregisters)  # P0-P9
        registers.append(cpu.gfx.Vregisters[0])  # VX
        registers.append(cpu.gfx.Vregisters[1])  # VY
        registers.append(cpu.gfx.Vregisters[3])  # VC
        
        for reg_value in reversed(registers):  # Push in reverse order so POPA can pop in forward order
            sp = int(cpu.Pregisters[8])
            sp = (sp - 2) & 0xFFFF
            cpu.Pregisters[8] = sp
            cpu.memory.write_word(sp, reg_value)

class Popa(BaseInstruction):
    """POPA instruction - pop all registers"""
    def __init__(self):
        opcode_val = 0x1D  # POPA
        super().__init__("POPA", opcode_val)
    
    def execute(self, cpu):
        # Pop all registers from stack (R0-R9, P0-P9, VX, VY, VC)
        registers_order = list(range(23))  # 0-22 (R0-R9, P0-P9, VX, VY, VC)
        
        for reg_num in registers_order:
            sp = int(cpu.Pregisters[8])
            if sp >= 0xFFFF:
                raise RuntimeError(f"Stack underflow during POPA: SP=0x{sp:04X}")
            
            value = cpu.memory.read_word(sp)
            sp = (sp + 2) & 0xFFFF
            cpu.Pregisters[8] = sp
            
            cpu.set_register_value(reg_num, value)

class Enter(BaseInstruction):
    """ENTER instruction - enter subroutine (stack frame)"""
    def __init__(self):
        opcode_val = 0x9B  # ENTER
        super().__init__("ENTER", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        frame_size = cpu.get_operand_value(operands[0])
        
        # Push old frame pointer (FP/P9)
        sp = int(cpu.Pregisters[8])
        sp = (sp - 2) & 0xFFFF
        cpu.memory.write_word(sp, cpu.Pregisters[9])
        cpu.Pregisters[8] = sp
        
        # Set new frame pointer to current stack pointer
        cpu.Pregisters[9] = sp
        
        # Allocate space for local variables
        sp = (sp - frame_size) & 0xFFFF
        cpu.Pregisters[8] = sp

class Leave(BaseInstruction):
    """LEAVE instruction - leave subroutine (stack frame)"""
    def __init__(self):
        opcode_val = 0x9C  # LEAVE
        super().__init__("LEAVE", opcode_val)
    
    def execute(self, cpu):
        # Restore frame pointer from memory
        old_fp = cpu.memory.read_word(cpu.Pregisters[9])
        
        # Restore stack pointer to frame pointer (deallocate locals)
        cpu.Pregisters[8] = cpu.Pregisters[9]
        
        # Pop the old FP from stack
        cpu.Pregisters[8] = (cpu.Pregisters[8] + 2) & 0xFFFF
        
        # Restore frame pointer
        cpu.Pregisters[9] = old_fp

# Control flow - jumps
class Jmp(BaseInstruction):
    """JMP instruction for prefixed operand system"""
    def __init__(self):
        opcode_val = 0x1E  # JMP
        super().__init__("JMP", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        target_address = cpu.get_operand_value(operands[0])
        
        # Smart prefetch handling: only invalidate if target is outside current buffer
        if (cpu.prefetch_valid and 
            target_address >= cpu.prefetch_pc and 
            target_address < cpu.prefetch_pc + 16):
            # Target is within current prefetch buffer, no need to invalidate
            pass
        else:
            cpu.invalidate_prefetch()
        
        # Invalidate instruction cache on jump
        cpu.invalidate_instruction_cache()
        
        cpu.pc = target_address

class Jz(BaseInstruction):
    """JZ instruction - jump if zero"""
    def __init__(self):
        opcode_val = 0x1F  # JZ
        super().__init__("JZ", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        if cpu.flags[7]:  # Zero flag
            target_address = cpu.get_operand_value(operands[0])
            
            # Smart prefetch handling: only invalidate if target is outside current buffer
            if (cpu.prefetch_valid and 
                target_address >= cpu.prefetch_pc and 
                target_address < cpu.prefetch_pc + 16):
                # Target is within current prefetch buffer, no need to invalidate
                pass
            else:
                cpu.invalidate_prefetch()
            
            cpu.pc = target_address

class Jnz(BaseInstruction):
    """JNZ instruction - jump if not zero"""
    def __init__(self):
        opcode_val = 0x20  # JNZ
        super().__init__("JNZ", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        if not cpu.flags[7]:  # Not zero flag
            target_address = cpu.get_operand_value(operands[0])
            
            # Smart prefetch handling: only invalidate if target is outside current buffer
            if (cpu.prefetch_valid and 
                target_address >= cpu.prefetch_pc and 
                target_address < cpu.prefetch_pc + 16):
                # Target is within current prefetch buffer, no need to invalidate
                pass
            else:
                cpu.invalidate_prefetch()
            
            # Invalidate instruction cache on conditional jump
            cpu.invalidate_instruction_cache()
            
            cpu.pc = target_address

class Jo(BaseInstruction):
    """JO instruction - jump if overflow"""
    def __init__(self):
        opcode_val = 0x21  # JO
        super().__init__("JO", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        if cpu.flags[2]:  # Overflow flag
            target_address = cpu.get_operand_value(operands[0])
            cpu.pc = target_address
            cpu.invalidate_prefetch()

class Jno(BaseInstruction):
    """JNO instruction - jump if no overflow"""
    def __init__(self):
        opcode_val = 0x22  # JNO
        super().__init__("JNO", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        if not cpu.flags[2]:  # No overflow flag
            target_address = cpu.get_operand_value(operands[0])
            cpu.pc = target_address
            cpu.invalidate_prefetch()

class Jc(BaseInstruction):
    """JC instruction - jump if carry"""
    def __init__(self):
        opcode_val = 0x23  # JC
        super().__init__("JC", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        if cpu.flags[6]:  # Carry flag
            target_address = cpu.get_operand_value(operands[0])
            cpu.pc = target_address
            cpu.invalidate_prefetch()

class Jnc(BaseInstruction):
    """JNC instruction - jump if no carry"""
    def __init__(self):
        opcode_val = 0x24  # JNC
        super().__init__("JNC", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        if not cpu.flags[6]:  # No carry flag
            target_address = cpu.get_operand_value(operands[0])
            cpu.pc = target_address
            cpu.invalidate_prefetch()

class Js(BaseInstruction):
    """JS instruction - jump if sign"""
    def __init__(self):
        opcode_val = 0x25  # JS
        super().__init__("JS", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        if cpu.flags[1]:  # Sign flag
            target_address = cpu.get_operand_value(operands[0])
            cpu.pc = target_address
            cpu.invalidate_prefetch()

class Jns(BaseInstruction):
    """JNS instruction - jump if no sign"""
    def __init__(self):
        opcode_val = 0x26  # JNS
        super().__init__("JNS", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        if not cpu.flags[1]:  # No sign flag
            target_address = cpu.get_operand_value(operands[0])
            cpu.pc = target_address
            cpu.invalidate_prefetch()

class Jgt(BaseInstruction):
    """JGT instruction - jump if greater than"""
    def __init__(self):
        opcode_val = 0x27  # JGT
        super().__init__("JGT", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        # Greater than: not zero and not overflow xor sign
        gt = not cpu.flags[7] and (cpu.flags[2] == cpu.flags[1])
        if gt:
            target_address = cpu.get_operand_value(operands[0])
            cpu.pc = target_address
            cpu.invalidate_prefetch()

class Jlt(BaseInstruction):
    """JLT instruction - jump if less than"""
    def __init__(self):
        opcode_val = 0x28  # JLT
        super().__init__("JLT", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        # Less than: overflow xor sign
        lt = cpu.flags[2] != cpu.flags[1]
        if lt:
            target_address = cpu.get_operand_value(operands[0])
            cpu.pc = target_address
            cpu.invalidate_prefetch()

class Jge(BaseInstruction):
    """JGE instruction - jump if greater or equal"""
    def __init__(self):
        opcode_val = 0x29  # JGE
        super().__init__("JGE", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        # Greater or equal: not (less than)
        lt = cpu.flags[2] != cpu.flags[1]
        if not lt:
            target_address = cpu.get_operand_value(operands[0])
            cpu.pc = target_address
            cpu.invalidate_prefetch()

class Jle(BaseInstruction):
    """JLE instruction - jump if less or equal"""
    def __init__(self):
        opcode_val = 0x2A  # JLE
        super().__init__("JLE", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        # Less or equal: zero or less than
        lt = cpu.flags[2] != cpu.flags[1]
        if cpu.flags[7] or lt:
            target_address = cpu.get_operand_value(operands[0])
            cpu.pc = target_address
            cpu.invalidate_prefetch()

# Control flow - branches (relative)
class Br(BaseInstruction):
    """BR instruction - branch (relative jump)"""
    def __init__(self):
        opcode_val = 0x2B  # BR
        super().__init__("BR", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        offset = cpu.get_operand_value(operands[0])
        # Sign extend 16-bit offset
        if offset & 0x8000:
            offset -= 0x10000
        cpu.pc = (cpu.pc + offset) & 0xFFFF
        cpu.invalidate_prefetch()

class Brz(BaseInstruction):
    """BRZ instruction - branch if zero"""
    def __init__(self):
        opcode_val = 0x2C  # BRZ
        super().__init__("BRZ", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        if cpu.flags[0]:  # Zero flag
            offset = cpu.get_operand_value(operands[0])
            # Sign extend 16-bit offset
            if offset & 0x8000:
                offset -= 0x10000
            cpu.pc = (cpu.pc + offset) & 0xFFFF
            cpu.invalidate_prefetch()

class Brnz(BaseInstruction):
    """BRNZ instruction - branch if not zero"""
    def __init__(self):
        opcode_val = 0x2D  # BRNZ
        super().__init__("BRNZ", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        if not cpu.flags[0]:  # Not zero flag
            offset = cpu.get_operand_value(operands[0])
            # Sign extend 16-bit offset
            if offset & 0x8000:
                offset -= 0x10000
            cpu.pc = (cpu.pc + offset) & 0xFFFF
            cpu.invalidate_prefetch()

# Comparison
class Cmp(BaseInstruction):
    """CMP instruction for prefixed operand system"""
    def __init__(self):
        opcode_val = 0x2E  # CMP
        super().__init__("CMP", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        op1 = cpu.get_operand_value(operands[0])
        op2 = cpu.get_operand_value(operands[1], operands[0])
        result = op1 - op2
        
        # Set flags based on operation (like SUB but without storing result)
        if operands[0]['type'] == 'register' and operands[0]['reg_type'] == 'R':
            masked_result = result & 0xFF
            cpu._set_overflow_flag_8bit(op1, op2, result, is_subtraction=True)
            cpu._set_flags_8bit(masked_result, result)
        else:
            masked_result = result & 0xFFFF
            cpu._set_overflow_flag_16bit(op1, op2, result, is_subtraction=True)
            cpu._set_flags_16bit(masked_result, result)
        
        # Mark that last operation was CMP for correct carry flag handling
        cpu._last_operation_was_cmp = True

# Call
class Call(BaseInstruction):
    """CALL instruction for prefixed operand system"""
    def __init__(self):
        opcode_val = 0x2F  # CALL
        super().__init__("CALL", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        target_address = cpu.get_operand_value(operands[0])
        
        # Push return address to stack
        sp = int(cpu.Pregisters[8])
        sp = (sp - 2) & 0xFFFF
        cpu.Pregisters[8] = sp
        cpu.memory.write_word(sp, cpu.pc)
        
        # Jump to target
        cpu.pc = target_address
        cpu.invalidate_prefetch()
        cpu.invalidate_instruction_cache()

# Interrupt
class Int(BaseInstruction):
    """INT instruction - software interrupt"""
    def __init__(self):
        opcode_val = 0x30  # INT
        super().__init__("INT", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        interrupt_number = cpu.get_operand_value(operands[0])
        
        # Check if interrupts are enabled
        if not cpu.interrupt_flag:
            # Interrupts disabled - INT should not execute but operands are still consumed
            return
        
        # Push PC and flags to stack
        flags_value = 0
        for i in range(12):
            if cpu.flags[i]:
                flags_value |= (1 << i)
        
        sp = int(cpu.Pregisters[8])
        sp = (sp - 2) & 0xFFFF
        cpu.Pregisters[8] = sp
        cpu.memory.write_word(sp, cpu.pc)
        
        sp = (sp - 2) & 0xFFFF
        cpu.Pregisters[8] = sp
        cpu.memory.write_word(sp, flags_value)
        
        # Clear interrupt flag
        cpu.flags[5] = 0
        
        # Jump to interrupt vector
        vector_addr = 0x0100 + (interrupt_number * 4)
        cpu.pc = cpu.memory.read_word(vector_addr)
        cpu.invalidate_prefetch()

# Advanced control flow and loops
class Callz(BaseInstruction):
    """CALLZ instruction - call if zero"""
    def __init__(self):
        opcode_val = 0x9D  # CALLZ
        super().__init__("CALLZ", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        target_address = cpu.get_operand_value(operands[0])

        if cpu.flags[7]:  # Zero flag
            sp = int(cpu.Pregisters[8])
            sp = (sp - 2) & 0xFFFF
            cpu.Pregisters[8] = sp
            cpu.memory.write_word(sp, cpu.pc)
            cpu.pc = target_address
            cpu.invalidate_prefetch()
            cpu.invalidate_instruction_cache()

class Callnz(BaseInstruction):
    """CALLNZ instruction - call if not zero"""
    def __init__(self):
        opcode_val = 0x9E  # CALLNZ
        super().__init__("CALLNZ", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        target_address = cpu.get_operand_value(operands[0])

        if not cpu.flags[7]:  # Not zero flag
            sp = int(cpu.Pregisters[8])
            sp = (sp - 2) & 0xFFFF
            cpu.Pregisters[8] = sp
            cpu.memory.write_word(sp, cpu.pc)
            cpu.pc = target_address
            cpu.invalidate_prefetch()
            cpu.invalidate_instruction_cache()

class Retn(BaseInstruction):
    """RETN instruction - return with value"""
    def __init__(self):
        opcode_val = 0x9F  # RETN
        super().__init__("RETN", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)  # Return value source
        return_value = cpu.get_operand_value(operands[0])

        # Expose return value in standard registers (R0/P0)
        cpu.Rregisters[0] = return_value & 0xFF
        cpu.Pregisters[0] = return_value & 0xFFFF
        cpu._set_flags_16bit(return_value & 0xFFFF, return_value)

        # Pop return address into PC (like RET)
        sp = int(cpu.Pregisters[8])
        if sp >= 0xFFFF:
            raise RuntimeError(f"Stack underflow: SP=0x{sp:04X}")
        cpu.pc = cpu.memory.read_word(sp)
        sp = (sp + 2) & 0xFFFF
        cpu.Pregisters[8] = sp

        cpu.invalidate_prefetch()
        cpu.invalidate_instruction_cache()

class Loopz(BaseInstruction):
    """LOOPZ instruction - loop while zero"""
    def __init__(self):
        opcode_val = 0xA0  # LOOPZ
        super().__init__("LOOPZ", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        counter = cpu.get_operand_value(operands[0])
        zero_flag_set = bool(cpu.flags[7])
        new_counter = (counter - 1) & 0xFFFF
        cpu.set_operand_value(operands[0], new_counter)

        if new_counter != 0 and zero_flag_set:
            target_address = cpu.get_operand_value(operands[1])
            cpu.pc = target_address
            cpu.invalidate_prefetch()

class While(BaseInstruction):
    """WHILE instruction - while loop start"""
    def __init__(self):
        opcode_val = 0xA1  # WHILE
        super().__init__("WHILE", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        condition = cpu.get_operand_value(operands[0])
        cpu._set_flags_16bit(condition, condition)

# Graphics operations
class Sblend(BaseInstruction):
    """SBLEND instruction - set blend mode"""
    def __init__(self):
        opcode_val = 0x31  # SBLEND
        super().__init__("SBLEND", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        blend_mode = cpu.get_operand_value(operands[0])
        cpu.gfx.set_blend_mode(blend_mode)

class Sread(BaseInstruction):
    """SREAD instruction - read screen pixel"""
    def __init__(self):
        opcode_val = 0x32  # SREAD
        super().__init__("SREAD", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        # Read pixel at VX,VY coordinates
        x = cpu.gfx.Vregisters[0]
        y = cpu.gfx.Vregisters[1]
        color = cpu.gfx.get_screen_val()
        cpu.set_operand_value(operands[0], color)

class Swrite(BaseInstruction):
    """SWRITE instruction - write screen pixel"""
    def __init__(self):
        opcode_val = 0x33  # SWRITE
        super().__init__("SWRITE", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        color = cpu.get_operand_value(operands[0])
        # Write pixel at VX,VY coordinates
        x = cpu.gfx.Vregisters[0]
        y = cpu.gfx.Vregisters[1]
        cpu.gfx.set_screen_val(color)

class Srol(BaseInstruction):
    """SROL instruction - roll screen by axis and amount"""
    def __init__(self):
        opcode_val = 0x34  # SROL
        super().__init__("SROL", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        axis = cpu.get_operand_value(operands[0])
        amount = cpu.get_operand_value(operands[1])
        
        if axis == 0:  # horizontal roll
            cpu.gfx.roll_x(-amount)
        elif axis == 1:  # vertical roll
            cpu.gfx.roll_y(-amount)
        else:
            raise ValueError(f"Invalid axis for SROL: {axis}")

class Srot(BaseInstruction):
    """SROT instruction - rotate screen by direction and amount"""
    def __init__(self):
        opcode_val = 0x35  # SROT
        super().__init__("SROT", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        direction = cpu.get_operand_value(operands[0])
        amount = cpu.get_operand_value(operands[1])
        
        if direction == 0:  # Left
            cpu.gfx.rotate_left(amount)
        elif direction == 1:  # Right
            cpu.gfx.rotate_right(amount)
        else:
            raise ValueError(f"Invalid direction for SROT: {direction}")

class Sshft(BaseInstruction):
    """SSHFT instruction - shift screen by axis and amount"""
    def __init__(self):
        opcode_val = 0x36  # SSHFT
        super().__init__("SSHFT", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        axis = cpu.get_operand_value(operands[0])
        amount = cpu.get_operand_value(operands[1])
        
        if axis == 0:  # X axis
            cpu.gfx.shift_x(amount)
        elif axis == 1:  # Y axis
            cpu.gfx.shift_y(amount)
        else:
            raise ValueError(f"Invalid axis for SSHFT: {axis}")

class Sflip(BaseInstruction):
    """SFLIP instruction - flip screen by axis"""
    def __init__(self):
        opcode_val = 0x37  # SFLIP
        super().__init__("SFLIP", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        axis = cpu.get_operand_value(operands[0])
        
        if axis == 0:  # X axis
            cpu.gfx.flip_x()
        elif axis == 1:  # Y axis
            cpu.gfx.flip_y()
        else:
            raise ValueError(f"Invalid axis for SFLIP: {axis}")

class Sblit(BaseInstruction):
    """SBLIT instruction - blit screen"""
    def __init__(self):
        opcode_val = 0x3C  # SBLIT
        super().__init__("SBLIT", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        source_addr = cpu.get_operand_value(operands[0])
        cpu.gfx.blit(source_addr)

class Sfill(BaseInstruction):
    """SFILL instruction - fill screen"""
    def __init__(self):
        opcode_val = 0x3D  # SFILL
        super().__init__("SFILL", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        color = cpu.get_operand_value(operands[0])
        cpu.gfx.fill_layer(color)

class Sline(BaseInstruction):
    """SLINE instruction - draw line from (VX,VY) to end x, end y (uses VC)"""
    def __init__(self):
        opcode_val = 0x38  # SLINE
        super().__init__("SLINE", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        x2 = cpu.get_operand_value(operands[0])
        y2 = cpu.get_operand_value(operands[1])
        x1 = cpu.gfx.Vregisters[0]  # VX register
        y1 = cpu.gfx.Vregisters[1]  # VY register
        color = cpu.gfx.Vregisters[3]  # VC register
        cpu.gfx.draw_line(x1, y1, x2, y2, color)

class Srect(BaseInstruction):
    """SRECT instruction - draw rectangle from (VX,VY) to end x, end y, filled (uses VC)"""
    def __init__(self):
        opcode_val = 0x39  # SRECT
        super().__init__("SRECT", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(3)
        x2 = cpu.get_operand_value(operands[0])
        y2 = cpu.get_operand_value(operands[1])
        filled = cpu.get_operand_value(operands[2]) != 0
        x1 = cpu.gfx.Vregisters[0]  # VX register
        y1 = cpu.gfx.Vregisters[1]  # VY register
        color = cpu.gfx.Vregisters[3]  # VC register
        cpu.gfx.draw_rectangle(x1, y1, x2, y2, color, filled)

class Scirc(BaseInstruction):
    """SCIRC instruction - draw circle at (VX,VY) with radius, filled (uses VC)"""
    def __init__(self):
        opcode_val = 0x3A  # SCIRC
        super().__init__("SCIRC", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        radius = cpu.get_operand_value(operands[0])
        filled = cpu.get_operand_value(operands[1]) != 0
        x = cpu.gfx.Vregisters[0]  # VX register
        y = cpu.gfx.Vregisters[1]  # VY register
        color = cpu.gfx.Vregisters[3]  # VC register
        cpu.gfx.draw_circle(x, y, radius, color, filled)

class Sinv(BaseInstruction):
    """SINV instruction - invert screen colors"""
    def __init__(self):
        opcode_val = 0x3B  # SINV
        super().__init__("SINV", opcode_val)
    
    def execute(self, cpu):
        cpu.gfx.invert_colors()

# VRAM operations
class Vread(BaseInstruction):
    """VREAD instruction - read VRAM"""
    def __init__(self):
        opcode_val = 0x3E  # VREAD
        super().__init__("VREAD", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        addr = cpu.get_operand_value(operands[0])
        # Convert linear address to x,y coordinates
        if 0 <= addr < 65536:  # 256*256 = 65536
            x = addr % 256
            y = addr // 256
            if 0 <= x < 256 and 0 <= y < 256:
                value = cpu.gfx.vram[y, x]
                cpu.set_operand_value(operands[0], value)
            else:
                raise IndexError(f"VRAM coordinates out of range: x={x}, y={y}")
        else:
            raise IndexError(f"VRAM address out of range: {addr}")

class Vwrite(BaseInstruction):
    """VWRITE instruction - write VRAM"""
    def __init__(self):
        opcode_val = 0x3F  # VWRITE
        super().__init__("VWRITE", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        addr = cpu.get_operand_value(operands[0])
        value = cpu.get_operand_value(operands[1])
        # Convert linear address to x,y coordinates
        if 0 <= addr < 65536:  # 256*256 = 65536
            x = addr % 256
            y = addr // 256
            if 0 <= x < 256 and 0 <= y < 256:
                cpu.gfx.vram[y, x] = value
            else:
                raise IndexError(f"VRAM coordinates out of range: x={x}, y={y}")
        else:
            raise IndexError(f"VRAM address out of range: {addr}")

class Vblit(BaseInstruction):
    """VBLIT instruction - blit VRAM"""
    def __init__(self):
        opcode_val = 0x40  # VBLIT
        super().__init__("VBLIT", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        source_addr = cpu.get_operand_value(operands[0])
        cpu.gfx.blit_vram(source_addr)

# Text operations
class Char(BaseInstruction):
    """CHAR instruction - draw character"""
    def __init__(self):
        opcode_val = 0x41  # CHAR
        super().__init__("CHAR", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)  # Parse 1 operand (char code)
        char_code = cpu.get_operand_value(operands[0])
        color = cpu.gfx.Vregisters[3]  # VC register
        x = cpu.gfx.Vregisters[0]
        x = int(x)
        y = cpu.gfx.Vregisters[1]
        cpu.gfx.draw_char(char_code, x, y, color)
        # Advance cursor by 8 pixels
        cpu.gfx.Vregisters[0] = int(x + 8) % 256

class Text(BaseInstruction):
    """TEXT instruction - draw text"""
    def __init__(self):
        opcode_val = 0x42  # TEXT
        super().__init__("TEXT", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)  # Parse 1 operand (text address)
        text_addr = cpu.get_operand_value(operands[0])
        color = cpu.gfx.Vregisters[3]  # VC register
        x = cpu.gfx.Vregisters[0]
        y = cpu.gfx.Vregisters[1]
        final_x, final_y = cpu.gfx.draw_text(x, y, color, text_addr, cpu.memory)
        cpu.gfx.Vregisters[0] = int(final_x) % 256
        cpu.gfx.Vregisters[1] = int(final_y) % 256

# Keyboard operations
class Keyin(BaseInstruction):
    """KEYIN instruction - read key"""
    def __init__(self):
        opcode_val = 0x43  # KEYIN
        super().__init__("KEYIN", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        key = cpu.read_key_from_buffer()
        cpu.set_operand_value(operands[0], key)

class Keystat(BaseInstruction):
    """KEYSTAT instruction - check key status"""
    def __init__(self):
        opcode_val = 0x44  # KEYSTAT
        super().__init__("KEYSTAT", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        status = 1 if (cpu.keyboard[1] & 0x01) else 0  # Check key available flag
        cpu.set_operand_value(operands[0], status)

class Keycount(BaseInstruction):
    """KEYCOUNT instruction - get key count"""
    def __init__(self):
        opcode_val = 0x45  # KEYCOUNT
        super().__init__("KEYCOUNT", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        count = cpu.keyboard[3]  # Buffer count register
        cpu.set_operand_value(operands[0], count)

class Keyclear(BaseInstruction):
    """KEYCLEAR instruction - clear keyboard buffer"""
    def __init__(self):
        opcode_val = 0x46  # KEYCLEAR
        super().__init__("KEYCLEAR", opcode_val)
    
    def execute(self, cpu):
        cpu.key_buffer.clear()  # Clear the key buffer
        cpu.keyboard[0] = 0  # Clear data register
        cpu.keyboard[1] &= ~0x03  # Clear available and full flags
        cpu.keyboard[3] = 0  # Reset buffer count

class Keyctrl(BaseInstruction):
    """KEYCTRL instruction - keyboard control"""
    def __init__(self):
        opcode_val = 0x47  # KEYCTRL
        super().__init__("KEYCTRL", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        control = cpu.get_operand_value(operands[0])
        cpu.keyboard[2] = control  # Set control register
        cpu.interrupts[2] = control  # Enable keyboard interrupt

# Random operations
class Rnd(BaseInstruction):
    """RND instruction - random number"""
    def __init__(self):
        opcode_val = 0x48  # RND
        super().__init__("RND", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        # Simple linear congruential generator
        cpu.rng_seed = (cpu.rng_seed * 1103515245 + 12345) & 0xFFFF
        random_value = cpu.rng_seed
        cpu.set_operand_value(operands[0], random_value)

class Rndr(BaseInstruction):
    """RNDR instruction - random number in range"""
    def __init__(self):
        opcode_val = 0x49  # RNDR
        super().__init__("RNDR", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(3)
        min_value = cpu.get_operand_value(operands[1])
        max_value = cpu.get_operand_value(operands[2])
        if max_value < min_value:
            random_value = min_value
        else:
            # Simple linear congruential generator
            cpu.rng_seed = (cpu.rng_seed * 1103515245 + 12345) & 0xFFFF
            random_value = min_value + (cpu.rng_seed % (max_value - min_value + 1))
        cpu.set_operand_value(operands[0], random_value)

# Memory operations
class Memcpy(BaseInstruction):
    """MEMCPY instruction - memory copy"""
    def __init__(self):
        opcode_val = 0x4A  # MEMCPY
        super().__init__("MEMCPY", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(3)
        dest_addr = cpu.get_operand_value(operands[0])
        source_addr = cpu.get_operand_value(operands[1])
        length = cpu.get_operand_value(operands[2])
        
        for i in range(length):
            data = cpu.memory.read((source_addr + i) & 0xFFFF, 1)[0]
            cpu.write_memory((dest_addr + i) & 0xFFFF, data, 1)

class Memset(BaseInstruction):
    """MEMSET instruction - memory set"""
    def __init__(self):
        opcode_val = 0x7C  # MEMSET
        super().__init__("MEMSET", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(3)
        dest_addr = cpu.get_operand_value(operands[0])
        fill_value = cpu.get_operand_value(operands[1])
        length = cpu.get_operand_value(operands[2])
        
        for i in range(length):
            cpu.write_memory((dest_addr + i) & 0xFFFF, fill_value, 1)

class Memtest(BaseInstruction):
    """MEMTEST instruction - memory test/compare"""
    def __init__(self):
        opcode_val = 0x7D  # MEMTEST
        super().__init__("MEMTEST", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(3)
        addr1 = cpu.get_operand_value(operands[0])
        addr2 = cpu.get_operand_value(operands[1])
        length = cpu.get_operand_value(operands[2])
        
        # Compare memory regions
        match = True
        for i in range(length):
            byte1 = cpu.memory.read((addr1 + i) & 0xFFFF, 1)[0]
            byte2 = cpu.memory.read((addr2 + i) & 0xFFFF, 1)[0]
            if byte1 != byte2:
                match = False
                break
        
        # Set zero flag if regions match (Z=1 means equal)
        cpu.flags[0] = 1 if match else 0  # Zero flag
        # Clear other flags
        cpu.flags[1] = 0  # Sign flag
        cpu.flags[2] = 0  # Overflow flag
        cpu.flags[3] = 0  # Carry flag

class Memmove(BaseInstruction):
    """MEMMOVE instruction - memory move (handles overlapping regions)"""
    def __init__(self):
        opcode_val = 0x7E  # MEMMOVE
        super().__init__("MEMMOVE", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(3)
        dest_addr = cpu.get_operand_value(operands[0])
        source_addr = cpu.get_operand_value(operands[1])
        length = cpu.get_operand_value(operands[2])
        
        # Handle overlapping regions correctly
        if dest_addr < source_addr:
            # Copy forward (no overlap issue)
            for i in range(length):
                data = cpu.memory.read((source_addr + i) & 0xFFFF, 1)[0]
                cpu.write_memory((dest_addr + i) & 0xFFFF, data, 1)
        else:
            # Copy backward to handle overlap
            for i in range(length - 1, -1, -1):
                data = cpu.memory.read((source_addr + i) &  0xFFFF, 1)[0]
                cpu.write_memory((dest_addr + i) & 0xFFFF, data, 1)

class Memcmp(BaseInstruction):
    """MEMCMP instruction - memory compare"""
    def __init__(self):
        opcode_val = 0x99  # MEMCMP
        super().__init__("MEMCMP", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(4)
        dest_operand = operands[0]
        addr1 = cpu.get_operand_value(operands[1])
        addr2 = cpu.get_operand_value(operands[2])
        length = cpu.get_operand_value(operands[3])
        
        # Compare memory regions and return result in destination
        result = 0  # Default: equal
        for i in range(length):
            byte1 = cpu.memory.read_byte((addr1 + i) & 0xFFFF)
            byte2 = cpu.memory.read_byte((addr2 + i) & 0xFFFF)
            if byte1 != byte2:
                result = 1 if byte1 > byte2 else -1  # 1 if addr1 > addr2, -1 if addr1 < addr2
                break
        
        # Store result in destination operand
        cpu.set_operand_value(dest_operand, result & 0xFFFF)
        cpu._set_flags_16bit(result & 0xFFFF, result & 0xFFFF)

class Memswap(BaseInstruction):
    """MEMSWAP instruction - memory swap"""
    def __init__(self):
        opcode_val = 0x9A  # MEMSWAP
        super().__init__("MEMSWAP", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(3)
        addr1 = cpu.get_operand_value(operands[0])
        addr2 = cpu.get_operand_value(operands[1])
        length = cpu.get_operand_value(operands[2])
        
        # Swap memory regions
        for i in range(length):
            byte1 = cpu.memory.read_byte((addr1 + i) & 0xFFFF)
            byte2 = cpu.memory.read_byte((addr2 + i) & 0xFFFF)
            cpu.write_memory((addr1 + i) & 0xFFFF, byte2, 1)
            cpu.write_memory((addr2 + i) & 0xFFFF, byte1, 1)

# Special register access instructions
class Sa(BaseInstruction):
    """SA instruction - access sound address register"""
    def __init__(self):
        opcode_val = 0xDD  # SA
        super().__init__("SA", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        value = cpu.get_operand_value(operands[0])
        cpu.sound.SA = value & 0xFFFF

class Sf(BaseInstruction):
    """SF instruction - access sound frequency register"""
    def __init__(self):
        opcode_val = 0xDE  # SF
        super().__init__("SF", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        value = cpu.get_operand_value(operands[0])
        cpu.sound.SF = value & 0xFFFF

class Sv(BaseInstruction):
    """SV instruction - access sound volume register"""
    def __init__(self):
        opcode_val = 0xDF  # SV
        super().__init__("SV", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        value = cpu.get_operand_value(operands[0])
        cpu.sound.SV = value & 0xFF

class Sw(BaseInstruction):
    """SW instruction - access sound waveform register"""
    def __init__(self):
        opcode_val = 0xE0  # SW
        super().__init__("SW", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        value = cpu.get_operand_value(operands[0])
        cpu.sound.SW = value & 0xFF

class Vm(BaseInstruction):
    """VM instruction - access video mode register"""
    def __init__(self):
        opcode_val = 0xE1  # VM
        super().__init__("VM", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        value = cpu.get_operand_value(operands[0])
        cpu.gfx.VM = value & 0xFF

class Vl(BaseInstruction):
    """VL instruction - access video layer register"""
    def __init__(self):
        opcode_val = 0xE2  # VL
        super().__init__("VL", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        value = cpu.get_operand_value(operands[0])
        cpu.gfx.VL = value & 0xFF

class Tt(BaseInstruction):
    """TT instruction - access timer register"""
    def __init__(self):
        opcode_val = 0xE3  # TT
        super().__init__("TT", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        value = cpu.get_operand_value(operands[0])
        cpu.timer[0] = value & 0xFFFF

class Tm(BaseInstruction):
    """TM instruction - access timer match register"""
    def __init__(self):
        opcode_val = 0xE4  # TM
        super().__init__("TM", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        value = cpu.get_operand_value(operands[0])
        cpu.timer[1] = value & 0xFFFF

class Tc(BaseInstruction):
    """TC instruction - access timer control register"""
    def __init__(self):
        opcode_val = 0xE5  # TC
        super().__init__("TC", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        value = cpu.get_operand_value(operands[0])
        cpu.timer[2] = value & 0xFF

class Ts(BaseInstruction):
    """TS instruction - access timer speed register"""
    def __init__(self):
        opcode_val = 0xE6  # TS
        super().__init__("TS", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        value = cpu.get_operand_value(operands[0])
        cpu.timer[3] = value & 0xFF

class Vx(BaseInstruction):
    """VX instruction - access video X coordinate register"""
    def __init__(self):
        opcode_val = 0xFD  # VX
        super().__init__("VX", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        value = cpu.get_operand_value(operands[0])
        cpu.gfx.Vregisters[0] = value & 0xFF

class Vy(BaseInstruction):
    """VY instruction - access video Y coordinate register"""
    def __init__(self):
        opcode_val = 0xFE  # VY
        super().__init__("VY", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        value = cpu.get_operand_value(operands[0])
        cpu.gfx.Vregisters[1] = value & 0xFF

# String operations
class Strcpy(BaseInstruction):
    """STRCPY instruction - string copy"""
    def __init__(self):
        opcode_val = 0x71  # STRCPY
        super().__init__("STRCPY", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        dest_addr = cpu.get_operand_value(operands[0])
        source_addr = cpu.get_operand_value(operands[1])
        
        i = 0
        while True:
            char = cpu.memory.read((source_addr + i) & 0xFFFF, 1)[0]
            cpu.write_memory((dest_addr + i) & 0xFFFF, char, 1)
            if char == 0:  # Null terminator
                break
            i += 1

class Strcat(BaseInstruction):
    """STRCAT instruction - string concatenate"""
    def __init__(self):
        opcode_val = 0x72  # STRCAT
        super().__init__("STRCAT", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        dest_addr = cpu.get_operand_value(operands[0])
        source_addr = cpu.get_operand_value(operands[1])
        
        # Find end of destination string
        i = 0
        while cpu.memory.read((dest_addr + i) & 0xFFFF, 1)[0] != 0:
            i += 1
        
        # Copy source string to end of destination
        j = 0
        while True:
            char = cpu.memory.read((source_addr + j) & 0xFFFF, 1)[0]
            cpu.write_memory((dest_addr + i + j) & 0xFFFF, char, 1)
            if char == 0:  # Null terminator
                break
            j += 1

class Strcmp(BaseInstruction):
    """STRCMP instruction - string compare"""
    def __init__(self):
        opcode_val = 0x73  # STRCMP
        super().__init__("STRCMP", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(3)
        str1_addr = cpu.get_operand_value(operands[0])
        str2_addr = cpu.get_operand_value(operands[1])
        max_length = cpu.get_operand_value(operands[2])
        
        result = 0
        for i in range(max_length):
            char1 = cpu.memory.read((str1_addr + i) & 0xFFFF, 1)[0]
            char2 = cpu.memory.read((str2_addr + i) & 0xFFFF, 1)[0]
            
            if char1 != char2:
                result = 1 if char1 > char2 else -1
                break
            if char1 == 0:  # End of string
                break
        
        # Store result in a register (typically R0)
        cpu.Rregisters[0] = result & 0xFF

class Strlen(BaseInstruction):
    """STRLEN instruction - string length"""
    def __init__(self):
        opcode_val = 0x74  # STRLEN
        super().__init__("STRLEN", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        str_addr = cpu.get_operand_value(operands[0])
        
        length = 0
        while cpu.memory.read((str_addr + length) & 0xFFFF, 1)[0] != 0:
            length += 1
        
        # Store result in R0
        cpu.Rregisters[0] = length & 0xFF

class Strext(BaseInstruction):
    """STREXT instruction - string extract"""
    def __init__(self):
        opcode_val = 0x75  # STREXT
        super().__init__("STREXT", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(4)
        dest_addr = cpu.get_operand_value(operands[0])
        haystack_addr = cpu.get_operand_value(operands[1])
        needle_addr = cpu.get_operand_value(operands[2])
        max_length = cpu.get_operand_value(operands[3])
        
        # Find needle in haystack
        needle = []
        i = 0
        while i < max_length:
            char = cpu.memory.read((needle_addr + i) & 0xFFFF, 1)[0]
            if char == 0:
                break
            needle.append(char)
            i += 1
        
        needle_len = len(needle)
        if needle_len == 0:
            # Empty needle - copy nothing
            cpu.memory.write(dest_addr & 0xFFFF, 0, 1)
            return
        
        # Search for needle in haystack
        found = False
        start_pos = 0
        for i in range(max_length - needle_len + 1):
            match = True
            for j in range(needle_len):
                h_char = cpu.memory.read((haystack_addr + i + j) & 0xFFFF, 1)[0]
                if h_char != needle[j]:
                    match = False
                    break
            if match:
                found = True
                start_pos = i
                break
        
        if found:
            # Copy from start_pos to end of haystack
            i = 0
            while i < max_length:
                char = cpu.memory.read((haystack_addr + start_pos + i) & 0xFFFF, 1)[0]
                cpu.memory.write((dest_addr + i) & 0xFFFF, char, 1)
                if char == 0:
                    break
                i += 1
        else:
            # Not found - empty result
            cpu.memory.write(dest_addr & 0xFFFF, 0, 1)

class Strexti(BaseInstruction):
    """STREXTI instruction - string extract case-insensitive"""
    def __init__(self):
        opcode_val = 0x76  # STREXTI
        super().__init__("STREXTI", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(4)
        dest_addr = cpu.get_operand_value(operands[0])
        haystack_addr = cpu.get_operand_value(operands[1])
        needle_addr = cpu.get_operand_value(operands[2])
        max_length = cpu.get_operand_value(operands[3])
        
        # Find needle in haystack (case-insensitive)
        needle = []
        i = 0
        while i < max_length:
            char = cpu.memory.read((needle_addr + i) & 0xFFFF, 1)[0]
            if char == 0:
                break
            needle.append(char)
            i += 1
        
        needle_len = len(needle)
        if needle_len == 0:
            # Empty needle - copy nothing
            cpu.memory.write(dest_addr & 0xFFFF, 0, 1)
            return
        
        # Search for needle in haystack (case-insensitive)
        found = False
        start_pos = 0
        for i in range(max_length - needle_len + 1):
            match = True
            for j in range(needle_len):
                h_char = cpu.memory.read((haystack_addr + i + j) & 0xFFFF, 1)[0]
                n_char = needle[j]
                # Simple case-insensitive comparison
                if h_char != n_char and not (
                    (h_char >= 65 and h_char <= 90 and n_char == h_char + 32) or
                    (h_char >= 97 and h_char <= 122 and n_char == h_char - 32)
                ):
                    match = False
                    break
            if match:
                found = True
                start_pos = i
                break
        
        if found:
            # Copy from start_pos to end of haystack
            i = 0
            while i < max_length:
                char = cpu.memory.read((haystack_addr + start_pos + i) & 0xFFFF, 1)[0]
                cpu.memory.write((dest_addr + i) & 0xFFFF, char, 1)
                if char == 0:
                    break
                i += 1
        else:
            # Not found - empty result
            cpu.memory.write(dest_addr & 0xFFFF, 0, 1)

class Strupr(BaseInstruction):
    """STRUPR instruction - string to uppercase"""
    def __init__(self):
        opcode_val = 0x77  # STRUPR
        super().__init__("STRUPR", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        str_addr = cpu.get_operand_value(operands[0])
        
        i = 0
        while True:
            char = cpu.memory.read((str_addr + i) & 0xFFFF, 1)[0]
            if char == 0:
                break
            if char >= 97 and char <= 122:  # lowercase a-z
                char -= 32
                cpu.memory.write((str_addr + i) & 0xFFFF, char, 1)
            i += 1

class Strlwr(BaseInstruction):
    """STRLWR instruction - string to lowercase"""
    def __init__(self):
        opcode_val = 0x78  # STRLWR
        super().__init__("STRLWR", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        str_addr = cpu.get_operand_value(operands[0])
        
        i = 0
        while True:
            char = cpu.memory.read((str_addr + i) & 0xFFFF, 1)[0]
            if char == 0:
                break
            if char >= 65 and char <= 90:  # uppercase A-Z
                char += 32
                cpu.memory.write((str_addr + i) & 0xFFFF, char, 1)
            i += 1

class Strrev(BaseInstruction):
    """STRREV instruction - string reverse"""
    def __init__(self):
        opcode_val = 0x79  # STRREV
        super().__init__("STRREV", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        str_addr = cpu.get_operand_value(operands[0])
        
        # Find string length
        length = 0
        while cpu.memory.read((str_addr + length) & 0xFFFF, 1)[0] != 0:
            length += 1
        
        # Reverse in place
        for i in range(length // 2):
            left = cpu.memory.read((str_addr + i) & 0xFFFF, 1)[0]
            right = cpu.memory.read((str_addr + length - 1 - i) & 0xFFFF, 1)[0]
            cpu.memory.write((str_addr + i) & 0xFFFF, right, 1)
            cpu.memory.write((str_addr + length - 1 - i) & 0xFFFF, left, 1)

class Strfind(BaseInstruction):
    """STRFIND instruction - string substring exists"""
    def __init__(self):
        opcode_val = 0x7A  # STRFIND
        super().__init__("STRFIND", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        haystack_addr = cpu.get_operand_value(operands[0])
        needle_addr = cpu.get_operand_value(operands[1])
        
        # Get needle
        needle = []
        i = 0
        while True:
            char = cpu.memory.read((needle_addr + i) & 0xFFFF, 1)[0]
            if char == 0:
                break
            needle.append(char)
            i += 1
        
        needle_len = len(needle)
        if needle_len == 0:
            cpu.Rregisters[0] = 1  # Empty needle always found
            return
        
        # Search for needle in haystack
        found = False
        i = 0
        while True:
            h_char = cpu.memory.read((haystack_addr + i) & 0xFFFF, 1)[0]
            if h_char == 0:
                break
            
            if i <= 1000 - needle_len:  # Prevent infinite loop
                match = True
                for j in range(needle_len):
                    if cpu.memory.read((haystack_addr + i + j) & 0xFFFF, 1)[0] != needle[j]:
                        match = False
                        break
                if match:
                    found = True
                    break
            i += 1
        
        cpu.Rregisters[0] = 1 if found else 0

class Strfindi(BaseInstruction):
    """STRFINDI instruction - string case-insensitive substring exists"""
    def __init__(self):
        opcode_val = 0x7B  # STRFINDI
        super().__init__("STRFINDI", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        haystack_addr = cpu.get_operand_value(operands[0])
        needle_addr = cpu.get_operand_value(operands[1])
        
        # Get needle
        needle = []
        i = 0
        while True:
            char = cpu.memory.read((needle_addr + i) & 0xFFFF, 1)[0]
            if char == 0:
                break
            needle.append(char)
            i += 1
        
        needle_len = len(needle)
        if needle_len == 0:
            cpu.Rregisters[0] = 1  # Empty needle always found
            return
        
        # Search for needle in haystack (case-insensitive)
        found = False
        i = 0
        while True:
            h_char = cpu.memory.read((haystack_addr + i) & 0xFFFF, 1)[0]
            if h_char == 0:
                break
            
            if i <= 1000 - needle_len:  # Prevent infinite loop
                match = True
                for j in range(needle_len):
                    n_char = needle[j]
                    h_cmp = cpu.memory.read((haystack_addr + i + j) & 0xFFFF, 1)[0]
                    # Simple case-insensitive comparison
                    if h_cmp != n_char and not (
                        (h_cmp >= 65 and h_cmp <= 90 and n_char == h_cmp + 32) or
                        (h_cmp >= 97 and h_cmp <= 122 and n_char == h_cmp - 32)
                    ):
                        match = False
                        break
                if match:
                    found = True
                    break
            i += 1
        
        cpu.Rregisters[0] = 1 if found else 0

# Type conversion operations
class Itob(BaseInstruction):
    """ITOB instruction - integer to binary string"""
    def __init__(self):
        opcode_val = 0x83  # ITOB
        super().__init__("ITOB", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        dest_addr = cpu.get_operand_value(operands[0])
        value = cpu.get_operand_value(operands[1])
        
        # Convert integer to binary string
        if value == 0:
            binary_str = "0"
        else:
            binary_str = ""
            temp = value
            while temp > 0:
                binary_str = str(temp & 1) + binary_str
                temp >>= 1
        
        # Write binary string to destination address
        for i, char in enumerate(binary_str):
            cpu.write_memory((dest_addr + i) & 0xFFFF, ord(char), 1)
        # Null terminate
        cpu.write_memory((dest_addr + len(binary_str)) & 0xFFFF, 0, 1)

class Btoi(BaseInstruction):
    """BTOI instruction - binary string to integer"""
    def __init__(self):
        opcode_val = 0x84  # BTOI
        super().__init__("BTOI", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        dest_operand = operands[0]
        source_addr = cpu.get_operand_value(operands[1])
        
        # Read binary string from source address
        binary_str = ""
        i = 0
        while True:
            char = cpu.memory.read((source_addr + i) & 0xFFFF, 1)[0]
            if char == 0 or char not in (48, 49):  # '0' or '1'
                break
            binary_str += chr(char)
            i += 1
        
        # Convert binary string to integer
        result = 0
        for char in binary_str:
            result = (result << 1) | (1 if char == '1' else 0)
        
        cpu.set_operand_value(dest_operand, result)

class Itos(BaseInstruction):
    """ITOS instruction - integer to decimal string"""
    def __init__(self):
        opcode_val = 0x85  # ITOS
        super().__init__("ITOS", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        dest_addr = cpu.get_operand_value(operands[0])
        value = cpu.get_operand_value(operands[1])
        
        # Convert integer to decimal string
        if value == 0:
            decimal_str = "0"
        else:
            decimal_str = ""
            temp = abs(value)
            while temp > 0:
                decimal_str = str(temp % 10) + decimal_str
                temp //= 10
            if value < 0:
                decimal_str = "-" + decimal_str
        
        # Write decimal string to destination address
        for i, char in enumerate(decimal_str):
            cpu.write_memory((dest_addr + i) & 0xFFFF, ord(char), 1)
        # Null terminate
        cpu.write_memory((dest_addr + len(decimal_str)) & 0xFFFF, 0, 1)

class Stoi(BaseInstruction):
    """STOI instruction - decimal string to integer"""
    def __init__(self):
        opcode_val = 0x86  # STOI
        super().__init__("STOI", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        dest_operand = operands[0]
        source_addr = cpu.get_operand_value(operands[1])
        
        # Read decimal string from source address
        decimal_str = ""
        i = 0
        while True:
            char = cpu.memory.read((source_addr + i) & 0xFFFF, 1)[0]
            if char == 0:
                break
            decimal_str += chr(char)
            i += 1
        
        # Convert decimal string to integer
        try:
            result = int(decimal_str)
        except ValueError:
            result = 0  # Invalid string defaults to 0
        
        cpu.set_operand_value(dest_operand, result)

# BCD operations
class Sed(BaseInstruction):
    """SED instruction - set BCD mode"""
    def __init__(self):
        opcode_val = 0x4B  # SED
        super().__init__("SED", opcode_val)
    
    def execute(self, cpu):
        cpu.decimal_flag = True

class Cld(BaseInstruction):
    """CLD instruction - clear BCD mode"""
    def __init__(self):
        opcode_val = 0x4C  # CLD
        super().__init__("CLD", opcode_val)
    
    def execute(self, cpu):
        cpu.decimal_flag = False

class Cla(BaseInstruction):
    """CLA instruction - clear BCD adjust flag"""
    def __init__(self):
        opcode_val = 0x4D  # CLA
        super().__init__("CLA", opcode_val)
    
    def execute(self, cpu):
        cpu.bcd_adjust_flag = 0

class Bcda(BaseInstruction):
    """BCDA instruction - BCD adjust after addition"""
    def __init__(self):
        opcode_val = 0x4E  # BCDA
        super().__init__("BCDA", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        dest_value = cpu.get_operand_value(operands[0])
        source_value = cpu.get_operand_value(operands[1], operands[0])
        
        # Perform addition first
        result = dest_value + source_value
        
        # In binary mode, add carry if aux_carry is set
        if not cpu.decimal_flag and hasattr(cpu, 'aux_carry') and cpu.aux_carry:
            result += 1
        
        # Adjust for BCD addition
        if cpu.decimal_flag:
            # Check if adjustment is needed for low digit
            if result & 0x0F > 9:
                result += 0x06
            
            # Check if adjustment is needed for high digit
            if (result >> 4) & 0x0F > 9:
                result += 0x60
            
            # Handle carry
            if result > 0x99:
                result += 0x60
        
        cpu.set_operand_value(operands[0], result & 0xFFFF)

class Bcds(BaseInstruction):
    """BCDS instruction - BCD subtract with borrow"""
    def __init__(self):
        opcode_val = 0x4F  # BCDS
        super().__init__("BCDS", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        dest_value = cpu.get_operand_value(operands[0])
        source_value = cpu.get_operand_value(operands[1], operands[0])
        
        # Perform subtraction first
        result = dest_value - source_value
        
        # In binary mode, subtract borrow if aux_carry is set
        if not cpu.decimal_flag and hasattr(cpu, 'aux_carry') and cpu.aux_carry:
            result -= 1
        
        # Adjust for BCD subtraction
        if cpu.decimal_flag:
            # Check if adjustment is needed for low digit
            if result & 0x0F > 9:
                result -= 0x06
            
            # Check if adjustment is needed for high digit
            if (result >> 4) & 0x0F > 9:
                result -= 0x60
            
            # Handle carry
            if result < 0:
                result += 0x100
        
        cpu.set_operand_value(operands[0], result & 0xFFFF)

class Bcdcmp(BaseInstruction):
    """BCDCMP instruction - compare BCD values"""
    def __init__(self):
        opcode_val = 0x50  # BCDCMP
        super().__init__("BCDCMP", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        bcd1 = cpu.get_operand_value(operands[0])
        bcd2 = cpu.get_operand_value(operands[1])
        
        # Normalize BCD values (adjust if in BCD mode)
        if cpu.decimal_flag:
            # bcd1 = cpu._normalize_bcd(bcd1)
            # bcd2 = cpu._normalize_bcd(bcd2)
            pass
        
        # Perform comparison
        if bcd1 == bcd2:
            cpu.zero_flag = True
            cpu.sign_flag = False
            cpu.carry_flag = False
        elif bcd1 < bcd2:
            cpu.zero_flag = False
            cpu.sign_flag = True  # Negative result
            cpu.carry_flag = True  # Borrow occurred
        else:
            cpu.zero_flag = False
            cpu.sign_flag = False
            cpu.carry_flag = False

class Bcd2bin(BaseInstruction):
    """BCD2BIN instruction - convert BCD to binary"""
    def __init__(self):
        opcode_val = 0x51  # BCD2BIN
        super().__init__("BCD2BIN", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        bcd_value = cpu.get_operand_value(operands[0])
        
        # Check if all digits are valid BCD (0-9)
        valid_bcd = True
        for i in range(4):  # For each BCD digit
            digit = (bcd_value >> (i * 4)) & 0x0F
            if digit > 9:
                valid_bcd = False
                break
        
        if valid_bcd:
            # Convert BCD to binary
            binary_value = 0
            for i in range(4):  # For each BCD digit
                digit = (bcd_value >> (i * 4)) & 0x0F
                binary_value += digit * (10 ** i)
            cpu.set_operand_value(operands[0], binary_value & 0xFFFF)
        else:
            # Invalid BCD, return as-is
            cpu.set_operand_value(operands[0], bcd_value & 0xFFFF)

class Bin2bcd(BaseInstruction):
    """BIN2BCD instruction - convert binary to BCD"""
    def __init__(self):
        opcode_val = 0x52  # BIN2BCD
        super().__init__("BIN2BCD", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        binary_value = cpu.get_operand_value(operands[0])
        
        # Convert binary to BCD
        bcd_value = 0
        for i in range(4):  # For each BCD digit
            binary_digit = (binary_value // (10 ** i)) % 10
            bcd_value |= (binary_digit << (i * 4))
        
        cpu.set_operand_value(operands[0], bcd_value & 0xFFFF)

class Bcdadd(BaseInstruction):
    """BCDADD instruction - add BCD values"""
    def __init__(self):
        opcode_val = 0x53  # BCDADD
        super().__init__("BCDADD", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        bcd1 = cpu.get_operand_value(operands[0])
        bcd2 = cpu.get_operand_value(operands[1])
        
        # Normalize BCD values (adjust if in BCD mode)
        if cpu.decimal_flag:
            # bcd1 = cpu._normalize_bcd(bcd1)
            # bcd2 = cpu._normalize_bcd(bcd2)
            pass
        
        result = bcd1 + bcd2
        
        # Adjust result if necessary
        if cpu.decimal_flag:
            if result & 0x0F > 9:
                result += 0x06
            if (result >> 4) & 0x0F > 9:
                result += 0x60
        
        cpu.set_operand_value(operands[0], result & 0xFFFF)

class Bcdsub(BaseInstruction):
    """BCDSUB instruction - subtract BCD values"""
    def __init__(self):
        opcode_val = 0x54  # BCDSUB
        super().__init__("BCDSUB", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        bcd1 = cpu.get_operand_value(operands[0])
        bcd2 = cpu.get_operand_value(operands[1])
        
        # Normalize BCD values (adjust if in BCD mode)
        if cpu.decimal_flag:
            # bcd1 = cpu._normalize_bcd(bcd1)
            # bcd2 = cpu._normalize_bcd(bcd2)
            pass
        
        result = bcd1 - bcd2
        
        # Adjust result if necessary
        if cpu.decimal_flag:
            if result & 0x0F > 9:
                result -= 0x06
            if ((result >> 4) & 0x0F) > 9:
                result -= 0x60
        
        cpu.set_operand_value(operands[0], result & 0xFFFF)

# Math functions
class Sin(BaseInstruction):
    """SIN instruction - sine of angle in radians"""
    def __init__(self):
        opcode_val = 0x5F  # SIN
        super().__init__("SIN", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        angle = cpu.get_operand_value(operands[0])
        # Convert from fixed-point (scale 256) to radians
        angle_radians = angle / 256.0
        result = int(math.sin(angle_radians) * 256)  # Scale back to fixed-point
        cpu.set_operand_value(operands[0], result & 0xFFFF)

class Cos(BaseInstruction):
    """COS instruction - cosine of angle in radians"""
    def __init__(self):
        opcode_val = 0x60  # COS
        super().__init__("COS", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        angle = cpu.get_operand_value(operands[0])
        # Convert from fixed-point (scale 256) to radians
        angle_radians = angle / 256.0
        result = int(math.cos(angle_radians) * 256)  # Scale back to fixed-point
        cpu.set_operand_value(operands[0], result & 0xFFFF)

class Tan(BaseInstruction):
    """TAN instruction - tangent of angle in radians"""
    def __init__(self):
        opcode_val = 0x61  # TAN
        super().__init__("TAN", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        angle = cpu.get_operand_value(operands[0])
        try:
            result = int(math.tan(angle) * 1000)  # Scale by 1000 for precision
            cpu.set_operand_value(operands[0], result & 0xFFFF)
        except:
            # Handle tan undefined cases
            cpu.set_operand_value(operands[0], 0)

class Log(BaseInstruction):
    """LOG instruction - natural logarithm"""
    def __init__(self):
        opcode_val = 0x5D  # LOG
        super().__init__("LOG", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        value = cpu.get_operand_value(operands[0])
        if value <= 0:
            cpu.set_operand_value(operands[0], 0)
        else:
            # Convert from fixed-point (scale 256) to float
            value_float = value / 256.0
            result = int(math.log(value_float) * 256)  # Scale back to fixed-point
            cpu.set_operand_value(operands[0], result & 0xFFFF)

class Exp(BaseInstruction):
    """EXP instruction - exponential function (e^x)"""
    def __init__(self):
        opcode_val = 0x5E  # EXP
        super().__init__("EXP", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        value = cpu.get_operand_value(operands[0])
        # Convert from fixed-point (scale 256) to float
        value_float = value / 256.0
        try:
            result = int(math.exp(value_float) * 256)  # Scale back to fixed-point
            cpu.set_operand_value(operands[0], result & 0xFFFF)
        except:
            # Handle overflow
            cpu.set_operand_value(operands[0], 0xFFFF)

class Powr(BaseInstruction):
    """POWR instruction - power function (base^exponent)"""
    def __init__(self):
        opcode_val = 0x5B  # POWR
        super().__init__("POWR", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        base = cpu.get_operand_value(operands[0])
        exponent = cpu.get_operand_value(operands[1])
        try:
            # For integer power operations, don't use fixed-point scaling
            result = int(math.pow(base, exponent))
            cpu.set_operand_value(operands[0], result & 0xFFFF)
        except:
            cpu.set_operand_value(operands[0], 0)

class Sqrt(BaseInstruction):
    """SQRT instruction - square root"""
    def __init__(self):
        opcode_val = 0x5C  # SQRT
        super().__init__("SQRT", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        value = cpu.get_operand_value(operands[0])
        # Convert to signed 16-bit value
        signed_value = value if value < 0x8000 else value - 0x10000
        if signed_value < 0:
            cpu.set_operand_value(operands[0], 0)
        else:
            result = int(math.sqrt(signed_value))
            cpu.set_operand_value(operands[0], result & 0xFFFF)

class Atan(BaseInstruction):
    """ATAN instruction - arctangent"""
    def __init__(self):
        opcode_val = 0x62  # ATAN
        super().__init__("ATAN", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        value = cpu.get_operand_value(operands[0])
        result = int(math.atan(value / 256.0) * 256)  # Fixed-point scaling
        cpu.set_operand_value(operands[0], result & 0xFFFF)

class Asin(BaseInstruction):
    """ASIN instruction - arcsine"""
    def __init__(self):
        opcode_val = 0x63  # ASIN
        super().__init__("ASIN", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        value = cpu.get_operand_value(operands[0])
        try:
            result = int(math.asin(value / 256.0) * 256)  # Fixed-point scaling
            cpu.set_operand_value(operands[0], result & 0xFFFF)
        except:
            cpu.set_operand_value(operands[0], 0)

class Acos(BaseInstruction):
    """ACOS instruction - arccosine"""
    def __init__(self):
        opcode_val = 0x64  # ACOS
        super().__init__("ACOS", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        value = cpu.get_operand_value(operands[0])
        try:
            result = int(math.acos(value / 256.0) * 256)  # Fixed-point scaling
            cpu.set_operand_value(operands[0], result & 0xFFFF)
        except:
            cpu.set_operand_value(operands[0], 0)

class Deg(BaseInstruction):
    """DEG instruction - convert degrees to radians"""
    def __init__(self):
        opcode_val = 0x65  # DEG
        super().__init__("DEG", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        degrees = cpu.get_operand_value(operands[0])
        result = int((degrees * math.pi / 180.0) * 256)  # Fixed-point scaling
        cpu.set_operand_value(operands[0], result & 0xFFFF)

class Rad(BaseInstruction):
    """RAD instruction - convert radians to degrees"""
    def __init__(self):
        opcode_val = 0x66  # RAD
        super().__init__("RAD", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        radians = cpu.get_operand_value(operands[0])
        result = int((radians / 256.0) * 180.0 / math.pi)  # Convert fixed-point radians to degrees
        cpu.set_operand_value(operands[0], result & 0xFFFF)

class Floor(BaseInstruction):
    """FLOOR instruction - floor function"""
    def __init__(self):
        opcode_val = 0x67  # FLOOR
        super().__init__("FLOOR", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        value = cpu.get_operand_value(operands[0])
        result = int(math.floor(value / 256.0))  # Convert from fixed-point and floor
        cpu.set_operand_value(operands[0], result & 0xFFFF)

class Ceil(BaseInstruction):
    """CEIL instruction - ceiling function"""
    def __init__(self):
        opcode_val = 0x68  # CEIL
        super().__init__("CEIL", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        value = cpu.get_operand_value(operands[0])
        result = int(math.ceil(value / 256.0))  # Convert from fixed-point and ceil
        cpu.set_operand_value(operands[0], result & 0xFFFF)

class Round(BaseInstruction):
    """ROUND instruction - round to nearest integer"""
    def __init__(self):
        opcode_val = 0x69  # ROUND
        super().__init__("ROUND", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        value = cpu.get_operand_value(operands[0])
        result = int(round(value / 256.0))  # Convert from fixed-point and round
        cpu.set_operand_value(operands[0], result & 0xFFFF)

class Trunc(BaseInstruction):
    """TRUNC instruction - truncate decimal part"""
    def __init__(self):
        opcode_val = 0x6A  # TRUNC
        super().__init__("TRUNC", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        value = cpu.get_operand_value(operands[0])
        result = int(value // 256)  # Truncate to integer part
        cpu.set_operand_value(operands[0], result & 0xFFFF)

class Frac(BaseInstruction):
    """FRAC instruction - get fractional part"""
    def __init__(self):
        opcode_val = 0x6B  # FRAC
        super().__init__("FRAC", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        value = cpu.get_operand_value(operands[0])
        result = value % 256  # Get fractional part in fixed-point
        cpu.set_operand_value(operands[0], result & 0xFFFF)

class Intgr(BaseInstruction):
    """INTGR instruction - get integer part"""
    def __init__(self):
        opcode_val = 0x6C  # INTGR
        super().__init__("INTGR", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        value = cpu.get_operand_value(operands[0])
        result = value // 256  # Get integer part
        cpu.set_operand_value(operands[0], result & 0xFFFF)

# Sprite operations
class Spblit(BaseInstruction):
    """SPBLIT instruction - blit sprite"""
    def __init__(self):
        opcode_val = 0x55  # SPBLIT
        super().__init__("SPBLIT", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        sprite_id = cpu.get_operand_value(operands[0])
        cpu.gfx.blit_sprite(sprite_id, cpu.memory)

class Spblitall(BaseInstruction):
    """SPBLITALL instruction - blit all sprites"""
    def __init__(self):
        opcode_val = 0x56  # SPBLITALL
        super().__init__("SPBLITALL", opcode_val)
    
    def execute(self, cpu):
        cpu.gfx.blit_all_sprites(cpu.memory)

# Sound operations
class Splay(BaseInstruction):
    """SPLAY instruction - play sound"""
    def __init__(self):
        opcode_val = 0x57  # SPLAY
        super().__init__("SPLAY", opcode_val)
    
    def execute(self, cpu):
        # Use channel from SW register (sound waveform/control register)
        channel = cpu.sound.SW & 0x07  # Lower 3 bits for channel
        success = cpu.sound.splay(channel)
        # Could set flags based on success, but for now just execute

class Sstop(BaseInstruction):
    """SSTOP instruction - stop sound"""
    def __init__(self):
        opcode_val = 0x58  # SSTOP
        super().__init__("SSTOP", opcode_val)
    
    def execute(self, cpu):
        # Use channel from SW register (sound waveform/control register)
        channel = cpu.sound.SW & 0x07  # Lower 3 bits for channel
        success = cpu.sound.sstop(channel)
        # Could set flags based on success, but for now just execute

class Strig(BaseInstruction):
    """STRIG instruction - trigger sound effect"""
    def __init__(self):
        opcode_val = 0x59  # STRIG
        super().__init__("STRIG", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        effect_type = cpu.get_operand_value(operands[0])
        success = cpu.sound.strig(effect_type)
        # Could set flags based on success, but for now just execute

class Loop(BaseInstruction):
    """LOOP instruction - decrement register and jump if not zero"""
    def __init__(self):
        opcode_val = 0x5A  # LOOP
        super().__init__("LOOP", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        # First operand is the counter register
        counter_value = cpu.get_operand_value(operands[0])
        # Decrement the counter
        new_value = (counter_value - 1) & 0xFFFF
        cpu.set_operand_value(operands[0], new_value)
        # If not zero, jump to the target address
        if new_value != 0:
            target_address = cpu.get_operand_value(operands[1])
            cpu.pc = target_address
            cpu.invalidate_prefetch()

# Instruction table creation

def create_instruction_table():
    """Create and return a dictionary mapping opcodes to instruction instances"""
    instructions = [
        # No-operand instructions
        Hlt(),   # 0x00
        Ret(),   # 0x01
        IRet(),  # 0x02
        Cli(),   # 0x03
        Sti(),   # 0x04
        Nop(),   # 0xFF

        # Data movement
        Mov(),  # 0x06

        # Arithmetic operations
        Add(),     # 0x07
        Sub(),     # 0x08
        Mul(),     # 0x09
        Div(),     # 0x0A
        Inc(),     # 0x0B
        Dec(),     # 0x0C
        Mod(),     # 0x0D
        Neg(),     # 0x0E
        Abs(),     # 0x0F

        # Enhanced arithmetic operations
        Adc(),     # 0x87
        Sbc(),     # 0x88
        Mulh(),    # 0x89
        Divh(),    # 0x8A
        Min(),     # 0x8B
        Max(),     # 0x8C
        Clz(),     # 0x8D
        Ctz(),     # 0x8E
        Popcnt(),  # 0x8F

        # Enhanced bitwise operations
        Sar(),     # 0x90
        Sal(),     # 0x91
        Rcl(),     # 0x92
        Rcr(),     # 0x93

        # Enhanced data movement
        Swap(),    # 0x94
        Xchng(),   # 0x95
        Movz(),    # 0x96
        Movnz(),   # 0x97
        Lea(),     # 0x98

        # Bitwise operations
        And(),      # 0x10
        Or(),       # 0x11
        Xor(),      # 0x12
        Not(),      # 0x13
        Shl(),      # 0x14
        Shr(),      # 0x15
        Rol(),      # 0x16
        Ror(),      # 0x17

        # Bit test and modify
        Btst(),     # 0x6D
        Bset(),     # 0x6E
        Bclr(),     # 0x6F
        Bflip(),    # 0x70

        # String operations
        Strcpy(),   # 0x71
        Strcat(),   # 0x72
        Strcmp(),   # 0x73
        Strlen(),   # 0x74
        Strext(),   # 0x75
        Strexti(),  # 0x76
        Strupr(),   # 0x77
        Strlwr(),   # 0x78
        Strrev(),   # 0x79
        Strfind(),  # 0x7A
        Strfindi(), # 0x7B

        # Stack operations
        Push(),     # 0x18
        Pop(),      # 0x19
        Pushf(),    # 0x1A
        Popf(),     # 0x1B
        Pusha(),    # 0x1C
        Popa(),     # 0x1D
        Enter(),    # 0x9B
        Leave(),    # 0x9C
        Callz(),    # 0x9D
        Callnz(),   # 0x9E
        Retn(),     # 0x9F
        Loopz(),    # 0xA0
        While(),    # 0xA1

        # Control flow - jumps
        Jmp(),      # 0x1E
        Jz(),       # 0x1F
        Jnz(),      # 0x20
        Jo(),       # 0x21
        Jno(),      # 0x22
        Jc(),       # 0x23
        Jnc(),      # 0x24
        Js(),       # 0x25
        Jns(),      # 0x26
        Jgt(),      # 0x27
        Jlt(),      # 0x28
        Jge(),      # 0x29
        Jle(),      # 0x2A

        # Control flow - branches (relative)
        Br(),       # 0x2B
        Brz(),      # 0x2C
        Brnz(),     # 0x2D

        # Comparison
        Cmp(),      # 0x2E

        # Call
        Call(),     # 0x2F

        # Interrupt
        Int(),      # 0x30

        # Graphics operations
        Sblend(),   # 0x31
        Sread(),    # 0x32
        Swrite(),   # 0x33
        Srol(),     # 0x34
        Srot(),     # 0x35
        Sshft(),    # 0x36
        Sflip(),    # 0x37
        Sline(),    # 0x38
        Srect(),    # 0x39
        Scirc(),    # 0x3A
        Sinv(),     # 0x3B
        Sblit(),    # 0x3C
        Sfill(),    # 0x3D

        # VRAM operations
        Vread(),    # 0x3E
        Vwrite(),   # 0x3F
        Vblit(),    # 0x40

        # Text operations
        Char(),     # 0x41
        Text(),     # 0x42

        # Keyboard operations
        Keyin(),    # 0x43
        Keystat(),  # 0x44
        Keycount(), # 0x45
        Keyclear(), # 0x46
        Keyctrl(),  # 0x47

        # Random operations
        Rnd(),      # 0x48
        Rndr(),     # 0x49

        # Memory operations
        Memcpy(),   # 0x4A

        # BCD operations
        Sed(),      # 0x4B
        Cld(),      # 0x4C
        Cla(),      # 0x4D
        Bcda(),     # 0x4E
        Bcds(),     # 0x4F
        Bcdcmp(),   # 0x50
        Bcd2bin(),  # 0x51
        Bin2bcd(),  # 0x52
        Bcdadd(),   # 0x53
        Bcdsub(),   # 0x54

        # Sprite operations
        Spblit(),   # 0x55
        Spblitall(),# 0x56

        # Sound operations
        Splay(),    # 0x57
        Sstop(),    # 0x58
        Strig(),    # 0x59

        # Loop operation
        Loop(),     # 0x5A

        # Math functions
        Powr(),     # 0x5B
        Sqrt(),     # 0x5C
        Log(),      # 0x5D
        Exp(),      # 0x5E
        Sin(),      # 0x5F
        Cos(),      # 0x60
        Tan(),      # 0x61
        Atan(),     # 0x62
        Asin(),     # 0x63
        Acos(),     # 0x64
        Deg(),      # 0x65
        Rad(),      # 0x66
        Floor(),    # 0x67
        Ceil(),     # 0x68
        Round(),    # 0x69
        Trunc(),    # 0x6A
        Frac(),     # 0x6B
        Intgr(),    # 0x6C

        # String operations
        Strcpy(),   # 0x71
        Strcat(),   # 0x72
        Strcmp(),   # 0x73
        Strlen(),   # 0x74
        Strext(),   # 0x75
        Strexti(),  # 0x76
        Strupr(),   # 0x77
        Strlwr(),   # 0x78
        Strrev(),   # 0x79
        Strfind(),  # 0x7A
        Strfindi(), # 0x7B

        # Type conversion operations
        Itob(),     # 0x83
        Btoi(),     # 0x84
        Itos(),     # 0x85
        Stoi(),     # 0x86

        Memset(),   # 0x7C
        Memtest(),  # 0x7D
        Memmove(),  # 0x7E
        Memcmp(),   # 0x99
        Memswap(),  # 0x9A

        # Special register access instructions
        Sa(),       # 0xDD
        Sf(),       # 0xDE
        Sv(),       # 0xDF
        Sw(),       # 0xE0
        Vm(),       # 0xE1
        Vl(),       # 0xE2
        Tt(),       # 0xE3
        Tm(),       # 0xE4
        Tc(),       # 0xE5
        Ts(),       # 0xE6
        Vx(),       # 0xFD
        Vy(),       # 0xFE

    ]
    
    # Create the dispatch table
    table = {}
    for instruction in instructions:
        table[instruction.opcode] = instruction
    
    return table
