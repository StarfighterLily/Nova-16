class BaseInstruction:
    """Base class for all instructions"""
    def __init__(self, name, opcode):
        self.name = name
        self.opcode = opcode
    
    def __repr__(self):
        return self.name.lower()
    
    def execute(self, cpu):
        raise NotImplementedError("Subclasses must implement execute method")

# Control Flow Instructions
class Hlt(BaseInstruction):
    def __init__(self):
        super().__init__("HLT", 0x00)
    
    def execute(self, cpu):
        cpu.halted = True

class Nop(BaseInstruction):
    def __init__(self):
        super().__init__("NOP", 0xFF)
    
    def execute(self, cpu):
        pass

class Ret(BaseInstruction):
    def __init__(self):
        super().__init__("RET", 0x01)
    
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
        super().__init__("IRET", 0x02)
    
    def execute(self, cpu):
        # Check stack bounds before reading PC
        if cpu.Pregisters[8] >= 0xFFFF:  # Stack underflow check
            raise RuntimeError(f"Stack underflow: SP=0x{cpu.Pregisters[8]:04X}")
        
        # Restore PC first (it was pushed last)
        pc_value = cpu.memory.read_word(cpu.Pregisters[8])
        cpu.pc = pc_value
        sp = int(cpu.Pregisters[8])
        sp = (sp + 2) & 0xFFFF
        cpu.Pregisters[8] = sp
        
        # Check stack bounds before reading flags
        if cpu.Pregisters[8] >= 0xFFFF:  # Stack underflow check
            raise RuntimeError(f"Stack underflow: SP=0x{cpu.Pregisters[8]:04X}")
        
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
        super().__init__("CLI", 0x03)
    
    def execute(self, cpu):
        cpu.flags[5] = 0  # Clear interrupt flag

class Sti(BaseInstruction):
    def __init__(self):
        super().__init__("STI", 0x04)
    
    def execute(self, cpu):
        cpu.flags[5] = 1  # Set interrupt flag

# Data Movement Instructions
class MovRegReg(BaseInstruction):
    def __init__(self):
        super().__init__("MOV", 0x05)
    
    def execute(self, cpu):
        reg1_code = cpu.fetch()
        reg2_code = cpu.fetch()
        idx1, type1 = cpu.reg_index(reg1_code)
        idx2, type2 = cpu.reg_index(reg2_code)
        
        # Get value from source register
        source_value = cpu._get_operand_value(type2, idx2)
        
        # Handle special cases for register type combinations
        if type1 == 'R':
            if type2 == ':P':
                cpu.Rregisters[idx1] = int(cpu.Pregisters[idx2]) & 0xFF
            elif type2 == 'P:':
                cpu.Rregisters[idx1] = int(cpu.Pregisters[idx2]) >> 8 & 0xFF
            else:
                cpu.Rregisters[idx1] = int(source_value) & 0xFF
        elif type1 == 'P':
            if type2 == 'R':
                cpu.Pregisters[idx1] = int(source_value) & 0xFFFF
            else:
                cpu.Pregisters[idx1] = int(source_value) & 0xFFFF
        elif type1 == 'V':
            if type2 == ':P':
                cpu.gfx.Vregisters[idx1] = int(cpu.Pregisters[idx2]) & 0xFF
            elif type2 == 'P:':
                cpu.gfx.Vregisters[idx1] = int(cpu.Pregisters[idx2]) >> 8 & 0xFF
            else:
                cpu.gfx.Vregisters[idx1] = int(source_value) & 0xFF
        elif type1 in ['TT', 'TM', 'TC', 'TS', 'VL']:
            # Timer and graphics layer registers can receive from any source
            cpu._set_operand_value(type1, idx1, source_value)

class MovRegImm8(BaseInstruction):
    def __init__(self):
        super().__init__("MOV", 0x06)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        imm8 = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        if typ == 'R':
            cpu.Rregisters[idx] = int(imm8) & 0xFF
        elif typ == 'P':
            cpu.Pregisters[idx] = int(imm8) & 0xFFFF
        elif typ == 'V':
            cpu.gfx.Vregisters[idx] = int(imm8) & 0xFF
        elif typ in ['TT', 'TM', 'TC', 'TS', 'VL']:
            cpu._set_operand_value(typ, idx, imm8)

class MovRegImm16(BaseInstruction):
    def __init__(self):
        super().__init__("MOV", 0x07)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        imm16 = cpu.fetch(2)
        idx, typ = cpu.reg_index(reg_code)
        if typ == 'P':
            cpu.Pregisters[idx] = int(imm16) & 0xFFFF
        elif typ in ['TT', 'TM', 'TC', 'TS', 'VL']:
            cpu._set_operand_value(typ, idx, imm16)

class MovRegRegIndir(BaseInstruction):
    def __init__(self):
        super().__init__("MOV", 0x08)
    
    def execute(self, cpu):
        reg1_code = cpu.fetch()
        reg2_code = cpu.fetch()
        idx1, type1 = cpu.reg_index(reg1_code)
        idx2, type2 = cpu.reg_index(reg2_code)
        
        # Always read a word (2 bytes) from memory when dereferencing a pointer
        # The target register type determines how much of the value to use
        bytes_to_read = 2
        
        if type2 == 'Rind':
            data = cpu.memory.read(cpu.Rregisters[idx2], bytes_to_read)
        elif type2 == 'Pind':
            data = cpu.memory.read(cpu.Pregisters[idx2], bytes_to_read)
        elif type2 == 'Vind':
            data = cpu.memory.read(cpu.gfx.Vregisters[idx2], bytes_to_read)
        else:
            data = [0, 0]  # Default to 2 bytes of zeros

        # Always construct the full 16-bit value from memory
        val = (int(data[0]) << 8) | int(data[1])
            
        if type1 == 'R':
            cpu.Rregisters[idx1] = val & 0xFF  # Truncate to 8 bits for R registers
        elif type1 == 'P':
            cpu.Pregisters[idx1] = val & 0xFFFF  # Full 16 bits for P registers

class MovRegRegIndex(BaseInstruction):
    def __init__(self):
        super().__init__("MOV", 0x09)
    
    def execute(self, cpu):
        reg1_code = cpu.fetch()
        reg2_code = cpu.fetch()
        offset = cpu.fetch()  # Fetch the offset byte
        idx1, type1 = cpu.reg_index(reg1_code)
        idx2, type2 = cpu.reg_index(reg2_code)
        
        # Convert offset to signed 8-bit value - ensure int conversion
        offset = int(offset)  # Convert from numpy type to Python int
        signed_offset = offset if offset < 128 else offset - 256
        
        if type2 == 'Ridx':
            addr = (int(cpu.Rregisters[idx2]) + signed_offset) & 0xFFFF
            # For big-endian architecture, determine byte to read based on target register type
            if type1 == 'R':  # 8-bit target register
                # Read the low byte (addr+1) for 8-bit registers in big-endian
                val = cpu.memory.read(int(addr + 1), 1)[0]
            else:  # 16-bit target register
                # Read full 16-bit value for P registers
                val = cpu.memory.read(int(addr), 2)
                val = (val[0] << 8) | val[1]  # Combine bytes in big-endian order
        elif type2 == 'Pidx':
            addr = (int(cpu.Pregisters[idx2]) + signed_offset) & 0xFFFF
            # For big-endian architecture, determine byte to read based on target register type
            if type1 == 'R':  # 8-bit target register
                # Read the low byte (addr+1) for 8-bit registers in big-endian
                val = cpu.memory.read(int(addr + 1), 1)[0]
            else:  # 16-bit target register
                # Read full 16-bit value for P registers
                val = cpu.memory.read(int(addr), 2)
                val = (val[0] << 8) | val[1]  # Combine bytes in big-endian order
        elif type2 == 'SPidx':
            addr = (int(cpu.SP) + signed_offset) & 0xFFFF
            # For big-endian architecture, determine byte to read based on target register type
            if type1 == 'R':  # 8-bit target register
                # Read the low byte (addr+1) for 8-bit registers in big-endian
                val = cpu.memory.read(int(addr + 1), 1)[0]
            else:  # 16-bit target register
                # Read full 16-bit value for P registers
                val = cpu.memory.read(int(addr), 2)
                val = (val[0] << 8) | val[1]  # Combine bytes in big-endian order
        elif type2 == 'FPidx':
            addr = (int(cpu.FP) + signed_offset) & 0xFFFF
            # For big-endian architecture, determine byte to read based on target register type
            if type1 == 'R':  # 8-bit target register
                # Read the low byte (addr+1) for 8-bit registers in big-endian
                val = cpu.memory.read(int(addr + 1), 1)[0]
            else:  # 16-bit target register
                # Read full 16-bit value for P registers
                val = cpu.memory.read(int(addr), 2)
                val = (val[0] << 8) | val[1]  # Combine bytes in big-endian order
        elif type2 == 'Vidx':
            addr = (int(cpu.gfx.Vregisters[idx2]) + signed_offset) & 0xFFFF
            # For big-endian architecture, determine byte to read based on target register type
            if type1 == 'R':  # 8-bit target register
                # Read the low byte (addr+1) for 8-bit registers in big-endian
                val = cpu.memory.read(int(addr + 1), 1)[0]
            else:  # 16-bit target register
                # Read full 16-bit value for P registers
                val = cpu.memory.read(int(addr), 2)
                val = (val[0] << 8) | val[1]  # Combine bytes in big-endian order
        else:
            val = 0
            
        if type1 == 'R':
            cpu.Rregisters[idx1] = int(val) & 0xFF
        elif type1 == 'P':
            cpu.Pregisters[idx1] = int(val) & 0xFFFF

class MovRegIndirReg(BaseInstruction):
    def __init__(self):
        super().__init__("MOV", 0x0A)
    
    def execute(self, cpu):
        reg1_code = cpu.fetch()
        reg2_code = cpu.fetch()
        idx1, type1 = cpu.reg_index(reg1_code)
        idx2, type2 = cpu.reg_index(reg2_code)
        
        if type2 == 'R':
            val = cpu.Rregisters[idx2]
        elif type2 == 'P':
            val = cpu.Pregisters[idx2]
        elif type2 == 'V':
            val = cpu.gfx.Vregisters[idx2]
        else:
            val = 0

        val = int(val)

        if type1 == 'Rind':
            cpu.write_memory(cpu.Rregisters[idx1], val & 0xFF, 1)
        elif type1 == 'Pind':
            cpu.write_memory(cpu.Pregisters[idx1], val & 0xFFFF, 2)

class MovRegIndexReg(BaseInstruction):
    def __init__(self):
        super().__init__("MOV", 0x0B)
    
    def execute(self, cpu):
        reg1_code = cpu.fetch()
        index = cpu.fetch()
        reg2_code = cpu.fetch()
        idx1, type1 = cpu.reg_index(reg1_code)
        idx2, type2 = cpu.reg_index(reg2_code)
        
        # Convert offset to signed 8-bit value - ensure int conversion
        index = int(index)  # Convert from numpy type to Python int
        signed_offset = index if index < 128 else index - 256
        
        if type2 == 'R':
            val = cpu.Rregisters[idx2]
        elif type2 == 'P':
            val = cpu.Pregisters[idx2]
        elif type2 == 'V':
            val = cpu.gfx.Vregisters[idx2]
        else:
            val = 0
        
        val = int(val)

        if type1 == 'Ridx':
            addr = (int(cpu.Rregisters[idx1]) + signed_offset) & 0xFFFF
            cpu.write_memory(int(addr), int(val) & 0xFF, 1)
        elif type1 == 'Pidx':
            addr = (int(cpu.Pregisters[idx1]) + signed_offset) & 0xFFFF
            # For P registers, we need to determine if we're writing 8-bit or 16-bit based on source
            if type2 == 'P' or type2 == 'V':
                cpu.write_memory(int(addr), int(val) & 0xFFFF, 2)  # Write 16-bit for P/V sources
            else:
                cpu.write_memory(int(addr), int(val) & 0xFF, 1)    # Write 8-bit for R sources
        elif type1 == 'SPidx':
            addr = (int(cpu.SP) + signed_offset) & 0xFFFF
            # Determine write size based on source register type
            if type2 == 'P' or type2 == 'V':
                cpu.write_memory(int(addr), int(val) & 0xFFFF, 2)  # Write 16-bit for P/V sources
            else:
                cpu.write_memory(int(addr), int(val) & 0xFF, 1)    # Write 8-bit for R sources
        elif type1 == 'FPidx':
            addr = (int(cpu.FP) + signed_offset) & 0xFFFF
            # Determine write size based on source register type
            if type2 == 'P' or type2 == 'V':
                cpu.write_memory(int(addr), int(val) & 0xFFFF, 2)  # Write 16-bit for P/V sources
            else:
                cpu.write_memory(int(addr), int(val) & 0xFF, 1)    # Write 8-bit for R sources
        elif type1 == 'Vidx':
            addr = (int(cpu.gfx.Vregisters[idx1]) + signed_offset) & 0xFFFF
            # Determine write size based on source register type
            if type2 == 'P' or type2 == 'V':
                cpu.write_memory(int(addr), int(val) & 0xFFFF, 2)  # Write 16-bit for P/V sources
            else:
                cpu.write_memory(int(addr), int(val) & 0xFF, 1)    # Write 8-bit for R sources

class MovRegIndirImm8(BaseInstruction):
    def __init__(self):
        super().__init__("MOV", 0x0C)

    def execute(self, cpu):
        reg_code = cpu.fetch()
        imm8 = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)

        if typ == 'Rind':
            cpu.write_memory(cpu.Rregisters[idx], imm8 & 0xFF, 1)
        elif typ == 'Pind':
            cpu.write_memory(cpu.Pregisters[idx], imm8 & 0xFF, 1)

class MovRegIndexImm8(BaseInstruction):
    def __init__(self):
        super().__init__("MOV", 0x0D)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        index = cpu.fetch()
        data = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        # Convert offset to signed 8-bit value - ensure int conversion
        index = int(index)  # Convert from numpy type to Python int
        signed_offset = index if index < 128 else index - 256
        
        if typ == 'Ridx':
            addr = (int(cpu.Rregisters[idx]) + signed_offset) & 0xFFFF
            cpu.write_memory(addr, data & 0xFF, 1)
        elif typ == 'Pidx':
            addr = (int(cpu.Pregisters[idx]) + signed_offset) & 0xFFFF
            cpu.write_memory(addr, data & 0xFF, 1)
        elif typ == 'SPidx':
            addr = (int(cpu.SP) + signed_offset) & 0xFFFF
            cpu.write_memory(addr, data & 0xFF, 1)
        elif typ == 'FPidx':
            addr = (int(cpu.FP) + signed_offset) & 0xFFFF
            cpu.write_memory(addr, data & 0xFF, 1)

