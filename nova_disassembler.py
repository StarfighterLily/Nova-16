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

def find_string_start(bytecode, start_pos):
    """
    Find the actual start of a string by looking backwards from start_pos.
    This handles cases where a symbol points to the middle of a string.
    Returns the start position of the string, or start_pos if no better start found.
    """
    if start_pos >= len(bytecode):
        return start_pos
    
    # Get the length of the string starting at the original position
    orig_is_string, orig_length = is_string_data(bytecode, start_pos)
    if not orig_is_string:
        return start_pos  # Not in a string, return original position
    
    # Look backwards for a longer string (which would indicate the real start)
    # Look back up to 20 bytes
    pos = start_pos
    lookback_limit = max(0, start_pos - 20)
    
    while pos > lookback_limit:
        # Check if this position has a longer string
        is_string, length = is_string_data(bytecode, pos - 1)
        if is_string and length > orig_length:
            return pos - 1  # Found a longer string, this is the real start
        pos -= 1
    
    # No longer string found, return original position
    return start_pos

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
    
    # Parse mode byte - extract modes for up to 4 operands
    op1_mode = mode_byte & 0x03
    op2_mode = (mode_byte >> 2) & 0x03
    op3_mode = (mode_byte >> 4) & 0x03
    op4_mode = (mode_byte >> 6) & 0x03  # Note: this overlaps with indexed bit
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
    
    # Parse all operands
    for i in range(operand_count):
        # Get mode for this operand
        if i == 0:
            mode = op1_mode
        elif i == 1:
            mode = op2_mode
        elif i == 2:
            mode = op3_mode
        elif i == 3:
            mode = op4_mode
        else:
            # For operands beyond 4, mode defaults to 0 (register direct)
            mode = 0
        
        if mode == 0:  # Register direct
            if current_pc < len(bytecode):
                reg_num = bytecode[current_pc]
                operands.append(reg_num_to_name(reg_num))
                current_pc += 1
                size += 1
        elif mode == 1:  # Immediate 8-bit
            if current_pc < len(bytecode):
                imm8 = bytecode[current_pc]
                operands.append(f"0x{imm8:02X}")
                current_pc += 1
                size += 1
        elif mode == 2:  # Immediate 16-bit
            if current_pc + 1 < len(bytecode):
                high = bytecode[current_pc]
                low = bytecode[current_pc + 1]
                imm16 = (high << 8) | low
                operands.append(f"0x{imm16:04X}")
                current_pc += 2
                size += 2
        elif mode == 3:  # Memory reference
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

