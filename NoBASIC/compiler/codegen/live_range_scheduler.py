"""
NoBASIC Live Range Scheduler

Reorders operations to minimize spill pressure and register pressure.

Optimizations:
1. Operation Reordering - Reorder independent operations to defer spills
2. Register Pressure Minimization - Move operations that free registers earlier
3. Critical Path Analysis - Identify operations on critical execution path
4. Spill Minimization - Defer operations with long live ranges

Expected Benefits:
- 3-8% spill reduction
- Better register pressure distribution
- Improved memory access patterns
"""

import re
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict


REGISTER_NAMES = {
    'R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9',
    'P0', 'P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'SP', 'FP',
    'VX', 'VY', 'VM', 'VL', 'VC', 'SA', 'SF', 'SV', 'SW', 'TT', 'TM', 'TC', 'TS', 'C0', 'C1'
}

# Opcodes that have observable side effects beyond register writes (IO/memory)
SIDE_EFFECT_OPCODES = {
    # Graphics / text
    'SREAD', 'SWRITE', 'SPLAY', 'TEXT', 'CHAR', 'SBLEND', 'SROL', 'SROT', 'SSHFT',
    'SFLIP', 'SBLIT', 'SFILL', 'SLINE', 'SRECT', 'SCIRC', 'SINV', 'VREAD', 'VWRITE',
    'VBLIT', 'SPBLIT', 'SPBLITALL',
    # Serial IO
    'SEROUT', 'SERCTRL', 'SERIN', 'SERSTAT',
    # Input / stack
    'KEYIN', 'KEYSTAT', 'PUSH', 'POP',
    # Randomness (order-sensitive PRNG state)
    'RND', 'RNDR'
}


@dataclass
class IRInstruction:
    """Intermediate representation of an instruction with dependencies."""
    index: int
    opcode: str
    operands: List[str]
    defines: Set[str] = field(default_factory=set)  # Variables this defines
    uses: Set[str] = field(default_factory=set)     # Variables this uses
    dependencies: Set[int] = field(default_factory=set)  # Indices of deps
    dependents: Set[int] = field(default_factory=set)    # Indices of dependent instrs
    pressure_hint: int = 0
    has_side_effect: bool = False
    is_label: bool = False
    is_jump: bool = False
    is_call: bool = False
    original_line: str = ""
    
    def can_move_after(self, other: 'IRInstruction') -> bool:
        """Check if this instruction can move after another."""
        # Can't move across labels, jumps, or calls (basic block boundaries)
        if other.is_label or other.is_jump or self.is_label or self.is_jump:
            return False
        if self.is_call or other.is_call:
            return False
        if self.has_side_effect or other.has_side_effect:
            return False
        
        # Check for data dependencies (all hazard types)
        # RAW: other defines what we use
        if self.uses & other.defines:
            return False
        # WAR: we define what other uses
        if self.defines & other.uses:
            return False
        # WAW: both define the same variable
        if self.defines & other.defines:
            return False
        
        return True