class MovRegIndirImm16(BaseInstruction):
    def __init__(self):
        super().__init__("MOV", 0x0E)

    def execute(self, cpu):
        reg_code = cpu.fetch()
        data = cpu.fetch(2)
        idx, typ = cpu.reg_index(reg_code)

        if typ == 'Rind':
            cpu.write_memory(cpu.Rregisters[idx], data & 0xFF, 1)
        elif typ == 'Pind':
            cpu.write_memory(cpu.Pregisters[idx], int(data) & 0xFFFF, 2)

class MovRegIndexImm16(BaseInstruction):
    def __init__(self):
        super().__init__("MOV", 0x0F)

    def execute(self, cpu):
        reg_code = cpu.fetch()
        index = cpu.fetch()
        imm16 = cpu.fetch(2)
        idx, typ = cpu.reg_index(reg_code)
        
        # Convert offset to signed 8-bit value - ensure int conversion
        index = int(index)  # Convert from numpy type to Python int
        signed_offset = index if index < 128 else index - 256
        
        if typ == 'Ridx':
            addr = (int(cpu.Rregisters[idx]) + signed_offset) & 0xFFFF
            cpu.write_memory(addr, imm16 & 0xFF, 1)
        elif typ == 'Pidx':
            addr = (int(cpu.Pregisters[idx]) + signed_offset) & 0xFFFF
            cpu.write_memory(addr, imm16 & 0xFFFF, 2)
        elif typ == 'SPidx':
            addr = (int(cpu.SP) + signed_offset) & 0xFFFF
            cpu.write_memory(addr, imm16 & 0xFFFF, 2)
        elif typ == 'FPidx':
            addr = (int(cpu.FP) + signed_offset) & 0xFFFF
            cpu.write_memory(addr, imm16 & 0xFFFF, 2)

class MovRegDirImm16(BaseInstruction):
    def __init__(self):
        super().__init__("MOV", 0x10)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        addr = cpu.fetch(2)
        idx, typ = cpu.reg_index(reg_code)
        
        # Determine bytes to read based on target register type
        bytes_to_read = 2 if typ == 'P' else 1
        
        data = cpu.memory.read(addr, bytes_to_read)
        
        if bytes_to_read == 1:
            val = int(data[0])
        else:
            val = (int(data[0]) << 8) | int(data[1])
            
        if typ == 'R':
            cpu.Rregisters[idx] = val & 0xFF
        elif typ == 'P':
            cpu.Pregisters[idx] = val & 0xFFFF
        elif typ == 'V':
            cpu.gfx.Vregisters[idx] = val & 0xFF

class MovDirImm16Reg(BaseInstruction):
    def __init__(self):
        super().__init__("MOV", 0x11)
    
    def execute(self, cpu):
        addr = cpu.fetch(2)
        reg_code = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        if typ == 'R':
            val = cpu.Rregisters[idx]
            cpu.write_memory(addr, val & 0xFF, 1)
        elif typ == 'P':
            val = cpu.Pregisters[idx]
            cpu.write_memory(addr, val & 0xFFFF, 2)
        elif typ == 'V':
            val = cpu.gfx.Vregisters[idx]
            cpu.write_memory(addr, val & 0xFF, 1)

# Arithmetic Instructions
class IncReg(BaseInstruction):
    def __init__(self):
        super().__init__("INC", 0x12)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        # Check if BCD mode is enabled
        if cpu.decimal_flag:
            # BCD increment
            original = cpu._get_operand_value(typ, idx)
            bcd_result, bcd_carry = cpu._bcd_add(original, 1)
            
            if typ == 'R':
                cpu.Rregisters[idx] = bcd_result & 0xFF
                cpu._set_flags_8bit_bcd(bcd_result, bcd_carry)
            elif typ == 'P':
                cpu.Pregisters[idx] = bcd_result & 0xFFFF
                cpu._set_flags_8bit_bcd(bcd_result & 0xFF, bcd_carry)
            elif typ == 'V':
                cpu.gfx.Vregisters[idx] = bcd_result & 0xFF
                cpu._set_flags_8bit_bcd(bcd_result, bcd_carry)
            elif typ in ['TT', 'TM', 'TC', 'TS']:
                cpu._set_operand_value(typ, idx, bcd_result & 0xFF)
                cpu._set_flags_8bit_bcd(bcd_result, bcd_carry)
        else:
            # Normal binary increment
            if typ == 'R':
                original = cpu.Rregisters[idx]
                raw_result = int(original) + 1
                result = raw_result & 0xFF
                cpu.Rregisters[idx] = result
                cpu._set_flags_8bit(result, raw_result)
            elif typ == 'P':
                original = cpu.Pregisters[idx]
                raw_result = int(original) + 1
                result = raw_result & 0xFFFF
                cpu.Pregisters[idx] = result
                cpu._set_flags_16bit(result, raw_result)
            elif typ == 'V':
                original = cpu.gfx.Vregisters[idx]
                raw_result = int(original) + 1
                result = raw_result & 0xFF
                cpu.gfx.Vregisters[idx] = result
                cpu._set_flags_8bit(result, raw_result)
            elif typ in ['TT', 'TM', 'TC', 'TS']:
                original = cpu._get_operand_value(typ, idx)
                raw_result = int(original) + 1
                result = raw_result & 0xFF
                cpu._set_operand_value(typ, idx, result)
                cpu._set_flags_8bit(result, raw_result)

class DecReg(BaseInstruction):
    def __init__(self):
        super().__init__("DEC", 0x13)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        # Check if BCD mode is enabled
        if cpu.decimal_flag:
            # BCD decrement
            original = cpu._get_operand_value(typ, idx)
            bcd_result, bcd_borrow = cpu._bcd_sub(original, 1)
            
            if typ == 'R':
                cpu.Rregisters[idx] = bcd_result & 0xFF
                cpu._set_flags_8bit_bcd(bcd_result, bcd_borrow)
            elif typ == 'P':
                cpu.Pregisters[idx] = bcd_result & 0xFFFF
                cpu._set_flags_8bit_bcd(bcd_result & 0xFF, bcd_borrow)
            elif typ == 'V':
                cpu.gfx.Vregisters[idx] = bcd_result & 0xFF
                cpu._set_flags_8bit_bcd(bcd_result, bcd_borrow)
            elif typ in ['TT', 'TM', 'TC', 'TS']:
                cpu._set_operand_value(typ, idx, bcd_result & 0xFF)
                cpu._set_flags_8bit_bcd(bcd_result, bcd_borrow)
        else:
            # Normal binary decrement
            if typ == 'R':
                original = cpu.Rregisters[idx]
                raw_result = int(original) - 1
                result = raw_result & 0xFF
                cpu.Rregisters[idx] = result
                cpu._set_flags_8bit(result, raw_result)
            elif typ == 'P':
                original = cpu.Pregisters[idx]
                raw_result = int(original) - 1
                result = raw_result & 0xFFFF
                cpu.Pregisters[idx] = result
                cpu._set_flags_16bit(result, raw_result)
            elif typ == 'V':
                original = cpu.gfx.Vregisters[idx]
                raw_result = int(original) - 1
                result = raw_result & 0xFF
                cpu.gfx.Vregisters[idx] = result
                cpu._set_flags_8bit(result, raw_result)
            elif typ in ['TT', 'TM', 'TC', 'TS']:
                original = cpu._get_operand_value(typ, idx)
                raw_result = int(original) - 1
                result = raw_result & 0xFF
                cpu._set_operand_value(typ, idx, result)
                cpu._set_flags_8bit(result, raw_result)

class AddRegReg(BaseInstruction):
    def __init__(self):
        super().__init__("ADD", 0x14)
    
    def execute(self, cpu):
        reg1_code = cpu.fetch()
        reg2_code = cpu.fetch()
        idx1, type1 = cpu.reg_index(reg1_code)
        idx2, type2 = cpu.reg_index(reg2_code)
        
        # Get operand values
        val1 = cpu._get_operand_value(type1, idx1)
        val2 = cpu._get_operand_value(type2, idx2)
        
        # Check if BCD mode is enabled
        if cpu.decimal_flag:
            # BCD arithmetic
            bcd_result, bcd_carry = cpu._bcd_add(val1, val2)
            result = bcd_result
            
            if type1 == 'R':
                cpu.Rregisters[idx1] = result & 0xFF
                cpu._set_flags_8bit_bcd(result, bcd_carry)
            elif type1 == 'P':
                # For 16-bit BCD, treat as two 8-bit BCD values
                cpu.Pregisters[idx1] = result & 0xFFFF
                cpu._set_flags_8bit_bcd(result & 0xFF, bcd_carry)  # Set flags based on low byte
            elif type1 == 'V':
                cpu.gfx.Vregisters[idx1] = result & 0xFF
                cpu._set_flags_8bit_bcd(result, bcd_carry)
            elif type1 in ['TT', 'TM', 'TC', 'TS']:
                cpu._set_operand_value(type1, idx1, result & 0xFF)
                cpu._set_flags_8bit_bcd(result, bcd_carry)
        else:
            # Normal binary arithmetic
            result = val1 + val2
            
            if type1 == 'R':
                cpu.Rregisters[idx1] = result & 0xFF
                cpu._set_flags_8bit(int(result) & 0xFF, result)
            elif type1 == 'P':
                cpu.Pregisters[idx1] = result & 0xFFFF
                cpu._set_flags_16bit(int(result) & 0xFFFF, result)
            elif type1 == 'V':
                cpu.gfx.Vregisters[idx1] = result & 0xFF
                cpu._set_flags_8bit(int(result) & 0xFF, result)
            elif type1 in ['TT', 'TM', 'TC', 'TS']:
                cpu._set_operand_value(type1, idx1, result & 0xFF)
                cpu._set_flags_8bit(int(result) & 0xFF, result)

class AddRegImm8(BaseInstruction):
    def __init__(self):
        super().__init__("ADD", 0x15)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        imm8 = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        # Check if BCD mode is enabled
        if cpu.decimal_flag:
            # BCD arithmetic
            original = cpu._get_operand_value(typ, idx)
            bcd_result, bcd_carry = cpu._bcd_add(original, imm8)
            
            if typ == 'R':
                cpu.Rregisters[idx] = bcd_result & 0xFF
                cpu._set_flags_8bit_bcd(bcd_result, bcd_carry)
            elif typ == 'P':
                cpu.Pregisters[idx] = bcd_result & 0xFFFF
                cpu._set_flags_8bit_bcd(bcd_result & 0xFF, bcd_carry)
            elif typ == 'V':
                cpu.gfx.Vregisters[idx] = bcd_result & 0xFF
                cpu._set_flags_8bit_bcd(bcd_result, bcd_carry)
            elif typ in ['TT', 'TM', 'TC', 'TS']:
                cpu._set_operand_value(typ, idx, bcd_result & 0xFF)
                cpu._set_flags_8bit_bcd(bcd_result, bcd_carry)
        else:
            # Normal binary arithmetic
            if typ == 'R':
                original = int(cpu.Rregisters[idx])
                imm8_val = int(imm8)
                result = original + imm8_val
                cpu.Rregisters[idx] = result & 0xFF
                cpu._set_flags_8bit(int(result) & 0xFF, result)
            elif typ == 'P':
                original = int(cpu.Pregisters[idx])
                imm8_val = int(imm8)
                result = original + imm8_val
                cpu.Pregisters[idx] = result & 0xFFFF
                cpu._set_flags_16bit(int(result) & 0xFFFF, result)
            elif typ == 'V':
                original = int(cpu.gfx.Vregisters[idx])
                imm8_val = int(imm8)
                result = original + imm8_val
                cpu.gfx.Vregisters[idx] = result & 0xFF
                cpu._set_flags_8bit(int(result) & 0xFF, result)
            elif typ in ['TT', 'TM', 'TC', 'TS']:
                original = cpu._get_operand_value(typ, idx)
                result = int(original + imm8)
                cpu._set_operand_value(typ, idx, result & 0xFF)
                cpu._set_flags_8bit(int(result) & 0xFF, result)

class AddRegImm16(BaseInstruction):
    def __init__(self):
        super().__init__("ADD", 0x16)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        imm16 = cpu.fetch(2)
        idx, typ = cpu.reg_index(reg_code)
        
        if typ == 'P':
            original = int(cpu.Pregisters[idx])
            result = original + imm16
            cpu.Pregisters[idx] = result & 0xFFFF
            cpu._set_flags_16bit(int(result) & 0xFFFF, result)

class SubRegReg(BaseInstruction):
    def __init__(self):
        super().__init__("SUB", 0x17)
    
    def execute(self, cpu):
        reg1_code = cpu.fetch()
        reg2_code = cpu.fetch()
        idx1, type1 = cpu.reg_index(reg1_code)
        idx2, type2 = cpu.reg_index(reg2_code)
        
        # Get operand values
        val1 = cpu._get_operand_value(type1, idx1)
        val2 = cpu._get_operand_value(type2, idx2)
        
        # Check if BCD mode is enabled
        if cpu.decimal_flag:
            # BCD arithmetic
            bcd_result, bcd_borrow = cpu._bcd_sub(val1, val2)
            result = bcd_result
            
            if type1 == 'R':
                cpu.Rregisters[idx1] = result & 0xFF
                cpu._set_flags_8bit_bcd(result, bcd_borrow)
            elif type1 == 'P':
                cpu.Pregisters[idx1] = result & 0xFFFF
                cpu._set_flags_8bit_bcd(result & 0xFF, bcd_borrow)
            elif type1 == 'V':
                cpu.gfx.Vregisters[idx1] = result & 0xFF
                cpu._set_flags_8bit_bcd(result, bcd_borrow)
            elif type1 in ['TT', 'TM', 'TC', 'TS']:
                cpu._set_operand_value(type1, idx1, result & 0xFF)
                cpu._set_flags_8bit_bcd(result, bcd_borrow)
        else:
            # Normal binary arithmetic
            result = val1 - val2
            
            if type1 == 'R':
                cpu.Rregisters[idx1] = result & 0xFF
                cpu._set_flags_8bit(int(result) & 0xFF, result)
            elif type1 == 'P':
                cpu.Pregisters[idx1] = result & 0xFFFF
                cpu._set_flags_16bit(int(result) & 0xFFFF, result)
            elif type1 == 'V':
                cpu.gfx.Vregisters[idx1] = result & 0xFF
                cpu._set_flags_8bit(int(result) & 0xFF, result)
            elif type1 in ['TT', 'TM', 'TC', 'TS']:
                cpu._set_operand_value(type1, idx1, result & 0xFF)
                cpu._set_flags_8bit(int(result) & 0xFF, result)