def disassemble( file_path, args ):
    """
    Reads a binary file and disassembles it into Nova-16 assembly code.
    This version correctly displays little-endian 16-bit values and detects string data.
    
    Args:
        file_path: Path to binary file to disassemble
        args: Parsed command-line arguments
    """
    if not file_path:
        if not args.quiet:
            print( "No file selected." )
        return

    try:
        with open( file_path, 'rb' ) as f:
            bytecode = f.read()
    except FileNotFoundError:
        if not args.quiet:
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
    
    # Handle output redirection
    output_file = None
    if args.output:
        try:
            output_file = open(args.output, 'w')
            import sys
            original_stdout = sys.stdout
            sys.stdout = output_file
        except IOError as e:
            if not args.quiet:
                print(f"Error opening output file: {e}")
            return
    
    try:
        # Process each segment
        for segment_idx, (start_addr, length, bin_offset) in enumerate(segments):
            # Show ORG directive for segments after the first
            if segment_idx > 0:
                print(f"\nORG 0x{start_addr:04X}")
            
            pc = bin_offset
            end_pc = bin_offset + length
            
            # Apply address range filtering
            if args.start is not None:
                # Find the PC corresponding to start address
                start_pc = bin_offset + (args.start - start_addr)
                if start_pc > pc:
                    pc = max(pc, start_pc)
            
            if args.end is not None:
                # Find the PC corresponding to end address
                end_pc = min(end_pc, bin_offset + (args.end - start_addr))
            
            while pc < end_pc:
                current_addr = start_addr + (pc - bin_offset)
                
                # Print any labels that are at or before this address
                while label_idx < len(labels) and labels[label_idx][0] <= current_addr:
                    addr, name = labels[label_idx]
                    print(f"\n{name}:")
                    label_idx += 1
                
                address_str = f"{current_addr:04X}:" if args.show_addresses else ""
                
                opcode = bytecode[ pc ]
                
                # Check if this looks like string data first
                is_string, str_length = is_string_data(bytecode, pc)
                if is_string and str_length > 1:  # At least one character plus null terminator
                    # Display as DEFSTR
                    hex_dump = ' '.join( f'{b:02X}' for b in bytecode[pc:pc + str_length] )
                    # Truncate hex dump if too long for better readability
                    if len(hex_dump) > 60:
                        truncated_hex = ' '.join( f'{b:02X}' for b in bytecode[pc:pc + min(20, str_length)] )
                        hex_dump = f"{truncated_hex}... (truncated)"
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
                        hex_dump = f"{opcode:02X} {next_byte:02X}" if args.show_hex else ""
                        print( f"{address_str:<6} {hex_dump:<12} DW {resolved_value}" )
                        pc += 2
                        continue
                
                if opcode in opcode_map:
                    # Use new prefixed operand disassembly
                    mnemonic, operands, size = disassemble_instruction_new(bytecode, pc, opcode_map, register_map)
                    
                    # Apply instruction filtering
                    if args.filter_instructions:
                        filter_list = [instr.strip().upper() for instr in args.filter_instructions.split(',')]
                        if mnemonic.upper() not in filter_list:
                            pc += size
                            continue
                    
                    if args.exclude_instructions:
                        exclude_list = [instr.strip().upper() for instr in args.exclude_instructions.split(',')]
                        if mnemonic.upper() in exclude_list:
                            pc += size
                            continue
                    
                    # Check if instruction is incomplete (has operands but none parsed)
                    instr_info = opcode_map.get(opcode)
                    if instr_info:
                        _, operand_count = instr_info
                        if operand_count > 0 and len(operands) == 0 and pc + 1 < end_pc:
                            # Incomplete instruction, likely data - show as DW
                            value = (bytecode[pc] << 8) | bytecode[pc + 1]  # Big-endian
                            resolved_value = resolve_symbol(value, symbol_table)
                            hex_dump = f"{bytecode[pc]:02X} {bytecode[pc + 1]:02X}" if args.show_hex else ""
                            print( f"{address_str:<6} {hex_dump:<12} DW {resolved_value}" )
                            pc += 2
                            continue
                    
                    # Bounds check to prevent reading past the end of the segment
                    if pc + size > end_pc:
                        hex_dump = ' '.join( f'{b:02X}' for b in bytecode[pc:end_pc] ) if args.show_hex else ""
                        print( f"{address_str:<6} {hex_dump:<12} ??? (Incomplete instruction)" )
                        break

                    instruction_bytes = bytecode[ pc : pc + size ]
                    hex_dump = ' '.join( f'{b:02X}' for b in instruction_bytes ) if args.show_hex else ""
                    
                    # Format operands
                    operand_str = ', '.join(operands) if operands else ""
                    instruction_str = mnemonic
                    print( f"{address_str:<6} {hex_dump:<12} {instruction_str:<8} {operand_str}" )

                    pc += size
                else:
                    hex_dump = f"{opcode:02X}" if args.show_hex else ""
                    print( f"{address_str:<6} {hex_dump:<12} DB 0x{opcode:02X}" )
                    pc += 1
        
        # Handle different output formats
        if args.format != 'text':
            if args.format == 'html':
                # Generate HTML output
                segments_for_analysis = [(0x0000, len(bytecode), 0)]  # Simplified
                control_flow = analyze_control_flow(bytecode, segments_for_analysis, opcode_map, register_map, reverse_symbol_table, symbol_table)
                xrefs = generate_cross_references(bytecode, segments_for_analysis, opcode_map, register_map, reverse_symbol_table, symbol_table)
                annotations = generate_annotations(bytecode, segments_for_analysis, control_flow, xrefs, symbol_table, reverse_symbol_table)
                performance = analyze_performance(bytecode, segments_for_analysis, opcode_map, register_map, reverse_symbol_table)
                
                # Add data flow analysis if requested
                data_flow = None
                if args.analyze_dataflow:
                    data_flow = analyze_data_flow(bytecode, segments_for_analysis, opcode_map, register_map, reverse_symbol_table, symbol_table)
                    if args.analyze_liveness:
                        analyze_register_liveness(bytecode, segments_for_analysis, opcode_map, register_map, data_flow)
                
                export_to_html(file_path, bytecode, segments_for_analysis, control_flow, xrefs, symbol_table, reverse_symbol_table, annotations, performance)
            elif args.format == 'json':
                segments_for_analysis = [(0x0000, len(bytecode), 0)]  # Simplified
                control_flow = analyze_control_flow(bytecode, segments_for_analysis, opcode_map, register_map, reverse_symbol_table, symbol_table)
                xrefs = generate_cross_references(bytecode, segments_for_analysis, opcode_map, register_map, reverse_symbol_table, symbol_table)
                export_to_json(file_path, bytecode, segments_for_analysis, control_flow, xrefs, symbol_table, reverse_symbol_table)
        
        # Perform additional analysis if requested
        if args.analyze_dataflow and not args.quiet:
            print("\n=== Data Flow Analysis ===")
            segments_for_analysis = [(0x0000, len(bytecode), 0)]  # Simplified
            data_flow = analyze_data_flow(bytecode, segments_for_analysis, opcode_map, register_map, reverse_symbol_table, symbol_table)
            
            print(f"Register definitions: {len(data_flow['register_definitions'])}")
            print(f"Register uses: {len(data_flow['register_uses'])}")
            print(f"Memory definitions: {len(data_flow['memory_definitions'])}")
            print(f"Memory uses: {len(data_flow['memory_uses'])}")
            
            if args.analyze_liveness:
                analyze_register_liveness(bytecode, segments_for_analysis, opcode_map, register_map, data_flow)
                print(f"Live register analysis completed for {len(data_flow['live_registers'])} addresses")
                print(f"Live register analysis completed for {len(data_flow['live_registers'])} addresses")
        
        if args.analyze_functions and not args.quiet:
            print("\n=== Function Analysis ===")
            segments_for_analysis = [(0x0000, len(bytecode), 0)]  # Simplified
            control_flow = analyze_control_flow(bytecode, segments_for_analysis, opcode_map, register_map, reverse_symbol_table, symbol_table)
            function_boundaries = analyze_function_boundaries(bytecode, segments_for_analysis, opcode_map, register_map, control_flow, symbol_table)
            print(f"Identified {len(function_boundaries)} functions")
            print(f"Found {len(control_flow['basic_blocks'])} basic blocks")
            
            # Show function details
            for addr, func_info in sorted(function_boundaries.items()):
                size_info = f" (size: {func_info['size']} bytes)" if func_info['size'] else ""
                print(f"  {func_info['name']} at 0x{addr:04X}{size_info} [{func_info['source']}]")
        
        if args.analyze_loops and not args.quiet:
            print("\n=== Loop Analysis ===")
            # Load segments same as disassembly
            base_name = file_path.rsplit('.', 1)[0]
            segments_for_analysis = load_org_segments(base_name + '.org')
            if not segments_for_analysis:
                segments_for_analysis = [(0x0000, len(bytecode), 0)]
            segments_for_analysis.sort(key=lambda x: x[2])
            
            control_flow = analyze_control_flow(bytecode, segments_for_analysis, opcode_map, register_map, reverse_symbol_table, symbol_table)
            loops = analyze_loops(bytecode, segments_for_analysis, opcode_map, register_map, control_flow)
            print(f"Detected {len(loops)} loops")
            print(f"Control flow has {len(control_flow['basic_blocks'])} basic blocks")
            
            for i, loop in enumerate(loops):
                print(f"  Loop {i+1}: header=0x{loop['header']:04X}, back_edge=0x{loop['back_edge_from']:04X}, type={loop['type']}")
                print(f"    Body blocks: {len(loop['body_blocks'])}")
            
            # Also check for simple loop patterns in the bytecode
            simple_loops = find_simple_loops(bytecode, segments_for_analysis, opcode_map, register_map)
            if simple_loops:
                print(f"Found {len(simple_loops)} simple loops via pattern matching")
                for i, loop in enumerate(simple_loops):
                    print(f"  Simple loop {i+1}: {loop['type']} from 0x{loop['start']:04X} to 0x{loop['end']:04X} (back jump at 0x{loop['back_jump_addr']:04X})")
        
        if args.analyze_deadcode and not args.quiet:
            print("\n=== Dead Code Analysis ===")
            # Load segments same as disassembly
            base_name = file_path.rsplit('.', 1)[0]
            segments_for_analysis = load_org_segments(base_name + '.org')
            if not segments_for_analysis:
                segments_for_analysis = [(0x0000, len(bytecode), 0)]
            segments_for_analysis.sort(key=lambda x: x[2])
            
            dead_code = analyze_dead_code(bytecode, segments_for_analysis, opcode_map, register_map)
            
            print(f"Total basic blocks: {dead_code['analysis_summary']['total_blocks']}")
            print(f"Reachable blocks: {dead_code['analysis_summary']['reachable_blocks']}")
            print(f"Unreachable blocks: {dead_code['analysis_summary']['unreachable_blocks']}")
            print(f"Dead stores: {dead_code['analysis_summary']['dead_stores']}")
            print(f"Unused functions: {dead_code['analysis_summary']['unused_functions']}")
            
            if dead_code['unreachable_blocks']:
                print("\nUnreachable blocks:")
                for block in dead_code['unreachable_blocks']:
                    print(f"  0x{block['address']:04X} ({block['size']} bytes) - {block['reason']}")
            
            if dead_code['dead_stores']:
                print("\nDead stores:")
                for store in dead_code['dead_stores']:
                    print(f"  0x{store['address']:04X}: {store['register']} - {store['reason']}")
            
            if dead_code['unused_functions']:
                print("\nUnused functions:")
                for func in dead_code['unused_functions']:
                    print(f"  {func['name']} at 0x{func['address']:04X} ({func['size']} bytes)")
        
        if args.analyze_security and not args.quiet:
            print("\n=== Security Analysis ===")
            # Security analysis would be implemented here
            print("Security analysis not yet implemented")
        
        if args.analyze_patterns and not args.quiet:
            print("\n=== Pattern Recognition ===")
            # Pattern recognition would be implemented here
            print("Pattern recognition not yet implemented")
    
    finally:
        # Restore stdout if redirected
        if output_file:
            output_file.close()
            import sys
            sys.stdout = original_stdout

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
                                # Jump - successor is target
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