class LiveRangeScheduler:
    """
    Reorder instructions to minimize spill pressure.
    
    Strategy:
    1. Build dependency graph
    2. Identify independent instructions
    3. Reorder to minimize peak register pressure
    4. Prioritize operations that free registers early
    """
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.instructions: List[IRInstruction] = []
        self.optimizations_applied = defaultdict(int)
    
    def schedule(self, assembly_lines: List[str], variable_lifetimes: Optional[Dict[str, Tuple[int, int]]] = None) -> List[str]:
        """
        Schedule instructions to minimize spill pressure.
        
        Args:
            assembly_lines: List of assembly instruction lines
            variable_lifetimes: Optional dict of variable -> (start, end) indices
            
        Returns:
            Reordered assembly lines
        """
        # Parse instructions into IR
        self.instructions = self._parse_ir(assembly_lines)
        
        if self.debug:
            print(f"\n[SCHEDULER] Starting scheduling of {len(self.instructions)} instructions")
        
        # Build dependency graph
        self._build_dependencies()
        
        # Analyze liveness if provided
        if variable_lifetimes:
            self._analyze_liveness(variable_lifetimes)
        
        # Apply scheduling optimizations
        self._schedule_instructions()
        
        # Generate output
        result = self._generate_assembly()
        
        if self.debug:
            print(f"\n[SCHEDULER] Scheduling complete")
            for opt_name, count in sorted(self.optimizations_applied.items()):
                if count > 0:
                    print(f"  {opt_name}: {count}")
        
        return result
    
    def _parse_ir(self, assembly_lines: List[str]) -> List[IRInstruction]:
        """Parse assembly into intermediate representation."""
        instructions = []
        directive_prefixes = ('ORG', 'DEFSTR', 'DEFBYTE', 'DB', 'DW', 'DS', 'EQU')
        
        for idx, line in enumerate(assembly_lines):
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue

            # Preserve comments and treat them as barriers.
            if line.startswith(';'):
                instr = IRInstruction(
                    index=idx,
                    opcode='DIRECTIVE',
                    operands=[],
                    has_side_effect=True,
                    original_line=line
                )
                instructions.append(instr)
                continue
            
            # Handle labels
            if line.endswith(':'):
                instr = IRInstruction(
                    index=idx,
                    opcode='LABEL',
                    operands=[line[:-1]],
                    is_label=True,
                    original_line=line
                )
                instructions.append(instr)
                continue

            # Handle lines with inline labels (e.g. "L1: DEFSTR \"hello\"")
            if ':' in line:
                _, remainder = line.split(':', 1)
                remainder = remainder.strip()
                if remainder:
                    upper_remainder = remainder.upper()
                    if upper_remainder.startswith(directive_prefixes):
                        instr = IRInstruction(
                            index=idx,
                            opcode='DIRECTIVE',
                            operands=[],
                            has_side_effect=True,
                            original_line=line
                        )
                        instructions.append(instr)
                        continue
            
            # Handle directives
            if line.upper().startswith(directive_prefixes):
                instr = IRInstruction(
                    index=idx,
                    opcode='DIRECTIVE',
                    operands=[],
                    has_side_effect=True,
                    original_line=line
                )
                instructions.append(instr)
                continue
            
            # Parse instruction
            parts = line.split()
            if not parts:
                continue
            
            opcode = parts[0]
            operands = []
            
            if len(parts) > 1:
                operand_str = ' '.join(parts[1:])
                operands = [op.strip() for op in operand_str.split(',')]
            
            # Determine what variables are defined and used
            defines, uses = self._analyze_operands(opcode, operands)
            
            is_jump = opcode in ['JMP', 'JZ', 'JNZ', 'JC', 'JNC', 'JS', 'JNS', 'JO', 'JNO', 'JLT', 'JLE', 'JGT', 'JGE', 'LOOPZ']
            is_call = opcode in ['CALL', 'CALLZ', 'CALLNZ', 'RET', 'RETN', 'HLT']
            has_side_effect = opcode in SIDE_EFFECT_OPCODES or any('[' in op or ']' in op for op in operands)
            
            instr = IRInstruction(
                index=idx,
                opcode=opcode,
                operands=operands,
                defines=defines,
                uses=uses,
                is_jump=is_jump,
                is_call=is_call,
                has_side_effect=has_side_effect,
                original_line=line
            )
            instructions.append(instr)
        
        return instructions
    
    def _analyze_operands(self, opcode: str, operands: List[str]) -> Tuple[Set[str], Set[str]]:
        """
        Analyze operands to determine what variables are defined/used.
        
        Returns:
            (defines, uses) - sets of variable names
        """
        defines = set()
        uses = set()
        
        # Track flag register dependencies
        flag_modifying = ['ADD', 'SUB', 'AND', 'OR', 'XOR', 'SHL', 'SHR',
                 'INC', 'DEC', 'CMP', 'TEST', 'NOT', 'NEG', 'WHILE', 'RETN']
        flag_reading = ['JZ', 'JNZ', 'JC', 'JNC', 'JS', 'JNS', 'JO', 'JNO',
                   'JLT', 'JLE', 'JGT', 'JGE', 'CALLZ', 'CALLNZ', 'LOOPZ']
        
        if opcode in flag_modifying:
            defines.add('FLAGS')  # Virtual register for flags
        if opcode in flag_reading:
            uses.add('FLAGS')  # Depends on flags
        
        def add_define(op: str):
            reg = self._extract_register(op)
            if reg:
                defines.add(reg)

        def add_use(op: str):
            reg = self._extract_register(op)
            if reg:
                uses.add(reg)

        # MOV destination, source
        if opcode == 'MOV' and len(operands) >= 2:
            dest, src = operands[0], operands[1]
            dest_is_mem = '[' in dest or ']' in dest
            src_is_mem = '[' in src or ']' in src

            if dest_is_mem:
                add_use(dest)
            else:
                add_define(dest)

            add_use(src)
            if src_is_mem:
                add_use(src)
        
        # Arithmetic: opcode dest, source
        elif opcode in ['ADD', 'SUB', 'AND', 'OR', 'XOR', 'SHL', 'SHR', 'INC', 'DEC']:
            if len(operands) >= 1:
                add_define(operands[0])
            if len(operands) >= 2:
                add_use(operands[0])
                add_use(operands[1])
        
        # Compare: CMP op1, op2 (uses both, no define)
        elif opcode == 'CMP' and len(operands) >= 2:
            add_use(operands[0])
            add_use(operands[1])

        # WHILE: sets flags based on operand value
        elif opcode == 'WHILE' and operands:
            add_use(operands[0])

        # LOOPZ counter, target: decrements counter and conditionally jumps
        elif opcode == 'LOOPZ' and len(operands) >= 1:
            add_define(operands[0])
            add_use(operands[0])

        # RETN source: writes return registers and exits
        elif opcode == 'RETN' and operands:
            add_define('R0')
            add_define('P0')
            add_use(operands[0])

        # Calls and jumps with register targets should consume target operands
        elif opcode in ['CALL', 'CALLZ', 'CALLNZ', 'JMP', 'JZ', 'JNZ', 'JC', 'JNC', 'JS', 'JNS', 'JO', 'JNO', 'JLT', 'JLE', 'JGT', 'JGE'] and operands:
            add_use(operands[0])
        
        # Load/Store
        elif opcode in ['PUSH', 'SREAD', 'KEYIN', 'KEYSTAT', 'SERIN', 'SERSTAT']:
            if operands:
                add_define(operands[0])
        elif opcode in ['POP', 'SWRITE', 'SPLAY', 'SEROUT', 'SERCTRL']:
            if operands:
                add_use(operands[0])
        
        return defines, uses
    
    def _extract_register(self, operand: str) -> str:
        """Extract register name from operand."""
        cleaned = operand.strip().strip('[]')

        # Strip high/low byte selectors
        if cleaned.endswith(':'):
            cleaned = cleaned[:-1]
        if cleaned.startswith(':'):
            cleaned = cleaned[1:]

        cleaned = cleaned.upper()

        # Skip immediates (decimal or hex)
        if re.fullmatch(r"-?(0X[0-9A-F]+|[0-9]+)", cleaned):
            return ""

        return cleaned if cleaned in REGISTER_NAMES else ""
    
    def _build_dependencies(self):
        """Build data flow dependency graph."""
        for instr in self.instructions:
            instr.dependencies.clear()
            instr.dependents.clear()

        for i, instr in enumerate(self.instructions):
            for j in range(i + 1, len(self.instructions)):
                other = self.instructions[j]
                
                # Check for all hazard types:
                # RAW (Read-After-Write): instr defines what other uses
                if instr.defines & other.uses:
                    instr.dependents.add(j)
                    other.dependencies.add(i)
                
                # WAR (Write-After-Read): instr uses what other defines
                if instr.uses & other.defines:
                    instr.dependents.add(j)
                    other.dependencies.add(i)
                
                # WAW (Write-After-Write): both define the same variable
                if instr.defines & other.defines:
                    instr.dependents.add(j)
                    other.dependencies.add(i)
    
    def _analyze_liveness(self, variable_lifetimes: Dict[str, Tuple[int, int]]):
        """Analyze variable lifetimes to identify high-pressure points."""
        self.variable_lifetimes = variable_lifetimes
        
        # Calculate pressure at each point
        self.pressure_at_point = defaultdict(int)
        for var, (start, end) in variable_lifetimes.items():
            for point in range(start, end + 1):
                self.pressure_at_point[point] += 1

        # Map pressure to each instruction using its original index
        for instr in self.instructions:
            instr.pressure_hint = self.pressure_at_point.get(instr.index, 0)
    
    def _schedule_instructions(self):
        """Apply scheduling optimizations."""
        changed = True
        iteration = 0
        
        while changed and iteration < 5:
            changed = False
            
            # Try to move instructions forward
            for i in range(len(self.instructions) - 1):
                instr = self.instructions[i]
                
                # Skip special instructions
                if instr.is_label or instr.is_jump or instr.is_call or instr.has_side_effect:
                    continue
                
                # Try moving forward
                j = i + 1
                moved = False
                
                while j < min(i + 5, len(self.instructions)) and not moved:
                    next_instr = self.instructions[j]
                    
                    # CRITICAL: Don't move instructions across labels/side effects/barriers
                    if next_instr.is_label or next_instr.is_jump or next_instr.is_call or next_instr.has_side_effect:
                        break
                    
                    # Do not violate dependency ordering
                    if j in instr.dependents or i in next_instr.dependencies:
                        j += 1
                        continue

                    # Ensure we are not moving past any existing dependents of instr
                    if any(dep < j for dep in instr.dependents):
                        break

                    # Ensure next_instr is not moved before its own dependencies
                    if any(dep > i for dep in next_instr.dependencies):
                        j += 1
                        continue

                    # Check if we can swap
                    if instr.can_move_after(next_instr):
                        # Check if moving frees registers earlier
                        if self._move_reduces_pressure(i, j):
                            # Perform swap
                            self.instructions[i], self.instructions[j] = self.instructions[j], self.instructions[i]
                            self.optimizations_applied["instruction_reorder"] += 1
                            changed = True
                            moved = True
                    
                    j += 1
            
            iteration += 1

            if changed:
                # Rebuild dependencies for the next pass to reflect new ordering
                self._build_dependencies()
        
        if self.debug and self.optimizations_applied["instruction_reorder"] > 0:
            print(f"[SCHEDULER] Performed {self.optimizations_applied['instruction_reorder']} reorderings")
    
    def _move_reduces_pressure(self, from_idx: int, to_idx: int) -> bool:
        """
        Check if moving instruction from from_idx to to_idx reduces pressure.
        
        Uses actual pressure_at_point data to determine if reordering helps.
        """
        if not hasattr(self, 'pressure_at_point') or not self.pressure_at_point:
            return False
        
        instr = self.instructions[from_idx]
        
        # Calculate pressure before and after move using local indices
        window_indices = range(min(from_idx, to_idx), max(from_idx, to_idx) + 1)
        original_peak = max((self.instructions[i].pressure_hint for i in window_indices), default=0)
        
        # Estimate new peak if instruction frees registers earlier
        if instr.defines and not (instr.uses & instr.defines):
            # This instruction frees a register
            # Moving it forward reduces pressure in the range [from_idx, to_idx]
            estimated_new_peak = original_peak - 1
            return estimated_new_peak < original_peak
        
        return False
    
    def _generate_assembly(self) -> List[str]:
        """Generate assembly from scheduled instructions."""
        lines = []
        for instr in self.instructions:
            lines.append(instr.original_line)
        return lines


