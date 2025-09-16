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

        # Handle all register types (direct, indirect, indexed, high/low byte)
        if mnemonic in reg_mnemonics or mnemonic.endswith( ':' ) or mnemonic.startswith( ':' ) or mnemonic in ['SP', 'FP']:
            # Determine register type based on opcode range
            if 0xBF <= opcode_val <= 0xC8:  # R indirect
                reg_name = f"R{opcode_val - 0xBF}"
                register_map[ opcode_val ] = f"[{reg_name}]"
            elif 0xC9 <= opcode_val <= 0xD2:  # P indirect
                reg_name = f"P{opcode_val - 0xC9}"
                register_map[ opcode_val ] = f"[{reg_name}]"
            elif 0xD3 <= opcode_val <= 0xD4:  # V indirect
                reg_name = "VX" if opcode_val == 0xD3 else "VY"
                register_map[ opcode_val ] = f"[{reg_name}]"
            elif 0xE9 <= opcode_val <= 0xF2:  # R indexed
                reg_name = f"R{opcode_val - 0xE9}"
                register_map[ opcode_val ] = f"R{opcode_val - 0xE9}_indexed"
            elif 0xF3 <= opcode_val <= 0xFB:  # P indexed (P0-P8)
                reg_name = f"P{opcode_val - 0xF3}"
                register_map[ opcode_val ] = f"P{opcode_val - 0xF3}_indexed"
            elif opcode_val == 0xFC:  # FP indexed (P9)
                register_map[ opcode_val ] = "FP_indexed"
            elif 0xFD <= opcode_val <= 0xFE:  # V indexed
                reg_name = "VX" if opcode_val == 0xFD else "VY"
                register_map[ opcode_val ] = f"{reg_name}_indexed"
            elif 0xD5 <= opcode_val <= 0xDE:  # P high byte
                reg_name = f"P{opcode_val - 0xD5}"
                register_map[ opcode_val ] = f"{reg_name}:"
            elif 0xDF <= opcode_val <= 0xE8:  # P low byte
                reg_name = f"P{opcode_val - 0xDF}"
                register_map[ opcode_val ] = f":{reg_name}"
            else:
                # Direct register - use the actual mnemonic from opcodes list
                register_map[ opcode_val ] = mnemonic
        else:
            # It's a standard instruction
            opcode_map[ opcode_val ] = ( mnemonic, size )
            
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
            mnemonic, size = opcode_map[ opcode ]
            
            # Bounds check to prevent reading past the end of the file
            if pc + size > len( bytecode ):
                hex_dump = ' '.join( f'{b:02X}' for b in bytecode[pc:] )
                print( f"{address_str:<6} {hex_dump:<12} ??? (Incomplete instruction)" )
                break

            instruction_bytes = bytecode[ pc : pc + size ]
            hex_dump = ' '.join( f'{b:02X}' for b in instruction_bytes )
            
            operands = []
            op_pc = 1 

            # Parse operands based on mnemonic pattern
            if mnemonic == "MOV reg direct":
                # opcode + reg + addr16
                if op_pc < len( instruction_bytes ):
                    reg_code = instruction_bytes[ op_pc ]
                    operands.append( register_map.get( reg_code, f"0x{reg_code:02X}" ) )
                    op_pc += 1
                if op_pc + 1 < len( instruction_bytes ):
                    high_byte = instruction_bytes[ op_pc ]
                    low_byte = instruction_bytes[ op_pc + 1 ]
                    addr = ( high_byte << 8 ) | low_byte
                    operands.append( f"[0x{addr:04X}]" )
                    op_pc += 2
            elif mnemonic == "MOV direct reg":
                # opcode + addr16 + reg
                if op_pc + 1 < len( instruction_bytes ):
                    high_byte = instruction_bytes[ op_pc ]
                    low_byte = instruction_bytes[ op_pc + 1 ]
                    addr = ( high_byte << 8 ) | low_byte
                    operands.append( f"[0x{addr:04X}]" )
                    op_pc += 2
                if op_pc < len( instruction_bytes ):
                    reg_code = instruction_bytes[ op_pc ]
                    operands.append( register_map.get( reg_code, f"0x{reg_code:02X}" ) )
                    op_pc += 1
            elif mnemonic == "MOV reg regIndir":
                # opcode + dest_reg + src_reg (indirect)
                if op_pc < len( instruction_bytes ):
                    reg_code = instruction_bytes[ op_pc ]
                    operands.append( register_map.get( reg_code, f"0x{reg_code:02X}" ) )
                    op_pc += 1
                if op_pc < len( instruction_bytes ):
                    reg_code = instruction_bytes[ op_pc ]
                    # The indirect register is already encoded in the register code
                    operands.append( register_map.get( reg_code, f"0x{reg_code:02X}" ) )
                    op_pc += 1
            elif mnemonic == "MOV regIndir reg":
                # opcode + dest_reg (indirect) + src_reg
                if op_pc < len( instruction_bytes ):
                    reg_code = instruction_bytes[ op_pc ]
                    # The indirect register is already encoded in the register code
                    operands.append( register_map.get( reg_code, f"0x{reg_code:02X}" ) )
                    op_pc += 1
                if op_pc < len( instruction_bytes ):
                    reg_code = instruction_bytes[ op_pc ]
                    operands.append( register_map.get( reg_code, f"0x{reg_code:02X}" ) )
                    op_pc += 1
            elif mnemonic == "MOV reg regIndex":
                # opcode + dest_reg + src_reg (indexed) + offset
                if op_pc < len( instruction_bytes ):
                    reg_code = instruction_bytes[ op_pc ]
                    operands.append( register_map.get( reg_code, f"0x{reg_code:02X}" ) )
                    op_pc += 1
                if op_pc < len( instruction_bytes ):
                    reg_code = instruction_bytes[ op_pc ]
                    op_pc += 1
                    # Check if there's an offset byte
                    if op_pc < len( instruction_bytes ):
                        offset_byte = instruction_bytes[ op_pc ]
                        formatted_reg = format_indexed_register(reg_code, offset_byte)
                        operands.append( formatted_reg )
                        op_pc += 1
                    else:
                        # Fallback for instructions without offset
                        operands.append( register_map.get( reg_code, f"0x{reg_code:02X}" ) )
            elif mnemonic == "MOV regIndex reg":
                # opcode + dest_reg (indexed) + offset + src_reg
                if op_pc < len( instruction_bytes ):
                    reg_code = instruction_bytes[ op_pc ]
                    op_pc += 1
                    # Get the offset byte
                    if op_pc < len( instruction_bytes ):
                        offset_byte = instruction_bytes[ op_pc ]
                        formatted_reg = format_indexed_register(reg_code, offset_byte)
                        operands.append( formatted_reg )
                        op_pc += 1
                    else:
                        # Fallback for instructions without offset
                        operands.append( register_map.get( reg_code, f"0x{reg_code:02X}" ) )
                if op_pc < len( instruction_bytes ):
                    reg_code = instruction_bytes[ op_pc ]
                    operands.append( register_map.get( reg_code, f"0x{reg_code:02X}" ) )
                    op_pc += 1
            elif mnemonic == "MOV regIndir imm8":
                # opcode + dest_reg (indirect) + imm8
                if op_pc < len( instruction_bytes ):
                    reg_code = instruction_bytes[ op_pc ]
                    # The indirect register is already encoded in the register code
                    operands.append( register_map.get( reg_code, f"0x{reg_code:02X}" ) )
                    op_pc += 1
                if op_pc < len( instruction_bytes ):
                    imm8 = instruction_bytes[ op_pc ]
                    operands.append( f"0x{imm8:02X}" )
                    op_pc += 1
            elif mnemonic == "MOV regIndex imm8":
                # opcode + dest_reg (indexed) + offset + imm8
                if op_pc < len( instruction_bytes ):
                    reg_code = instruction_bytes[ op_pc ]
                    op_pc += 1
                    # Check if there's an offset byte
                    if op_pc < len( instruction_bytes ):
                        offset_byte = instruction_bytes[ op_pc ]
                        formatted_reg = format_indexed_register(reg_code, offset_byte)
                        operands.append( formatted_reg )
                        op_pc += 1
                    else:
                        # Fallback for instructions without offset
                        operands.append( register_map.get( reg_code, f"0x{reg_code:02X}" ) )
                if op_pc < len( instruction_bytes ):
                    imm8 = instruction_bytes[ op_pc ]
                    operands.append( f"0x{imm8:02X}" )
                    op_pc += 1
            elif mnemonic == "MOV regIndir imm16":
                # opcode + dest_reg (indirect) + imm16
                if op_pc < len( instruction_bytes ):
                    reg_code = instruction_bytes[ op_pc ]
                    # The indirect register is already encoded in the register code
                    operands.append( register_map.get( reg_code, f"0x{reg_code:02X}" ) )
                    op_pc += 1
                if op_pc + 1 < len( instruction_bytes ):
                    high_byte = instruction_bytes[ op_pc ]
                    low_byte = instruction_bytes[ op_pc + 1 ]
                    imm16 = ( high_byte << 8 ) | low_byte
                    operands.append( f"0x{imm16:04X}" )
                    op_pc += 2
            elif mnemonic == "MOV regIndex imm16":
                # opcode + dest_reg (indexed) + offset + imm16
                if op_pc < len( instruction_bytes ):
                    reg_code = instruction_bytes[ op_pc ]
                    op_pc += 1
                    # Check if there's an offset byte
                    if op_pc < len( instruction_bytes ):
                        offset_byte = instruction_bytes[ op_pc ]
                        formatted_reg = format_indexed_register(reg_code, offset_byte)
                        operands.append( formatted_reg )
                        op_pc += 1
                    else:
                        # Fallback for instructions without offset
                        operands.append( register_map.get( reg_code, f"0x{reg_code:02X}" ) )
                if op_pc + 1 < len( instruction_bytes ):
                    high_byte = instruction_bytes[ op_pc ]
                    low_byte = instruction_bytes[ op_pc + 1 ]
                    imm16 = ( high_byte << 8 ) | low_byte
                    operands.append( f"0x{imm16:04X}" )
                    op_pc += 2
            else:
                # Default parsing for other instructions
                # Parse based on the mnemonic structure
                parts = mnemonic.split()
                
                # Skip the instruction name (first part)
                for part in parts[1:]:
                    if part == 'reg':
                        if op_pc < len( instruction_bytes ):
                            reg_code = instruction_bytes[ op_pc ]
                            operands.append( register_map.get( reg_code, f"0x{reg_code:02X}" ) )
                            op_pc += 1
                    elif part == 'imm8':
                        if op_pc < len( instruction_bytes ):
                            imm8 = instruction_bytes[ op_pc ]
                            operands.append( f"0x{imm8:02X}" )
                            op_pc += 1
                    elif part == 'imm16':
                        if op_pc + 1 < len( instruction_bytes ):
                            high_byte = instruction_bytes[ op_pc ]
                            low_byte = instruction_bytes[ op_pc + 1 ]
                            imm16 = ( high_byte << 8 ) | low_byte
                            operands.append( f"0x{imm16:04X}" )
                            op_pc += 2

            instruction_str = mnemonic.split( ' ' )[ 0 ]
            operands_str = ", ".join( operands )
            print( f"{address_str:<6} {hex_dump:<12} {instruction_str:<8} {operands_str}" )

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

