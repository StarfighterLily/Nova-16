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

# Data movement
class Mov(BaseInstruction):
    """MOV instruction for prefixed operand system"""
    def __init__(self):
        opcode_val = 0x06  # MOV
        super().__init__("MOV", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        source_value = cpu.get_operand_value(operands[1])
        cpu.set_operand_value(operands[0], source_value)

# Arithmetic operations
class Add(BaseInstruction):
    """ADD instruction for prefixed operand system"""
    def __init__(self):
        opcode_val = 0x07  # ADD
        super().__init__("ADD", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        dest_value = cpu.get_operand_value(operands[0])
        source_value = cpu.get_operand_value(operands[1])
        result = dest_value + source_value
        cpu.set_operand_value(operands[0], result)
        # Set flags based on destination operand type and masked result
        if operands[0]['type'] == 'register' and operands[0]['reg_type'] == 'R':
            masked_result = result & 0xFF
            cpu._set_flags_8bit(masked_result, result)
        else:
            masked_result = result & 0xFFFF
            cpu._set_flags_16bit(masked_result, result)

class Sub(BaseInstruction):
    """SUB instruction for prefixed operand system"""
    def __init__(self):
        opcode_val = 0x08  # SUB
        super().__init__("SUB", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        dest_value = cpu.get_operand_value(operands[0])
        source_value = cpu.get_operand_value(operands[1])
        result = dest_value - source_value
        cpu.set_operand_value(operands[0], result)
        # Set flags based on destination operand type and masked result
        if operands[0]['type'] == 'register' and operands[0]['reg_type'] == 'R':
            masked_result = result & 0xFF
            cpu._set_flags_8bit(masked_result, result)
        else:
            masked_result = result & 0xFFFF
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

# Bitwise operations
class And(BaseInstruction):
    """AND instruction for prefixed operand system"""
    def __init__(self):
        opcode_val = 0x10  # AND
        super().__init__("AND", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        dest_value = cpu.get_operand_value(operands[0])
        source_value = cpu.get_operand_value(operands[1])
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
        source_value = cpu.get_operand_value(operands[1])
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
        source_value = cpu.get_operand_value(operands[1])
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
        sp = int(cpu.Pregisters[8])
        cpu.memory.write_byte(sp, value & 0xFF)
        sp = (sp - 1) & 0xFFFF
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
        if sp >= 0xFFFF:
            raise RuntimeError(f"Stack underflow: SP=0x{sp:04X}")
        
        sp = (sp + 1) & 0xFFFF
        value = cpu.memory.read_byte(sp)
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
        # Push all registers (R0-R9, P0-P9, VX, VY) to stack
        registers = []
        registers.extend(cpu.Rregisters)  # R0-R9
        registers.extend(cpu.Pregisters)  # P0-P9
        registers.extend(cpu.gfx.Vregisters[:2])  # VX, VY
        
        for reg_value in reversed(registers):  # Push in reverse order
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
        # Pop all registers from stack (R0-R9, P0-P9, VX, VY)
        registers_order = list(range(21))  # 0-20 (R0-R9, P0-P9, VX, VY)
        
        for reg_num in registers_order:
            sp = int(cpu.Pregisters[8])
            if sp >= 0xFFFF:
                raise RuntimeError(f"Stack underflow during POPA: SP=0x{sp:04X}")
            
            value = cpu.memory.read_word(sp)
            sp = (sp + 2) & 0xFFFF
            cpu.Pregisters[8] = sp
            
            cpu.set_register_value(reg_num, value)

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
        dest_value = cpu.get_operand_value(operands[0])
        source_value = cpu.get_operand_value(operands[1])
        result = dest_value - source_value
        cpu._set_flags_16bit(result, result)

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
    """SLINE instruction - draw line x1, y1, x2, y2, color"""
    def __init__(self):
        opcode_val = 0x38  # SLINE
        super().__init__("SLINE", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(5)
        x1 = cpu.get_operand_value(operands[0])
        y1 = cpu.get_operand_value(operands[1])
        x2 = cpu.get_operand_value(operands[2])
        y2 = cpu.get_operand_value(operands[3])
        color = cpu.get_operand_value(operands[4])
        cpu.gfx.draw_line(x1, y1, x2, y2, color)

class Srect(BaseInstruction):
    """SRECT instruction - draw rectangle x1, y1, x2, y2, color, filled"""
    def __init__(self):
        opcode_val = 0x39  # SRECT
        super().__init__("SRECT", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(6)
        x1 = cpu.get_operand_value(operands[0])
        y1 = cpu.get_operand_value(operands[1])
        x2 = cpu.get_operand_value(operands[2])
        y2 = cpu.get_operand_value(operands[3])
        color = cpu.get_operand_value(operands[4])
        filled = cpu.get_operand_value(operands[5]) != 0
        cpu.gfx.draw_rectangle(x1, y1, x2, y2, color, filled)

class Scirc(BaseInstruction):
    """SCIRC instruction - draw circle x, y, radius, color, filled"""
    def __init__(self):
        opcode_val = 0x3A  # SCIRC
        super().__init__("SCIRC", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(5)
        x = cpu.get_operand_value(operands[0])
        y = cpu.get_operand_value(operands[1])
        radius = cpu.get_operand_value(operands[2])
        color = cpu.get_operand_value(operands[3])
        filled = cpu.get_operand_value(operands[4]) != 0
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
        operands = cpu.parse_operands(2)
        char_code = cpu.get_operand_value(operands[0])
        color = cpu.get_operand_value(operands[1])
        x = cpu.gfx.Vregisters[0]
        y = cpu.gfx.Vregisters[1]
        cpu.gfx.draw_char(x, y, char_code, color)

class Text(BaseInstruction):
    """TEXT instruction - draw text"""
    def __init__(self):
        opcode_val = 0x42  # TEXT
        super().__init__("TEXT", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        text_addr = cpu.get_operand_value(operands[0])
        color = cpu.get_operand_value(operands[1])
        x = cpu.gfx.Vregisters[0]
        y = cpu.gfx.Vregisters[1]
        cpu.gfx.draw_text(x, y, text_addr, color, cpu.memory)

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
            cpu.memory.write((dest_addr + i) & 0xFFFF, data, 1)

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
            cpu.memory.write((dest_addr + i) & 0xFFFF, fill_value, 1)

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
            cpu.memory.write((dest_addr + i) & 0xFFFF, char, 1)
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
            cpu.memory.write((dest_addr + i + j) & 0xFFFF, char, 1)
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
            char = cpu.memory.read((needleAddr + i) & 0xFFFF, 1)[0]
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
            char = cpu.memory.read((needleAddr + i) & 0xFFFF, 1)[0]
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

# Layer operations
class Lcpy(BaseInstruction):
    """LCPY instruction - copy contents of layer dest, source"""
    def __init__(self):
        opcode_val = 0x83  # LCPY
        super().__init__("LCPY", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        dest_layer = cpu.get_operand_value(operands[0])
        source_layer = cpu.get_operand_value(operands[1])
        cpu.gfx.copy_layer(source_layer, dest_layer)

class Lclr(BaseInstruction):
    """LCLR instruction - clear layer to color"""
    def __init__(self):
        opcode_val = 0x84  # LCLR
        super().__init__("LCLR", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        layer_num = cpu.get_operand_value(operands[0])
        color = cpu.get_operand_value(operands[1])
        cpu.gfx.fill_layer(color, layer_num)

class Lmov(BaseInstruction):
    """LMOV instruction - move contents of layer dest, source"""
    def __init__(self):
        opcode_val = 0x85  # LMOV
        super().__init__("LMOV", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        dest_layer = cpu.get_operand_value(operands[0])
        source_layer = cpu.get_operand_value(operands[1])
        cpu.gfx.copy_layer(source_layer, dest_layer)
        cpu.gfx.clear_layer(0, source_layer)  # Clear source after copy

class Lshft(BaseInstruction):
    """LSHFT instruction - shift layer by axis, amount"""
    def __init__(self):
        opcode_val = 0x86  # LSHFT
        super().__init__("LSHFT", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(3)
        layer_num = cpu.get_operand_value(operands[0])
        axis = cpu.get_operand_value(operands[1])
        amount = cpu.get_operand_value(operands[2])
        
        if axis == 0:  # X axis
            cpu.gfx.shift_layer_x(amount, layer_num)
        elif axis == 1:  # Y axis
            cpu.gfx.shift_layer_y(amount, layer_num)
        else:
            raise ValueError(f"Invalid axis for LSHFT: {axis}")

class Lrot(BaseInstruction):
    """LROT instruction - rotate layer by direction, amount"""
    def __init__(self):
        opcode_val = 0x87  # LROT
        super().__init__("LROT", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(3)
        layer_num = cpu.get_operand_value(operands[0])
        direction = cpu.get_operand_value(operands[1])
        amount = cpu.get_operand_value(operands[2])
        
        if direction == 0:  # Left
            cpu.gfx.rotate_layer_left(amount, layer_num)
        elif direction == 1:  # Right
            cpu.gfx.rotate_layer_right(amount, layer_num)
        else:
            raise ValueError(f"Invalid direction for LROT: {direction}")

class Lflip(BaseInstruction):
    """LFLIP instruction - flip layer by axis"""
    def __init__(self):
        opcode_val = 0x88  # LFLIP
        super().__init__("LFLIP", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        layer_num = cpu.get_operand_value(operands[0])
        axis = cpu.get_operand_value(operands[1])
        
        if axis == 0:  # X axis
            cpu.gfx.flip_layer_x(layer_num)
        elif axis == 1:  # Y axis
            cpu.gfx.flip_layer_y(layer_num)
        else:
            raise ValueError(f"Invalid axis for LFLIP: {axis}")

class Lswap(BaseInstruction):
    """LSWAP instruction - swap two layers dest, source"""
    def __init__(self):
        opcode_val = 0x89  # LSWAP
        super().__init__("LSWAP", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        layer1 = cpu.get_operand_value(operands[0])
        layer2 = cpu.get_operand_value(operands[1])
        cpu.gfx.swap_layers(layer1, layer2)

# Register/special references (for direct access)

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

        # Stack operations
        Push(),     # 0x18
        Pop(),      # 0x19
        Pushf(),    # 0x1A
        Popf(),     # 0x1B
        Pusha(),    # 0x1C
        Popa(),     # 0x1D

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
        Memset(),   # 0x7C

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

        # Layer operations
        Lcpy(),     # 0x83
        Lclr(),     # 0x84
        Lmov(),     # 0x85
        Lshft(),    # 0x86
        Lrot(),     # 0x87
        Lflip(),    # 0x88
        Lswap(),    # 0x89

        # BCD operations
        # Sed(),      # 0x4B
        # Cld(),      # 0x4C
        # Cla(),      # 0x4D
        # Bcda(),     # 0x4E
        # Bcds(),     # 0x4F
        # Bcdcmp(),   # 0x50
        # Bcd2bin(),  # 0x51
        # Bin2bcd(),  # 0x52
        # Bcdadd(),   # 0x53
        # Bcdsub(),   # 0x54

        # Sprite operations
        # Spblit(),   # 0x55
        # Spblitall(),# 0x56

        # Sound operations
        # Splay(),    # 0x57
        # Sstop(),    # 0x58
        # Strig(),    # 0x59

        # Loop operation
        # Loop(),     # 0x5A

        # Math functions
        # Powr(),     # 0x5B
        # Sqrt(),     # 0x5C
        # Log(),      # 0x5D
        # Exp(),      # 0x5E
        # Sin(),      # 0x5F
        # Cos(),      # 0x60
        # Tan(),      # 0x61
        # Atan(),     # 0x62
        # Asin(),     # 0x63
        # Acos(),     # 0x64
        # Deg(),      # 0x65
        # Rad(),      # 0x66
        # Floor(),    # 0x67
        # Ceil(),     # 0x68
        # Round(),    # 0x69
        # Trunc(),    # 0x6A
        # Frac(),     # 0x6B
        # Intgr(),    # 0x6C
    ]
    
    # Create the dispatch table
    table = {}
    for instruction in instructions:
        table[instruction.opcode] = instruction
    
    return table