class SubRegImm8(BaseInstruction):
    def __init__(self):
        super().__init__("SUB", 0x18)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        imm8 = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        # Check if BCD mode is enabled
        if cpu.decimal_flag:
            # BCD arithmetic
            original = cpu._get_operand_value(typ, idx)
            bcd_result, bcd_borrow = cpu._bcd_sub(original, imm8)
            
            if typ == 'R':
                cpu.Rregisters[idx] = bcd_result & 0xFF
                cpu._set_flags_8bit_bcd(bcd_result, bcd_borrow)
            elif typ == 'P':
                cpu.Pregisters[idx] = bcd_result & 0xFFFF
                cpu._set_flags_8bit_bcd(bcd_result & 0xFF, bcd_borrow)
            elif typ == 'V':
                cpu.gfx.Vregisters[idx] = bcd_result & 0xFF
                cpu._set_flags_8bit_bcd(bcd_result, bcd_borrow)
            elif typ in ['TT', 'TM', 'TC', 'TS']:
                cpu._set_operand_value(typ, idx, bcd_result & 0xFF)
                cpu._set_flags_8bit_bcd(bcd_result, bcd_borrow)
        else:
            # Normal binary arithmetic
            if typ == 'R':
                original = int(cpu.Rregisters[idx])
                result = original - imm8
                cpu.Rregisters[idx] = result & 0xFF
                cpu._set_flags_8bit(int(result) & 0xFF, result)
            elif typ == 'P':
                original = int(cpu.Pregisters[idx])
                imm8_val = int(imm8)
                result = original - imm8_val
                cpu.Pregisters[idx] = result & 0xFFFF
                cpu._set_flags_16bit(int(result) & 0xFFFF, result)
            elif typ == 'V':
                original = int(cpu.gfx.Vregisters[idx])
                result = original - imm8
                cpu.gfx.Vregisters[idx] = result & 0xFF
                cpu._set_flags_8bit(int(result) & 0xFF, result)
            elif typ in ['TT', 'TM', 'TC', 'TS']:
                original = cpu._get_operand_value(typ, idx)
                result = original - imm8
                cpu._set_operand_value(typ, idx, result & 0xFF)
                cpu._set_flags_8bit(int(result) & 0xFF, result)

class SubRegImm16(BaseInstruction):
    def __init__(self):
        super().__init__("SUB", 0x19)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        imm16 = cpu.fetch(2)
        idx, typ = cpu.reg_index(reg_code)
        
        if typ == 'P':
            original = int(cpu.Pregisters[idx])
            result = original - imm16
            cpu.Pregisters[idx] = result & 0xFFFF
            cpu._set_flags_16bit(int(result) & 0xFFFF, result)

class MulRegReg(BaseInstruction):
    def __init__(self):
        super().__init__("MUL", 0x1A)
    
    def execute(self, cpu):
        reg1_code = cpu.fetch()
        reg2_code = cpu.fetch()
        idx1, type1 = cpu.reg_index(reg1_code)
        idx2, type2 = cpu.reg_index(reg2_code)
        
        # Get operand values
        val1 = cpu._get_operand_value(type1, idx1)
        val2 = cpu._get_operand_value(type2, idx2)
        
        result = val1 * val2
        
        if type1 == 'R':
            cpu.Rregisters[idx1] = result & 0xFF
            cpu._set_flags_8bit(int(result) & 0xFF, result)
        elif type1 == 'P':
            cpu.Pregisters[idx1] = result & 0xFFFF
            cpu._set_flags_16bit(int(result) & 0xFFFF, result)
        elif type1 == 'V':
            cpu.gfx.Vregisters[idx1] = result & 0xFF
            cpu._set_flags_8bit(int(result) & 0xFF, result)

class MulRegImm8(BaseInstruction):
    def __init__(self):
        super().__init__("MUL", 0x1B)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        imm8 = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        if typ == 'R':
            original = int(cpu.Rregisters[idx])
            result = original * imm8
            cpu.Rregisters[idx] = result & 0xFF
            cpu._set_flags_8bit(int(result) & 0xFF, result)
        elif typ == 'P':
            original = int(cpu.Pregisters[idx])
            result = original * imm8
            cpu.Pregisters[idx] = result & 0xFFFF
            cpu._set_flags_16bit(int(result) & 0xFFFF, result)

class MulRegImm16(BaseInstruction):
    def __init__(self):
        super().__init__("MUL", 0x1C)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        imm16 = cpu.fetch(2)
        idx, typ = cpu.reg_index(reg_code)
        
        if typ == 'P':
            original = int(cpu.Pregisters[idx])
            result = original * imm16
            cpu.Pregisters[idx] = result & 0xFFFF
            cpu._set_flags_16bit(int(result) & 0xFFFF, result)

class DivRegReg(BaseInstruction):
    def __init__(self):
        super().__init__("DIV", 0x1D)
    
    def execute(self, cpu):
        reg1_code = cpu.fetch()
        reg2_code = cpu.fetch()
        idx1, type1 = cpu.reg_index(reg1_code)
        idx2, type2 = cpu.reg_index(reg2_code)
        
        # Get operand values
        val1 = cpu._get_operand_value(type1, idx1)
        val2 = cpu._get_operand_value(type2, idx2)
        
        if val2 == 0:
            # Division by zero - set error flags
            cpu.flags[2] = 1  # Overflow flag
            return
        
        result = val1 // val2
        remainder = val1 % val2
        
        # Set quotient in first register
        if type1 == 'R':
            cpu.Rregisters[idx1] = result & 0xFF
            cpu._set_flags_8bit(int(result) & 0xFF, result)
        elif type1 == 'P':
            cpu.Pregisters[idx1] = result & 0xFFFF
            cpu._set_flags_16bit(int(result) & 0xFFFF, result)
        elif type1 == 'V':
            cpu.gfx.Vregisters[idx1] = result & 0xFF
            cpu._set_flags_8bit(int(result) & 0xFF, result)
        
        # Set remainder in second register
        if type2 == 'R':
            cpu.Rregisters[idx2] = remainder & 0xFF
        elif type2 == 'P':
            cpu.Pregisters[idx2] = remainder & 0xFFFF
        elif type2 == 'V':
            cpu.gfx.Vregisters[idx2] = remainder & 0xFF

class DivRegImm8(BaseInstruction):
    def __init__(self):
        super().__init__("DIV", 0x1E)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        imm8 = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        if imm8 == 0:
            cpu.flags[2] = 1  # Overflow flag for division by zero
            return
        
        if typ == 'R':
            original = int(cpu.Rregisters[idx])
            result = original // imm8
            remainder = original % imm8
            cpu.Rregisters[idx] = result & 0xFF
            cpu._set_flags_8bit(int(result) & 0xFF, result)
        elif typ == 'P':
            original = int(cpu.Pregisters[idx])
            result = original // imm8
            remainder = original % imm8
            cpu.Pregisters[idx] = result & 0xFFFF
            cpu._set_flags_16bit(int(result) & 0xFFFF, result)
        
        # Set remainder in P3
        cpu.Pregisters[3] = remainder & 0xFFFF

class DivRegImm16(BaseInstruction):
    def __init__(self):
        super().__init__("DIV", 0x1F)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        imm16 = cpu.fetch(2)
        idx, typ = cpu.reg_index(reg_code)
        
        if imm16 == 0:
            cpu.flags[2] = 1  # Overflow flag for division by zero
            return
        
        if typ == 'P':
            original = int(cpu.Pregisters[idx])
            result = original // imm16
            remainder = original % imm16
            cpu.Pregisters[idx] = result & 0xFFFF
            cpu._set_flags_16bit(int(result) & 0xFFFF, result)
        
        # Set remainder in P3
        cpu.Pregisters[3] = remainder & 0xFFFF

# Logical Instructions
class AndRegReg(BaseInstruction):
    def __init__(self):
        super().__init__("AND", 0x20)
    
    def execute(self, cpu):
        reg1_code = cpu.fetch()
        reg2_code = cpu.fetch()
        idx1, type1 = cpu.reg_index(reg1_code)
        idx2, type2 = cpu.reg_index(reg2_code)
        
        val1 = cpu._get_operand_value(type1, idx1)
        val2 = cpu._get_operand_value(type2, idx2)
        
        result = val1 & val2
        
        if type1 == 'R':
            cpu.Rregisters[idx1] = result & 0xFF
            cpu._set_flags_8bit(int(result) & 0xFF, result)
        elif type1 == 'P':
            cpu.Pregisters[idx1] = result & 0xFFFF
            cpu._set_flags_16bit(int(result) & 0xFFFF, result)
        elif type1 == 'V':
            cpu.gfx.Vregisters[idx1] = result & 0xFF
            cpu._set_flags_8bit(int(result) & 0xFF, result)

class AndRegImm8(BaseInstruction):
    def __init__(self):
        super().__init__("AND", 0x21)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        imm8 = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        if typ == 'R':
            original = cpu.Rregisters[idx]
            result = original & imm8
            cpu.Rregisters[idx] = result & 0xFF
            cpu._set_flags_8bit(int(result) & 0xFF, result)
        elif typ == 'P':
            original = cpu.Pregisters[idx]
            result = original & imm8
            cpu.Pregisters[idx] = result & 0xFFFF
            cpu._set_flags_16bit(int(result) & 0xFFFF, result)

class AndRegImm16(BaseInstruction):
    def __init__(self):
        super().__init__("AND", 0x22)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        imm16 = cpu.fetch(2)
        idx, typ = cpu.reg_index(reg_code)
        
        if typ == 'P':
            original = cpu.Pregisters[idx]
            result = original & imm16
            cpu.Pregisters[idx] = result & 0xFFFF
            cpu._set_flags_16bit(int(result) & 0xFFFF, result)

class OrRegReg(BaseInstruction):
    def __init__(self):
        super().__init__("OR", 0x23)
    
    def execute(self, cpu):
        reg1_code = cpu.fetch()
        reg2_code = cpu.fetch()
        idx1, type1 = cpu.reg_index(reg1_code)
        idx2, type2 = cpu.reg_index(reg2_code)
        
        val1 = cpu._get_operand_value(type1, idx1)
        val2 = cpu._get_operand_value(type2, idx2)
        
        result = val1 | val2
        
        if type1 == 'R':
            cpu.Rregisters[idx1] = result & 0xFF
            cpu._set_flags_8bit(int(result) & 0xFF, result)
        elif type1 == 'P':
            cpu.Pregisters[idx1] = result & 0xFFFF
            cpu._set_flags_16bit(int(result) & 0xFFFF, result)
        elif type1 == 'V':
            cpu.gfx.Vregisters[idx1] = result & 0xFF
            cpu._set_flags_8bit(int(result) & 0xFF, result)

class OrRegImm8(BaseInstruction):
    def __init__(self):
        super().__init__("OR", 0x24)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        imm8 = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        if typ == 'R':
            original = cpu.Rregisters[idx]
            result = original | imm8
            cpu.Rregisters[idx] = result & 0xFF
            cpu._set_flags_8bit(int(result) & 0xFF, result)
        elif typ == 'P':
            original = cpu.Pregisters[idx]
            result = original | imm8
            cpu.Pregisters[idx] = result & 0xFFFF
            cpu._set_flags_16bit(int(result) & 0xFFFF, result)

class OrRegImm16(BaseInstruction):
    def __init__(self):
        super().__init__("OR", 0x25)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        imm16 = cpu.fetch(2)
        idx, typ = cpu.reg_index(reg_code)
        
        if typ == 'P':
            original = cpu.Pregisters[idx]
            result = original | imm16
            cpu.Pregisters[idx] = result & 0xFFFF
            cpu._set_flags_16bit(int(result) & 0xFFFF, result)

class XorRegReg(BaseInstruction):
    def __init__(self):
        super().__init__("XOR", 0x26)
    
    def execute(self, cpu):
        reg1_code = cpu.fetch()
        reg2_code = cpu.fetch()
        idx1, type1 = cpu.reg_index(reg1_code)
        idx2, type2 = cpu.reg_index(reg2_code)
        
        val1 = cpu._get_operand_value(type1, idx1)
        val2 = cpu._get_operand_value(type2, idx2)
        
        result = val1 ^ val2
        
        if type1 == 'R':
            cpu.Rregisters[idx1] = result & 0xFF
            cpu._set_flags_8bit(int(result) & 0xFF, result)
        elif type1 == 'P':
            cpu.Pregisters[idx1] = result & 0xFFFF
            cpu._set_flags_16bit(int(result) & 0xFFFF, result)
        elif type1 == 'V':
            cpu.gfx.Vregisters[idx1] = result & 0xFF
            cpu._set_flags_8bit(int(result) & 0xFF, result)

class XorRegImm8(BaseInstruction):
    def __init__(self):
        super().__init__("XOR", 0x27)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        imm8 = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        if typ == 'R':
            original = cpu.Rregisters[idx]
            result = original ^ imm8
            cpu.Rregisters[idx] = result & 0xFF
            cpu._set_flags_8bit(int(result) & 0xFF, result)
        elif typ == 'P':
            original = cpu.Pregisters[idx]
            result = original ^ imm8
            cpu.Pregisters[idx] = result & 0xFFFF
            cpu._set_flags_16bit(int(result) & 0xFFFF, result)

class XorRegImm16(BaseInstruction):
    def __init__(self):
        super().__init__("XOR", 0x28)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        imm16 = cpu.fetch(2)
        idx, typ = cpu.reg_index(reg_code)
        
        if typ == 'P':
            original = cpu.Pregisters[idx]
            result = original ^ imm16
            cpu.Pregisters[idx] = result & 0xFFFF
            cpu._set_flags_16bit(int(result) & 0xFFFF, result)

class NotReg(BaseInstruction):
    def __init__(self):
        super().__init__("NOT", 0x29)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        if typ == 'R':
            original = cpu.Rregisters[idx]
            result = (~original) & 0xFF
            cpu.Rregisters[idx] = result
            cpu._set_flags_8bit(result, result)
        elif typ == 'P':
            original = cpu.Pregisters[idx]
            result = (~original) & 0xFFFF
            cpu.Pregisters[idx] = result
            cpu._set_flags_16bit(result, result)
        elif typ == 'V':
            original = cpu.gfx.Vregisters[idx]
            result = (~original) & 0xFF
            cpu.gfx.Vregisters[idx] = result
            cpu._set_flags_8bit(result, result)

