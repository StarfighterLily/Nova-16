import sys
import tkinter as tk
from tkinter import filedialog
from opcodes import opcodes

def create_reverse_maps():
    """
    Creates reverse lookup maps from the opcodes list for quick disassembly.
    - opcode_map: Maps a hex opcode to its mnemonic and total size.
    - register_map: Maps a hex register code to its string representation.
    """
    opcode_map = {}
    register_map = {}
    
    # A set of all register mnemonics for quick checking
    reg_mnemonics = { f"R{i}" for i in range(10) } | { f"P{i}" for i in range(10) } | { "VM", "VX", "VY" } | { "VL", "TT", "TM", "TC", "TS", "SF", "SV", "SW", "SA" }

    for mnemonic, opcode_str, size in opcodes:
        opcode_val = int( opcode_str, 16 )

        # For new prefixed operand system, all instructions have size 1 (just opcode)
        # The actual size is calculated dynamically based on mode byte
        if mnemonic in reg_mnemonics or mnemonic.endswith( ':' ) or mnemonic.startswith( ':' ) or mnemonic in ['SP', 'FP']:
            # Direct register - use the actual mnemonic from opcodes list
            register_map[ opcode_val ] = mnemonic
        else:
            # It's a standard instruction - for new system, size is operand count
            opcode_map[ opcode_val ] = ( mnemonic, size )  # Size is now operand count
            
    return opcode_map, register_map

def format_indexed_register(reg_code, offset_byte):
    """
    Format indexed register with offset for proper display.
    Returns formatted string like [FP-4], [P0+10], etc.
    """
    # Convert signed offset
    if offset_byte > 127:
        offset = offset_byte - 256  # Convert to signed
        offset_str = f"-{abs(offset)}"
    else:
        offset_str = f"+{offset_byte}" if offset_byte > 0 else ""
    
    # Map register codes to names
    if 0xE9 <= reg_code <= 0xF2:  # R indexed
        reg_name = f"R{reg_code - 0xE9}"
    elif 0xF3 <= reg_code <= 0xFB:  # P indexed (P0-P8)
        reg_name = f"P{reg_code - 0xF3}"
    elif reg_code == 0xFC:  # FP indexed (P9)
        reg_name = "FP"
    elif reg_code == 0xFD:  # VX indexed
        reg_name = "VX"
    elif reg_code == 0xFE:  # VY indexed
        reg_name = "VY"
    else:
        reg_name = f"0x{reg_code:02X}"
    
    if offset_str:
        return f"[{reg_name}{offset_str}]"
    else:
        return f"[{reg_name}]"

def is_string_data(bytecode, start_pos):
    """
    Check if data at start_pos looks like a null-terminated string.
    Returns (is_string, string_length) where string_length includes the null terminator.
    Be more conservative to avoid misinterpreting instructions as strings.
    """
    if start_pos >= len(bytecode):
        return False, 0
    
    length = 0
    pos = start_pos
    printable_count = 0
    
    # Look for printable ASCII characters followed by null terminator
    while pos < len(bytecode):
        byte = bytecode[pos]
        if byte == 0:  # Null terminator found
            # Only consider it a string if we have at least 3 printable characters
            # and the majority are printable
            if length >= 3 and printable_count >= length * 0.8:
                return True, length + 1  # Include null terminator in length
            else:
                return False, 0
        elif 32 <= byte <= 126:  # Printable ASCII range
            printable_count += 1
            length += 1
            pos += 1
            # Don't let strings get too long without validation
            if length > 50:
                return False, 0
        else:
            # Non-printable character that's not null - not a string
            return False, 0
    
    # Reached end of file without null terminator
    return False, 0

def format_string_data(bytecode, start_pos, length):
    """
    Format string data as a DEFSTR directive.
    """
    string_bytes = bytecode[start_pos:start_pos + length - 1]  # Exclude null terminator
    try:
        # Convert bytes to string, handling escape sequences
        string_content = ""
        for byte in string_bytes:
            if byte == ord('"'):
                string_content += '\\"'
            elif byte == ord('\\'):
                string_content += '\\\\'
            elif 32 <= byte <= 126:  # Printable ASCII
                string_content += chr(byte)
            else:
                string_content += f"\\x{byte:02X}"
        
        return f'DEFSTR "{string_content}"'
    except:
        # Fallback to hex dump if string conversion fails
        hex_bytes = ' '.join(f'{b:02X}' for b in bytecode[start_pos:start_pos + length])
        return f'DB {hex_bytes}'