def analyze_data_flow(bytecode, segments, opcode_map, register_map, reverse_symbol_table, symbol_table):
    """
    Perform data flow analysis to track how data flows through registers and memory.
    Returns a dictionary with data flow information.
    """
    data_flow = {
        'register_definitions': {},  # addr -> (register, value_source)
        'register_uses': {},         # addr -> (register, use_type)
        'memory_definitions': {},    # addr -> memory_location
        'memory_uses': {},          # addr -> memory_location
        'data_dependencies': {},    # instruction -> list of dependencies
        'reaching_definitions': {}, # register -> list of definitions that reach each use
        'live_registers': {}        # addr -> set of live registers
    }
    
    # Track register states
    register_state = {}  # register -> last_definition_addr
    
    for start_addr, length, bin_offset in segments:
        pc = bin_offset
        end_pc = bin_offset + length
        
        while pc < end_pc:
            current_addr = start_addr + (pc - bin_offset)
            opcode = bytecode[pc]
            
            if opcode in opcode_map:
                mnemonic, operands, size = disassemble_instruction_new(bytecode, pc, opcode_map, register_map)
                
                if pc + size <= len(bytecode):
                    # Analyze data flow for this instruction
                    analyze_instruction_data_flow(mnemonic, operands, current_addr, data_flow, register_state)
                
                pc += size
            else:
                pc += 1
    
    # Compute reaching definitions
    compute_reaching_definitions(data_flow)
    
    return data_flow

def analyze_instruction_data_flow(mnemonic, operands, addr, data_flow, register_state):
    """
    Analyze data flow for a single instruction.
    """
    # Track register definitions (writes)
    if mnemonic in ['MOV', 'ADD', 'SUB', 'MUL', 'DIV', 'AND', 'OR', 'XOR', 'NOT', 'INC', 'DEC', 'NEG', 'ABS', 'POP', 'POPA']:
        if operands:
            dest_reg = operands[0]
            if is_register(dest_reg):
                data_flow['register_definitions'][addr] = (dest_reg, 'computation')
                register_state[dest_reg] = addr
    
    # Track register uses (reads) for all instructions that read registers
    if operands:
        for i, operand in enumerate(operands):
            if is_register(operand):
                # Skip destination operand for instructions that write to it
                if i == 0 and mnemonic in ['MOV', 'ADD', 'SUB', 'MUL', 'DIV', 'AND', 'OR', 'XOR', 'NOT', 'INC', 'DEC', 'NEG', 'ABS']:
                    continue
                # Skip destination for POP operations
                if i == 0 and mnemonic in ['POP', 'POPA']:
                    continue
                
                # This is a register read
                if addr not in data_flow['register_uses']:
                    data_flow['register_uses'][addr] = []
                data_flow['register_uses'][addr].append((operand, 'read'))
    
    # Track memory operations
    elif mnemonic in ['VREAD', 'VWRITE', 'SREAD', 'SWRITE', 'MEMCPY']:
        for operand in operands:
            if is_memory_reference(operand):
                if mnemonic in ['VREAD', 'SREAD']:
                    data_flow['memory_uses'][addr] = operand
                else:
                    data_flow['memory_definitions'][addr] = operand
    
    # Track control flow that affects registers
    elif mnemonic in ['PUSH', 'POP', 'PUSHA', 'POPA', 'PUSHF', 'POPF']:
        if mnemonic in ['POP', 'POPA'] and operands:
            dest_reg = operands[0]
            if is_register(dest_reg):
                data_flow['register_definitions'][addr] = (dest_reg, 'stack')
                register_state[dest_reg] = addr
        elif mnemonic == 'PUSH' and operands:
            src_reg = operands[0]
            if is_register(src_reg):
                if addr not in data_flow['register_uses']:
                    data_flow['register_uses'][addr] = []
                data_flow['register_uses'][addr].append((src_reg, 'read'))