# Bit Shift Instructions
class ShlReg(BaseInstruction):
    def __init__(self):
        super().__init__("SHL", 0x2A)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        if typ == 'R':
            original = cpu.Rregisters[idx]
            result = (original << 1) & 0xFF
            cpu.Rregisters[idx] = result
            # Set carry flag if bit was shifted out
            cpu.flags[6] = (original & 0x80) >> 7
            cpu._set_flags_8bit(result, result)
        elif typ == 'P':
            original = cpu.Pregisters[idx]
            result = (original << 1) & 0xFFFF
            cpu.Pregisters[idx] = result
            # Set carry flag if bit was shifted out
            cpu.flags[6] = (original & 0x8000) >> 15
            cpu._set_flags_16bit(result, result)
        elif typ == 'V':
            original = cpu.gfx.Vregisters[idx]
            result = (original << 1) & 0xFF
            cpu.gfx.Vregisters[idx] = result
            cpu.flags[6] = (original & 0x80) >> 7
            cpu._set_flags_8bit(result, result)

class ShrReg(BaseInstruction):
    def __init__(self):
        super().__init__("SHR", 0x2B)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        if typ == 'R':
            original = cpu.Rregisters[idx]
            result = original >> 1
            cpu.Rregisters[idx] = result
            # Set carry flag if bit was shifted out
            cpu.flags[6] = original & 0x01
            cpu._set_flags_8bit(result, result)
        elif typ == 'P':
            original = cpu.Pregisters[idx]
            result = original >> 1
            cpu.Pregisters[idx] = result
            # Set carry flag if bit was shifted out
            cpu.flags[6] = original & 0x01
            cpu._set_flags_16bit(result, result)
        elif typ == 'V':
            original = cpu.gfx.Vregisters[idx]
            result = original >> 1
            cpu.gfx.Vregisters[idx] = result
            cpu.flags[6] = original & 0x01
            cpu._set_flags_8bit(result, result)

class RolReg(BaseInstruction):
    def __init__(self):
        super().__init__("ROL", 0x2C)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        if typ == 'R':
            original = cpu.Rregisters[idx]
            result = ((original << 1) | (original >> 7)) & 0xFF
            cpu.Rregisters[idx] = result
            cpu.flags[6] = (original & 0x80) >> 7
            cpu._set_flags_8bit(result, result)
        elif typ == 'P':
            original = cpu.Pregisters[idx]
            result = ((original << 1) | (original >> 15)) & 0xFFFF
            cpu.Pregisters[idx] = result
            cpu.flags[6] = (original & 0x8000) >> 15
            cpu._set_flags_16bit(result, result)

class RorReg(BaseInstruction):
    def __init__(self):
        super().__init__("ROR", 0x2D)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        if typ == 'R':
            original = cpu.Rregisters[idx]
            result = ((original >> 1) | (original << 7)) & 0xFF
            cpu.Rregisters[idx] = result
            cpu.flags[6] = original & 0x01
            cpu._set_flags_8bit(result, result)
        elif typ == 'P':
            original = cpu.Pregisters[idx]
            result = ((original >> 1) | (original << 15)) & 0xFFFF
            cpu.Pregisters[idx] = result
            cpu.flags[6] = original & 0x01
            cpu._set_flags_16bit(result, result)

class PushReg(BaseInstruction):
    def __init__(self):
        super().__init__("PUSH", 0x2E)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        if typ == 'R':
            val = cpu.Rregisters[idx]
        elif typ == 'P':
            val = cpu.Pregisters[idx]
        elif typ == 'V':
            val = cpu.gfx.Vregisters[idx]
        else:
            val = 0
        
        # Check stack bounds before writing
        sp = int(cpu.Pregisters[8])
        if sp <= 0x0120:  # Stack overflow check (protect interrupt vectors)
            raise RuntimeError(f"Stack overflow: SP=0x{sp:04X}")
        
        # Push to stack in memory using standardized pattern
        sp = (sp - 2) & 0xFFFF
        cpu.Pregisters[8] = sp
        cpu.memory.write_word(cpu.Pregisters[8], val)

class PopReg(BaseInstruction):
    def __init__(self):
        super().__init__("POP", 0x2F)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        # Check stack bounds before reading
        if cpu.Pregisters[8] >= 0xFFFF:  # Stack underflow check
            raise RuntimeError(f"Stack underflow: SP=0x{cpu.Pregisters[8]:04X}")
        
        # Pop from stack in memory
        val = cpu.memory.read_word(cpu.Pregisters[8])
        
        # Use standardized SP manipulation
        sp = int(cpu.Pregisters[8])
        sp = (sp + 2) & 0xFFFF
        cpu.Pregisters[8] = sp
        
        # Proper type conversion for register assignment
        if typ == 'R':
            cpu.Rregisters[idx] = int(val) & 0xFF
        elif typ == 'P':
            cpu.Pregisters[idx] = int(val) & 0xFFFF
        elif typ == 'V':
            cpu.gfx.Vregisters[idx] = int(val) & 0xFF

class PushF(BaseInstruction):
    def __init__(self):
        super().__init__("PUSHF", 0x30)
    
    def execute(self, cpu):
        # Convert flags array to a single value
        flags_val = 0
        for i in range(12):
            if int(cpu._flags[i]) != 0:
                flags_val |= (1 << i)
        
        # Check stack bounds before writing
        sp = int(cpu.Pregisters[8])
        if sp <= 0x0120:  # Stack overflow check (protect interrupt vectors)
            raise RuntimeError(f"Stack overflow: SP=0x{sp:04X}")
        
        # Push to stack in memory using standardized pattern
        sp = (sp - 2) & 0xFFFF
        cpu.Pregisters[8] = sp
        cpu.memory.write_word(cpu.Pregisters[8], flags_val)

class PopF(BaseInstruction):
    def __init__(self):
        super().__init__("POPF", 0x31)
    
    def execute(self, cpu):
        # Check stack bounds before reading
        if cpu.Pregisters[8] >= 0xFFFF:  # Stack underflow check
            raise RuntimeError(f"Stack underflow: SP=0x{cpu.Pregisters[8]:04X}")
        
        # Pop flags from stack in memory
        flags_val = cpu.memory.read_word(cpu.Pregisters[8])
        
        # Use standardized SP manipulation
        sp = int(cpu.Pregisters[8])
        sp = (sp + 2) & 0xFFFF
        cpu.Pregisters[8] = sp
        
        # Convert single value back to flags array with proper type conversion
        for i in range(12):
            bit_set = (flags_val >> i) & 1
            flag_value = 1 if bit_set else 0
            cpu._flags[i] = int(flag_value) & 0xFF

# Additional Stack Instructions
class PushA(BaseInstruction):
    def __init__(self):
        super().__init__("PUSHA", 0x32)
    
    def execute(self, cpu):
        # Push all R registers to stack in memory
        for i in range(10):
            # Check stack bounds before writing
            sp = int(cpu.Pregisters[8])
            if sp <= 0x0120:  # Stack overflow check (protect interrupt vectors)
                raise RuntimeError(f"Stack overflow: SP=0x{sp:04X}")
            
            # Use standardized SP manipulation
            sp = (sp - 2) & 0xFFFF
            cpu.Pregisters[8] = sp
            cpu.memory.write_word(cpu.Pregisters[8], cpu.Rregisters[i])

class PopA(BaseInstruction):
    def __init__(self):
        super().__init__("POPA", 0x33)
    
    def execute(self, cpu):
        # Pop all R registers from stack in memory in reverse order
        for i in range(9, -1, -1):
            # Check stack bounds before reading
            if cpu.Pregisters[8] >= 0xFFFF:  # Stack underflow check
                raise RuntimeError(f"Stack underflow: SP=0x{cpu.Pregisters[8]:04X}")
            
            # Proper type conversion to avoid numpy overflow
            value = int(cpu.memory.read_word(cpu.Pregisters[8])) & 0xFF
            cpu.Rregisters[i] = value
            
            # Use standardized SP manipulation
            sp = int(cpu.Pregisters[8])
            sp = (sp + 2) & 0xFFFF
            cpu.Pregisters[8] = sp

# Jump Instructions
class JmpImm16(BaseInstruction):
    def __init__(self):
        super().__init__("JMP", 0x34)
    
    def execute(self, cpu):
        addr = cpu.fetch(2)
        cpu.pc = addr
        # Invalidate prefetch buffer after jump
        cpu.invalidate_prefetch()

class JmpReg(BaseInstruction):
    def __init__(self):
        super().__init__("JMP", 0x35)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        if typ == 'P':
            cpu.pc = cpu.Pregisters[idx]
        elif typ == 'R':
            cpu.pc = cpu.Rregisters[idx]
        # Invalidate prefetch buffer after jump
        cpu.invalidate_prefetch()

class JzImm16(BaseInstruction):
    def __init__(self):
        super().__init__("JZ", 0x36)
    
    def execute(self, cpu):
        addr = cpu.fetch(2)
        if cpu.flags[7]:  # Zero flag
            cpu.pc = addr

class JzReg(BaseInstruction):
    def __init__(self):
        super().__init__("JZ", 0x37)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        if cpu.flags[7]:  # Zero flag
            if typ == 'P':
                cpu.pc = cpu.Pregisters[idx]
            elif typ == 'R':
                cpu.pc = cpu.Rregisters[idx]

class JnzImm16(BaseInstruction):
    def __init__(self):
        super().__init__("JNZ", 0x38)
    
    def execute(self, cpu):
        addr = cpu.fetch(2)
        if not cpu.flags[7]:  # Zero flag not set
            cpu.pc = addr

class JnzReg(BaseInstruction):
    def __init__(self):
        super().__init__("JNZ", 0x39)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        if not cpu.flags[7]:  # Zero flag not set
            if typ == 'P':
                cpu.pc = cpu.Pregisters[idx]
            elif typ == 'R':
                cpu.pc = cpu.Rregisters[idx]

class JoImm16(BaseInstruction):
    def __init__(self):
        super().__init__("JO", 0x3A)
    
    def execute(self, cpu):
        addr = cpu.fetch(2)
        if cpu.flags[2]:  # Overflow flag set
            cpu.pc = addr

class JoReg(BaseInstruction):
    def __init__(self):
        super().__init__("JO", 0x3B)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        if cpu.flags[2]:  # Overflow flag set
            if typ == 'P':
                cpu.pc = cpu.Pregisters[idx]
            elif typ == 'R':
                cpu.pc = cpu.Rregisters[idx]

class JnoImm16(BaseInstruction):
    def __init__(self):
        super().__init__("JNO", 0x3C)
    
    def execute(self, cpu):
        addr = cpu.fetch(2)
        if not cpu.flags[2]:  # Overflow flag not set
            cpu.pc = addr

class JnoReg(BaseInstruction):
    def __init__(self):
        super().__init__("JNO", 0x3D)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        if not cpu.flags[2]:  # Overflow flag not set
            if typ == 'P':
                cpu.pc = cpu.Pregisters[idx]
            elif typ == 'R':
                cpu.pc = cpu.Rregisters[idx]

class JcImm16(BaseInstruction):
    def __init__(self):
        super().__init__("JC", 0x3E)
    
    def execute(self, cpu):
        addr = cpu.fetch(2)
        if cpu.flags[6]:  # Carry flag set
            cpu.pc = addr

class JcReg(BaseInstruction):
    def __init__(self):
        super().__init__("JC", 0x3F)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        if cpu.flags[6]:  # Carry flag set
            if typ == 'P':
                cpu.pc = cpu.Pregisters[idx]
            elif typ == 'R':
                cpu.pc = cpu.Rregisters[idx]

class JncImm16(BaseInstruction):
    def __init__(self):
        super().__init__("JNC", 0x40)
    
    def execute(self, cpu):
        addr = cpu.fetch(2)
        if not cpu.flags[6]:  # Carry flag not set
            cpu.pc = addr

class JncReg(BaseInstruction):
    def __init__(self):
        super().__init__("JNC", 0x41)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        if not cpu.flags[6]:  # Carry flag not set
            if typ == 'P':
                cpu.pc = cpu.Pregisters[idx]
            elif typ == 'R':
                cpu.pc = cpu.Rregisters[idx]

class JsImm16(BaseInstruction):
    def __init__(self):
        super().__init__("JS", 0x42)
    
    def execute(self, cpu):
        addr = cpu.fetch(2)
        if cpu.flags[1]:  # Sign flag set
            cpu.pc = addr

class JsReg(BaseInstruction):
    def __init__(self):
        super().__init__("JS", 0x43)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        if cpu.flags[1]:  # Sign flag set
            if typ == 'P':
                cpu.pc = cpu.Pregisters[idx]
            elif typ == 'R':
                cpu.pc = cpu.Rregisters[idx]

class JnsImm16(BaseInstruction):
    def __init__(self):
        super().__init__("JNS", 0x44)
    
    def execute(self, cpu):
        addr = cpu.fetch(2)
        if not cpu.flags[1]:  # Sign flag not set
            cpu.pc = addr

class JnsReg(BaseInstruction):
    def __init__(self):
        super().__init__("JNS", 0x45)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        if not cpu.flags[1]:  # Sign flag not set
            if typ == 'P':
                cpu.pc = cpu.Pregisters[idx]
            elif typ == 'R':
                cpu.pc = cpu.Rregisters[idx]

# Branch Instructions (relative jumps)
class BrImm8(BaseInstruction):
    def __init__(self):
        super().__init__("BR", 0x46)
    
    def execute(self, cpu):
        offset = cpu.fetch()
        # Convert to signed 8-bit integer
        if offset > 127:
            offset -= 256
        cpu.pc = (cpu.pc + offset) & 0xFF

class BrReg(BaseInstruction):
    def __init__(self):
        super().__init__("BR", 0x47)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        if typ == 'R':
            offset = cpu.Rregisters[idx]
            # Convert to signed offset
            if offset > 127:
                offset -= 256
            cpu.pc = (cpu.pc + offset) & 0xFF

class BrzImm8(BaseInstruction):
    def __init__(self):
        super().__init__("BRZ", 0x48)
    
    def execute(self, cpu):
        offset = cpu.fetch()
        if cpu.flags[7]:  # Zero flag set
            # Convert to signed offset
            if offset > 127:
                offset -= 256
            cpu.pc = (cpu.pc + offset) & 0xFF

class BrzReg(BaseInstruction):
    def __init__(self):
        super().__init__("BRZ", 0x49)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        if cpu.flags[7]:  # Zero flag set
            if typ == 'R':
                offset = cpu.Rregisters[idx]
                # Convert to signed offset
                if offset > 127:
                    offset -= 256
                cpu.pc = (cpu.pc + offset) & 0xFF