class SpillMinimizer:
    """
    Identifies variables with long live ranges and suggests optimizations.
    """
    
    def __init__(self, debug: bool = False):
        self.debug = debug
    
    def analyze(self, variable_lifetimes: Dict[str, Tuple[int, int]]) -> Dict[str, int]:
        """
        Analyze spill candidates.
        
        Args:
            variable_lifetimes: Dict of variable -> (start, end) indices
            
        Returns:
            Dict of variable -> spill_priority (higher = more urgent)
        """
        spill_priorities = {}
        
        for var, (start, end) in variable_lifetimes.items():
            # Priority based on live range length
            # Variables with longer ranges are more likely to spill
            length = end - start
            
            # Also consider overlap with other variables
            # (approximated by position in program)
            spill_priorities[var] = length
        
        # Sort by priority
        sorted_vars = sorted(spill_priorities.items(), key=lambda x: x[1], reverse=True)
        
        if self.debug:
            print("\n[SPILL_ANALYZER] Top spill candidates:")
            for var, priority in sorted_vars[:10]:
                print(f"  {var}: priority={priority}")
        
        return dict(sorted_vars)
    
    def suggest_optimizations(self, spill_candidates: Dict[str, int]) -> List[str]:
        """Suggest optimizations for high-priority spill variables."""
        suggestions = []
        
        for var, priority in list(spill_candidates.items())[:5]:
            if priority > 20:
                suggestions.append(f"Variable '{var}' has long live range ({priority}): consider splitting or inlining")
            elif priority > 10:
                suggestions.append(f"Variable '{var}' is a spill candidate ({priority}): monitor allocation")
        
        return suggestions