def is_register(operand):
    """
    Check if an operand is a register.
    """
    register_prefixes = ['R', 'P', 'V', 'S', 'F', 'T', 'SA', 'SF', 'SV', 'SW', 'VM', 'VL', 'TT', 'TM', 'TC', 'TS']
    return any(operand.startswith(prefix) for prefix in register_prefixes) or operand in ['SP', 'FP', 'VX', 'VY']

def is_memory_reference(operand):
    """
    Check if an operand is a memory reference.
    """
    return operand.startswith('[') and operand.endswith(']')

def compute_reaching_definitions(data_flow):
    """
    Compute reaching definitions for each register use.
    """
    # Simple forward data flow analysis
    for addr, uses in data_flow['register_uses'].items():
        for reg, use_type in uses:
            reaching_defs = []
            # Find all definitions of this register that reach this use
            for def_addr, (def_reg, def_type) in data_flow['register_definitions'].items():
                if def_reg == reg and def_addr < addr:
                    # Check if there's a redefinition between def and use
                    redefined = False
                    for intermediate_addr, (intermediate_reg, _) in data_flow['register_definitions'].items():
                        if def_addr < intermediate_addr < addr and intermediate_reg == reg:
                            redefined = True
                            break
                    if not redefined:
                        reaching_defs.append((def_addr, def_type))
            
            if reaching_defs:
                if reg not in data_flow['reaching_definitions']:
                    data_flow['reaching_definitions'][reg] = {}
                data_flow['reaching_definitions'][reg][addr] = reaching_defs

def analyze_register_liveness(bytecode, segments, opcode_map, register_map, data_flow):
    """
    Perform register liveness analysis.
    Returns liveness information for each address.
    """
    liveness = {}
    
    # Backward data flow analysis
    for start_addr, length, bin_offset in segments:
        pc = bin_offset + length  # Start from end
        
        # Initialize live registers at end of segment
        live_regs = set()
        
        while pc > bin_offset:
            current_addr = start_addr + (pc - bin_offset)
            liveness[current_addr] = live_regs.copy()
            
            opcode = bytecode[pc - 1] if pc > bin_offset else 0
            
            if opcode in opcode_map:
                # Get instruction size first
                size = 1  # Minimum size
                if pc > bin_offset:
                    try:
                        _, _, size = disassemble_instruction_new(bytecode, pc - 1, opcode_map, register_map)
                    except:
                        size = 1
                
                mnemonic, operands, _ = disassemble_instruction_new(bytecode, pc - size, opcode_map, register_map)
                
                # Update liveness based on instruction
                if operands:
                    # Last operand is destination (killed)
                    dest_operand = operands[0]
                    if is_register(dest_operand):
                        live_regs.discard(dest_operand)
                    
                    # Source operands are used (made live)
                    for operand in operands[1:]:
                        if is_register(operand):
                            live_regs.add(operand)
                
                pc -= size
            else:
                pc -= 1
    
    data_flow['live_registers'] = liveness
    return liveness

def analyze_dead_code(bytecode, segments, opcode_map, register_map, cfg=None):
    """
    Analyze for dead/unreachable code and dead stores.
    Returns dictionary with dead code analysis results.
    """
    dead_code_info = {
        'unreachable_blocks': [],
        'dead_stores': [],
        'unused_functions': [],
        'analysis_summary': {}
    }

    if not cfg:
        cfg = build_control_flow_graph(bytecode, segments, opcode_map, register_map)

    # Find unreachable basic blocks
    reachable_blocks = set()
    worklist = [cfg['entry_point']] if cfg['entry_point'] else []

    while worklist:
        current = worklist.pop()
        if current in reachable_blocks:
            continue
        reachable_blocks.add(current)

        if current in cfg['blocks']:
            for succ in cfg['blocks'][current]['successors']:
                if succ not in reachable_blocks:
                    worklist.append(succ)

    # Check for unreachable blocks
    for addr, block in cfg['blocks'].items():
        if addr not in reachable_blocks:
            dead_code_info['unreachable_blocks'].append({
                'address': addr,
                'size': block['end'] - block['start'],
                'reason': 'unreachable'
            })

    # Analyze for dead stores (simplified)
    # This is a basic implementation - could be enhanced with more sophisticated analysis
    for addr, block in cfg['blocks'].items():
        if addr in reachable_blocks:
            dead_stores = find_dead_stores_in_block(block, bytecode, opcode_map, register_map)
            dead_code_info['dead_stores'].extend(dead_stores)

    # Find unused functions (simplified - based on function boundaries)
    if 'functions' in cfg:
        for func_addr, func_info in cfg['functions'].items():
            # Check if function is called
            called = False
            for block_addr, block in cfg['blocks'].items():
                if block_addr in reachable_blocks:
                    if is_function_called(func_addr, block, bytecode, opcode_map):
                        called = True
                        break
            if not called and func_addr != cfg.get('entry_point'):
                dead_code_info['unused_functions'].append({
                    'address': func_addr,
                    'name': func_info.get('name', f'func_{func_addr:04X}'),
                    'size': func_info.get('size', 0)
                })

    # Generate summary
    dead_code_info['analysis_summary'] = {
        'total_blocks': len(cfg['blocks']),
        'reachable_blocks': len(reachable_blocks),
        'unreachable_blocks': len(dead_code_info['unreachable_blocks']),
        'dead_stores': len(dead_code_info['dead_stores']),
        'unused_functions': len(dead_code_info['unused_functions'])
    }

    return dead_code_info

