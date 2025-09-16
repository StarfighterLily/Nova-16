#!/usr/bin/env python3
"""
Astrid Assembly Inspector
Analyzes generated assembly code and correlates it with source code.
"""

import argparse
import sys
import os
import subprocess
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class AssemblyBlock:
    """Represents a block of assembly instructions."""
    start_line: int
    end_line: int
    instructions: List[str]
    source_function: Optional[str] = None
    label: Optional[str] = None
    instruction_count: int = 0


@dataclass
class InstructionInfo:
    """Information about an assembly instruction."""
    line_number: int
    instruction: str
    operands: List[str]
    addressing_mode: str
    estimated_cycles: int
    register_usage: List[str]
    flags_affected: List[str]


class AstridAssemblyInspector:
    """Inspector for Astrid-generated assembly code."""
    
    def __init__(self):
        self.nova_dir = Path(__file__).parent
        
        # Nova-16 instruction timing (estimated cycles)
        self.instruction_timing = {
            'MOV': 1, 'ADD': 1, 'SUB': 1, 'MUL': 3, 'DIV': 5,
            'AND': 1, 'OR': 1, 'XOR': 1, 'NOT': 1,
            'SHL': 1, 'SHR': 1, 'ROL': 1, 'ROR': 1,
            'CMP': 1, 'TST': 1,
            'JMP': 2, 'JZ': 2, 'JNZ': 2, 'JC': 2, 'JNC': 2,
            'CALL': 3, 'RET': 2, 'IRET': 3,
            'PUSH': 2, 'POP': 2,
            'LOAD': 2, 'STORE': 2,
            'SWRITE': 2, 'SREAD': 2, 'VWRITE': 2, 'VREAD': 2,
            'SROLX': 2, 'SROLY': 2, 'SPLAY': 2, 'SSTOP': 1,
            'KEYIN': 2, 'KEYSTAT': 1,
            'HALT': 1, 'NOP': 1
        }
        
        # Register categories
        self.r_registers = [f'R{i}' for i in range(10)]
        self.p_registers = [f'P{i}' for i in range(10)]
        self.special_registers = ['VX', 'VY', 'VM', 'VL', 'SA', 'SF', 'SV', 'SW', 
                                'TT', 'TM', 'TC', 'TS', 'SP', 'FP']
    
    def inspect_assembly(self, ast_file: str) -> Dict[str, Any]:
        """
        Inspect assembly generated from an Astrid file.
        
        Args:
            ast_file: Path to the Astrid source file
            
        Returns:
            Dictionary containing inspection results
        """
        results = {
            'source_file': ast_file,
            'compilation': {},
            'assembly_file': None,
            'blocks': [],
            'instructions': [],
            'statistics': {},
            'optimization_analysis': {},
            'correlations': {}
        }
        
        # Step 1: Compile to assembly
        print("🔄 Compiling Astrid to assembly...")
        compile_result = self._compile_to_assembly(ast_file)
        results['compilation'] = compile_result
        
        if not compile_result.get('success'):
            return results
        
        asm_file = compile_result['assembly_file']
        results['assembly_file'] = asm_file
        
        # Step 2: Parse assembly file
        print("📖 Parsing assembly code...")
        assembly_data = self._parse_assembly_file(asm_file)
        results.update(assembly_data)
        
        # Step 3: Analyze instructions
        print("🔍 Analyzing instructions...")
        instruction_analysis = self._analyze_instructions(assembly_data['instructions'])
        results['instruction_analysis'] = instruction_analysis
        
        # Step 4: Calculate statistics
        print("📊 Calculating statistics...")
        statistics = self._calculate_statistics(assembly_data, instruction_analysis)
        results['statistics'] = statistics
        
        # Step 5: Optimization analysis
        print("💡 Analyzing optimizations...")
        optimization_analysis = self._analyze_optimizations(assembly_data['instructions'])
        results['optimization_analysis'] = optimization_analysis
        
        # Step 6: Source correlation (if possible)
        print("🔗 Correlating with source...")
        correlations = self._correlate_with_source(ast_file, assembly_data)
        results['correlations'] = correlations
        
        return results
    
    def _compile_to_assembly(self, ast_file: str) -> Dict[str, Any]:
        """Compile Astrid source to assembly."""
        try:
            ast_path = Path(ast_file)
            astrid_dir = self.nova_dir / "astrid"
            
            # Run Astrid compiler
            cmd = ["python", "run_astrid.py", str(ast_path.name)]
            result = subprocess.run(cmd, cwd=astrid_dir, capture_output=True, text=True)
            
            asm_file = astrid_dir / f"{ast_path.stem}.asm"
            
            return {
                'success': result.returncode == 0,
                'assembly_file': str(asm_file) if result.returncode == 0 else None,
                'output': result.stdout,
                'errors': result.stderr,
                'return_code': result.returncode
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _parse_assembly_file(self, asm_file: str) -> Dict[str, Any]:
        """Parse assembly file into structured data."""
        try:
            with open(asm_file, 'r') as f:
                lines = f.readlines()
            
            blocks = []
            instructions = []
            current_block = None
            current_function = None
            
            for line_num, line in enumerate(lines, 1):
                original_line = line
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith(';'):
                    continue
                
                # Function labels (comments indicating source functions)
                if line.startswith('; Function:'):
                    match = re.search(r'; Function: (\w+)', line)
                    if match:
                        current_function = match.group(1)
                        if current_block:
                            current_block.end_line = line_num - 1
                            blocks.append(current_block)
                        current_block = AssemblyBlock(line_num, line_num, [], current_function)
                    continue
                
                # Labels
                if line.endswith(':'):
                    label = line[:-1]
                    if current_block:
                        current_block.end_line = line_num - 1
                        blocks.append(current_block)
                    current_block = AssemblyBlock(line_num, line_num, [], current_function, label)
                    continue
                
                # Instructions
                if re.match(r'^[A-Z]+\b', line):
                    if not current_block:
                        current_block = AssemblyBlock(line_num, line_num, [], current_function)
                    
                    current_block.instructions.append(line)
                    current_block.instruction_count += 1
                    current_block.end_line = line_num
                    
                    # Parse instruction details
                    instruction_info = self._parse_instruction(line, line_num)
                    instructions.append(instruction_info)
            
            # Close final block
            if current_block:
                blocks.append(current_block)
            
            return {
                'blocks': blocks,
                'instructions': instructions,
                'total_lines': len(lines),
                'code_lines': len([l for l in lines if l.strip() and not l.strip().startswith(';')])
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _parse_instruction(self, line: str, line_num: int) -> InstructionInfo:
        """Parse a single assembly instruction."""
        parts = re.split(r'[,\s]+', line.strip())
        instruction = parts[0] if parts else ''
        operands = [op.strip() for op in parts[1:] if op.strip()]
        
        # Determine addressing mode
        addressing_mode = 'register'
        for operand in operands:
            if operand.startswith('#'):
                addressing_mode = 'immediate'
                break
            elif operand.startswith('[') or operand.startswith('('):
                addressing_mode = 'indirect'
                break
            elif re.match(r'^\d+$', operand) or operand.startswith('0x'):
                addressing_mode = 'direct'
                break
        
        # Estimate cycles
        cycles = self.instruction_timing.get(instruction, 1)
        if addressing_mode == 'indirect':
            cycles += 1
        
        # Determine register usage
        register_usage = []
        for operand in operands:
            clean_operand = re.sub(r'[^\w]', '', operand)
            if clean_operand in self.r_registers + self.p_registers + self.special_registers:
                register_usage.append(clean_operand)
        
        return InstructionInfo(
            line_number=line_num,
            instruction=instruction,
            operands=operands,
            addressing_mode=addressing_mode,
            estimated_cycles=cycles,
            register_usage=register_usage,
            flags_affected=[]  # Could be expanded based on instruction
        )
    
    def _analyze_instructions(self, instructions: List[InstructionInfo]) -> Dict[str, Any]:
        """Analyze instruction patterns and characteristics."""
        analysis = {
            'instruction_frequency': defaultdict(int),
            'addressing_modes': defaultdict(int),
            'register_pressure': defaultdict(int),
            'total_estimated_cycles': 0,
            'critical_path_instructions': [],
            'register_usage_patterns': defaultdict(list)
        }
        
        for instr in instructions:
            analysis['instruction_frequency'][instr.instruction] += 1
            analysis['addressing_modes'][instr.addressing_mode] += 1
            analysis['total_estimated_cycles'] += instr.estimated_cycles
            
            # Track register usage
            for reg in instr.register_usage:
                analysis['register_pressure'][reg] += 1
                analysis['register_usage_patterns'][reg].append(instr.line_number)
            
            # Mark expensive instructions
            if instr.estimated_cycles > 2:
                analysis['critical_path_instructions'].append({
                    'line': instr.line_number,
                    'instruction': instr.instruction,
                    'cycles': instr.estimated_cycles
                })
        
        return dict(analysis)
    
    def _calculate_statistics(self, assembly_data: Dict, instruction_analysis: Dict) -> Dict[str, Any]:
        """Calculate comprehensive statistics."""
        instructions = assembly_data.get('instructions', [])
        blocks = assembly_data.get('blocks', [])
        
        stats = {
            'total_instructions': len(instructions),
            'total_blocks': len(blocks),
            'average_block_size': 0,
            'max_block_size': 0,
            'estimated_execution_cycles': instruction_analysis.get('total_estimated_cycles', 0),
            'code_density': 0,
            'register_utilization': {},
            'instruction_mix': {}
        }
        
        if blocks:
            block_sizes = [block.instruction_count for block in blocks]
            stats['average_block_size'] = sum(block_sizes) / len(block_sizes)
            stats['max_block_size'] = max(block_sizes)
        
        # Code density (instructions per line)
        if assembly_data.get('total_lines', 0) > 0:
            stats['code_density'] = len(instructions) / assembly_data['total_lines']
        
        # Register utilization
        register_pressure = instruction_analysis.get('register_pressure', {})
        total_register_uses = sum(register_pressure.values())
        
        if total_register_uses > 0:
            # Calculate register utilization percentages
            for reg_type in ['R', 'P']:
                type_usage = sum(count for reg, count in register_pressure.items() 
                               if reg.startswith(reg_type))
                stats['register_utilization'][f'{reg_type}_registers'] = type_usage / total_register_uses
        
        # Instruction mix percentages
        freq = instruction_analysis.get('instruction_frequency', {})
        total = sum(freq.values())
        if total > 0:
            for instr, count in freq.items():
                stats['instruction_mix'][instr] = count / total
        
        return stats
    
    def _analyze_optimizations(self, instructions: List[InstructionInfo]) -> Dict[str, Any]:
        """Analyze optimization opportunities in the assembly code."""
        optimizations = {
            'opportunities': [],
            'redundant_moves': [],
            'dead_code': [],
            'register_spills': [],
            'optimization_score': 0
        }
        
        # Look for optimization patterns
        for i, instr in enumerate(instructions):
            # Redundant MOV instructions
            if instr.instruction == 'MOV' and i < len(instructions) - 1:
                next_instr = instructions[i + 1]
                if (next_instr.instruction == 'MOV' and 
                    len(instr.operands) >= 2 and len(next_instr.operands) >= 2 and
                    instr.operands[1] == next_instr.operands[0]):
                    optimizations['redundant_moves'].append({
                        'line': instr.line_number,
                        'pattern': f"MOV {instr.operands[0]}, {instr.operands[1]} -> MOV {next_instr.operands[0]}, {next_instr.operands[1]}",
                        'suggestion': f"Could be optimized to MOV {instr.operands[0]}, {next_instr.operands[1]}"
                    })
            
            # Memory-to-memory moves (potential for register optimization)
            if instr.instruction == 'MOV' and len(instr.operands) >= 2:
                src, dst = instr.operands[0], instr.operands[1]
                if (not any(src.startswith(reg) for reg in self.r_registers + self.p_registers) and
                    not any(dst.startswith(reg) for reg in self.r_registers + self.p_registers)):
                    optimizations['register_spills'].append({
                        'line': instr.line_number,
                        'instruction': f"MOV {src}, {dst}",
                        'suggestion': "Consider using a register intermediate"
                    })
        
        # Calculate optimization score (0-100)
        total_instructions = len(instructions)
        issues = (len(optimizations['redundant_moves']) + 
                 len(optimizations['register_spills']))
        optimizations['optimization_score'] = max(0, 100 - (issues * 10))
        
        return optimizations
    
    def _correlate_with_source(self, ast_file: str, assembly_data: Dict) -> Dict[str, Any]:
        """Correlate assembly code with source code."""
        correlations = {
            'function_mappings': {},
            'line_mappings': {},
            'source_efficiency': {}
        }
        
        try:
            # Read source file
            with open(ast_file, 'r') as f:
                source_lines = f.readlines()
            
            # Extract function information from source
            source_functions = {}
            current_func = None
            brace_count = 0
            
            for line_num, line in enumerate(source_lines, 1):
                line = line.strip()
                
                # Function declarations
                func_match = re.match(r'(void|int8|int16)\s+(\w+)\s*\([^)]*\)\s*{?', line)
                if func_match:
                    current_func = func_match.group(2)
                    source_functions[current_func] = {
                        'start_line': line_num,
                        'end_line': None,
                        'source_lines': 0
                    }
                
                if current_func:
                    if '{' in line:
                        brace_count += line.count('{')
                    if '}' in line:
                        brace_count -= line.count('}')
                        if brace_count == 0:
                            source_functions[current_func]['end_line'] = line_num
                            source_functions[current_func]['source_lines'] = (
                                line_num - source_functions[current_func]['start_line'] + 1
                            )
                            current_func = None
            
            # Map to assembly blocks
            blocks = assembly_data.get('blocks', [])
            for block in blocks:
                if block.source_function and block.source_function in source_functions:
                    src_func = source_functions[block.source_function]
                    correlations['function_mappings'][block.source_function] = {
                        'source_lines': src_func['source_lines'],
                        'assembly_instructions': block.instruction_count,
                        'expansion_ratio': block.instruction_count / max(1, src_func['source_lines']),
                        'assembly_start': block.start_line,
                        'assembly_end': block.end_line
                    }
            
            # Calculate overall efficiency
            total_source_lines = len([l for l in source_lines if l.strip() and not l.strip().startswith('//')])
            total_asm_instructions = len(assembly_data.get('instructions', []))
            
            correlations['source_efficiency'] = {
                'source_lines': total_source_lines,
                'assembly_instructions': total_asm_instructions,
                'overall_expansion_ratio': total_asm_instructions / max(1, total_source_lines)
            }
            
        except Exception as e:
            correlations['error'] = str(e)
        
        return correlations


def print_inspection_results(results: Dict[str, Any], verbose: bool = False):
    """Print assembly inspection results."""
    print(f"=== ASTRID ASSEMBLY INSPECTOR ===")
    print(f"Source: {results['source_file']}")
    print(f"Assembly: {results.get('assembly_file', 'N/A')}")
    
    # Compilation status
    comp = results['compilation']
    if comp.get('success'):
        print(f"✅ Compilation: SUCCESS")
    else:
        print(f"❌ Compilation: FAILED")
        if 'error' in comp:
            print(f"   Error: {comp['error']}")
        return
    
    # Statistics
    stats = results.get('statistics', {})
    print(f"\n📊 ASSEMBLY STATISTICS:")
    print(f"  Total instructions: {stats.get('total_instructions', 0)}")
    print(f"  Total blocks: {stats.get('total_blocks', 0)}")
    print(f"  Average block size: {stats.get('average_block_size', 0):.1f}")
    print(f"  Estimated cycles: {stats.get('estimated_execution_cycles', 0)}")
    print(f"  Code density: {stats.get('code_density', 0):.2f}")
    
    # Instruction analysis
    instr_analysis = results.get('instruction_analysis', {})
    if verbose and 'instruction_frequency' in instr_analysis:
        print(f"\n🔧 INSTRUCTION FREQUENCY:")
        freq = dict(instr_analysis['instruction_frequency'])
        for instr, count in sorted(freq.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {instr}: {count}")
    
    # Register utilization
    if 'register_utilization' in stats:
        print(f"\n📝 REGISTER UTILIZATION:")
        for reg_type, util in stats['register_utilization'].items():
            print(f"  {reg_type}: {util:.1%}")
    
    # Optimization analysis
    opt_analysis = results.get('optimization_analysis', {})
    if opt_analysis:
        print(f"\n💡 OPTIMIZATION ANALYSIS:")
        print(f"  Optimization score: {opt_analysis.get('optimization_score', 0)}/100")
        
        if opt_analysis.get('redundant_moves'):
            print(f"  Redundant moves: {len(opt_analysis['redundant_moves'])}")
        
        if opt_analysis.get('register_spills'):
            print(f"  Potential register spills: {len(opt_analysis['register_spills'])}")
        
        if verbose:
            for opportunity in opt_analysis.get('opportunities', [])[:5]:
                print(f"    - Line {opportunity.get('line', '?')}: {opportunity.get('suggestion', 'N/A')}")
    
    # Source correlation
    correlations = results.get('correlations', {})
    if 'source_efficiency' in correlations:
        eff = correlations['source_efficiency']
        print(f"\n🔗 SOURCE CORRELATION:")
        print(f"  Source lines: {eff.get('source_lines', 0)}")
        print(f"  Assembly instructions: {eff.get('assembly_instructions', 0)}")
        print(f"  Expansion ratio: {eff.get('overall_expansion_ratio', 0):.1f}x")
    
    if verbose and 'function_mappings' in correlations:
        print(f"\n🔧 FUNCTION MAPPINGS:")
        for func_name, mapping in correlations['function_mappings'].items():
            print(f"  {func_name}: {mapping['source_lines']} lines → {mapping['assembly_instructions']} instructions ({mapping['expansion_ratio']:.1f}x)")


def main():
    parser = argparse.ArgumentParser(description="Astrid Assembly Inspector")
    parser.add_argument("source", help="Astrid source file (.ast)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.source):
        print(f"Error: Source file '{args.source}' not found")
        sys.exit(1)
    
    inspector = AstridAssemblyInspector()
    results = inspector.inspect_assembly(args.source)
    
    if args.json:
        import json
        # Make results JSON-serializable
        json_results = {}
        for key, value in results.items():
            if isinstance(value, (defaultdict, dict)):
                json_results[key] = dict(value)
            elif hasattr(value, '__dict__'):
                json_results[key] = value.__dict__
            elif isinstance(value, list) and value and hasattr(value[0], '__dict__'):
                json_results[key] = [item.__dict__ if hasattr(item, '__dict__') else item for item in value]
            else:
                json_results[key] = value
        print(json.dumps(json_results, indent=2))
    else:
        print_inspection_results(results, args.verbose)


if __name__ == "__main__":
    main()
