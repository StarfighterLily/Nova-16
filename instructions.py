from opcodes import opcodes

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
        
        # Restore PC first (it was pushed last)
        pc_value = cpu.memory.read_word(cpu.Pregisters[8])
        cpu.pc = pc_value
        sp = int(cpu.Pregisters[8])
        sp = (sp + 2) & 0xFFFF
        cpu.Pregisters[8] = sp
        
        # Restore flags second (they were pushed first)
        flags_val = cpu.memory.read_word(cpu.Pregisters[8])
        sp = int(cpu.Pregisters[8])
        sp = (sp + 2) & 0xFFFF
        cpu.Pregisters[8] = sp
        
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
        # Set flags based on destination operand type
        if operands[0]['type'] == 'register' and operands[0]['reg_type'] == 'R':
            cpu._set_flags_8bit(result, result)
        else:
            cpu._set_flags_16bit(result, result)

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
        # Set flags based on destination operand type
        if operands[0]['type'] == 'register' and operands[0]['reg_type'] == 'R':
            cpu._set_flags_8bit(result, result)
        else:
            cpu._set_flags_16bit(result, result)

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
        result = ~value
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
        shift_amount = cpu.get_operand_value(operands[1])
        result = dest_value << shift_amount
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
        shift_amount = cpu.get_operand_value(operands[1])
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
        rotate_amount = cpu.get_operand_value(operands[1])
        result = ((dest_value << rotate_amount) | (dest_value >> (16 - rotate_amount))) & 0xFFFF
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
        rotate_amount = cpu.get_operand_value(operands[1])
        result = ((dest_value >> rotate_amount) | (dest_value << (16 - rotate_amount))) & 0xFFFF
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
        cpu.pc = target_address
        cpu.invalidate_prefetch()