def find_dead_stores_in_block(block, bytecode, opcode_map, register_map):
    """Find dead stores within a basic block (simplified analysis)."""
    dead_stores = []
    defined_regs = set()
    used_regs = set()

    # Simple analysis: track register definitions and uses within the block
    for addr in range(block['start'], block['end']):
        if addr >= len(bytecode):
            break

        opcode = bytecode[addr]
        if opcode in opcode_map:
            mnemonic, operand_count = opcode_map[opcode]
            operands = get_instruction_operands(bytecode, addr, instr=(mnemonic, operand_count))

            # Check for register definitions (simplified)
            if mnemonic in ['MOV', 'ADD', 'SUB', 'MUL', 'DIV', 'AND', 'OR', 'XOR', 'NOT', 'INC', 'DEC', 'NEG', 'ABS', 'POP', 'POPA']:
                if operands and len(operands) > 0:
                    dest_reg = operands[0]
                    if is_register_name(dest_reg):
                        defined_regs.add(dest_reg)

            # Check for register uses (simplified)
            for operand in operands:
                if is_register_name(operand):
                    used_regs.add(operand)

    # Find dead stores (defined but not used in this block)
    for reg in defined_regs:
        if reg not in used_regs:
            dead_stores.append({
                'address': block['start'],
                'register': reg,
                'reason': 'defined but not used in block'
            })

    return dead_stores

def is_register_name(operand):
    """Check if operand is a register name (simplified)."""
    if not operand or not isinstance(operand, str):
        return False
    
    register_prefixes = ['R', 'P', 'V', 'S', 'F', 'T', 'SA', 'SF', 'SV', 'SW', 'VM', 'VL', 'TT', 'TM', 'TC', 'TS']
    return any(operand.startswith(prefix) for prefix in register_prefixes) or operand in ['SP', 'FP', 'VX', 'VY']

def is_function_called(func_addr, block, bytecode, opcode_map):
    """Check if a function is called from a block."""
    for addr in range(block['start'], block['end']):
        if addr >= len(bytecode):
            break

        opcode = bytecode[addr]
        if opcode in opcode_map:
            mnemonic, operand_count = opcode_map[opcode]
            if mnemonic in ['CALL', 'JMP']:
                operands = get_instruction_operands(bytecode, addr, instr=(mnemonic, operand_count))
                if operands and len(operands) > 0:
                    target_addr = operands[0]
                    if isinstance(target_addr, int) and target_addr == func_addr:
                        return True
                    elif isinstance(target_addr, str) and target_addr.startswith('0x'):
                        try:
                            addr_val = int(target_addr, 16)
                            if addr_val == func_addr:
                                return True
                        except ValueError:
                            pass
    return False

def get_instruction_operands(bytecode, addr, instr):
    """Extract operands from an instruction (simplified)."""
    operands = []
    # This is a simplified version - would need to be enhanced for full operand parsing
    return operands

def get_register_name(operands, register_map):
    """Extract register name from operands (simplified)."""
    # This is a simplified version - would need to be enhanced for full register detection
    return None

def build_control_flow_graph(bytecode, segments, opcode_map, register_map):
    """Build a basic control flow graph for dead code analysis."""
    cfg = {
        'blocks': {},
        'entry_point': segments[0][0] if segments else 0x0000,  # Use first segment start as entry point
        'functions': {}
    }

    # Build CFG based on segments
    for start_addr, length, bin_offset in segments:
        current_block_start = bin_offset
        end_pc = bin_offset + length
        
        for pc in range(bin_offset, end_pc):
            byte = bytecode[pc] if pc < len(bytecode) else 0
            if byte in opcode_map:
                mnemonic, operand_count = opcode_map[byte]
                if mnemonic in ['JMP', 'JZ', 'JNZ', 'CALL', 'RET', 'IRET']:
                    # End current block and start new one
                    if current_block_start < pc:
                        block_addr = start_addr + (current_block_start - bin_offset)
                        cfg['blocks'][block_addr] = {
                            'start': current_block_start,
                            'end': pc,
                            'successors': []
                        }
                    current_block_start = pc

        # Add final block for this segment
        if current_block_start < end_pc:
            block_addr = start_addr + (current_block_start - bin_offset)
            cfg['blocks'][block_addr] = {
                'start': current_block_start,
                'end': end_pc,
                'successors': []
            }

    return cfg

def analyze_loops(bytecode, segments, opcode_map, register_map, control_flow):
    """
    Analyze control flow to detect loops.
    Returns information about identified loops.
    """
    loops = []
    
    # Find back edges in the control flow graph
    for block_addr, block_info in control_flow['basic_blocks'].items():
        for successor in block_info['successors']:
            # Check if successor is an ancestor (back edge)
            if successor <= block_addr:
                # This is a potential back edge (loop)
                loop_info = {
                    'header': successor,
                    'back_edge_from': block_addr,
                    'body_blocks': find_loop_body(successor, block_addr, control_flow),
                    'type': classify_loop_type(successor, block_addr, bytecode, segments, opcode_map, register_map)
                }
                loops.append(loop_info)
    
    return loops