def disassemble_instruction_new(bytecode, pc, opcode_map, register_map):
    """
    Disassemble a single instruction in the new prefixed operand format.
    Returns (mnemonic, operands_list, instruction_size)
    """
    if pc >= len(bytecode):
        return "???", [], 1
    
    opcode = bytecode[pc]
    if opcode not in opcode_map:
        return f"0x{opcode:02X}", [], 1
    
    mnemonic, operand_count = opcode_map[opcode]
    
    # For new format, read mode byte
    if pc + 1 >= len(bytecode):
        return mnemonic, [], 1  # Incomplete instruction
    
    mode_byte = bytecode[pc + 1]
    
    # Parse mode byte
    op1_mode = mode_byte & 0x03
    op2_mode = (mode_byte >> 2) & 0x03
    op3_mode = (mode_byte >> 4) & 0x03
    indexed = (mode_byte & (1 << 6)) != 0
    direct = (mode_byte & (1 << 7)) != 0
    
    operands = []
    current_pc = pc + 2  # Start after opcode and mode byte
    size = 2  # opcode + mode byte
    
    # Helper function to get register name from number
    def reg_num_to_name(reg_num):
        if 0xA9 <= reg_num <= 0xB2:
            return f"R{reg_num - 0xA9}"
        elif 0xB3 <= reg_num <= 0xBC:
            return f"P{reg_num - 0xB3}"
        elif reg_num == 0xBD:
            return "VX"
        elif reg_num == 0xBE:
            return "VY"
        elif reg_num == 0x5F:
            return "VM"
        elif reg_num == 0x60:
            return "VL"
        elif reg_num == 0x61:
            return "TT"
        elif reg_num == 0x62:
            return "TM"
        elif reg_num == 0x63:
            return "TC"
        elif reg_num == 0x64:
            return "TS"
        else:
            return f"0x{reg_num:02X}"
    
    # Parse operand 1
    if operand_count >= 1:
        if op1_mode == 0:  # Register direct
            if current_pc < len(bytecode):
                reg_num = bytecode[current_pc]
                operands.append(reg_num_to_name(reg_num))
                current_pc += 1
                size += 1
        elif op1_mode == 1:  # Immediate 8-bit
            if current_pc < len(bytecode):
                imm8 = bytecode[current_pc]
                operands.append(f"0x{imm8:02X}")
                current_pc += 1
                size += 1
        elif op1_mode == 2:  # Immediate 16-bit
            if current_pc + 1 < len(bytecode):
                high = bytecode[current_pc]
                low = bytecode[current_pc + 1]
                imm16 = (high << 8) | low
                operands.append(f"0x{imm16:04X}")
                current_pc += 2
                size += 2
        elif op1_mode == 3:  # Memory reference
            if direct and not indexed:
                # Direct memory address
                if current_pc + 1 < len(bytecode):
                    high = bytecode[current_pc]
                    low = bytecode[current_pc + 1]
                    addr = (high << 8) | low
                    operands.append(f"[0x{addr:04X}]")
                    current_pc += 2
                    size += 2
            elif not direct and not indexed:
                # Register indirect
                if current_pc < len(bytecode):
                    reg_num = bytecode[current_pc]
                    reg_name = reg_num_to_name(reg_num)
                    operands.append(f"[{reg_name}]")
                    current_pc += 1
                    size += 1
            elif not direct and indexed:
                # Register indexed
                if current_pc + 1 < len(bytecode):
                    reg_num = bytecode[current_pc]
                    offset = bytecode[current_pc + 1]
                    reg_name = reg_num_to_name(reg_num)
                    if offset > 127:
                        offset = offset - 256
                        operands.append(f"[{reg_name}{offset}]")
                    else:
                        operands.append(f"[{reg_name}+{offset}]")
                    current_pc += 2
                    size += 2
            elif direct and indexed:
                # Direct indexed
                if current_pc + 2 < len(bytecode):
                    high = bytecode[current_pc]
                    low = bytecode[current_pc + 1]
                    addr = (high << 8) | low
                    offset = bytecode[current_pc + 2]
                    if offset > 127:
                        offset = offset - 256
                        operands.append(f"[0x{addr:04X}{offset}]")
                    else:
                        operands.append(f"[0x{addr:04X}+{offset}]")
                    current_pc += 3
                    size += 3
    
    # Parse operand 2 (same logic as operand 1)
    if operand_count >= 2:
        if op2_mode == 0:  # Register direct
            if current_pc < len(bytecode):
                reg_num = bytecode[current_pc]
                operands.append(reg_num_to_name(reg_num))
                current_pc += 1
                size += 1
        elif op2_mode == 1:  # Immediate 8-bit
            if current_pc < len(bytecode):
                imm8 = bytecode[current_pc]
                operands.append(f"0x{imm8:02X}")
                current_pc += 1
                size += 1
        elif op2_mode == 2:  # Immediate 16-bit
            if current_pc + 1 < len(bytecode):
                high = bytecode[current_pc]
                low = bytecode[current_pc + 1]
                imm16 = (high << 8) | low
                operands.append(f"0x{imm16:04X}")
                current_pc += 2
                size += 2
        elif op2_mode == 3:  # Memory reference
            if direct and not indexed:
                # Direct memory address
                if current_pc + 1 < len(bytecode):
                    high = bytecode[current_pc]
                    low = bytecode[current_pc + 1]
                    addr = (high << 8) | low
                    operands.append(f"[0x{addr:04X}]")
                    current_pc += 2
                    size += 2
            elif not direct and not indexed:
                # Register indirect
                if current_pc < len(bytecode):
                    reg_num = bytecode[current_pc]
                    reg_name = reg_num_to_name(reg_num)
                    operands.append(f"[{reg_name}]")
                    current_pc += 1
                    size += 1
            elif not direct and indexed:
                # Register indexed
                if current_pc + 1 < len(bytecode):
                    reg_num = bytecode[current_pc]
                    offset = bytecode[current_pc + 1]
                    reg_name = reg_num_to_name(reg_num)
                    if offset > 127:
                        offset = offset - 256
                        operands.append(f"[{reg_name}{offset}]")
                    else:
                        operands.append(f"[{reg_name}+{offset}]")
                    current_pc += 2
                    size += 2
            elif direct and indexed:
                # Direct indexed
                if current_pc + 2 < len(bytecode):
                    high = bytecode[current_pc]
                    low = bytecode[current_pc + 1]
                    addr = (high << 8) | low
                    offset = bytecode[current_pc + 2]
                    if offset > 127:
                        offset = offset - 256
                        operands.append(f"[0x{addr:04X}{offset}]")
                    else:
                        operands.append(f"[0x{addr:04X}+{offset}]")
                    current_pc += 3
                    size += 3
    
    return mnemonic, operands, size

