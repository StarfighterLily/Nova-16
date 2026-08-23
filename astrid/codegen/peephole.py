# Astrid Language Peephole Optimizer
# File: astrid/codegen/peephole.py
# Post-generation assembly optimizer ported from NoBASIC's peephole optimizer.
#
# Optimizations:
# 1. Self-Move Elimination - Remove MOV A, A
# 2. Redundant Move Elimination - Remove consecutive MOV with same dest
# 3. Consecutive Loads - Remove unused loads when dest is re-loaded
# 4. Dead Code Before Jump - Remove instructions after unconditional jumps
# 5. Load-Store Copy Propagation - MOV A, X; MOV Y, A -> MOV Y, X
# 6. Constant Folding - MOV A, 5; ADD A, 3 -> MOV A, 8
# 7. Register Chain Elimination - MOV A, B; MOV C, A -> MOV C, B

import re
from typing import List, Dict, Tuple, Optional
from collections import defaultdict


class Instruction:
    """Represents a single Nova-16 assembly instruction."""
    def __init__(self, opcode, operands, original_line="", is_label=False, is_directive=False):
        self.opcode = opcode
        self.operands = operands
        self.original_line = original_line
        self.is_label = is_label
        self.is_directive = is_directive

    def __str__(self):
        if self.is_label or self.is_directive:
            return self.original_line
        if not self.operands:
            return self.opcode
        return f"{self.opcode} {', '.join(self.operands)}"

    def matches(self, opcode, arg_count=None):
        if self.opcode != opcode:
            return False
        if arg_count is not None and len(self.operands) != arg_count:
            return False
        return True