def find_loop_body(header_addr, back_edge_addr, control_flow):
    """
    Find all blocks that belong to a loop given the header and back edge.
    """
    body_blocks = set()
    to_visit = [back_edge_addr]
    visited = set()
    
    while to_visit:
        current = to_visit.pop(0)
        if current in visited:
            continue
        
        visited.add(current)
        
        # Add this block to the loop body
        body_blocks.add(current)
        
        # Add predecessors that are dominated by the header
        # For simplicity, we'll include all blocks between header and back edge
        if current >= header_addr:
            body_blocks.add(current)
            
            # Add successors that are also in the loop
            if current in control_flow['control_flow_graph']:
                for succ in control_flow['control_flow_graph'][current]:
                    if succ >= header_addr and succ not in visited:
                        to_visit.append(succ)
    
    return sorted(list(body_blocks))

def classify_loop_type(header_addr, back_edge_addr, bytecode, segments, opcode_map, register_map):
    """
    Classify the type of loop based on the control structure.
    """
    # Find the segment containing the loop
    for start_addr, length, bin_offset in segments:
        if start_addr <= header_addr < start_addr + length:
            segment_start = start_addr
            bin_offset_start = bin_offset
            break
    else:
        return "unknown"
    
    # Look at the loop header and back edge
    header_pc = bin_offset_start + (header_addr - segment_start)
    back_edge_pc = bin_offset_start + (back_edge_addr - segment_start)
    
    if header_pc >= len(bytecode) or back_edge_pc >= len(bytecode):
        return "unknown"
    
    # Get the instruction at the back edge
    back_opcode = bytecode[back_edge_pc]
    if back_opcode in opcode_map:
        back_mnemonic, back_operands, _ = disassemble_instruction_new(bytecode, back_edge_pc, opcode_map, register_map)
        
        if back_mnemonic in ['JNZ', 'JZ', 'JC', 'JNC', 'JO', 'JNO', 'JS', 'JNS']:
            return "conditional"
        elif back_mnemonic == 'JMP':
            return "unconditional"
    
    return "unknown"

def find_simple_loops(bytecode, segments, opcode_map, register_map):
    """
    Find simple loops by pattern matching in the bytecode.
    Looks for backward jumps that could indicate loops.
    """
    loops = []
    
    for start_addr, length, bin_offset in segments:
        pc = bin_offset
        end_pc = bin_offset + length
        
        while pc < end_pc:
            current_addr = start_addr + (pc - bin_offset)
            opcode = bytecode[pc]
            
            if opcode in opcode_map:
                mnemonic, operands, size = disassemble_instruction_new(bytecode, pc, opcode_map, register_map)
                
                # Look for backward jumps
                if mnemonic in ['JMP', 'JNZ', 'JZ', 'JC', 'JNC', 'JO', 'JNO', 'JS', 'JNS'] and operands:
                    target = operands[0]
                    if target.startswith('0x'):
                        try:
                            target_addr = int(target, 16)
                            if target_addr < current_addr and target_addr >= start_addr:
                                # This is a backward jump - potential loop
                                loop_info = {
                                    'start': target_addr,
                                    'end': current_addr + size,
                                    'type': 'conditional' if mnemonic != 'JMP' else 'unconditional',
                                    'back_jump_addr': current_addr
                                }
                                loops.append(loop_info)
                        except ValueError:
                            pass
                
                pc += size
            else:
                pc += 1
    
    return loops

def analyze_function_boundaries(bytecode, segments, opcode_map, register_map, control_flow, symbol_table):
    """
    Perform automatic function boundary detection beyond symbol table entries.
    Identifies potential function starts based on control flow patterns.
    """
    function_candidates = {}
    
    # Start with known functions from symbol table
    for symbol, addr_str in symbol_table.items():
        if addr_str.startswith('0x'):
            try:
                addr = int(addr_str, 16)
                function_candidates[addr] = {
                    'name': symbol,
                    'source': 'symbol_table',
                    'confidence': 1.0
                }
            except ValueError:
                pass
    
    # Analyze control flow to find potential function starts
    for start_addr, length, bin_offset in segments:
        pc = bin_offset
        end_pc = bin_offset + length
        
        while pc < end_pc:
            current_addr = start_addr + (pc - bin_offset)
            opcode = bytecode[pc]
            
            if opcode in opcode_map:
                mnemonic, operands, size = disassemble_instruction_new(bytecode, pc, opcode_map, register_map)
                
                # Look for CALL instructions
                if mnemonic == 'CALL' and operands:
                    target = operands[0]
                    if target.startswith('0x'):
                        try:
                            target_addr = int(target, 16)
                            # Check if this target is already a known function
                            if target_addr not in function_candidates:
                                # This might be a function start
                                function_candidates[target_addr] = {
                                    'name': f'func_{target_addr:04X}',
                                    'source': 'call_target',
                                    'confidence': 0.8,
                                    'called_from': [current_addr]
                                }
                            else:
                                # Add caller information
                                if 'called_from' not in function_candidates[target_addr]:
                                    function_candidates[target_addr]['called_from'] = []
                                if current_addr not in function_candidates[target_addr]['called_from']:
                                    function_candidates[target_addr]['called_from'].append(current_addr)
                        except ValueError:
                            pass
                
                pc += size
            else:
                pc += 1
    
    # Analyze function sizes and boundaries
    for func_addr, func_info in function_candidates.items():
        # Find the end of the function
        end_addr = find_function_end(func_addr, bytecode, segments, opcode_map, register_map, control_flow)
        func_info['end_addr'] = end_addr
        
        # Estimate function size
        if end_addr:
            func_info['size'] = end_addr - func_addr
        else:
            func_info['size'] = None
    
    return function_candidates