class Jz(BaseInstruction):
    """JZ instruction - jump if zero"""
    def __init__(self):
        opcode_val = 0x1F  # JZ
        super().__init__("JZ", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        if cpu.flags[7]:  # Zero flag
            target_address = cpu.get_operand_value(operands[0])
            cpu.pc = target_address
            cpu.invalidate_prefetch()

class Jnz(BaseInstruction):
    """JNZ instruction - jump if not zero"""
    def __init__(self):
        opcode_val = 0x20  # JNZ
        super().__init__("JNZ", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        if not cpu.flags[7]:  # Not zero flag
            target_address = cpu.get_operand_value(operands[0])
            cpu.pc = target_address
            cpu.invalidate_prefetch()

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
        color = cpu.gfx.read_pixel(x, y)
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

class Srolx(BaseInstruction):
    """SROLX instruction - rotate screen X"""
    def __init__(self):
        opcode_val = 0x34  # SROLX
        super().__init__("SROLX", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        amount = cpu.get_operand_value(operands[0])
        cpu.gfx.rotate_x(amount)

class Sroly(BaseInstruction):
    """SROLY instruction - rotate screen Y"""
    def __init__(self):
        opcode_val = 0x35  # SROLY
        super().__init__("SROLY", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        amount = cpu.get_operand_value(operands[0])
        cpu.gfx.rotate_y(amount)

class Srotl(BaseInstruction):
    """SROTL instruction - rotate screen left"""
    def __init__(self):
        opcode_val = 0x36  # SROTL
        super().__init__("SROTL", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        amount = cpu.get_operand_value(operands[0])
        cpu.gfx.rotate_left(amount)

class Srotr(BaseInstruction):
    """SROTR instruction - rotate screen right"""
    def __init__(self):
        opcode_val = 0x37  # SROTR
        super().__init__("SROTR", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        amount = cpu.get_operand_value(operands[0])
        cpu.gfx.rotate_right(amount)

class Sshftx(BaseInstruction):
    """SSHFTX instruction - shift screen X"""
    def __init__(self):
        opcode_val = 0x38  # SSHFTX
        super().__init__("SSHFTX", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        amount = cpu.get_operand_value(operands[0])
        cpu.gfx.shift_x(amount)

class Sshfty(BaseInstruction):
    """SSHFTY instruction - shift screen Y"""
    def __init__(self):
        opcode_val = 0x39  # SSHFTY
        super().__init__("SSHFTY", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        amount = cpu.get_operand_value(operands[0])
        cpu.gfx.shift_y(amount)

class Sflipx(BaseInstruction):
    """SFLIPX instruction - flip screen X"""
    def __init__(self):
        opcode_val = 0x3A  # SFLIPX
        super().__init__("SFLIPX", opcode_val)
    
    def execute(self, cpu):
        cpu.gfx.flip_x()

class Sflipy(BaseInstruction):
    """SFLIPY instruction - flip screen Y"""
    def __init__(self):
        opcode_val = 0x3B  # SFLIPY
        super().__init__("SFLIPY", opcode_val)
    
    def execute(self, cpu):
        cpu.gfx.flip_y()

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
        cpu.gfx.fill(color)

# VRAM operations
class Vread(BaseInstruction):
    """VREAD instruction - read VRAM"""
    def __init__(self):
        opcode_val = 0x3E  # VREAD
        super().__init__("VREAD", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        addr = cpu.get_operand_value(operands[0])
        value = cpu.gfx.read_vram(addr)
        cpu.set_operand_value(operands[0], value)

class Vwrite(BaseInstruction):
    """VWRITE instruction - write VRAM"""
    def __init__(self):
        opcode_val = 0x3F  # VWRITE
        super().__init__("VWRITE", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        addr = cpu.get_operand_value(operands[0])
        value = cpu.get_operand_value(operands[1])
        cpu.gfx.write_vram(addr, value)

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
        cpu.gfx.draw_text(x, y, text_addr, color)

# Keyboard operations
class Keyin(BaseInstruction):
    """KEYIN instruction - read key"""
    def __init__(self):
        opcode_val = 0x43  # KEYIN
        super().__init__("KEYIN", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        key = cpu.keyboard.read_key()
        cpu.set_operand_value(operands[0], key)

class Keystat(BaseInstruction):
    """KEYSTAT instruction - check key status"""
    def __init__(self):
        opcode_val = 0x44  # KEYSTAT
        super().__init__("KEYSTAT", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        status = 1 if cpu.keyboard.key_available() else 0
        cpu.set_operand_value(operands[0], status)

class Keycount(BaseInstruction):
    """KEYCOUNT instruction - get key count"""
    def __init__(self):
        opcode_val = 0x45  # KEYCOUNT
        super().__init__("KEYCOUNT", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        count = cpu.keyboard.get_key_count()
        cpu.set_operand_value(operands[0], count)

class Keyclear(BaseInstruction):
    """KEYCLEAR instruction - clear keyboard buffer"""
    def __init__(self):
        opcode_val = 0x46  # KEYCLEAR
        super().__init__("KEYCLEAR", opcode_val)
    
    def execute(self, cpu):
        cpu.keyboard.clear_buffer()

class Keyctrl(BaseInstruction):
    """KEYCTRL instruction - keyboard control"""
    def __init__(self):
        opcode_val = 0x47  # KEYCTRL
        super().__init__("KEYCTRL", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        control = cpu.get_operand_value(operands[0])
        cpu.keyboard.control(control)

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
        operands = cpu.parse_operands(1)
        max_value = cpu.get_operand_value(operands[0])
        if max_value == 0:
            random_value = 0
        else:
            # Simple linear congruential generator
            cpu.rng_seed = (cpu.rng_seed * 1103515245 + 12345) & 0xFFFF
            random_value = cpu.rng_seed % (max_value + 1)
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

# BCD operations
class Sed(BaseInstruction):
    """SED instruction - set decimal flag"""
    def __init__(self):
        opcode_val = 0x4B  # SED
        super().__init__("SED", opcode_val)
    
    def execute(self, cpu):
        cpu.decimal_mode = True

class Cld(BaseInstruction):
    """CLD instruction - clear decimal flag"""
    def __init__(self):
        opcode_val = 0x4C  # CLD
        super().__init__("CLD", opcode_val)
    
    def execute(self, cpu):
        cpu.decimal_mode = False

class Cla(BaseInstruction):
    """CLA instruction - clear auxiliary carry"""
    def __init__(self):
        opcode_val = 0x4D  # CLA
        super().__init__("CLA", opcode_val)
    
    def execute(self, cpu):
        cpu.aux_carry = False

class Bcda(BaseInstruction):
    """BCDA instruction - BCD add with carry"""
    def __init__(self):
        opcode_val = 0x4E  # BCDA
        super().__init__("BCDA", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        dest_value = cpu.get_operand_value(operands[0])
        source_value = cpu.get_operand_value(operands[1])
        
        if cpu.decimal_mode:
            result = cpu.bcd_add(dest_value, source_value)
        else:
            result = dest_value + source_value + (1 if cpu.aux_carry else 0)
        
        cpu.set_operand_value(operands[0], result)

class Bcds(BaseInstruction):
    """BCDS instruction - BCD subtract with carry"""
    def __init__(self):
        opcode_val = 0x4F  # BCDS
        super().__init__("BCDS", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        dest_value = cpu.get_operand_value(operands[0])
        source_value = cpu.get_operand_value(operands[1])
        
        if cpu.decimal_mode:
            result = cpu.bcd_subtract(dest_value, source_value)
        else:
            result = dest_value - source_value - (1 if cpu.aux_carry else 0)
        
        cpu.set_operand_value(operands[0], result)

class Bcdcmp(BaseInstruction):
    """BCDCMP instruction - BCD compare"""
    def __init__(self):
        opcode_val = 0x50  # BCDCMP
        super().__init__("BCDCMP", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        dest_value = cpu.get_operand_value(operands[0])
        source_value = cpu.get_operand_value(operands[1])
        
        if cpu.decimal_mode:
            result = cpu.bcd_compare(dest_value, source_value)
        else:
            result = dest_value - source_value
        
        cpu._set_flags_16bit(result, result)

class Bcd2bin(BaseInstruction):
    """BCD2BIN instruction - BCD to binary"""
    def __init__(self):
        opcode_val = 0x51  # BCD2BIN
        super().__init__("BCD2BIN", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        bcd_value = cpu.get_operand_value(operands[0])
        binary_value = cpu.bcd_to_binary(bcd_value)
        cpu.set_operand_value(operands[0], binary_value)

class Bin2bcd(BaseInstruction):
    """BIN2BCD instruction - binary to BCD"""
    def __init__(self):
        opcode_val = 0x52  # BIN2BCD
        super().__init__("BIN2BCD", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        binary_value = cpu.get_operand_value(operands[0])
        bcd_value = cpu.binary_to_bcd(binary_value)
        cpu.set_operand_value(operands[0], bcd_value)

class Bcdadd(BaseInstruction):
    """BCDADD instruction - BCD add immediate"""
    def __init__(self):
        opcode_val = 0x53  # BCDADD
        super().__init__("BCDADD", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        dest_value = cpu.get_operand_value(operands[0])
        imm_value = cpu.get_operand_value(operands[1])
        
        if cpu.decimal_mode:
            result = cpu.bcd_add(dest_value, imm_value)
        else:
            result = dest_value + imm_value
        
        cpu.set_operand_value(operands[0], result)

class Bcdsub(BaseInstruction):
    """BCDSUB instruction - BCD subtract immediate"""
    def __init__(self):
        opcode_val = 0x54  # BCDSUB
        super().__init__("BCDSUB", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        dest_value = cpu.get_operand_value(operands[0])
        imm_value = cpu.get_operand_value(operands[1])
        
        if cpu.decimal_mode:
            result = cpu.bcd_subtract(dest_value, imm_value)
        else:
            result = dest_value - imm_value
        
        cpu.set_operand_value(operands[0], result)

# Sprite operations
class Spblit(BaseInstruction):
    """SPBLIT instruction - blit sprite"""
    def __init__(self):
        opcode_val = 0x55  # SPBLIT
        super().__init__("SPBLIT", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        sprite_id = cpu.get_operand_value(operands[0])
        cpu.gfx.blit_sprite(sprite_id)

class Spblitall(BaseInstruction):
    """SPBLITALL instruction - blit all sprites"""
    def __init__(self):
        opcode_val = 0x56  # SPBLITALL
        super().__init__("SPBLITALL", opcode_val)
    
    def execute(self, cpu):
        cpu.gfx.blit_all_sprites()

# Sound operations
class Splay(BaseInstruction):
    """SPLAY instruction - play sound"""
    def __init__(self):
        opcode_val = 0x57  # SPLAY
        super().__init__("SPLAY", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        sound_id = cpu.get_operand_value(operands[0])
        cpu.sound.play(sound_id)

class Sstop(BaseInstruction):
    """SSTOP instruction - stop sound"""
    def __init__(self):
        opcode_val = 0x58  # SSTOP
        super().__init__("SSTOP", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        sound_id = cpu.get_operand_value(operands[0])
        cpu.sound.stop(sound_id)

class Strig(BaseInstruction):
    """STRIG instruction - trigger sound effect"""
    def __init__(self):
        opcode_val = 0x59  # STRIG
        super().__init__("STRIG", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(1)
        effect_id = cpu.get_operand_value(operands[0])
        cpu.sound.trigger_effect(effect_id)

# Loop operation
class Loop(BaseInstruction):
    """LOOP instruction"""
    def __init__(self):
        opcode_val = 0x5A  # LOOP
        super().__init__("LOOP", opcode_val)
    
    def execute(self, cpu):
        operands = cpu.parse_operands(2)
        # Decrement counter register
        counter_value = cpu.get_operand_value(operands[0]) - 1
        cpu.set_operand_value(operands[0], counter_value)
        
        # If counter != 0, branch back
        if counter_value != 0:
            offset = cpu.get_operand_value(operands[1])
            if offset & 0x8000:  # Sign extend
                offset -= 0x10000
            cpu.pc = (cpu.pc + offset) & 0xFFFF
            cpu.invalidate_prefetch()

# Register/special references (for direct access)
# These are handled by the assembler, not individual instructions

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
        Srolx(),    # 0x34
        Sroly(),    # 0x35
        Srotl(),    # 0x36
        Srotr(),    # 0x37
        Sshftx(),   # 0x38
        Sshfty(),   # 0x39
        Sflipx(),   # 0x3A
        Sflipy(),   # 0x3B
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
    ]
    
    # Create the dispatch table
    table = {}
    for instruction in instructions:
        table[instruction.opcode] = instruction
    
    return table