class PeepholeOptimizer:
    """Post-generation optimizer for Nova-16 assembly instruction sequences."""

    def __init__(self, debug=False):
        self.debug = debug
        self.optimizations_applied = defaultdict(int)
        self.instructions = []

    def optimize(self, assembly_code):
        """Optimize assembly code using peephole patterns."""
        self.instructions = self._parse_assembly(assembly_code)

        if self.debug:
            print(f"\n[PEEPHOLE] Starting optimization of {len(self.instructions)} instructions")

        changed = True
        iteration = 0
        while changed and iteration < 10:
            changed = False
            new_instructions = []
            i = 0

            while i < len(self.instructions):
                optimized, skip = self._try_optimizations(i)

                if optimized is not None:
                    new_instructions.extend(optimized)
                    changed = True
                    i += skip
                else:
                    new_instructions.append(self.instructions[i])
                    i += 1

            self.instructions = new_instructions
            iteration += 1

            if self.debug and changed:
                print(f"[PEEPHOLE] Iteration {iteration}: {len(self.instructions)} instructions")

        result = self._generate_assembly()

        if self.debug:
            print(f"\n[PEEPHOLE] Optimization complete")
            for opt_name, count in sorted(self.optimizations_applied.items()):
                if count > 0:
                    print(f"  {opt_name}: {count}")

        return result

    def _try_optimizations(self, index):
        result = self._pattern_self_mov(index)
        if result:
            return result

        result = self._pattern_redundant_mov(index)
        if result:
            return result

        result = self._pattern_consecutive_loads(index)
        if result:
            return result

        result = self._pattern_dead_before_jump(index)
        if result:
            return result

        result = self._pattern_load_store_same(index)
        if result:
            return result

        result = self._pattern_constant_folding(index)
        if result:
            return result

        result = self._pattern_register_chain(index)
        if result:
            return result

        return None, 0

    def _pattern_self_mov(self, index):
        instr = self.instructions[index]
        if not instr.matches('MOV', 2):
            return None
        if instr.operands[0] == instr.operands[1]:
            self.optimizations_applied["self_mov"] += 1
            return [], 1
        return None

    def _pattern_redundant_mov(self, index):
        if not (index + 1 < len(self.instructions)):
            return None

        curr = self.instructions[index]
        next_instr = self.instructions[index + 1]

        if not (curr.matches('MOV', 2) and next_instr.matches('MOV', 2)):
            return None
        if curr.operands[0] != next_instr.operands[0]:
            return None

        dest = curr.operands[0]

        if curr.operands == next_instr.operands:
            self.optimizations_applied["redundant_mov"] += 1
            return [next_instr], 2

        if not self._is_register_used(dest, index + 1, index + 2):
            self.optimizations_applied["redundant_mov"] += 1
            return [next_instr], 2

        return None

    def _pattern_consecutive_loads(self, index):
        if not (index + 1 < len(self.instructions)):
            return None

        curr = self.instructions[index]
        next_instr = self.instructions[index + 1]

        if not (curr.matches('MOV', 2) and next_instr.matches('MOV', 2)):
            return None
        if curr.operands[0] != next_instr.operands[0]:
            return None
        if self._is_register_used(curr.operands[0], index + 1, index + 2):
            return None

        self.optimizations_applied["consecutive_loads"] += 1
        return [next_instr], 2

    def _pattern_dead_before_jump(self, index):
        if index + 2 >= len(self.instructions):
            return None

        curr = self.instructions[index]
        next_instr = self.instructions[index + 1]

        if not self._is_unconditional_jump(curr.opcode):
            return None
        if next_instr.is_label or next_instr.is_directive:
            return None

        self.optimizations_applied["dead_before_jump"] += 1
        return [curr], 2

    def _pattern_load_store_same(self, index):
        if not (index + 1 < len(self.instructions)):
            return None

        load = self.instructions[index]
        store = self.instructions[index + 1]

        if not (load.matches('MOV', 2) and store.matches('MOV', 2)):
            return None
        if load.operands[0] != store.operands[1]:
            return None
        if '[' in store.operands[0] or ']' in store.operands[0]:
            return None

        temp_reg = load.operands[0]
        if not self._is_copy_propagation_safe_register(temp_reg):
            return None

        source = load.operands[1]
        dest = store.operands[0]
        if '[' in source or ']' in source:
            return None
        if not self._is_register_operand(temp_reg) or not self._is_register_operand(dest):
            return None

        source_reg = self._normalize_register_name(source)
        dest_reg = self._normalize_register_name(dest)
        if source_reg and dest_reg and not self._same_register_family(source_reg, dest_reg):
            return None
        if source_reg and temp_reg and not self._same_register_family(source_reg, self._normalize_register_name(temp_reg)):
            return None

        if self._is_register_used(temp_reg, index + 2, min(index + 5, len(self.instructions))):
            return None

        optimized = Instruction('MOV', [store.operands[0], load.operands[1]])
        self.optimizations_applied["load_store_opt"] += 1
        return [optimized], 2

    def _pattern_constant_folding(self, index):
        if not (index + 1 < len(self.instructions)):
            return None

        load = self.instructions[index]
        oper = self.instructions[index + 1]

        if not load.matches('MOV', 2):
            return None
        if not oper.matches('ADD', 2) and not oper.matches('SUB', 2) and not oper.matches('AND', 2):
            return None
        if load.operands[0] != oper.operands[0]:
            return None

        try:
            const1 = self._parse_constant(load.operands[1])
            const2 = self._parse_constant(oper.operands[1])

            if const1 is None or const2 is None:
                return None

            if oper.opcode == 'ADD':
                result = const1 + const2
            elif oper.opcode == 'SUB':
                result = const1 - const2
            elif oper.opcode == 'AND':
                result = const1 & const2
            else:
                return None

            result = result & 0xFFFF

            optimized = Instruction('MOV', [load.operands[0], f'0x{result:04X}'])
            self.optimizations_applied["constant_folding"] += 1
            return [optimized], 2

        except (ValueError, AttributeError):
            return None

    def _pattern_register_chain(self, index):
        if not (index + 1 < len(self.instructions)):
            return None

        move1 = self.instructions[index]
        move2 = self.instructions[index + 1]

        if not (move1.matches('MOV', 2) and move2.matches('MOV', 2)):
            return None
        if move1.operands[0] != move2.operands[1]:
            return None
        if '[' in move2.operands[0] or ']' in move2.operands[0]:
            return None

        temp_reg = move1.operands[0]
        source = move1.operands[1]
        dest = move2.operands[0]

        if not self._is_copy_propagation_safe_register(temp_reg):
            return None
        if '[' in source or ']' in source:
            return None
        if not self._is_register_operand(temp_reg) or not self._is_register_operand(dest) or not self._is_register_operand(source):
            return None

        source_reg = self._normalize_register_name(source)
        dest_reg = self._normalize_register_name(dest)
        temp_family = self._normalize_register_name(temp_reg)
        if source_reg and dest_reg and not self._same_register_family(source_reg, dest_reg):
            return None
        if temp_family and dest_reg and not self._same_register_family(temp_family, dest_reg):
            return None
        if source_reg and temp_family and not self._same_register_family(source_reg, temp_family):
            return None

        if self._is_register_used(temp_reg, index + 2, min(index + 5, len(self.instructions))):
            return None

        optimized = Instruction('MOV', [dest, source])
        self.optimizations_applied["register_chain"] += 1
        return [optimized], 2

    # ===== Helper Methods =====

    def _is_register_operand(self, operand):
        cleaned = operand.strip().upper()
        if not cleaned:
            return False
        if cleaned.startswith('[') or cleaned.endswith(']'):
            return False
        return bool(re.fullmatch(r'(?:R[0-9]|P[0-9]|SP|FP|VX|VY|VM|VL|VC|SA|SF|SV|SW|TT|TM|TC|TS|C[01])', cleaned))

    def _normalize_register_name(self, operand):
        cleaned = operand.strip().strip('[]')
        if cleaned.endswith(':'):
            cleaned = cleaned[:-1]
        if cleaned.startswith(':'):
            cleaned = cleaned[1:]
        cleaned = cleaned.upper()
        return cleaned if re.fullmatch(r'R[0-9]|P[0-7]|SP|FP|VX|VY|VM|VL|VC|SA|SF|SV|SW|TT|TM|TC|TS|C0|C1', cleaned) else ''

    def _same_register_family(self, left, right):
        if not left or not right:
            return False
        if left.startswith('R') and right.startswith('R'):
            return True
        if left.startswith('P') and right.startswith('P'):
            return True
        special = {'SP', 'FP', 'VX', 'VY', 'VM', 'VL', 'VC', 'SA', 'SF', 'SV', 'SW', 'TT', 'TM', 'TC', 'TS', 'C0', 'C1'}
        return left in special and right in special and left == right

    def _is_copy_propagation_safe_register(self, reg):
        reg = reg.strip().upper()
        # P0 and R0 are the function return-value registers (ABI): callers
        # read them after RET, which is invisible to the local use-scan, so
        # moves that DEFINE P0/R0 must never be eliminated or propagated
        # away. P7/P8/P9-class and special registers are likewise reserved.
        if reg in {'SP', 'FP', 'P0', 'R0', 'P7', 'VX', 'VY', 'VM', 'VL', 'VC',
                   'SA', 'SF', 'SV', 'SW', 'TT', 'TM', 'TC', 'TS', 'C0', 'C1'}:
            return False
        return bool(re.fullmatch(r'R[0-9]|P[0-6]', reg))

    def _is_register_used(self, reg, start, end):
        reg = reg.strip().upper()

        for i in range(start, end):
            if i >= len(self.instructions):
                break
            instr = self.instructions[i]

            for operand in instr.operands:
                operand_clean = operand.strip().upper()

                if operand_clean == reg:
                    return True
                if f'[{reg}]' in operand_clean:
                    return True
                if reg.startswith('P') and (f'{reg}:' in operand_clean or f':{reg}' in operand_clean):
                    return True
                if f'[{reg}+' in operand_clean or f'[{reg}-' in operand_clean:
                    return True

        return False

    def _is_unconditional_jump(self, opcode):
        return opcode in ['JMP', 'RET', 'RETN', 'HLT']

    def _is_conditional_jump(self, opcode):
        return opcode in ['JZ', 'JNZ', 'JC', 'JNC', 'JS', 'JNS', 'JO', 'JNO', 'JLT', 'JLE', 'JGT', 'JGE', 'CALLZ', 'CALLNZ', 'LOOPZ']

    def _modifies_flags(self, opcode):
        return opcode in ['ADD', 'SUB', 'AND', 'OR', 'XOR', 'SHL', 'SHR',
                         'INC', 'DEC', 'CMP', 'TEST', 'NOT', 'NEG', 'WHILE', 'RETN']

    def _reads_flags(self, opcode):
        return self._is_conditional_jump(opcode) or opcode in ['CMOV', 'SETcc']

    def _parse_constant(self, operand):
        try:
            if operand.startswith('0x') or operand.startswith('0X'):
                return int(operand, 16)
            else:
                return int(operand)
        except ValueError:
            return None

    def _has_flag_dependency_between(self, start, end):
        flag_modified = False
        for i in range(start, end):
            if i >= len(self.instructions):
                break
            instr = self.instructions[i]

            if flag_modified and self._reads_flags(instr.opcode):
                return True
            if self._modifies_flags(instr.opcode):
                flag_modified = True

        return False

    def _parse_assembly(self, code):
        instructions = []
        directive_prefixes = ('ORG', 'DEFSTR', 'DEFBYTE', 'DB', 'DW', 'DS', 'EQU')

        for line in code.split('\n'):
            line = line.strip()

            if not line:
                continue

            if line.startswith(';'):
                instructions.append(Instruction('', [], line, is_directive=True))
                continue

            if line.endswith(':'):
                instructions.append(Instruction('', [], line, is_label=True))
                continue

            if ':' in line:
                _, remainder = line.split(':', 1)
                remainder = remainder.strip()
                if remainder:
                    upper_remainder = remainder.upper()
                    if upper_remainder.startswith(directive_prefixes):
                        instructions.append(Instruction('', [], line, is_directive=True))
                        continue

            if line.upper().startswith(directive_prefixes):
                instructions.append(Instruction('', [], line, is_directive=True))
                continue

            parts = line.split()
            if not parts:
                continue

            opcode = parts[0]
            operands = []

            if len(parts) > 1:
                operand_str = ' '.join(parts[1:])
                operands = [op.strip() for op in operand_str.split(',')]

            instructions.append(Instruction(opcode, operands, line))

        return instructions

    def _generate_assembly(self):
        return '\n'.join(str(instr) for instr in self.instructions)