def find_function_end(func_addr, bytecode, segments, opcode_map, register_map, control_flow):
    """
    Find the end address of a function by analyzing control flow.
    """
    # Find which segment contains this function
    for start_addr, length, bin_offset in segments:
        if start_addr <= func_addr < start_addr + length:
            segment_start = start_addr
            segment_end = start_addr + length
            bin_offset_start = bin_offset
            break
    else:
        return None
    
    # Start from function address
    pc = bin_offset_start + (func_addr - segment_start)
    end_pc = bin_offset_start + length
    
    visited = set()
    to_visit = [pc]
    
    while to_visit:
        current_pc = to_visit.pop(0)
        if current_pc in visited or current_pc >= end_pc:
            continue
        
        visited.add(current_pc)
        current_addr = segment_start + (current_pc - bin_offset_start)
        
        if current_pc >= len(bytecode):
            continue
            
        opcode = bytecode[current_pc]
        if opcode not in opcode_map:
            current_pc += 1
            continue
            
        mnemonic, operands, size = disassemble_instruction_new(bytecode, current_pc, opcode_map, register_map)
        
        # Check for return instructions
        if mnemonic in ['RET', 'IRET']:
            # This is a potential function end
            return current_addr + size
        
        # Check for unconditional jumps that exit the function
        elif mnemonic == 'JMP' and operands:
            target = operands[0]
            if target.startswith('0x'):
                try:
                    target_addr = int(target, 16)
                    # If jump target is outside the segment, consider it a function exit
                    if target_addr < segment_start or target_addr >= segment_end:
                        return current_addr + size
                except ValueError:
                    pass
        
        # Add next instruction to visit
        next_pc = current_pc + size
        if next_pc < end_pc and next_pc not in visited:
            to_visit.append(next_pc)
    
    # If we can't find a clear end, use the segment end
    return segment_end

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
    
    # Scan through all instructions, skipping data
    for start_addr, length, bin_offset in segments:
        pc = bin_offset
        end_pc = bin_offset + length
        
        while pc < end_pc:
            current_addr = start_addr + (pc - bin_offset)
            opcode = bytecode[pc]
            
            # Check if this looks like string data first (same as main disassembly)
            is_string, str_length = is_string_data(bytecode, pc)
            if is_string and str_length > 1:  # At least one character plus null terminator
                # Skip string data
                pc += str_length
                continue
            
            # Check for DW directive (16-bit data) - same logic as main disassembly
            # Check this BEFORE validating opcodes
            if pc + 1 < end_pc:
                next_byte = bytecode[pc + 1] if pc + 1 < len(bytecode) else 0
                # If neither byte is a valid opcode, treat as DW data
                if opcode not in opcode_map and next_byte not in opcode_map:
                    # Skip DW data
                    pc += 2
                    continue
            
            # Check for DB directive (8-bit data) - single non-opcode byte
            if opcode not in opcode_map:
                # Single byte of data, skip it
                pc += 1
                continue
            
            # Only process actual instructions
            if opcode in opcode_map:
                mnemonic, operands, size = disassemble_instruction_new(bytecode, pc, opcode_map, register_map)
                
                if pc + size <= len(bytecode):
                    # Check if instruction parsing failed (same logic as main disassembly)
                    instr_info = opcode_map.get(opcode)
                    if instr_info:
                        _, operand_count = instr_info
                        if operand_count > 0 and len(operands) == 0 and pc + 1 < end_pc:
                            # Incomplete instruction, likely data - skip as DW
                            pc += 2
                            continue
                    
                    # Valid instruction - count it
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
                    # Incomplete instruction, skip this byte
                    pc += 1
            else:
                # Not an opcode, skip this byte
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