class BrnzImm8(BaseInstruction):
    def __init__(self):
        super().__init__("BRNZ", 0x4A)
    
    def execute(self, cpu):
        offset = cpu.fetch()
        if not cpu.flags[7]:  # Zero flag not set
            # Convert to signed offset
            if offset > 127:
                offset -= 256
            cpu.pc = (cpu.pc + offset) & 0xFF

class BrnzReg(BaseInstruction):
    def __init__(self):
        super().__init__("BRNZ", 0x4B)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        if not cpu.flags[7]:  # Zero flag not set
            if typ == 'R':
                offset = cpu.Rregisters[idx]
                # Convert to signed offset
                if offset > 127:
                    offset -= 256
                cpu.pc = (cpu.pc + offset) & 0xFF

# Interrupt Instructions
class IntImm8(BaseInstruction):
    def __init__(self):
        super().__init__("INT", 0x4C)
    
    def execute(self, cpu):
        int_num = cpu.fetch()
        # Ensure int_num is a Python int, not numpy.uint8
        int_num = int(int_num)
        print(f"INT: Interrupt number {int_num}")
        
        # Check stack bounds before writing (need to push 2 words)
        sp = int(cpu.Pregisters[8])
        if sp <= 0x0124:  # Stack overflow check (protect interrupt vectors + need 4 bytes)
            raise RuntimeError(f"Stack overflow: SP=0x{sp:04X}")
        
        # Push current PC and flags onto stack in memory
        flags_val = 0
        for i in range(12):
            # Ensure flag values are properly bounded
            flag_value = int(cpu._flags[i]) & 0xFF
            print(f"INT: Flag {i} = {flag_value}")
            if flag_value != 0:
                flags_val |= (1 << i)
        
        print(f"INT: Computed flags_val = 0x{flags_val:04X}")
        
        # Push flags first (using standardized pattern)
        sp = (sp - 2) & 0xFFFF
        cpu.Pregisters[8] = sp
        print(f"INT: Pushing flags 0x{flags_val:04X} to address 0x{cpu.Pregisters[8]:04X}")
        cpu.memory.write_word(cpu.Pregisters[8], flags_val)
        
        # Push PC second (using standardized pattern)
        sp = (sp - 2) & 0xFFFF
        cpu.Pregisters[8] = sp
        print(f"INT: Pushing PC 0x{cpu.pc:04X} to address 0x{cpu.Pregisters[8]:04X}")
        try:
            cpu.memory.write_word(cpu.Pregisters[8], cpu.pc)
            print(f"INT: Successfully wrote PC to memory")
        except Exception as e:
            print(f"INT: Error writing PC to memory: {e}")
            raise
        
        # Jump to interrupt handler (simplified)
        print(f"INT: About to compute new_pc with int_num={int_num}")
        try:
            new_pc = 0x0100 + (int_num * 4)
            print(f"INT: Computed new_pc = 0x{new_pc:04X}")
        except Exception as e:
            print(f"INT: ERROR in new_pc computation: {e}")
            print(f"INT: int_num = {int_num}, type = {type(int_num)}")
            raise
        
        print(f"INT: About to set PC from 0x{cpu.pc:04X} to 0x{new_pc:04X}")
        try:
            cpu.pc = new_pc  # Simple interrupt vector table
            print(f"INT: PC set to 0x{cpu.pc:04X}")
        except Exception as e:
            print(f"INT: ERROR in PC assignment: {e}")
            print(f"INT: new_pc = {new_pc}, type = {type(new_pc)}")
            raise
        
        # Invalidate prefetch buffer after jump
        print(f"INT: About to invalidate prefetch")
        cpu.invalidate_prefetch()
        print(f"INT: Prefetch invalidated, INT complete")

class IntReg(BaseInstruction):
    def __init__(self):
        super().__init__("INT", 0x4D)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        if typ == 'R':
            int_num = cpu.Rregisters[idx]
        elif typ == 'P':
            int_num = cpu.Pregisters[idx] & 0xFF
        else:
            int_num = 0
        
        # Check stack bounds before writing (need to push 2 words)
        sp = int(cpu.Pregisters[8])
        if sp <= 0x0124:  # Stack overflow check (protect interrupt vectors + need 4 bytes)
            raise RuntimeError(f"Stack overflow: SP=0x{sp:04X}")
            
        # Push current PC and flags onto stack in memory
        flags_val = 0
        for i in range(12):
            # Ensure flag values are properly bounded
            flag_value = int(cpu.flags[i]) & 0xFF
            if flag_value != 0:
                flags_val |= (1 << i)
        
        # Push flags first (using standardized pattern)
        sp = (sp - 2) & 0xFFFF
        cpu.Pregisters[8] = sp
        cpu.memory.write_word(cpu.Pregisters[8], flags_val)
        
        # Push PC second (using standardized pattern)
        sp = (sp - 2) & 0xFFFF
        cpu.Pregisters[8] = sp
        cpu.memory.write_word(cpu.Pregisters[8], cpu.pc)
        
        # Jump to interrupt handler (simplified)
        cpu.pc = 0x0100 + (int_num * 4)

# Graphics Mode and Sprite Instructions
# Note: SMODE instruction removed - use VM register (V2) instead

class SblendImm(BaseInstruction):
    def __init__(self):
        super().__init__("SBLEND", 0x4E)
    
    def execute(self, cpu):
        mode = cpu.fetch()
        cpu.gfx.blend_mode = mode & 0x0F  # Limit to 0-15
        cpu.gfx.blend_alpha = 255  # Default full intensity

class SblendImmImm(BaseInstruction):
    def __init__(self):
        super().__init__("SBLEND", 0x4F)
    
    def execute(self, cpu):
        mode = cpu.fetch()
        alpha = cpu.fetch()
        cpu.gfx.blend_mode = mode & 0x0F  # Limit to 0-15
        cpu.gfx.blend_alpha = alpha & 0xFF

class SreadReg(BaseInstruction):
    def __init__(self):
        super().__init__("SREAD", 0x50)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        # Read sprite data using graphics system's method
        val = cpu.gfx.get_screen_val()
        
        if typ == 'R':
            cpu.Rregisters[idx] = val & 0xFF
            cpu.flags[7] = int(val == 0)
        elif typ == 'P':
            cpu.Pregisters[idx] = val & 0xFFFF
            cpu.flags[7] = int(val == 0)
        elif typ == 'V':
            cpu.gfx.Vregisters[idx] = val & 0xFF
            cpu.flags[7] = int(val == 0)

class SwriteReg(BaseInstruction):
    def __init__(self):
        super().__init__("SWRITE", 0x51)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        # Get value to write - optimized version
        if typ == 'R':
            val = cpu.Rregisters[idx]
        elif typ == 'P':
            val = cpu.Pregisters[idx] & 0xFF
        elif typ == 'V':
            val = cpu.gfx.Vregisters[idx]
        else:
            val = 0
        
        # Use fast screen writing method when possible
        if hasattr(cpu.gfx, 'set_screen_val_fast'):
            cpu.gfx.set_screen_val_fast(val)
        else:
            cpu.gfx.set_screen_val(val)
        cpu.flags[7] = int(val == 0)

class SwriteImm16(BaseInstruction):
    def __init__(self):
        super().__init__("SWRITE", 0x52)
    
    def execute(self, cpu):
        imm16 = cpu.fetch(2)
        
        # Write immediate value to sprite buffer using graphics system's method
        cpu.gfx.set_screen_val(imm16 & 0xFF)
        cpu.flags[7] = int((imm16 & 0xFF) == 0)

# Screen Transform Instructions
class SrolxReg(BaseInstruction):
    def __init__(self):
        super().__init__("SROLX", 0x53)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        if typ == 'R':
            amount = cpu.Rregisters[idx]
        elif typ == 'P':
            amount = cpu.Pregisters[idx] & 0xFF
        elif typ == 'V':
            amount = cpu.gfx.Vregisters[idx] & 0xFF
        else:
            amount = 0
            
        # Use layer-aware roll if VL is set to a layer, otherwise use main screen
        if cpu.gfx.VL == 0:
            cpu.gfx.roll_x(amount)
        else:
            cpu.gfx.roll_x_layer(amount, cpu.gfx.VL)
        cpu.flags[7] = int((cpu.gfx.screen == 0).all())

class SrolxImm(BaseInstruction):
    def __init__(self):
        super().__init__("SROLX", 0x54)
    
    def execute(self, cpu):
        imm8 = cpu.fetch()
        # Use layer-aware roll if VL is set to a layer, otherwise use main screen
        if cpu.gfx.VL == 0:
            cpu.gfx.roll_x(imm8)
        else:
            cpu.gfx.roll_x_layer(imm8, cpu.gfx.VL)
        cpu.flags[7] = int((cpu.gfx.screen == 0).all())

class SrolyReg(BaseInstruction):
    def __init__(self):
        super().__init__("SROLY", 0x55)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        if typ == 'R':
            amount = cpu.Rregisters[idx]
        elif typ == 'P':
            amount = cpu.Pregisters[idx] & 0xFF
        elif typ == 'V':
            amount = cpu.gfx.Vregisters[idx] & 0xFF
        else:
            amount = 0
            
        # Use layer-aware roll if VL is set to a layer, otherwise use main screen
        if cpu.gfx.VL == 0:
            cpu.gfx.roll_y(amount)
        else:
            cpu.gfx.roll_y_layer(amount, cpu.gfx.VL)
        cpu.flags[7] = int((cpu.gfx.screen == 0).all())

class SrolyImm(BaseInstruction):
    def __init__(self):
        super().__init__("SROLY", 0x56)
    
    def execute(self, cpu):
        imm8 = cpu.fetch()
        # Use layer-aware roll if VL is set to a layer, otherwise use main screen
        if cpu.gfx.VL == 0:
            cpu.gfx.roll_y(imm8)
        else:
            cpu.gfx.roll_y_layer(imm8, cpu.gfx.VL)
        cpu.flags[7] = int((cpu.gfx.screen == 0).all())

class SrotlReg(BaseInstruction):
    def __init__(self):
        super().__init__("SROTL", 0x57)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        if typ == 'R':
            amount = cpu.Rregisters[idx]
        elif typ == 'P':
            amount = cpu.Pregisters[idx] & 0xFF
        elif typ == 'V':
            amount = cpu.gfx.Vregisters[idx] & 0xFF
        else:
            amount = 0
            
        cpu.gfx.rotate_l(amount)
        cpu.flags[7] = int((cpu.gfx.screen == 0).all())

class SrotlImm(BaseInstruction):
    def __init__(self):
        super().__init__("SROTL", 0x58)
    
    def execute(self, cpu):
        val = cpu.fetch()
        cpu.gfx.rotate_l(val)
        cpu.flags[7] = int((cpu.gfx.screen == 0).all())

class SrotrReg(BaseInstruction):
    def __init__(self):
        super().__init__("SROTR", 0x59)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        if typ == 'R':
            amount = cpu.Rregisters[idx]
        elif typ == 'P':
            amount = cpu.Pregisters[idx] & 0xFF
        elif typ == 'V':
            amount = cpu.gfx.Vregisters[idx] & 0xFF
        else:
            amount = 0
            
        cpu.gfx.rotate_r(amount)
        cpu.flags[7] = int((cpu.gfx.screen == 0).all())

class SrotrImm(BaseInstruction):
    def __init__(self):
        super().__init__("SROTR", 0x5A)
    
    def execute(self, cpu):
        val = cpu.fetch()
        cpu.gfx.rotate_r(val)
        cpu.flags[7] = int((cpu.gfx.screen == 0).all())

class SshftxReg(BaseInstruction):
    def __init__(self):
        super().__init__("SSHFTX", 0x5B)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        if typ == 'R':
            amount = cpu.Rregisters[idx]
        elif typ == 'P':
            amount = cpu.Pregisters[idx] & 0xFF
        elif typ == 'V':
            amount = cpu.gfx.Vregisters[idx] & 0xFF
        else:
            amount = 0
            
        cpu.gfx.shift_x(amount)
        cpu.flags[7] = int((cpu.gfx.screen == 0).all())

class SshftxImm(BaseInstruction):
    def __init__(self):
        super().__init__("SSHFTX", 0x5C)
    
    def execute(self, cpu):
        val = cpu.fetch()
        cpu.gfx.shift_x(val)
        cpu.flags[7] = int((cpu.gfx.screen == 0).all())

class SshftyReg(BaseInstruction):
    def __init__(self):
        super().__init__("SSHFTY", 0x5D)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        if typ == 'R':
            amount = cpu.Rregisters[idx]
        elif typ == 'P':
            amount = cpu.Pregisters[idx] & 0xFF
        elif typ == 'V':
            amount = cpu.gfx.Vregisters[idx] & 0xFF
        else:
            amount = 0
            
        cpu.gfx.shift_y(amount)
        cpu.flags[7] = int((cpu.gfx.screen == 0).all())

class SshftyImm(BaseInstruction):
    def __init__(self):
        super().__init__("SSHFTY", 0x5E)
    
    def execute(self, cpu):
        val = cpu.fetch()
        cpu.gfx.shift_y(val)
        cpu.flags[7] = int((cpu.gfx.screen == 0).all())

class Sflipx(BaseInstruction):
    def __init__(self):
        super().__init__("SFLIPX", 0x5F)
    
    def execute(self, cpu):
        # Use layer-aware flip if VL is set to a layer, otherwise use main screen
        if cpu.gfx.VL == 0:
            cpu.gfx.flip_x()
        else:
            cpu.gfx.flip_x_layer(cpu.gfx.VL)
        cpu.flags[7] = int((cpu.gfx.screen == 0).all())

class Sflipy(BaseInstruction):
    def __init__(self):
        super().__init__("SFLIPY", 0x60)
    
    def execute(self, cpu):
        # Use layer-aware flip if VL is set to a layer, otherwise use main screen
        if cpu.gfx.VL == 0:
            cpu.gfx.flip_y()
        else:
            cpu.gfx.flip_y_layer(cpu.gfx.VL)
        cpu.flags[7] = int((cpu.gfx.screen == 0).all())

class Sblit(BaseInstruction):
    def __init__(self):
        super().__init__("SBLIT", 0x61)
    
    def execute(self, cpu):
        cpu.gfx.ScreenToVRAM()
        cpu.flags[7] = int((cpu.gfx.screen == 0).all())

