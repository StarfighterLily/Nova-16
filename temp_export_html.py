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
                mnemonic, operands, size = disassemble_instruction_new(bytecode, pc, opcode_map, register_map, reverse_symbol_table)
                
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