def disassemble( file_path, org_base=0x0000 ):
    """
    Reads a binary file and disassembles it into Nova-16 assembly code.
    This version correctly displays little-endian 16-bit values and detects string data.
    
    Args:
        file_path: Path to binary file to disassemble
        org_base: Base address offset from ORG directive (default 0x0000)
    """
    if not file_path:
        print( "No file selected." )
        return

    try:
        with open( file_path, 'rb' ) as f:
            bytecode = f.read()
    except FileNotFoundError:
        print( f"Error: File not found at '{file_path}'" )
        return

    opcode_map, register_map = create_reverse_maps()
    
    pc = 0
    while pc < len( bytecode ):
        address_str = f"{pc + org_base:04X}:"
        opcode = bytecode[ pc ]
        
        # Check if this looks like string data first
        is_string, str_length = is_string_data(bytecode, pc)
        if is_string and str_length > 1:  # At least one character plus null terminator
            # Display as DEFSTR
            hex_dump = ' '.join( f'{b:02X}' for b in bytecode[pc:pc + str_length] )
            # Truncate hex dump if too long for better readability
            if len(hex_dump) > 60:
                truncated_hex = ' '.join( f'{b:02X}' for b in bytecode[pc:pc + min(20, str_length)] )
                hex_dump = f"{truncated_hex}..."
            string_directive = format_string_data(bytecode, pc, str_length)
            print( f"{address_str:<6} {hex_dump:<12} {string_directive}" )
            pc += str_length
            continue
        
        if opcode in opcode_map:
            # Use new prefixed operand disassembly
            mnemonic, operands, size = disassemble_instruction_new(bytecode, pc, opcode_map, register_map)
            
            # Bounds check to prevent reading past the end of the file
            if pc + size > len( bytecode ):
                hex_dump = ' '.join( f'{b:02X}' for b in bytecode[pc:] )
                print( f"{address_str:<6} {hex_dump:<12} ??? (Incomplete instruction)" )
                break

            instruction_bytes = bytecode[ pc : pc + size ]
            hex_dump = ' '.join( f'{b:02X}' for b in instruction_bytes )
            
            # Format operands
            operand_str = ', '.join(operands) if operands else ""
            instruction_str = mnemonic
            print( f"{address_str:<6} {hex_dump:<12} {instruction_str:<8} {operand_str}" )

            pc += size
        else:
            hex_dump = f"{opcode:02X}"
            print( f"{address_str:<6} {hex_dump:<12} DB 0x{opcode:02X}" )
            pc += 1


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Nova-16 Disassembler')
    parser.add_argument('file', nargs='?', help='Binary file to disassemble')
    parser.add_argument('--org', type=lambda x: int(x, 0), default=0x0000, 
                        help='Base address (ORG directive) in hex, e.g., 0x1000')
    
    args = parser.parse_args()
    
    if args.file:
        file_path = args.file
    else:
        # Otherwise, open a file dialog to choose the file
        print( "Opening file dialog to select a .bin file..." )
        root = tk.Tk()
        root.withdraw()  # Hide the main Tkinter window
        file_path = filedialog.askopenfilename(
            title="Select a Nova-16 Binary File",
            filetypes=[ ( "Binary files", "*.bin" ), ( "All files", "*.*" ) ]
        )
        root.destroy()

    disassemble( file_path, args.org )