class CmpRegReg(BaseInstruction):
    def __init__(self):
        super().__init__("CMP", 0x62)
    
    def execute(self, cpu):
        reg1_code = cpu.fetch()
        reg2_code = cpu.fetch()
        idx1, type1 = cpu.reg_index(reg1_code)
        idx2, type2 = cpu.reg_index(reg2_code)
        
        # Get operand values
        val1 = cpu._get_operand_value(type1, idx1)
        val2 = cpu._get_operand_value(type2, idx2)
        
        # Perform comparison (subtraction without storing result)
        result = val1 - val2
        
        # Mark this as a CMP operation for correct carry flag handling
        cpu._last_operation_was_cmp = True
        
        # Set flags based on comparison
        if type1 == 'R' or type1 == 'V':
            cpu._set_flags_8bit(int(result) & 0xFF, result)
        elif type1 == 'P':
            cpu._set_flags_16bit(int(result) & 0xFFFF, result)

class CmpRegImm8(BaseInstruction):
    def __init__(self):
        super().__init__("CMP", 0x63)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        imm8 = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        # Mark this as a CMP operation for correct carry flag handling
        cpu._last_operation_was_cmp = True
        
        if typ == 'R':
            val = int(cpu.Rregisters[idx])
            imm8_val = int(imm8)
            result = val - imm8_val
            cpu._set_flags_8bit(int(result) & 0xFF, result)
        elif typ == 'P':
            val = int(cpu.Pregisters[idx])
            imm8_val = int(imm8)
            result = val - imm8_val
            masked_result = int(result) & 0xFFFF
            cpu._set_flags_16bit(masked_result, result)
        elif typ == 'V':
            val = int(cpu.gfx.Vregisters[idx])
            imm8_val = int(imm8)
            result = val - imm8_val
            cpu._set_flags_8bit(int(result) & 0xFF, result)

class CmpRegImm16(BaseInstruction):
    def __init__(self):
        super().__init__("CMP", 0x64)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        imm16 = cpu.fetch(2)
        idx, typ = cpu.reg_index(reg_code)
        
        # Mark this as a CMP operation for correct carry flag handling
        cpu._last_operation_was_cmp = True
        
        if typ == 'R':
            val = int(cpu.Rregisters[idx])
            result = val - int(imm16)
            cpu._set_flags_8bit(int(result) & 0xFF, result)
        elif typ == 'P':
            val = int(cpu.Pregisters[idx])  # Convert to int to prevent overflow
            result = val - int(imm16)       # Ensure both are int
            cpu._set_flags_16bit(int(result) & 0xFFFF, result)
        elif typ == 'V':
            val = int(cpu.gfx.Vregisters[idx])
            result = val - int(imm16)
            cpu._set_flags_8bit(int(result) & 0xFF, result)

# Graphics/VRAM Instructions
class VreadReg(BaseInstruction):
    def __init__(self):
        super().__init__("VREAD", 0x65)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        # Read from VRAM using graphics system method
        pixel = cpu.gfx.get_vram_val()
        
        if typ == 'R':
            cpu.Rregisters[idx] = pixel & 0xFF
        elif typ == 'P':
            cpu.Pregisters[idx] = pixel & 0xFFFF
        elif typ == 'V':
            cpu.gfx.Vregisters[idx] = pixel & 0xFF

class VwriteReg(BaseInstruction):
    def __init__(self):
        super().__init__("VWRITE", 0x66)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        # Get value to write
        if typ == 'R':
            val = cpu.Rregisters[idx]
        elif typ == 'P':
            val = cpu.Pregisters[idx]
        elif typ == 'V':
            val = cpu.gfx.Vregisters[idx]
        else:
            val = 0
        
        # Write to VRAM using graphics system method
        cpu.gfx.set_vram_val(val & 0xFF)

class VwriteImm16(BaseInstruction):
    def __init__(self):
        super().__init__("VWRITE", 0x67)
    
    def execute(self, cpu):
        imm16 = cpu.fetch(2)
        
        # Write immediate value to VRAM using graphics system method
        cpu.gfx.set_vram_val(imm16 & 0xFF)

class Vblit(BaseInstruction):
    def __init__(self):
        super().__init__("VBLIT", 0x68)
    
    def execute(self, cpu):
        # Copy VRAM to screen buffer (blit operation)
        cpu.gfx.VRAMtoScreen()

class CallImm16(BaseInstruction):
    def __init__(self):
        super().__init__("CALL", 0x69)
    
    def execute(self, cpu):
        addr = cpu.fetch(2)
        
        # Check stack bounds before writing
        sp = int(cpu.Pregisters[8])
        if sp <= 0x0120:  # Stack overflow check (protect interrupt vectors)
            raise RuntimeError(f"Stack overflow: SP=0x{sp:04X}")
        
        # Push PC to stack in memory using standardized pattern
        sp = (sp - 2) & 0xFFFF
        cpu.Pregisters[8] = sp
        cpu.memory.write_word(cpu.Pregisters[8], cpu.pc)
        cpu.pc = addr
        # Invalidate prefetch buffer after jump
        cpu.invalidate_prefetch()

# Character Drawing Instructions
class CharRegImm8(BaseInstruction):
    def __init__(self):
        super().__init__("CHAR", 0x6A)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        color = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        # Get character code from register
        if typ == 'R':
            char_code = cpu.Rregisters[idx] & 0xFF
        elif typ == 'P':
            char_code = cpu.Pregisters[idx] & 0xFF
        elif typ == 'V':
            char_code = cpu.gfx.Vregisters[idx] & 0xFF
        else:
            char_code = 0
        
        # Draw sinVLe character at VX, VY position
        x = cpu.gfx.Vregisters[0]  # VX
        y = cpu.gfx.Vregisters[1]  # VY
        cpu.gfx.draw_char_to_screen(chr(char_code), x, y, color)

class TextRegImm8(BaseInstruction):
    def __init__(self):
        super().__init__("TEXT", 0x6B)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        color = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        if typ == 'R':
            addr = cpu.Rregisters[idx]
        elif typ == 'P':
            addr = cpu.Pregisters[idx]
        elif typ == 'V':
            addr = cpu.gfx.Vregisters[idx]
        else:
            addr = 0
        
        # Read null-terminated string from memory
        text = ""
        while True:
            char_code = cpu.memory.read_byte(addr)
            if char_code == 0:
                break
            text += chr(char_code & 0xFF)
            addr += 1
        
        x = cpu.gfx.Vregisters[0]  # VX
        y = cpu.gfx.Vregisters[1]  # VY
        cpu.gfx.draw_string_to_screen(text, x, y, color)

class TextImm16Imm8(BaseInstruction):
    def __init__(self):
        super().__init__("TEXT", 0x6C)
    
    def execute(self, cpu):
        addr = cpu.fetch(2)  # 16-bit address
        color = cpu.fetch()  # 8-bit color
        
        # Read null-terminated string from memory
        text = ""
        while True:
            char_code = cpu.memory.read_byte(addr)
            if char_code == 0:
                break
            text += chr(char_code & 0xFF)
            addr += 1
        
        x = cpu.gfx.Vregisters[0]  # VX
        y = cpu.gfx.Vregisters[1]  # VY
        cpu.gfx.draw_string_to_screen(text, x, y, color)

class CharRegReg(BaseInstruction):
    def __init__(self):
        super().__init__("CHAR", 0x6D)
    
    def execute(self, cpu):
        char_reg_code = cpu.fetch()
        color_reg_code = cpu.fetch()
        
        # Get character code from first register
        idx1, typ1 = cpu.reg_index(char_reg_code)
        if typ1 == 'R':
            char_code = cpu.Rregisters[idx1] & 0xFF
        elif typ1 == 'P':
            char_code = cpu.Pregisters[idx1] & 0xFF
        elif typ1 == 'V':
            char_code = cpu.gfx.Vregisters[idx1] & 0xFF
        else:
            char_code = 0
        
        # Get color from second register
        idx2, typ2 = cpu.reg_index(color_reg_code)
        if typ2 == 'R':
            color = cpu.Rregisters[idx2] & 0xFF
        elif typ2 == 'P':
            color = cpu.Pregisters[idx2] & 0xFF
        elif typ2 == 'V':
            color = cpu.gfx.Vregisters[idx2] & 0xFF
        else:
            color = 0xFF
        
        # Draw sinVLe character at VX, VY position
        x = cpu.gfx.Vregisters[0]  # VX
        y = cpu.gfx.Vregisters[1]  # VY
        cpu.gfx.draw_char_to_screen(chr(char_code), x, y, color)

class TextRegReg(BaseInstruction):
    def __init__(self):
        super().__init__("TEXT", 0x6E)
    
    def execute(self, cpu):
        addr_reg_code = cpu.fetch()
        color_reg_code = cpu.fetch()
        
        # Get address from first register
        idx1, typ1 = cpu.reg_index(addr_reg_code)
        if typ1 == 'R':
            addr = cpu.Rregisters[idx1]
        elif typ1 == 'P':
            addr = cpu.Pregisters[idx1]
        elif typ1 == 'V':
            addr = cpu.gfx.Vregisters[idx1]
        else:
            addr = 0
        
        # Get color from second register
        idx2, typ2 = cpu.reg_index(color_reg_code)
        if typ2 == 'R':
            color = cpu.Rregisters[idx2] & 0xFF
        elif typ2 == 'P':
            color = cpu.Pregisters[idx2] & 0xFF
        elif typ2 == 'V':
            color = cpu.gfx.Vregisters[idx2] & 0xFF
        else:
            color = 0xFF
        
        # Read null-terminated string from memory
        text = ""
        while True:
            char_code = cpu.memory.read_byte(addr)
            if char_code == 0:
                break
            text += chr(char_code & 0xFF)
            addr += 1
        
        # Draw text at VX, VY position
        x = cpu.gfx.Vregisters[0]  # VX
        y = cpu.gfx.Vregisters[1]  # VY
        cpu.gfx.draw_string_to_screen(text, x, y, color)

class TextImm16Reg(BaseInstruction):
    def __init__(self):
        super().__init__("TEXT", 0x6F)
    
    def execute(self, cpu):
        addr = cpu.fetch(2)  # 16-bit address
        reg_code = cpu.fetch()  # Color register
        idx, typ = cpu.reg_index(reg_code)
        
        # Get color from register
        if typ == 'R':
            color = cpu.Rregisters[idx] & 0xFF
        elif typ == 'P':
            color = cpu.Pregisters[idx] & 0xFF
        elif typ == 'V':
            color = cpu.gfx.Vregisters[idx] & 0xFF
        else:
            color = 0
        
        # Read null-terminated string from memory
        text = ""
        while True:
            char_code = cpu.memory.read_byte(addr)
            if char_code == 0:
                break
            text += chr(char_code & 0xFF)
            addr += 1
        
        x = cpu.gfx.Vregisters[0]  # VX
        y = cpu.gfx.Vregisters[1]  # VY
        cpu.gfx.draw_string_to_screen(text, x, y, color)

# Control Flow 2 Instructions
class JgtImm16(BaseInstruction):
    def __init__(self):
        super().__init__("JGT", 0x70)
    
    def execute(self, cpu):
        addr = cpu.fetch(2)
        # Jump if greater than (carry clear AND zero clear)
        if not cpu.flags[6] and not cpu.flags[7]:  # Not carry and not zero
            cpu.pc = addr

class JltImm16(BaseInstruction):
    def __init__(self):
        super().__init__("JLT", 0x71)
    
    def execute(self, cpu):
        addr = cpu.fetch(2)
        # Jump if less than (carry flag set)
        if cpu.flags[6]:  # Carry flag
            cpu.pc = addr

class JgeImm16(BaseInstruction):
    def __init__(self):
        super().__init__("JGE", 0x72)
    
    def execute(self, cpu):
        addr = cpu.fetch(2)
        # Jump if greater than or equal (carry clear)
        if not cpu.flags[6]:  # Not carry
            cpu.pc = addr

class JleImm16(BaseInstruction):
    def __init__(self):
        super().__init__("JLE", 0x73)
    
    def execute(self, cpu):
        addr = cpu.fetch(2)
        # Jump if less than or equal (carry set OR zero set)
        if cpu.flags[6] or cpu.flags[7]:  # Carry or zero
            cpu.pc = addr

# Keyboard I/O Instructions
class KeyinReg(BaseInstruction):
    def __init__(self):
        super().__init__("KEYIN", 0x74)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        key_code = cpu.read_key_from_buffer()
        
        if typ == 'R':
            cpu.Rregisters[idx] = key_code & 0xFF
        elif typ == 'P':
            cpu.Pregisters[idx] = key_code & 0xFFFF
        elif typ == 'V':
            cpu.gfx.Vregisters[idx] = key_code & 0xFF
        
        # Set zero flag if no key available
        cpu.flags[7] = int(key_code == 0)

class KeystatReg(BaseInstruction):
    def __init__(self):
        super().__init__("KEYSTAT", 0x75)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        status = cpu.keyboard[1]  # Status register
        
        if typ == 'R':
            cpu.Rregisters[idx] = status & 0xFF
        elif typ == 'P':
            cpu.Pregisters[idx] = status & 0xFFFF
        elif typ == 'V':
            cpu.gfx.Vregisters[idx] = status & 0xFF

class KeycountReg(BaseInstruction):
    def __init__(self):
        super().__init__("KEYCOUNT", 0x76)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        count = cpu.keyboard[3]  # Buffer count
        
        if typ == 'R':
            cpu.Rregisters[idx] = count & 0xFF
        elif typ == 'P':
            cpu.Pregisters[idx] = count & 0xFFFF
        elif typ == 'V':
            cpu.gfx.Vregisters[idx] = count & 0xFF

class Keyclear(BaseInstruction):
    def __init__(self):
        super().__init__("KEYCLEAR", 0x77)
    
    def execute(self, cpu):
        cpu.clear_keyboard_buffer()

class KeyctrlReg(BaseInstruction):
    def __init__(self):
        super().__init__("KEYCTRL", 0x78)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        if typ == 'R':
            cpu.keyboard[2] = cpu.Rregisters[idx] & 0xFF
        elif typ == 'P':
            cpu.keyboard[2] = cpu.Pregisters[idx] & 0xFF
        elif typ == 'V':
            cpu.keyboard[2] = cpu.gfx.Vregisters[idx] & 0xFF
        
        # Enable/disable keyboard interrupt based on control register
        cpu.interrupts[2] = (cpu.keyboard[2] & 0x01)

