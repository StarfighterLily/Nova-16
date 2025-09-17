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

def load_symbol_table(sym_file_path):
    """
    Load symbol table from .sym file.
    Returns a dictionary mapping symbol names to addresses.
    """
    symbol_table = {}
    try:
        with open(sym_file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    parts = line.split()
                    if len(parts) >= 2:
                        symbol = parts[0]
                        addr_str = parts[1]
                        symbol_table[symbol] = addr_str
    except FileNotFoundError:
        pass  # Symbol file is optional
    return symbol_table

def load_org_segments(org_file_path):
    """
    Load ORG segments from .org file.
    Returns a list of (start_address, length, binary_offset) tuples.
    """
    segments = []
    try:
        with open(org_file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    parts = line.split()
                    if len(parts) >= 3:
                        start_addr = int(parts[0], 16)
                        length = int(parts[1])
                        binary_offset = int(parts[2])
                        segments.append((start_addr, length, binary_offset))
    except FileNotFoundError:
        pass  # ORG file is optional
    return segments

def resolve_symbol(value, symbol_table):
    """
    Try to resolve a value to a symbol name.
    Returns the symbol name if found, otherwise the hex value.
    """
    hex_value = f"0x{value:04X}"
    for symbol, addr_str in symbol_table.items():
        if addr_str == hex_value:
            return symbol
    return hex_value

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
    
    # For instructions with no operands, no mode byte
    if operand_count == 0:
        return mnemonic, [], 1
    
    # For new format, read mode byte
    if pc + 1 >= len(bytecode):
        return mnemonic, [], 1  # Incomplete instruction
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
        # Direct register access (from opcodes.py)
        if reg_num == 0xDD:
            return "SA"
        elif reg_num == 0xDE:
            return "SF"
        elif reg_num == 0xDF:
            return "SV"
        elif reg_num == 0xE0:
            return "SW"
        elif reg_num == 0xE1:
            return "VM"
        elif reg_num == 0xE2:
            return "VL"
        elif reg_num == 0xE3:
            return "TT"
        elif reg_num == 0xE4:
            return "TM"
        elif reg_num == 0xE5:
            return "TC"
        elif reg_num == 0xE6:
            return "TS"
        elif 0xE7 <= reg_num <= 0xF0:
            return f"R{reg_num - 0xE7}"
        elif 0xF1 <= reg_num <= 0xFA:
            return f"P{reg_num - 0xF1}"
        elif reg_num == 0xFB:
            return "SP"
        elif reg_num == 0xFC:
            return "FP"
        elif reg_num == 0xFD:
            return "VX"
        elif reg_num == 0xFE:
            return "VY"
        # Indirect/indexed register access
        elif 0xA9 <= reg_num <= 0xB2:
            return f"R{reg_num - 0xA9}"
        elif 0xB3 <= reg_num <= 0xBC:
            return f"P{reg_num - 0xB3}"
        elif reg_num == 0xBD:
            return "VX"
        elif reg_num == 0xBE:
            return "VY"
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

    # Load symbol table and ORG segments
    base_name = file_path.rsplit('.', 1)[0]  # Remove .bin extension
    symbol_table = load_symbol_table(base_name + '.sym')
    segments = load_org_segments(base_name + '.org')
    
    # Create reverse symbol table (address -> symbol)
    reverse_symbol_table = {}
    for symbol, addr_str in symbol_table.items():
        if addr_str.startswith('0x'):
            try:
                addr = int(addr_str, 16)
                reverse_symbol_table[addr] = symbol
            except ValueError:
                pass
    
    # Get all labels sorted by address
    labels = sorted((int(addr_str, 16), name) for name, addr_str in symbol_table.items() if addr_str.startswith('0x'))
    label_idx = 0

    opcode_map, register_map = create_reverse_maps()
    
    # Sort segments by binary offset
    segments.sort(key=lambda x: x[2])
    
    # Process each segment
    for segment_idx, (start_addr, length, bin_offset) in enumerate(segments):
        # Show ORG directive for segments after the first
        if segment_idx > 0:
            print(f"\nORG 0x{start_addr:04X}")
        
        pc = bin_offset
        end_pc = bin_offset + length
        
        while pc < end_pc:
            current_addr = start_addr + (pc - bin_offset)
            
            # Print any labels that are at or before this address
            while label_idx < len(labels) and labels[label_idx][0] <= current_addr:
                addr, name = labels[label_idx]
                print(f"\n{name}:")
                label_idx += 1
            
            address_str = f"{current_addr:04X}:"
            
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
            
            # Check for DW directive (16-bit data)
            if pc + 1 < end_pc and opcode not in opcode_map:
                # Check if next byte is also not an opcode (likely data)
                next_byte = bytecode[pc + 1]
                if next_byte not in opcode_map:
                    # Try to interpret as DW
                    value = (next_byte << 8) | opcode
                    resolved_value = resolve_symbol(value, symbol_table)
                    hex_dump = f"{opcode:02X} {next_byte:02X}"
                    print( f"{address_str:<6} {hex_dump:<12} DW {resolved_value}" )
                    pc += 2
                    continue
            
            if opcode in opcode_map:
                # Use new prefixed operand disassembly
                mnemonic, operands, size = disassemble_instruction_new(bytecode, pc, opcode_map, register_map)
                
                # Check if instruction is incomplete (has operands but none parsed)
                instr_info = opcode_map.get(opcode)
                if instr_info:
                    _, operand_count = instr_info
                    if operand_count > 0 and len(operands) == 0 and pc + 1 < end_pc:
                        # Incomplete instruction, likely data - show as DW
                        value = (bytecode[pc] << 8) | bytecode[pc + 1]  # Big-endian
                        resolved_value = resolve_symbol(value, symbol_table)
                        hex_dump = f"{bytecode[pc]:02X} {bytecode[pc + 1]:02X}"
                        print( f"{address_str:<6} {hex_dump:<12} DW {resolved_value}" )
                        pc += 2
                        continue
                
                # Bounds check to prevent reading past the end of the segment
                if pc + size > end_pc:
                    hex_dump = ' '.join( f'{b:02X}' for b in bytecode[pc:end_pc] )
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

def analyze_control_flow(bytecode, segments, opcode_map, register_map, reverse_symbol_table, symbol_table):
    """
    Generate comprehensive control flow analysis.
    Returns a dictionary with control flow information.
    """
    control_flow = {
        'basic_blocks': {},
        'control_flow_graph': {},
        'functions': {},
        'calls': [],
        'jumps': [],
        'returns': []
    }
    
    # First pass: identify all potential leaders (function starts, jump targets, etc.)
    leaders = set()
    
    # Add function starts from symbol table
    for symbol, addr_str in symbol_table.items():
        if addr_str.startswith('0x'):
            try:
                addr = int(addr_str, 16)
                leaders.add(addr)
                control_flow['functions'][addr] = {
                    'name': symbol,
                    'basic_blocks': []
                }
            except ValueError:
                pass
    
    # Second pass: scan for control flow instructions
    for start_addr, length, bin_offset in segments:
        pc = bin_offset
        end_pc = bin_offset + length
        
        while pc < end_pc:
            current_addr = start_addr + (pc - bin_offset)
            opcode = bytecode[pc]
            
            if opcode in opcode_map:
                mnemonic, operands, size = disassemble_instruction_new(bytecode, pc, opcode_map, register_map)
                
                if pc + size <= len(bytecode):
                    # Check for control flow instructions
                    if mnemonic in ['JMP', 'JZ', 'JNZ', 'JC', 'JNC', 'JO', 'JNO', 'JS', 'JNS']:
                        # Jump instructions
                        if operands:
                            target = operands[-1]  # Last operand is usually the target
                            if target.startswith('0x'):
                                try:
                                    target_addr = int(target, 16)
                                    leaders.add(target_addr)
                                    control_flow['jumps'].append((current_addr, target_addr))
                                except ValueError:
                                    pass
                    
                    elif mnemonic == 'CALL':
                        # Function calls
                        if operands:
                            target = operands[-1]
                            if target.startswith('0x'):
                                try:
                                    target_addr = int(target, 16)
                                    leaders.add(target_addr)
                                    control_flow['calls'].append((current_addr, target_addr))
                                except ValueError:
                                    pass
                    
                    elif mnemonic in ['RET', 'IRET']:
                        # Returns
                        control_flow['returns'].append(current_addr)
                        # Next instruction is a leader
                        if pc + size < end_pc:
                            next_addr = start_addr + (pc + size - bin_offset)
                            leaders.add(next_addr)
                    
                    pc += size
            else:
                pc += 1
    
    # Third pass: build basic blocks
    current_block = None
    block_start = None
    
    for start_addr, length, bin_offset in segments:
        pc = bin_offset
        end_pc = bin_offset + length
        
        while pc < end_pc:
            current_addr = start_addr + (pc - bin_offset)
            
            # Check if this is a leader
            if current_addr in leaders:
                # End current block
                if current_block is not None:
                    control_flow['basic_blocks'][block_start] = {
                        'end_addr': current_addr - 1,
                        'instructions': current_block['instructions'],
                        'successors': []
                    }
                
                # Start new block
                current_block = {
                    'instructions': [],
                    'start_addr': current_addr
                }
                block_start = current_addr
            
            if current_block is not None:
                current_block['instructions'].append(current_addr)
            
            # Get instruction size
            opcode = bytecode[pc]
            if opcode in opcode_map:
                _, _, size = disassemble_instruction_new(bytecode, pc, opcode_map, register_map)
                pc += size
            else:
                pc += 1
        
        # End last block
        if current_block is not None:
            control_flow['basic_blocks'][block_start] = {
                'end_addr': start_addr + (pc - bin_offset) - 1,
                'instructions': current_block['instructions'],
                'successors': []
            }
    
    # Build control flow graph
    for block_addr, block_info in control_flow['basic_blocks'].items():
        successors = []
        
        # Check last instruction of block
        last_instr = block_info['instructions'][-1] if block_info['instructions'] else None
        if last_instr is not None:
            # Find the instruction details
            for start_addr, length, bin_offset in segments:
                if start_addr <= last_instr < start_addr + length:
                    rel_pc = last_instr - start_addr + bin_offset
                    if rel_pc < len(bytecode):
                        opcode = bytecode[rel_pc]
                        if opcode in opcode_map:
                            mnemonic, operands, size = disassemble_instruction_new(bytecode, rel_pc, opcode_map, register_map)
                            
                            if mnemonic in ['JMP', 'JZ', 'JNZ', 'JC', 'JNC', 'JO', 'JNO', 'JS', 'JNS']:
                                # Unconditional jump
                                if operands:
                                    target = operands[-1]
                                    if target.startswith('0x'):
                                        try:
                                            target_addr = int(target, 16)
                                            successors.append(target_addr)
                                        except ValueError:
                                            pass
                            
                            elif mnemonic == 'CALL':
                                # Call - successor is next instruction
                                next_addr = last_instr + size
                                successors.append(next_addr)
                            
                            elif mnemonic in ['RET', 'IRET', 'HLT']:
                                # No successors
                                pass
                            
                            else:
                                # Fall through to next instruction
                                next_addr = last_instr + size
                                successors.append(next_addr)
        
        control_flow['control_flow_graph'][block_addr] = successors
        block_info['successors'] = successors
    
    # Associate basic blocks with functions
    for func_addr, func_info in control_flow['functions'].items():
        func_blocks = []
        for block_addr in control_flow['basic_blocks']:
            if block_addr >= func_addr:
                func_blocks.append(block_addr)
        func_info['basic_blocks'] = sorted(func_blocks)
    
    return control_flow

def generate_cross_references(bytecode, segments, opcode_map, register_map, reverse_symbol_table, symbol_table):
    """
    Generate comprehensive cross-reference tables for all symbols.
    Returns a dictionary with cross-reference information.
    """
    xrefs = {}
    
    # Initialize xref entries for all symbols
    for symbol, value in symbol_table.items():
        if value.startswith('0x'):
            try:
                addr = int(value, 16)
                xrefs[symbol] = {
                    'address': addr,
                    'references': [],  # List of (address, type) where this symbol is referenced
                    'definition': None  # Where this symbol is defined (if known)
                }
            except ValueError:
                pass
    
    # Also add entries for addresses that have symbols but might not be in symbol_table
    for addr, symbol in reverse_symbol_table.items():
        if symbol not in xrefs:
            xrefs[symbol] = {
                'address': addr,
                'references': [],
                'definition': None
            }
    
    # Scan through all code to find references
    for start_addr, length, bin_offset in segments:
        pc = bin_offset
        end_pc = bin_offset + length
        
        while pc < end_pc:
            current_addr = start_addr + (pc - bin_offset)
            opcode = bytecode[pc]
            
            if opcode in opcode_map:
                mnemonic, operands, size = disassemble_instruction_new(bytecode, pc, opcode_map, register_map)
                
                if pc + size <= len(bytecode):
                    # Check each operand for symbol references
                    for operand in operands:
                        # Check for direct symbol references
                        if operand in xrefs:
                            xrefs[operand]['references'].append((current_addr, 'direct'))
                        
                        # Check for address references that match symbol addresses
                        if operand.startswith('0x'):
                            try:
                                ref_addr = int(operand, 16)
                                # Find if this address has a symbol
                                if ref_addr in reverse_symbol_table:
                                    symbol = reverse_symbol_table[ref_addr]
                                    if symbol in xrefs:
                                        xrefs[symbol]['references'].append((current_addr, 'address'))
                            except ValueError:
                                pass
                    
                    # Special handling for data references (DW, DB with symbols)
                    if mnemonic.upper() in ['DW', 'DB'] and operands:
                        for operand in operands:
                            if operand in xrefs:
                                xrefs[operand]['references'].append((current_addr, 'data'))
                
                pc += size
            else:
                pc += 1
    
    # Sort references by address
    for symbol in xrefs:
        xrefs[symbol]['references'].sort(key=lambda x: x[0])
    
    return xrefs

def generate_annotations(bytecode, segments, control_flow, xrefs, symbol_table, reverse_symbol_table):
    """
    Generate annotations and comments for the disassembly.
    Returns a dictionary mapping addresses to annotation strings.
    """
    annotations = {}
    
    opcode_map, register_map = create_reverse_maps()
    
    # Annotate function starts
    for func_addr, func_info in control_flow['functions'].items():
        annotations[func_addr] = f"; Function {func_info['name']}"
    
    # Annotate basic block starts
    for block_addr in control_flow['basic_blocks']:
        if block_addr not in annotations:  # Don't overwrite function annotations
            annotations[block_addr] = "; Basic block"
    
    # Annotate control flow instructions
    for jump_addr, target_addr in control_flow['jumps']:
        target_symbol = reverse_symbol_table.get(target_addr, f"0x{target_addr:04X}")
        annotations[jump_addr] = f"; Jump to {target_symbol}"
    
    for call_addr, target_addr in control_flow['calls']:
        target_symbol = reverse_symbol_table.get(target_addr, f"0x{target_addr:04X}")
        annotations[call_addr] = f"; Call {target_symbol}"
    
    # Annotate returns
    for ret_addr in control_flow['returns']:
        annotations[ret_addr] = "; Return from function"
    
    # Annotate data references
    for symbol, info in xrefs.items():
        for ref_addr, ref_type in info['references']:
            if ref_type == 'data':
                annotations[ref_addr] = f"; References {symbol}"
            elif ref_type == 'address':
                annotations[ref_addr] = f"; Address of {symbol}"
    
    # Annotate register usage patterns
    for start_addr, length, bin_offset in segments:
        pc = bin_offset
        end_pc = bin_offset + length
        
        while pc < end_pc:
            current_addr = start_addr + (pc - bin_offset)
            opcode = bytecode[pc]
            
            if opcode in opcode_map:
                mnemonic, operands, size = disassemble_instruction_new(bytecode, pc, opcode_map, register_map)
                
                if pc + size <= len(bytecode):
                    # Add annotations for specific instruction patterns
                    if mnemonic == 'MOV' and len(operands) >= 2:
                        dest, src = operands[0], operands[1]
                        if dest in ['VM', 'VX', 'VY', 'VL']:
                            annotations[current_addr] = "; Graphics register setup"
                        elif dest in ['SA', 'SF', 'SV', 'SW']:
                            annotations[current_addr] = "; Sound register setup"
                        elif dest in ['TT', 'TM', 'TC', 'TS']:
                            annotations[current_addr] = "; Timer register setup"
                    
                    elif mnemonic in ['PUSH', 'POP']:
                        annotations[current_addr] = "; Stack operation"
                    
                    elif mnemonic == 'INT':
                        annotations[current_addr] = "; Software interrupt"
                    
                    pc += size
            else:
                pc += 1
    
    return annotations

def analyze_performance(bytecode, segments, opcode_map, register_map, reverse_symbol_table):
    """
    Analyze performance characteristics of the code.
    Returns performance metrics and profiling information.
    """
    performance = {
        'instruction_counts': {},
        'instruction_cycles': {},
        'total_instructions': 0,
        'estimated_cycles': 0,
        'hotspots': [],
        'memory_accesses': 0,
        'control_flow_instructions': 0
    }
    
    # Define cycle counts for different instruction types (approximate)
    cycle_counts = {
        'MOV': 2,
        'ADD': 3,
        'SUB': 3,
        'MUL': 4,
        'DIV': 8,
        'AND': 2,
        'OR': 2,
        'XOR': 2,
        'NOT': 2,
        'CMP': 3,
        'INC': 2,
        'DEC': 2,
        'SHL': 3,
        'SHR': 3,
        'JMP': 3,
        'JZ': 3,
        'JNZ': 3,
        'JC': 3,
        'JNC': 3,
        'CALL': 4,
        'RET': 4,
        'PUSH': 2,
        'POP': 2,
        'INT': 8,
        'IRET': 6,
        'STI': 1,
        'CLI': 1,
        'HLT': 1,
        'NOP': 1,
        'SWRITE': 2,
        'SREAD': 2,
        'KEYSTAT': 2,
        'KEYIN': 3,
        'TEXT': 2,
        'BCDA': 2,
        'BCDCMP': 3,
        'SROLX': 2,
        'DW': 0,  # Data directive
        'DB': 0   # Data directive
    }
    
    # Scan through all instructions
    for start_addr, length, bin_offset in segments:
        pc = bin_offset
        end_pc = bin_offset + length
        
        while pc < end_pc:
            current_addr = start_addr + (pc - bin_offset)
            opcode = bytecode[pc]
            
            if opcode in opcode_map:
                mnemonic, operands, size = disassemble_instruction_new(bytecode, pc, opcode_map, register_map)
                
                if pc + size <= len(bytecode):
                    # Count instruction
                    performance['instruction_counts'][mnemonic] = performance['instruction_counts'].get(mnemonic, 0) + 1
                    performance['total_instructions'] += 1
                    
                    # Add cycles
                    cycles = cycle_counts.get(mnemonic, 2)  # Default 2 cycles
                    performance['instruction_cycles'][mnemonic] = performance['instruction_cycles'].get(mnemonic, 0) + cycles
                    performance['estimated_cycles'] += cycles
                    
                    # Count memory accesses
                    if mnemonic in ['MOV', 'ADD', 'SUB', 'AND', 'OR', 'XOR', 'CMP'] and any('[' in op for op in operands):
                        performance['memory_accesses'] += 1
                    
                    # Count control flow instructions
                    if mnemonic in ['JMP', 'JZ', 'JNZ', 'JC', 'JNC', 'JO', 'JNO', 'JS', 'JNS', 'CALL', 'RET', 'IRET', 'INT']:
                        performance['control_flow_instructions'] += 1
                    
                    pc += size
            else:
                pc += 1
    
    # Generate hotspots (instructions with highest cycle counts)
    hotspots = []
    for mnemonic, cycles in performance['instruction_cycles'].items():
        hotspots.append((mnemonic, cycles))
    
    hotspots.sort(key=lambda x: x[1], reverse=True)
    performance['hotspots'] = hotspots[:10]  # Top 10
    
    return performance

def export_to_json(file_path, bytecode, segments, control_flow, xrefs, symbol_table, reverse_symbol_table):
    """Export disassembly and analysis to JSON format"""
    import json
    
    opcode_map, register_map = create_reverse_maps()
    
    # Generate disassembly data
    disassembly = []
    for start_addr, length, bin_offset in segments:
        pc = bin_offset
        end_pc = bin_offset + length
        
        while pc < end_pc:
            current_addr = start_addr + (pc - bin_offset)
            opcode = bytecode[pc]
            
            if opcode in opcode_map:
                mnemonic, operands, size = disassemble_instruction_new(bytecode, pc, opcode_map, register_map)
                
                if pc + size <= len(bytecode):
                    instruction_bytes = bytecode[pc:pc + size]
                    hex_dump = ' '.join(f'{b:02X}' for b in instruction_bytes)
                    
                    disassembly.append({
                        'address': current_addr,
                        'mnemonic': mnemonic,
                        'operands': operands,
                        'bytes': hex_dump,
                        'symbol': reverse_symbol_table.get(current_addr, None)
                    })
                
                pc += size
            else:
                disassembly.append({
                    'address': current_addr,
                    'mnemonic': 'DB',
                    'operands': [f'0x{opcode:02X}'],
                    'bytes': f'{opcode:02X}',
                    'symbol': reverse_symbol_table.get(current_addr, None)
                })
                pc += 1
    
    # Prepare data for JSON export
    data = {
        'file': file_path,
        'timestamp': __import__('datetime').datetime.now().isoformat(),
        'symbols': symbol_table,
        'reverse_symbols': {int(k): v for k, v in reverse_symbol_table.items()},
        'disassembly': disassembly,
        'basic_blocks': {int(k): {'end_addr': int(v['end_addr']), 'instructions': v['instructions'], 'successors': [int(s) for s in v['successors']]} for k, v in control_flow['basic_blocks'].items()},
        'control_flow_graph': {int(k): [int(s) for s in v] for k, v in control_flow['control_flow_graph'].items()},
        'functions': {int(k): v for k, v in control_flow['functions'].items()},
        'calls': [(int(addr), int(target)) for addr, target in control_flow['calls']],
        'jumps': [(int(addr), int(target)) for addr, target in control_flow['jumps']],
        'cross_references': {k: {'address': int(v['address']), 'references': v['references'], 'definition': v['definition']} for k, v in xrefs.items()}
    }
    
    # Write to file
    json_file = file_path.replace('.bin', '.json')
    with open(json_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"JSON data exported to: {json_file}")

def export_to_html(file_path, bytecode, segments, control_flow, xrefs, symbol_table, reverse_symbol_table, annotations, performance):
    """Export disassembly and analysis to HTML format"""
    import json
    
    opcode_map, register_map = create_reverse_maps()
    
    # Generate disassembly data
    disassembly = []
    for start_addr, length, bin_offset in segments:
        pc = bin_offset
        end_pc = bin_offset + length
        
        while pc < end_pc:
            current_addr = start_addr + (pc - bin_offset)
            opcode = bytecode[pc]
            
            if opcode in opcode_map:
                mnemonic, operands, size = disassemble_instruction_new(bytecode, pc, opcode_map, register_map)
                
                if pc + size <= len(bytecode):
                    instruction_bytes = bytecode[pc:pc + size]
                    hex_dump = ' '.join(f'{b:02X}' for b in instruction_bytes)
                    
                    disassembly.append({
                        'address': current_addr,
                        'mnemonic': mnemonic,
                        'operands': operands,
                        'bytes': hex_dump,
                        'symbol': reverse_symbol_table.get(current_addr, None),
                        'annotation': annotations.get(current_addr, '')
                    })
                
                pc += size
            else:
                disassembly.append({
                    'address': current_addr,
                    'mnemonic': 'DB',
                    'operands': [f'0x{opcode:02X}'],
                    'bytes': f'{opcode:02X}',
                    'symbol': reverse_symbol_table.get(current_addr, None),
                    'annotation': annotations.get(current_addr, '')
                })
                pc += 1
    
    # Generate HTML content
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Nova-16 Disassembly - {file_path}</title>
    <style>
        body {{ font-family: 'Courier New', monospace; margin: 20px; }}
        .header {{ background: #f0f0f0; padding: 10px; margin-bottom: 20px; }}
        .section {{ margin-bottom: 30px; }}
        .section h2 {{ color: #333; border-bottom: 2px solid #333; padding-bottom: 5px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .address {{ color: #666; font-weight: bold; }}
        .mnemonic {{ color: #000080; font-weight: bold; }}
        .operand {{ color: #008000; }}
        .bytes {{ color: #800080; font-size: 0.9em; }}
        .symbol {{ color: #ff6600; font-weight: bold; }}
        .annotation {{ color: #666; font-style: italic; }}
        .function {{ background-color: #e6f3ff; }}
        .jump {{ background-color: #fff2e6; }}
        .call {{ background-color: #e6ffe6; }}
        .hotspot {{ background-color: #ffe6e6; }}
        .stats {{ background-color: #f9f9f9; padding: 15px; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Nova-16 Disassembly Analysis</h1>
        <p><strong>File:</strong> {file_path}</p>
        <p><strong>Generated:</strong> {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="section stats">
        <h2>Performance Statistics</h2>
        <p><strong>Total Instructions:</strong> {performance['total_instructions']}</p>
        <p><strong>Estimated Cycles:</strong> {performance['estimated_cycles']}</p>
        <p><strong>Memory Accesses:</strong> {performance['memory_accesses']}</p>
        <p><strong>Control Flow Instructions:</strong> {performance['control_flow_instructions']}</p>
    </div>
    
    <div class="section">
        <h2>Disassembly</h2>
        <table>
            <thead>
                <tr>
                    <th>Address</th>
                    <th>Bytes</th>
                    <th>Mnemonic</th>
                    <th>Operands</th>
                    <th>Symbol</th>
                    <th>Annotation</th>
                </tr>
            </thead>
            <tbody>
"""
    
    # Add disassembly rows
    for instr in disassembly:
        addr = instr['address']
        css_class = ""
        if addr in control_flow['functions']:
            css_class = "function"
        elif any(addr == jump_addr for jump_addr, _ in control_flow['jumps']):
            css_class = "jump"
        elif any(addr == call_addr for call_addr, _ in control_flow['calls']):
            css_class = "call"
        elif any(addr == hotspot_addr for hotspot_addr, _, _ in performance['hotspots'][:5]):
            css_class = "hotspot"
        
        symbol_html = f"<span class='symbol'>{instr['symbol']}</span>" if instr['symbol'] else ""
        annotation_html = f"<span class='annotation'>{instr['annotation']}</span>" if instr['annotation'] else ""
        
        html_content += f"""                <tr class="{css_class}">
                    <td class="address">0x{addr:04X}</td>
                    <td class="bytes">{instr['bytes']}</td>
                    <td class="mnemonic">{instr['mnemonic']}</td>
                    <td class="operand">{', '.join(instr['operands'])}</td>
                    <td>{symbol_html}</td>
                    <td>{annotation_html}</td>
                </tr>
"""
    
    html_content += """            </tbody>
        </table>
    </div>
    
    <div class="section">
        <h2>Functions</h2>
        <table>
            <thead>
                <tr>
                    <th>Address</th>
                    <th>Name</th>
                    <th>Basic Blocks</th>
                </tr>
            </thead>
            <tbody>
"""
    
    for addr, func_info in control_flow['functions'].items():
        html_content += f"""                <tr>
                    <td>0x{addr:04X}</td>
                    <td>{func_info['name']}</td>
                    <td>{len(func_info['basic_blocks'])}</td>
                </tr>
"""
    
    html_content += """            </tbody>
        </table>
    </div>
    
    <div class="section">
        <h2>Cross-References</h2>
        <table>
            <thead>
                <tr>
                    <th>Symbol</th>
                    <th>Address</th>
                    <th>References</th>
                </tr>
            </thead>
            <tbody>
"""
    
    for symbol, info in xrefs.items():
        refs = ", ".join([f"0x{addr:04X} ({ref_type})" for addr, ref_type in info['references']])
        html_content += f"""                <tr>
                    <td>{symbol}</td>
                    <td>0x{info['address']:04X}</td>
                    <td>{refs if refs else "(no references)"}</td>
                </tr>
"""
    
    html_content += """            </tbody>
        </table>
    </div>
    
    <div class="section">
        <h2>Performance Hotspots</h2>
        <table>
            <thead>
                <tr>
                    <th>Address</th>
                    <th>Instruction</th>
                    <th>Cycles</th>
                </tr>
            </thead>
            <tbody>
"""
    
    for addr, mnemonic, cycles in performance['hotspots'][:10]:
        html_content += f"""                <tr>
                    <td>0x{addr:04X}</td>
                    <td>{mnemonic}</td>
                    <td>{cycles}</td>
                </tr>
"""
    
    html_content += """            </tbody>
        </table>
    </div>
</body>
</html>"""
    
    # Write to file
    html_file = file_path.replace('.bin', '.html')
    with open(html_file, 'w') as f:
        f.write(html_content)
    
    print(f"HTML report exported to: {html_file}")

def interactive_mode(file_path):
    """
    Interactive disassembly and analysis mode.
    Provides commands for advanced debugging and analysis.
    """
    # Load the binary file
    try:
        with open(file_path, 'rb') as f:
            bytecode = f.read()
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        return
    
    # Load symbol table if available
    symbol_table = {}
    reverse_symbol_table = {}
    symbol_file = file_path.replace('.bin', '.sym')
    try:
        with open(symbol_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    parts = line.split()
                    if len(parts) >= 2:
                        symbol = parts[0]
                        addr_str = parts[1]
                        symbol_table[symbol] = addr_str
                        if addr_str.startswith('0x'):
                            try:
                                addr = int(addr_str, 16)
                                reverse_symbol_table[addr] = symbol
                            except ValueError:
                                pass
    except FileNotFoundError:
        pass  # No symbol file, continue without symbols
    
    # Create segments (for now, treat entire file as one segment)
    segments = [(0x0000, len(bytecode), 0)]
    
    # Create opcode maps
    opcode_map, register_map = create_reverse_maps()
    
    # Perform analysis
    control_flow = analyze_control_flow(bytecode, segments, opcode_map, register_map, reverse_symbol_table, symbol_table)
    xrefs = generate_cross_references(bytecode, segments, opcode_map, register_map, reverse_symbol_table, symbol_table)
    annotations = generate_annotations(bytecode, segments, control_flow, xrefs, symbol_table, reverse_symbol_table)
    performance = analyze_performance(bytecode, segments, opcode_map, register_map, reverse_symbol_table)
    
    print("Nova-16 Interactive Disassembler")
    print("Type 'help' for commands, 'quit' to exit")
    print()
    
    while True:
        try:
            cmd_line = input("disasm> ").strip()
            if not cmd_line:
                continue
            
            parts = cmd_line.split()
            cmd = parts[0].lower()
            
            if cmd == 'quit' or cmd == 'q':
                break
            
            elif cmd == 'help' or cmd == 'h':
                print("Available commands:")
                print("  disasm [addr]     - Disassemble from address (or current PC)")
                print("  functions         - Show identified functions")
                print("  blocks            - Show all basic blocks")
                print("  cfg [addr]        - Show control flow graph (or for specific function)")
                print("  calls             - Show all function calls")
                print("  jumps             - Show all jump instructions")
                print("  xrefs             - Show all cross-references")
                print("  export html       - Export analysis to HTML")
                print("  export json       - Export analysis to JSON")
                print("  perf              - Show performance analysis")
                print("  help              - Show this help")
                print("  quit              - Exit")
            
            elif cmd == 'disasm':
                # Disassemble with annotations
                start_addr = 0
                if len(parts) > 1:
                    try:
                        start_addr = int(parts[1], 16)
                    except ValueError:
                        print(f"Invalid address: {parts[1]}")
                        continue
                
                print(f"Disassembly starting from 0x{start_addr:04X}:")
                for start_seg, length, bin_offset in segments:
                    pc = bin_offset
                    end_pc = bin_offset + length
                    
                    while pc < end_pc:
                        current_addr = start_seg + (pc - bin_offset)
                        if current_addr < start_addr:
                            opcode = bytecode[pc] if pc < len(bytecode) else 0
                            if opcode in opcode_map:
                                _, _, size = disassemble_instruction_new(bytecode, pc, opcode_map, register_map)
                                pc += size
                            else:
                                pc += 1
                            continue
                        
                        if current_addr >= start_addr + 0x100:  # Limit output
                            print("... (output truncated)")
                            break
                        
                        # Show symbol if present
                        symbol = reverse_symbol_table.get(current_addr, "")
                        if symbol:
                            print(f"{symbol}:")
                        
                        # Show annotation if present
                        annotation = annotations.get(current_addr, "")
                        if annotation:
                            print(f"{'':<20} {annotation}")
                        
                        opcode = bytecode[pc] if pc < len(bytecode) else 0
                        address_str = f"{current_addr:04X}:"
                        
                        if opcode in opcode_map:
                            mnemonic, operands, size = disassemble_instruction_new(bytecode, pc, opcode_map, register_map)
                            
                            if pc + size <= len(bytecode):
                                instruction_bytes = bytecode[pc:pc + size]
                                hex_dump = ' '.join(f'{b:02X}' for b in instruction_bytes)
                                operands_str = ', '.join(operands)
                                print(f"{address_str:<6} {hex_dump:<12} {mnemonic:<8} {operands_str}")
                            
                            pc += size
                        else:
                            hex_dump = f'{opcode:02X}'
                            print(f"{address_str:<6} {hex_dump:<12} DB      0x{opcode:02X}")
                            pc += 1
                
                print()
            
            elif cmd == 'functions':
                print("Identified functions:")
                for addr, func_info in control_flow['functions'].items():
                    print(f"  {func_info['name']} (0x{addr:04X}): {len(func_info['basic_blocks'])} basic blocks")
                print()
            
            elif cmd == 'blocks':
                print("All basic blocks:")
                for addr, block_info in control_flow['basic_blocks'].items():
                    successors = ", ".join(f"0x{s:04X}" for s in block_info['successors'])
                    print(f"  0x{addr:04X}-0x{block_info['end_addr']:04X}: {len(block_info['instructions'])} instructions, successors: {successors}")
                print()
            
            elif cmd == 'cfg':
                if len(parts) > 1:
                    try:
                        func_addr = int(parts[1], 16)
                        if func_addr in control_flow['functions']:
                            func_info = control_flow['functions'][func_addr]
                            print(f"Control flow graph for {func_info['name']} (0x{func_addr:04X}):")
                            for block_addr in func_info['basic_blocks']:
                                if block_addr in control_flow['control_flow_graph']:
                                    successors = control_flow['control_flow_graph'][block_addr]
                                    succ_str = ", ".join(f"0x{s:04X}" for s in successors)
                                    print(f"  0x{block_addr:04X} -> {succ_str}")
                        else:
                            print(f"No function found at 0x{func_addr:04X}")
                    except ValueError:
                        print(f"Invalid address: {parts[1]}")
                else:
                    print("Control flow graph:")
                    for addr, successors in control_flow['control_flow_graph'].items():
                        succ_str = ", ".join(f"0x{s:04X}" for s in successors)
                        print(f"  0x{addr:04X} -> {succ_str}")
                print()
            
            elif cmd == 'calls':
                print("Function calls:")
                for addr, target in control_flow['calls']:
                    target_symbol = reverse_symbol_table.get(target, f"0x{target:04X}")
                    print(f"  0x{addr:04X}: CALL {target_symbol}")
                print()
            
            elif cmd == 'jumps':
                print("Jump instructions:")
                for addr, target in control_flow['jumps']:
                    target_symbol = reverse_symbol_table.get(target, f"0x{target:04X}")
                    print(f"  0x{addr:04X}: JMP to {target_symbol}")
                print()
            
            elif cmd == 'xrefs':
                print("Cross-references for all symbols:")
                for symbol, info in xrefs.items():
                    refs = ", ".join([f"0x{addr:04X} ({ref_type})" for addr, ref_type in info['references']])
                    print(f"  {symbol} (0x{info['address']:04X}):")
                    if refs:
                        print(f"    References: {refs}")
                    else:
                        print("    (no references)")
                print()
            
            elif cmd == 'perf':
                print("Performance Analysis:")
                print(f"  Total instructions: {performance['total_instructions']}")
                print(f"  Estimated cycles: {performance['estimated_cycles']}")
                print(f"  Memory accesses: {performance['memory_accesses']}")
                print(f"  Control flow instructions: {performance['control_flow_instructions']}")
                print()
                print("Instruction counts:")
                for mnemonic, count in sorted(performance['instruction_counts'].items()):
                    cycles = performance['instruction_cycles'].get(mnemonic, 0)
                    avg_cycles = cycles / count if count > 0 else 0
                    print(f"  {mnemonic:<8}: {count:>3} times, {cycles:>3} cycles, {avg_cycles:.1f} avg")
                print()
                print("Performance hotspots (top 10):")
                for i, (mnemonic, cycles) in enumerate(performance['hotspots'][:10]):
                    print(f"  {i+1}. {mnemonic}: {cycles} cycles")
                print()
            
            elif cmd == 'export':
                if len(parts) > 1:
                    format_type = parts[1].lower()
                    if format_type == 'html':
                        export_to_html(file_path, bytecode, segments, control_flow, xrefs, symbol_table, reverse_symbol_table, annotations, performance)
                    elif format_type == 'json':
                        export_to_json(file_path, bytecode, segments, control_flow, xrefs, symbol_table, reverse_symbol_table)
                    else:
                        print(f"Unknown export format: {format_type}. Supported: html, json")
                else:
                    print("Usage: export <format> (html or json)")
            
            else:
                print(f"Unknown command: {cmd}. Type 'help' for available commands.")
        
        except KeyboardInterrupt:
            print("\nInterrupted. Type 'quit' to exit.")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Nova-16 Disassembler')
    parser.add_argument('file', nargs='?', help='Binary file to disassemble')
    parser.add_argument('--org', type=lambda x: int(x, 0), default=0x0000, 
                        help='Base address (ORG directive) in hex, e.g., 0x1000')
    parser.add_argument('--interactive', '-i', action='store_true',
                        help='Start interactive disassembly and analysis mode')
    
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

    if args.interactive:
        interactive_mode(file_path)
    else:
        disassemble( file_path, args.org )

