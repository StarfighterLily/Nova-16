#!/usr/bin/env python3
"""
FORTH Compiler Optimizer for Nova-16
Provides advanced optimization passes for FORTH-to-assembly compilation.

Phase 4D: Optimization & Integration - Focus Areas:
1. Register allocation for stack operations
2. Code size optimization
3. Performance benchmarking
4. Integration testing
"""

import sys
import os
import re
from typing import Dict, List, Tuple, Optional, Set
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

class ForthOptimizer:
    """
    Advanced optimizer for FORTH compiled assembly code.
    Implements register allocation, dead code elimination, and performance optimizations.
    """

    def __init__(self):
        # Optimization settings
        self.enable_register_allocation = False  # Disabled for now - needs more work
        self.enable_peephole_optimization = True
        self.enable_dead_code_elimination = True
        self.enable_stack_optimization = True
        
        # Register allocation state
        self.register_map = {
            'R0': None,  # Currently allocated value
            'R1': None,
            'R2': None,
            'R3': None,
            'R4': None,
            'R5': None,
            'R6': None,
            'R7': None,
        }
        
        # Stack depth tracking for optimization
        self.current_stack_depth = 0
        self.max_stack_depth = 0
        
        # Performance metrics
        self.original_size = 0
        self.optimized_size = 0
        self.optimization_passes = 0

    def optimize_assembly(self, assembly_lines: List[str]) -> List[str]:
        """
        Apply comprehensive optimization passes to assembly code.
        
        Returns optimized assembly with performance improvements.
        """
        self.original_size = len(assembly_lines)
        optimized = assembly_lines.copy()
        
        if self.enable_register_allocation:
            optimized = self._optimize_register_allocation(optimized)
            
        if self.enable_stack_optimization:
            optimized = self._optimize_stack_operations(optimized)
            
        if self.enable_peephole_optimization:
            optimized = self._apply_peephole_optimization(optimized)
            
        if self.enable_dead_code_elimination:
            optimized = self._eliminate_dead_code(optimized)
            
        self.optimized_size = len(optimized)
        return optimized

    def _optimize_register_allocation(self, lines: List[str]) -> List[str]:
        """
        Optimize register allocation for frequently used values.
        Keep stack top in registers when possible.
        """
        optimized = []
        stack_top_reg = None  # Track which register holds stack top
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Detect stack operations and optimize
            if self._is_stack_push(line):
                # Try to keep value in register instead of immediate stack write
                if stack_top_reg is None:
                    stack_top_reg = 'R0'
                    # Instead of immediate stack write, keep in register
                    optimized.append(line.replace('[P8]', stack_top_reg))
                else:
                    # Need to spill current register to stack first
                    optimized.extend([
                        f"    DEC P8",
                        f"    DEC P8", 
                        f"    MOV [P8], {stack_top_reg}",
                        line
                    ])
                    
            elif self._is_stack_pop(line):
                if stack_top_reg is not None:
                    # Value already in register, use it directly
                    optimized.append(line.replace('[P8]', stack_top_reg))
                    stack_top_reg = None
                else:
                    optimized.append(line)
                    
            else:
                optimized.append(line)
                
            i += 1
            
        return optimized

    def _optimize_stack_operations(self, lines: List[str]) -> List[str]:
        """
        Optimize common stack operation patterns.
        """
        optimized = []
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Pattern: DEC P8; DEC P8; MOV [P8], Rx followed by MOV Ry, [P8]; INC P8; INC P8
            # This is a push followed immediately by pop - can be optimized to register move
            if (i + 5 < len(lines) and
                line == "DEC P8" and 
                lines[i+1].strip() == "DEC P8" and
                lines[i+2].strip().startswith("MOV [P8], ") and
                lines[i+3].strip().startswith("MOV ") and "[P8]" in lines[i+3] and
                lines[i+4].strip() == "INC P8" and
                lines[i+5].strip() == "INC P8"):
                
                # Extract register names
                push_reg = lines[i+2].strip().split(", ")[1]
                pop_line = lines[i+3].strip()
                pop_reg = pop_line.split(", ")[0].split()[1]
                
                # Replace with direct register move if different registers
                if push_reg != pop_reg:
                    optimized.append(f"    MOV {pop_reg}, {push_reg}  ; Optimized push/pop")
                else:
                    # Same register - this is a no-op, skip entirely
                    optimized.append("    ; Eliminated redundant push/pop")
                
                i += 6  # Skip the optimized pattern
                continue
                
            # Pattern: INC followed by DEC of same register -> eliminate both
            elif (i + 1 < len(lines) and
                  line.startswith("INC ") and
                  lines[i+1].strip().startswith("DEC ") and
                  line.split()[1] == lines[i+1].strip().split()[1]):
                
                # Skip both instructions (they cancel out)
                optimized.append("    ; Eliminated INC/DEC pair")
                i += 2
                continue
                
            # Pattern: DEC followed by INC of same register -> eliminate both  
            elif (i + 1 < len(lines) and
                  line.startswith("DEC ") and
                  lines[i+1].strip().startswith("INC ") and
                  line.split()[1] == lines[i+1].strip().split()[1]):
                
                # Skip both instructions (they cancel out)
                optimized.append("    ; Eliminated DEC/INC pair")
                i += 2
                continue
                
            else:
                optimized.append(lines[i])
                
            i += 1
            
        return optimized

    def _apply_peephole_optimization(self, lines: List[str]) -> List[str]:
        """
        Apply peephole optimizations for common instruction patterns.
        """
        optimized = []
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Pattern: MOV R0, X followed by MOV R1, R0 -> MOV R1, X
            if (i + 1 < len(lines) and
                line.startswith("MOV R") and ", " in line and
                lines[i+1].strip().startswith("MOV R") and
                line.split(", ")[0].split()[1] in lines[i+1]):
                
                parts1 = line.split(", ")
                parts2 = lines[i+1].strip().split(", ")
                
                if len(parts1) == 2 and len(parts2) == 2:
                    reg1 = parts1[0].split()[1]
                    val1 = parts1[1]
                    reg2 = parts2[0].split()[1]
                    val2 = parts2[1]
                    
                    if val2 == reg1:  # Second instruction uses first register
                        optimized.extend([
                            lines[i],  # Keep first instruction
                            f"    MOV {reg2}, {val1}"  # Optimize second
                        ])
                        i += 2
                        continue
            
            # Pattern: INC followed by DEC of same register -> eliminate both
            elif (i + 1 < len(lines) and
                  line.startswith("INC ") and
                  lines[i+1].strip().startswith("DEC ") and
                  line.split()[1] == lines[i+1].strip().split()[1]):
                
                # Skip both instructions (they cancel out)
                i += 2
                continue
                
            # Pattern: DEC followed by INC of same register -> eliminate both  
            elif (i + 1 < len(lines) and
                  line.startswith("DEC ") and
                  lines[i+1].strip().startswith("INC ") and
                  line.split()[1] == lines[i+1].strip().split()[1]):
                
                # Skip both instructions (they cancel out)
                i += 2
                continue
                
            else:
                optimized.append(lines[i])
                
            i += 1
            
        return optimized

    def _eliminate_dead_code(self, lines: List[str]) -> List[str]:
        """
        Remove dead code and unused labels.
        """
        optimized = []
        used_labels = set()
        
        # First pass: find all referenced labels
        for line in lines:
            stripped = line.strip()
            # Look for jumps, calls, and references
            if any(instr in stripped for instr in ['JMP', 'JZ', 'JNZ', 'JGE', 'JLE', 'CALL']):
                words = stripped.split()
                if len(words) >= 2:
                    target = words[-1]  # Last word is usually the target
                    used_labels.add(target)
        
        # Second pass: remove unused labels and unreachable code
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Keep labels that are used
            if stripped.endswith(':'):
                label = stripped[:-1]
                if label in used_labels or label in ['main', 'forth_main']:  # Always keep entry points
                    optimized.append(line)
                # Skip unused labels
                
            # Keep all other non-empty lines (comments, instructions)
            elif stripped:
                optimized.append(line)
            else:
                # Keep empty lines for readability
                optimized.append(line)
                
        return optimized

    def _is_stack_push(self, line: str) -> bool:
        """Check if line is a stack push operation."""
        return (line.strip().startswith("DEC P8") or 
                (line.strip().startswith("MOV [P8],") and "DEC P8" in line))

    def _is_stack_pop(self, line: str) -> bool:
        """Check if line is a stack pop operation."""
        return (line.strip().startswith("INC P8") or 
                (line.strip().startswith("MOV") and "[P8]" in line and "INC P8" in line))

    def _generate_optimized_dup(self, count: int) -> List[str]:
        """Generate optimized assembly for multiple DUP operations."""
        lines = []
        
        if count == 1:
            # Single DUP - standard implementation
            lines.extend([
                "    ; DUP (optimized)",
                "    MOV R0, [P8]",
                "    DEC P8",
                "    DEC P8", 
                "    MOV [P8], R0"
            ])
        elif count <= 4:
            # Multiple DUPs - unroll for better performance
            lines.append(f"    ; {count}x DUP (optimized unroll)")
            lines.append("    MOV R0, [P8]")
            
            for i in range(count):
                lines.extend([
                    "    DEC P8",
                    "    DEC P8",
                    "    MOV [P8], R0"
                ])
        else:
            # Many DUPs - use loop
            lines.extend([
                f"    ; {count}x DUP (optimized loop)",
                "    MOV R0, [P8]",
                f"    MOV R1, {count}",
                "dup_loop:",
                "    DEC P8", 
                "    DEC P8",
                "    MOV [P8], R0",
                "    DEC R1",
                "    JNZ dup_loop"
            ])
            
        return lines

    def get_optimization_report(self) -> str:
        """Generate optimization report."""
        size_reduction = self.original_size - self.optimized_size
        if self.original_size > 0:
            percentage = (size_reduction / self.original_size) * 100
        else:
            percentage = 0
            
        report = f"""
FORTH Compiler Optimization Report
==================================

Original size: {self.original_size} lines
Optimized size: {self.optimized_size} lines
Size reduction: {size_reduction} lines ({percentage:.1f}%)

Optimization passes applied:
- Register allocation: {"✓" if self.enable_register_allocation else "✗"}
- Stack optimization: {"✓" if self.enable_stack_optimization else "✗"}
- Peephole optimization: {"✓" if self.enable_peephole_optimization else "✗"}
- Dead code elimination: {"✓" if self.enable_dead_code_elimination else "✗"}

Max stack depth detected: {self.max_stack_depth}
"""
        return report.strip()


def main():
    """Test the optimizer with sample assembly code."""
    optimizer = ForthOptimizer()
    
    # Sample assembly code with optimization opportunities
    sample_code = [
        "; Test assembly code",
        "    MOV R0, 5",
        "    DEC P8",
        "    DEC P8", 
        "    MOV [P8], R0",
        "    MOV R1, [P8]",
        "    INC P8",
        "    INC P8",
        "    DEC P8",
        "    DEC P8",
        "    MOV [P8], R1",
        "    ; End test"
    ]
    
    print("Original code:")
    for i, line in enumerate(sample_code):
        print(f"{i+1:2d}: {line}")
    
    optimized = optimizer.optimize_assembly(sample_code)
    
    print("\nOptimized code:")
    for i, line in enumerate(optimized):
        print(f"{i+1:2d}: {line}")
        
    print(optimizer.get_optimization_report())


if __name__ == "__main__":
    main()