class KeyctrlImm(BaseInstruction):
    def __init__(self):
        super().__init__("KEYCTRL", 0x79)
    
    def execute(self, cpu):
        imm8 = cpu.fetch()
        cpu.keyboard[2] = imm8 & 0xFF
        # Enable/disable keyboard interrupt based on control register
        cpu.interrupts[2] = (cpu.keyboard[2] & 0x01)

# Misc Instructions
class ModRegReg(BaseInstruction):
    def __init__(self):
        super().__init__("MOD", 0x7A)
    
    def execute(self, cpu):
        reg1_code = cpu.fetch()
        reg2_code = cpu.fetch()
        idx1, type1 = cpu.reg_index(reg1_code)
        idx2, type2 = cpu.reg_index(reg2_code)
        
        # Get operand values
        val1 = cpu._get_operand_value(type1, idx1)
        val2 = cpu._get_operand_value(type2, idx2)
        
        if val2 == 0:
            # Division by zero - set result to 0 and set overflow flag
            result = 0
            cpu.overflow_flag = True
        else:
            result = val1 % val2
        
        if type1 == 'R':
            cpu.Rregisters[idx1] = result & 0xFF
            cpu._set_flags_8bit(int(result) & 0xFF, result)
        elif type1 == 'P':
            cpu.Pregisters[idx1] = result & 0xFFFF
            cpu._set_flags_16bit(int(result) & 0xFFFF, result)
        elif type1 == 'V':
            cpu.gfx.Vregisters[idx1] = result & 0xFF
            cpu._set_flags_8bit(int(result) & 0xFF, result)

class ModRegImm8(BaseInstruction):
    def __init__(self):
        super().__init__("MOD", 0x7B)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        imm8 = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        if imm8 == 0:
            # Division by zero - set result to 0 and set overflow flag
            result = 0
            cpu.overflow_flag = True
        else:
            if typ == 'R':
                original = int(cpu.Rregisters[idx])
                result = original % imm8
                cpu.Rregisters[idx] = result & 0xFF
                cpu._set_flags_8bit(int(result) & 0xFF, result)
            elif typ == 'P':
                original = int(cpu.Pregisters[idx])
                result = original % imm8
                cpu.Pregisters[idx] = result & 0xFFFF
                cpu._set_flags_16bit(int(result) & 0xFFFF, result)

class ModRegImm16(BaseInstruction):
    def __init__(self):
        super().__init__("MOD", 0x7C)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        imm16 = cpu.fetch(2)
        idx, typ = cpu.reg_index(reg_code)
        
        if imm16 == 0:
            # Division by zero - set result to 0 and set overflow flag
            result = 0
            cpu.overflow_flag = True
        else:
            if typ == 'P':
                original = int(cpu.Pregisters[idx])
                result = original % imm16
                cpu.Pregisters[idx] = result & 0xFFFF
                cpu._set_flags_16bit(int(result) & 0xFFFF, result)

class NegReg(BaseInstruction):
    def __init__(self):
        super().__init__("NEG", 0x7D)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        if typ == 'R':
            original = cpu.Rregisters[idx]
            # Two's complement negation
            result = (~original + 1) & 0xFF
            cpu.Rregisters[idx] = result
            cpu._set_flags_8bit(result, result)
        elif typ == 'P':
            original = cpu.Pregisters[idx]
            # Two's complement negation
            result = (~original + 1) & 0xFFFF
            cpu.Pregisters[idx] = result
            cpu._set_flags_16bit(result, result)
        elif typ == 'V':
            original = cpu.gfx.Vregisters[idx]
            # Two's complement negation
            result = (~original + 1) & 0xFF
            cpu.gfx.Vregisters[idx] = result
            cpu._set_flags_8bit(result, result)

class AbsReg(BaseInstruction):
    def __init__(self):
        super().__init__("ABS", 0x7E)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        if typ == 'R':
            original = cpu.Rregisters[idx]
            # Check if negative (bit 7 set)
            if original & 0x80:
                result = (~original + 1) & 0xFF
            else:
                result = original
            cpu.Rregisters[idx] = result
            cpu._set_flags_8bit(result, result)
        elif typ == 'P':
            original = cpu.Pregisters[idx]
            # Check if negative (bit 15 set)
            if original & 0x8000:
                result = (~original + 1) & 0xFFFF
            else:
                result = original
            cpu.Pregisters[idx] = result
            cpu._set_flags_16bit(result, result)
        elif typ == 'V':
            original = cpu.gfx.Vregisters[idx]
            # Check if negative (bit 7 set)
            if original & 0x80:
                result = (~original + 1) & 0xFF
            else:
                result = original
            cpu.gfx.Vregisters[idx] = result
            cpu._set_flags_8bit(result, result)

class SfillReg(BaseInstruction):
    def __init__(self):
        super().__init__("SFILL", 0x7F)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        # Get fill value
        fill_value = cpu._get_operand_value(typ, idx) & 0xFF
        
        # Fill current layer with value
        cpu.gfx.fill_layer(fill_value)

class SfillImm8(BaseInstruction):
    def __init__(self):
        super().__init__("SFILL", 0x80)
    
    def execute(self, cpu):
        fill_value = cpu.fetch()
        
        # Fill current layer with value
        cpu.gfx.fill_layer(fill_value)

class LoopRegReg(BaseInstruction):
    def __init__(self):
        super().__init__("LOOP", 0x81)
    
    def execute(self, cpu):
        counter_reg_code = cpu.fetch()
        target_reg_code = cpu.fetch()
        counter_idx, counter_typ = cpu.reg_index(counter_reg_code)
        target_idx, target_typ = cpu.reg_index(target_reg_code)
        
        # Get current counter value
        counter_value = cpu._get_operand_value(counter_typ, counter_idx)
        
        if counter_value > 0:
            # Decrement counter
            new_counter = counter_value - 1
            cpu._set_operand_value(counter_typ, counter_idx, new_counter)
            
            # If counter is not zero, jump to target
            if new_counter > 0:
                target_address = cpu._get_operand_value(target_typ, target_idx)
                cpu.pc = target_address & 0xFFFF

class LoopImm8Reg(BaseInstruction):
    def __init__(self):
        super().__init__("LOOP", 0x82)
    
    def execute(self, cpu):
        counter_value = cpu.fetch()
        target_reg_code = cpu.fetch()
        target_idx, target_typ = cpu.reg_index(target_reg_code)
        
        if counter_value > 0:
            # Decrement counter (stored nowhere, just immediate check)
            new_counter = counter_value - 1
            
            # If counter is not zero, jump to target
            if new_counter > 0:
                target_address = cpu._get_operand_value(target_typ, target_idx)
                cpu.pc = target_address & 0xFFFF

class RndReg(BaseInstruction):
    def __init__(self):
        super().__init__("RND", 0x83)
    
    def execute(self, cpu):
        import random
        reg_code = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        # Generate random number 0-65535
        random_value = random.randint(0, 65535)
        
        if typ == 'R':
            # Store low byte only
            cpu.Rregisters[idx] = random_value & 0xFF
        elif typ == 'P':
            # Store full 16-bit value
            cpu.Pregisters[idx] = random_value & 0xFFFF
        elif typ == 'V':
            # Store low byte only
            cpu.gfx.Vregisters[idx] = random_value & 0xFF

class RndrRegRegReg(BaseInstruction):
    def __init__(self):
        super().__init__("RNDR", 0x84)
    
    def execute(self, cpu):
        import random
        dest_reg_code = cpu.fetch()
        lower_reg_code = cpu.fetch()
        upper_reg_code = cpu.fetch()
        dest_idx, dest_typ = cpu.reg_index(dest_reg_code)
        lower_idx, lower_typ = cpu.reg_index(lower_reg_code)
        upper_idx, upper_typ = cpu.reg_index(upper_reg_code)
        
        # Get lower and upper bound values
        lower_value = cpu._get_operand_value(lower_typ, lower_idx)
        upper_value = cpu._get_operand_value(upper_typ, upper_idx)
        
        # Ensure valid range and handle edge cases
        # Handle potential signed/unsigned issues
        lower_value = int(lower_value) & 0xFFFF  # Ensure unsigned
        upper_value = int(upper_value) & 0xFFFF  # Ensure unsigned
        
        if lower_value > upper_value:
            lower_value, upper_value = upper_value, lower_value
        
        # Always check for equal values or invalid ranges
        if lower_value == upper_value or upper_value < lower_value:
            random_value = lower_value
        else:
            random_value = random.randint(lower_value, upper_value)
        
        if dest_typ == 'R':
            cpu.Rregisters[dest_idx] = random_value & 0xFF
        elif dest_typ == 'P':
            cpu.Pregisters[dest_idx] = random_value & 0xFFFF
        elif dest_typ == 'V':
            cpu.gfx.Vregisters[dest_idx] = random_value & 0xFF

class RndrRegImm8Imm8(BaseInstruction):
    def __init__(self):
        super().__init__("RNDR", 0x85)
    
    def execute(self, cpu):
        import random
        dest_reg_code = cpu.fetch()
        lower_value = cpu.fetch()
        upper_value = cpu.fetch()
        dest_idx, dest_typ = cpu.reg_index(dest_reg_code)
        
        # Ensure valid range and handle edge cases
        # Handle potential signed/unsigned issues
        lower_value = int(lower_value) & 0xFF  # Ensure 8-bit unsigned
        upper_value = int(upper_value) & 0xFF  # Ensure 8-bit unsigned
        
        if lower_value > upper_value:
            lower_value, upper_value = upper_value, lower_value
        
        # Always check for equal values or invalid ranges
        if lower_value == upper_value or upper_value < lower_value:
            random_value = lower_value
        else:
            random_value = random.randint(lower_value, upper_value)
        
        if dest_typ == 'R':
            cpu.Rregisters[dest_idx] = random_value & 0xFF
        elif dest_typ == 'P':
            cpu.Pregisters[dest_idx] = random_value & 0xFFFF
        elif dest_typ == 'V':
            cpu.gfx.Vregisters[dest_idx] = random_value & 0xFF

class RndrRegImm16Imm16(BaseInstruction):
    def __init__(self):
        super().__init__("RNDR", 0x86)
    
    def execute(self, cpu):
        import random
        dest_reg_code = cpu.fetch()
        lower_value = cpu.fetch(2)
        upper_value = cpu.fetch(2)
        dest_idx, dest_typ = cpu.reg_index(dest_reg_code)
        
        # Ensure valid range and handle edge cases
        # Handle potential signed/unsigned issues and overflow
        lower_value = int(lower_value) & 0xFFFF  # Ensure 16-bit unsigned
        upper_value = int(upper_value) & 0xFFFF  # Ensure 16-bit unsigned
        
        if lower_value > upper_value:
            lower_value, upper_value = upper_value, lower_value
        
        # Always check for equal values or invalid ranges
        if lower_value == upper_value or upper_value < lower_value:
            random_value = lower_value
        else:
            random_value = random.randint(lower_value, upper_value)
        
        if dest_typ == 'R':
            cpu.Rregisters[dest_idx] = random_value & 0xFF
        elif dest_typ == 'P':
            cpu.Pregisters[dest_idx] = random_value & 0xFFFF
        elif dest_typ == 'V':
            cpu.gfx.Vregisters[dest_idx] = random_value & 0xFF

class MemcpyRegRegReg(BaseInstruction):
    def __init__(self):
        super().__init__("MEMCPY", 0x87)
    
    def execute(self, cpu):
        dest_reg_code = cpu.fetch()
        src_reg_code = cpu.fetch()
        count_reg_code = cpu.fetch()
        dest_idx, dest_typ = cpu.reg_index(dest_reg_code)
        src_idx, src_typ = cpu.reg_index(src_reg_code)
        count_idx, count_typ = cpu.reg_index(count_reg_code)
        
        # Get addresses and count
        dest_addr = cpu._get_operand_value(dest_typ, dest_idx)
        src_addr = cpu._get_operand_value(src_typ, src_idx)
        count = cpu._get_operand_value(count_typ, count_idx)
        
        # Copy memory
        for i in range(count):
            if src_addr + i < cpu.memory.size and dest_addr + i < cpu.memory.size:
                value = cpu.memory.read_byte(src_addr + i)
                cpu.write_memory(dest_addr + i, value)

class MemcpyRegRegImm8(BaseInstruction):
    def __init__(self):
        super().__init__("MEMCPY", 0x88)
    
    def execute(self, cpu):
        dest_reg_code = cpu.fetch()
        src_reg_code = cpu.fetch()
        count = cpu.fetch()
        dest_idx, dest_typ = cpu.reg_index(dest_reg_code)
        src_idx, src_typ = cpu.reg_index(src_reg_code)
        
        # Get addresses
        dest_addr = cpu._get_operand_value(dest_typ, dest_idx)
        src_addr = cpu._get_operand_value(src_typ, src_idx)
        
        # Copy memory
        for i in range(count):
            if src_addr + i < cpu.memory.size and dest_addr + i < cpu.memory.size:
                value = cpu.memory.read_byte(src_addr + i)
                cpu.write_memory(dest_addr + i, value)

class MemcpyRegRegImm16(BaseInstruction):
    def __init__(self):
        super().__init__("MEMCPY", 0x89)
    
    def execute(self, cpu):
        dest_reg_code = cpu.fetch()
        src_reg_code = cpu.fetch()
        count = cpu.fetch(2)
        dest_idx, dest_typ = cpu.reg_index(dest_reg_code)
        src_idx, src_typ = cpu.reg_index(src_reg_code)
        
        # Get addresses
        dest_addr = cpu._get_operand_value(dest_typ, dest_idx)
        src_addr = cpu._get_operand_value(src_typ, src_idx)
        
        # Copy memory
        for i in range(count):
            if src_addr + i < cpu.memory.size and dest_addr + i < cpu.memory.size:
                value = cpu.memory.read_byte(src_addr + i)
                cpu.write_memory(dest_addr + i, value)

class Sed(BaseInstruction):
    """Set Decimal flag - enable BCD mode"""
    def __init__(self):
        super().__init__("SED", 0x8A)
    
    def execute(self, cpu):
        cpu.decimal_flag = True

class Cld(BaseInstruction):
    """Clear Decimal flag - disable BCD mode"""
    def __init__(self):
        super().__init__("CLD", 0x8B)
    
    def execute(self, cpu):
        cpu.decimal_flag = False

class Cla(BaseInstruction):
    """Clear BCD auxiliary carry flag"""
    def __init__(self):
        super().__init__("CLA", 0x8C)
    
    def execute(self, cpu):
        cpu.bcd_carry_flag = False