def interactive_mode(file_path, args):
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
    
    # Load ORG segments (same as main disassembly)
    org_file = file_path.replace('.bin', '.org')
    segments = load_org_segments(org_file)
    if not segments:
        # Fallback: treat entire file as one segment
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
                        address_str = f"{current_addr:04X}"
                        
                        # Check if this looks like string data first (same as main disassembly)
                        is_string, str_length = is_string_data(bytecode, pc)
                        if is_string and str_length > 1:  # At least one character plus null terminator
                            # Display as DEFSTR
                            hex_dump = ' '.join(f'{b:02X}' for b in bytecode[pc:pc + str_length])
                            # Truncate hex dump if too long for better readability
                            if len(hex_dump) > 60:
                                truncated_hex = ' '.join(f'{b:02X}' for b in bytecode[pc:pc + min(20, str_length)])
                                hex_dump = f"{truncated_hex}... (truncated)"
                            string_directive = format_string_data(bytecode, pc, str_length)
                            print(f"{address_str:<6} {hex_dump:<12} {string_directive}")
                            pc += str_length
                            continue
                        
                        # Check for DW directive (16-bit data) - same logic as main disassembly
                        if pc + 1 < end_pc:
                            next_byte = bytecode[pc + 1] if pc + 1 < len(bytecode) else 0
                            # If neither byte is a valid opcode, treat as DW data
                            if opcode not in opcode_map and next_byte not in opcode_map:
                                # Display as DW
                                value = (next_byte << 8) | opcode
                                resolved_value = resolve_symbol(value, symbol_table)
                                hex_dump = f"{opcode:02X} {next_byte:02X}"
                                print(f"{address_str:<6} {hex_dump:<12} DW      {resolved_value}")
                                pc += 2
                                continue
                        
                        # Check for DB directive (8-bit data)
                        if opcode not in opcode_map:
                            hex_dump = f"{opcode:02X}"
                            print(f"{address_str:<6} {hex_dump:<12} DB      0x{opcode:02X}")
                            pc += 1
                            continue
                        
                        if opcode in opcode_map:
                            mnemonic, operands, size = disassemble_instruction_new(bytecode, pc, opcode_map, register_map)
                            
                            if pc + size <= len(bytecode):
                                # Check if instruction parsing failed (same logic as main disassembly)
                                instr_info = opcode_map.get(opcode)
                                if instr_info:
                                    _, operand_count = instr_info
                                    if operand_count > 0 and len(operands) == 0 and pc + 1 < end_pc:
                                        # Incomplete instruction, likely data - skip as DW
                                        pc += 2
                                        continue
                                
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
                print("Code Functions:")
                functions_shown = 0
                for addr, func_info in control_flow['functions'].items():
                    # Check if this address is within an executable segment
                    in_executable_segment = False
                    for start_seg, length, bin_offset in segments:
                        if start_seg <= addr < start_seg + length:
                            in_executable_segment = True
                            break
                    
                    if in_executable_segment:
                        # Additional check: see if this address contains executable code
                        bin_addr = None
                        for start_seg, length, bin_offset in segments:
                            if start_seg <= addr < start_seg + length:
                                bin_addr = bin_offset + (addr - start_seg)
                                break
                        
                        # Check if this looks like executable code (not string data)
                        is_executable = False
                        if bin_addr is not None and bin_addr < len(bytecode):
                            opcode = bytecode[bin_addr] if bin_addr < len(bytecode) else 0
                            # If it's a valid opcode and not string data, consider it executable
                            if opcode in opcode_map:
                                is_string, _ = is_string_data(bytecode, bin_addr)
                                if not is_string:
                                    is_executable = True
                        
                        # Only show as function if it's executable code
                        if is_executable:
                            print(f"  {func_info['name']} (0x{addr:04X}): {len(func_info['basic_blocks'])} basic blocks")
                            functions_shown += 1
                
                if functions_shown == 0:
                    print("  No functions identified in executable segments")
                
                # Show constants and data separately
                print("\nConstants and Data:")
                constants_shown = 0
                for symbol, addr_str in symbol_table.items():
                    if addr_str.startswith('0x'):
                        try:
                            addr = int(addr_str, 16)
                            
                            # Find the binary address for this symbol
                            bin_addr = None
                            for start_seg, length, bin_offset in segments:
                                if start_seg <= addr < start_seg + length:
                                    bin_addr = bin_offset + (addr - start_seg)
                                    break
                            
                            if bin_addr is not None and bin_addr < len(bytecode):
                                # First try to find the actual start of the string
                                string_start = find_string_start(bytecode, bin_addr)
                                is_string, str_length = is_string_data(bytecode, string_start)
                                if is_string and str_length > 1:
                                    # Extract and format the string from the actual start
                                    string_content = format_string_data(bytecode, string_start, str_length)
                                    # Remove the "DEFSTR " prefix for display
                                    if string_content.startswith('DEFSTR "'):
                                        # Find the closing quote
                                        end_quote = string_content.find('"', 8)
                                        if end_quote != -1:
                                            string_value = string_content[7:end_quote + 1]  # Include quotes
                                            print(f"  {symbol} = {string_value} (string)")
                                        else:
                                            print(f"  {symbol} = {string_content[8:]} (string)")
                                    else:
                                        print(f"  {symbol} = {addr_str} (string)")
                                    constants_shown += 1
                                    continue
                            
                            # Check if this is NOT in an executable segment (likely a constant)
                            in_executable_segment = False
                            for start_seg, length, bin_offset in segments:
                                if start_seg <= addr < start_seg + length:
                                    in_executable_segment = True
                                    break
                            
                            if not in_executable_segment:
                                # Regular constant
                                print(f"  {symbol} = {addr_str}")
                                constants_shown += 1
                        except ValueError:
                            pass
                
                if constants_shown == 0:
                    print("  No constants or data found")
                
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

def main():
    """Main entry point for the disassembler"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Nova-16 Disassembler')
    parser.add_argument('file', help='Binary file to disassemble')
    parser.add_argument('--output', '-o', help='Output file (default: stdout)')
    parser.add_argument('--quiet', '-q', action='store_true', help='Suppress non-essential output')
    parser.add_argument('--show-hex', action='store_true', help='Show hex dump of instructions')
    parser.add_argument('--show-addresses', action='store_true', help='Show addresses')
    parser.add_argument('--start', type=lambda x: int(x, 0), help='Start address for disassembly')
    parser.add_argument('--end', type=lambda x: int(x, 0), help='End address for disassembly')
    parser.add_argument('--filter-instructions', help='Comma-separated list of instructions to show')
    parser.add_argument('--exclude-instructions', help='Comma-separated list of instructions to hide')
    parser.add_argument('--format', choices=['text', 'html', 'json'], default='text', help='Output format')
    parser.add_argument('--interactive', '-i', action='store_true', help='Start interactive mode')
    parser.add_argument('--analyze-dataflow', action='store_true', help='Perform data flow analysis')
    parser.add_argument('--analyze-liveness', action='store_true', help='Perform register liveness analysis')
    parser.add_argument('--analyze-functions', action='store_true', help='Analyze function boundaries')
    parser.add_argument('--analyze-loops', action='store_true', help='Analyze loop structures')
    parser.add_argument('--analyze-deadcode', action='store_true', help='Analyze dead code')
    parser.add_argument('--analyze-security', action='store_true', help='Perform security analysis')
    parser.add_argument('--analyze-patterns', action='store_true', help='Perform pattern recognition')
    
    args = parser.parse_args()
    
    if args.interactive:
        # Create a mock args object for interactive mode
        class MockArgs:
            def __init__(self, original_args):
                self.quiet = original_args.quiet
                self.analyze_dataflow = original_args.analyze_dataflow
                self.analyze_liveness = original_args.analyze_liveness
                self.analyze_functions = original_args.analyze_functions
                self.analyze_loops = original_args.analyze_loops
                self.analyze_deadcode = original_args.analyze_deadcode
                self.analyze_security = original_args.analyze_security
                self.analyze_patterns = original_args.analyze_patterns
        
        mock_args = MockArgs(args)
        interactive_mode(args.file, mock_args)
    else:
        # Regular disassembly
        disassemble(args.file, args)

if __name__ == '__main__':
    main()