class BcdaRegReg(BaseInstruction):
    """BCD Add with auxiliary carry"""
    def __init__(self):
        super().__init__("BCDA", 0x8D)
    
    def execute(self, cpu):
        reg1_code = cpu.fetch()
        reg2_code = cpu.fetch()
        idx1, type1 = cpu.reg_index(reg1_code)
        idx2, type2 = cpu.reg_index(reg2_code)
        
        # Get operand values
        val1 = cpu._get_operand_value(type1, idx1)
        val2 = cpu._get_operand_value(type2, idx2)
        
        # Always perform BCD arithmetic regardless of decimal flag
        bcd_result, bcd_carry = cpu._bcd_add(val1, val2)
        
        # Store result
        if type1 == 'R':
            cpu.Rregisters[idx1] = bcd_result & 0xFF
        elif type1 == 'P':
            cpu.Pregisters[idx1] = bcd_result & 0xFFFF
        elif type1 == 'V':
            cpu.gfx.Vregisters[idx1] = bcd_result & 0xFF
        elif type1 in ['TT', 'TM', 'TC', 'TS']:
            cpu._set_operand_value(type1, idx1, bcd_result & 0xFF)
        
        cpu._set_flags_8bit_bcd(bcd_result, bcd_carry)

class BcdsRegReg(BaseInstruction):
    """BCD Subtract with auxiliary carry"""
    def __init__(self):
        super().__init__("BCDS", 0x8E)
    
    def execute(self, cpu):
        reg1_code = cpu.fetch()
        reg2_code = cpu.fetch()
        idx1, type1 = cpu.reg_index(reg1_code)
        idx2, type2 = cpu.reg_index(reg2_code)
        
        # Get operand values
        val1 = cpu._get_operand_value(type1, idx1)
        val2 = cpu._get_operand_value(type2, idx2)
        
        # Always perform BCD arithmetic regardless of decimal flag
        bcd_result, bcd_borrow = cpu._bcd_sub(val1, val2)
        
        # Store result
        if type1 == 'R':
            cpu.Rregisters[idx1] = bcd_result & 0xFF
        elif type1 == 'P':
            cpu.Pregisters[idx1] = bcd_result & 0xFFFF
        elif type1 == 'V':
            cpu.gfx.Vregisters[idx1] = bcd_result & 0xFF
        elif type1 in ['TT', 'TM', 'TC', 'TS']:
            cpu._set_operand_value(type1, idx1, bcd_result & 0xFF)
        
        cpu._set_flags_8bit_bcd(bcd_result, bcd_borrow)

class BcdcmpRegReg(BaseInstruction):
    """BCD Compare - sets flags without storing result"""
    def __init__(self):
        super().__init__("BCDCMP", 0x8F)
    
    def execute(self, cpu):
        reg1_code = cpu.fetch()
        reg2_code = cpu.fetch()
        idx1, type1 = cpu.reg_index(reg1_code)
        idx2, type2 = cpu.reg_index(reg2_code)
        
        # Get operand values
        val1 = cpu._get_operand_value(type1, idx1)
        val2 = cpu._get_operand_value(type2, idx2)
        
        # Perform BCD subtraction but don't store result
        bcd_result, bcd_borrow = cpu._bcd_sub(val1, val2)
        
        # Only set flags
        cpu._set_flags_8bit_bcd(bcd_result, bcd_borrow)

class Bcd2bin(BaseInstruction):
    """Convert BCD to binary in register"""
    def __init__(self):
        super().__init__("BCD2BIN", 0x90)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        # Get BCD value
        bcd_value = cpu._get_operand_value(typ, idx)
        
        # Convert to binary
        binary_value = cpu._bcd_to_binary(bcd_value)
        
        # Store result
        if typ == 'R':
            cpu.Rregisters[idx] = binary_value & 0xFF
        elif typ == 'P':
            cpu.Pregisters[idx] = binary_value & 0xFFFF
        elif typ == 'V':
            cpu.gfx.Vregisters[idx] = binary_value & 0xFF
        elif typ in ['TT', 'TM', 'TC', 'TS']:
            cpu._set_operand_value(typ, idx, binary_value & 0xFF)
        
        # Set flags based on binary result
        cpu._set_flags_8bit(binary_value & 0xFF, binary_value)

class Bin2bcd(BaseInstruction):
    """Convert binary to BCD in register"""
    def __init__(self):
        super().__init__("BIN2BCD", 0x91)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        # Get binary value
        binary_value = cpu._get_operand_value(typ, idx)
        
        # Convert to BCD
        bcd_value = cpu._binary_to_bcd(binary_value)
        
        # Store result
        if typ == 'R':
            cpu.Rregisters[idx] = bcd_value & 0xFF
        elif typ == 'P':
            cpu.Pregisters[idx] = bcd_value & 0xFFFF
        elif typ == 'V':
            cpu.gfx.Vregisters[idx] = bcd_value & 0xFF
        elif typ in ['TT', 'TM', 'TC', 'TS']:
            cpu._set_operand_value(typ, idx, bcd_value & 0xFF)
        
        # Set flags based on BCD result
        cpu._set_flags_8bit_bcd(bcd_value, False)

class BcdaddRegImm8(BaseInstruction):
    """BCD Add immediate"""
    def __init__(self):
        super().__init__("BCDADD", 0x92)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        imm8 = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        # Get register value
        reg_value = cpu._get_operand_value(typ, idx)
        
        # Always perform BCD arithmetic
        bcd_result, bcd_carry = cpu._bcd_add(reg_value, imm8)
        
        # Store result
        if typ == 'R':
            cpu.Rregisters[idx] = bcd_result & 0xFF
        elif typ == 'P':
            cpu.Pregisters[idx] = bcd_result & 0xFFFF
        elif typ == 'V':
            cpu.gfx.Vregisters[idx] = bcd_result & 0xFF
        elif typ in ['TT', 'TM', 'TC', 'TS']:
            cpu._set_operand_value(typ, idx, bcd_result & 0xFF)
        
        cpu._set_flags_8bit_bcd(bcd_result, bcd_carry)

class BcdsubRegImm8(BaseInstruction):
    """BCD Subtract immediate"""
    def __init__(self):
        super().__init__("BCDSUB", 0x93)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        imm8 = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        # Get register value
        reg_value = cpu._get_operand_value(typ, idx)
        
        # Always perform BCD arithmetic
        bcd_result, bcd_borrow = cpu._bcd_sub(reg_value, imm8)
        
        # Store result
        if typ == 'R':
            cpu.Rregisters[idx] = bcd_result & 0xFF
        elif typ == 'P':
            cpu.Pregisters[idx] = bcd_result & 0xFFFF
        elif typ == 'V':
            cpu.gfx.Vregisters[idx] = bcd_result & 0xFF
        elif typ in ['TT', 'TM', 'TC', 'TS']:
            cpu._set_operand_value(typ, idx, bcd_result & 0xFF)
        
        cpu._set_flags_8bit_bcd(bcd_result, bcd_borrow)

# Sprite Instructions
class SpBlitReg(BaseInstruction):
    """Blit specific sprite by ID from register"""
    def __init__(self):
        super().__init__("SPBLIT", 0x94)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        # Get sprite ID from register
        sprite_id = cpu._get_operand_value(typ, idx) & 0xFF
        
        # Clip sprite ID to valid range (0-15)
        sprite_id = sprite_id % 16
        
        # Blit the sprite
        cpu.gfx.blit_sprite(sprite_id, cpu.memory)

class SpBlitImm(BaseInstruction):
    """Blit specific sprite by immediate ID"""
    def __init__(self):
        super().__init__("SPBLIT", 0x95)
    
    def execute(self, cpu):
        sprite_id = cpu.fetch() & 0xFF
        
        # Clip sprite ID to valid range (0-15)
        sprite_id = sprite_id % 16
        
        # Blit the sprite
        cpu.gfx.blit_sprite(sprite_id, cpu.memory)

class SpBlitAll(BaseInstruction):
    """Blit all active sprites"""
    def __init__(self):
        super().__init__("SPBLITALL", 0x96)
    
    def execute(self, cpu):
        # Blit all sprites
        cpu.gfx.blit_all_sprites(cpu.memory)


# Sound Instructions
class SPlay(BaseInstruction):
    """Start playing sound using current sound registers"""
    def __init__(self):
        super().__init__("SPLAY", 0x97)
    
    def execute(self, cpu):
        # Play sound using current sound register values
        cpu.sound.splay()

class SPlayReg(BaseInstruction):
    """Start playing sound on specific channel from register"""
    def __init__(self):
        super().__init__("SPLAY", 0x98)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        # Get channel number from register
        channel = cpu._get_operand_value(typ, idx) & 0xFF
        
        # Clip channel to valid range (0-7)
        channel = channel % 8
        
        # Play sound on specified channel
        cpu.sound.splay(channel)

class SStop(BaseInstruction):
    """Stop all sound channels"""
    def __init__(self):
        super().__init__("SSTOP", 0x99)
    
    def execute(self, cpu):
        # Stop all sound channels
        cpu.sound.sstop()

class SStopReg(BaseInstruction):
    """Stop specific sound channel from register"""
    def __init__(self):
        super().__init__("SSTOP", 0x9A)
    
    def execute(self, cpu):
        reg_code = cpu.fetch()
        idx, typ = cpu.reg_index(reg_code)
        
        # Get channel number from register
        channel = cpu._get_operand_value(typ, idx) & 0xFF
        
        # Clip channel to valid range (0-7)
        channel = channel % 8
        
        # Stop sound on specified channel
        cpu.sound.sstop(channel)

class STrig(BaseInstruction):
    """Trigger sound effect (type from SW register)"""
    def __init__(self):
        super().__init__("STRIG", 0x9B)
    
    def execute(self, cpu):
        # Get effect type from SW register (lower 3 bits)
        effect_type = cpu.sound.get_register('SW') & 0x07
        
        # Trigger the sound effect
        cpu.sound.strig(effect_type)

class STrigImm(BaseInstruction):
    """Trigger specific sound effect type"""
    def __init__(self):
        super().__init__("STRIG", 0x9C)
    
    def execute(self, cpu):
        effect_type = cpu.fetch() & 0xFF
        
        # Clip effect type to valid range (0-7)
        effect_type = effect_type % 8
        
        # Trigger the sound effect
        cpu.sound.strig(effect_type)



def create_instruction_table():
    """Create and return a dictionary mapping opcodes to instruction instances"""
    instructions = [
        # Control Flow
        Hlt(), Ret(), IRet(), Cli(), Sti(), Nop(),
        
        # Data Movement
        MovRegReg(), MovRegImm8(), MovRegImm16(), MovRegRegIndir(),
        MovRegRegIndex(), MovRegIndirReg(), MovRegIndexReg(),
        MovRegDirImm16(), MovDirImm16Reg(),
        
        # Load/Store
        MovRegIndirImm8(), MovRegIndexImm8(), MovRegIndirImm16(),
        MovRegIndexImm16(), MovRegDirImm16(), MovDirImm16Reg(),
        
        # Arithmetic
        IncReg(), DecReg(), AddRegReg(), AddRegImm8(), AddRegImm16(),
        SubRegReg(), SubRegImm8(), SubRegImm16(),
        MulRegReg(), MulRegImm8(), MulRegImm16(),
        DivRegReg(), DivRegImm8(), DivRegImm16(),
        
        # Logical
        AndRegReg(), AndRegImm8(), AndRegImm16(),
        OrRegReg(), OrRegImm8(), OrRegImm16(),
        XorRegReg(), XorRegImm8(), XorRegImm16(),
        NotReg(),
        
        # Bit Shift
        ShlReg(), ShrReg(), RolReg(), RorReg(),
        
        # Stack
        PushReg(), PopReg(), PushF(), PopF(), PushA(), PopA(),
        
        # Control Flow / Jumps
        JmpImm16(), JmpReg(), JzImm16(), JzReg(),
        JnzImm16(), JnzReg(), JoImm16(), JoReg(), JnoImm16(), JnoReg(),
        JcImm16(), JcReg(), JncImm16(), JncReg(), JsImm16(), JsReg(),
        JnsImm16(), JnsReg(),
        
        # Branch Instructions
        BrImm8(), BrReg(), BrzImm8(), BrzReg(), BrnzImm8(), BrnzReg(),
        
        # Calls
        CallImm16(),
        
        # Interrupts
        IntImm8(), IntReg(),
        
        # Comparison
        CmpRegReg(), CmpRegImm8(), CmpRegImm16(),
        
        # Graphics/VRAM
        VreadReg(), VwriteReg(), VwriteImm16(), Vblit(),
        
        # Sprite Graphics (SMODE removed - use VM register instead)
        SblendImm(), SblendImmImm(), SreadReg(), SwriteReg(), SwriteImm16(),
        
        # Sprite Transforms
        SrolxReg(), SrolxImm(), SrolyReg(), SrolyImm(),
        SrotlReg(), SrotlImm(), SrotrReg(), SrotrImm(),
        SshftxReg(), SshftxImm(), SshftyReg(), SshftyImm(),
        Sflipx(), Sflipy(), Sblit(),
        
        # Character/Text Drawing
        TextImm16Imm8(), TextRegImm8(), CharRegImm8(),
        CharRegReg(), TextImm16Reg(), TextRegReg(),
        
        
        # Control Flow 2 Instructions (0x7A-0x7F)
        JgtImm16(), JltImm16(), JgeImm16(), JleImm16(),
        
        # Keyboard I/O
        KeyinReg(), KeystatReg(), KeycountReg(), Keyclear(),
        KeyctrlReg(), KeyctrlImm(),
        
        # Misc Instructions
        ModRegReg(), ModRegImm8(), ModRegImm16(),
        NegReg(), AbsReg(),
        SfillReg(), SfillImm8(),
        LoopRegReg(), LoopImm8Reg(),
        RndReg(),
        RndrRegRegReg(), RndrRegImm8Imm8(), RndrRegImm16Imm16(),
        MemcpyRegRegReg(), MemcpyRegRegImm8(), MemcpyRegRegImm16(),
        
        # BCD Instructions
        Sed(), Cld(), Cla(),
        BcdaRegReg(), BcdsRegReg(), BcdcmpRegReg(),
        Bcd2bin(), Bin2bcd(),
        BcdaddRegImm8(), BcdsubRegImm8(),
        
        # Sprite Instructions
        SpBlitReg(), SpBlitImm(), SpBlitAll(),
        
        # Sound Instructions
        SPlay(), SPlayReg(), SStop(), SStopReg(),
        STrig(), STrigImm(),
        
    ]
    
    # Create the dispatch table
    table = {}
    for instruction in instructions:
        table[instruction.opcode] = instruction
    
    return table
