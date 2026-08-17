# Live Range Scheduler for Astrid (moved into astrid.codegen)
# Ported from top-level live_range_scheduler.py
import re
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict


REGISTER_NAMES = {
    'R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9',
    'P0', 'P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P8', 'P9', 'SP', 'FP',
    'VX', 'VY', 'VM', 'VL', 'VC', 'SA', 'SF', 'SV', 'SW', 'TT', 'TM', 'TC', 'TS', 'C0', 'C1'
}

SIDE_EFFECT_OPCODES = {
    'SREAD', 'SWRITE', 'SPLAY', 'TEXT', 'CHAR', 'SBLEND', 'SROL', 'SROT', 'SSHFT',
    'SFLIP', 'SBLIT', 'SFILL', 'SLINE', 'SRECT', 'SCIRC', 'SINV', 'VREAD', 'VWRITE',
    'VBLIT', 'SPBLIT', 'SPBLITALL', 'SEROUT', 'SERCTRL', 'SERIN', 'SERSTAT',
    'KEYIN', 'KEYSTAT', 'PUSH', 'POP', 'RND', 'RNDR'
}

FLAG_MODIFYING_OPCODES = {
    'ADD', 'SUB', 'MUL', 'DIV', 'MOD', 'ADC', 'SBC',
    'MULH', 'DIVH', 'MIN', 'MAX', 'AND', 'OR', 'XOR', 'NOT',
    'SHL', 'SHR', 'SAR', 'ROL', 'ROR', 'RCL', 'RCR', 'BSET', 'BCLR', 'BFLIP',
    'BTST', 'INC', 'DEC', 'NEG', 'ABS', 'CMP', 'TEST', 'WHILE',
    'RETN', 'MEMTEST', 'MEMCMP', 'MOVZ', 'MOVNZ', 'XCHNG',
    'SWAP', 'LEA', 'FMUL', 'FDIV', 'STRCMP', 'STRFIND',
    'STRFINDI', 'STRLEN', 'BTOI', 'ITOS', 'STOI', 'RND', 'RNDR',
    'CLZ', 'CTZ', 'POPCNT', 'SQRT', 'POWR', 'LOG', 'EXP', 'SIN',
    'COS', 'TAN', 'ATAN', 'ASIN', 'ACOS', 'DEG', 'RAD', 'FLOOR',
    'CEIL', 'ROUND', 'TRUNC', 'FRAC', 'INTGR', 'ITOF', 'FTOI',
    'CLA', 'CLD', 'SED', 'INT', 'DISATRAP', 'ENATRAP',
    'BCDA', 'BCDS', 'BCDADD', 'BCDSUB', 'BCDCMP', 'BCD2BIN',
    'BIN2BCD'
}

FLAG_READING_OPCODES = {
    'JZ', 'JNZ', 'JC', 'JNC', 'JS', 'JNS', 'JO', 'JNO',
    'JLT', 'JLE', 'JGT', 'JGE', 'CALLZ', 'CALLNZ', 'LOOPZ',
    'BRZ', 'BRNZ'
}

UNCONDITIONAL_JUMPS = {'JMP', 'RET', 'RETN', 'HLT', 'IRET', 'INT'}
CONDITIONAL_JUMPS = {
    'JZ', 'JNZ', 'JC', 'JNC', 'JS', 'JNS', 'JO', 'JNO',
    'JLT', 'JLE', 'JGT', 'JGE', 'LOOPZ', 'BR', 'BRZ', 'BRNZ'
}
CALLS = {'CALL', 'CALLZ', 'CALLNZ'}


@dataclass
class IRInstruction:
    index: int
    opcode: str
    operands: List[str]
    defines: Set[str] = field(default_factory=set)
    uses: Set[str] = field(default_factory=set)
    dependencies: Set[int] = field(default_factory=set)
    dependents: Set[int] = field(default_factory=set)
    pressure_hint: int = 0
    has_side_effect: bool = False
    is_label: bool = False
    is_jump: bool = False
    is_call: bool = False
    original_line: str = ""

    def can_move_after(self, other: 'IRInstruction') -> bool:
        if other.is_label or other.is_jump or self.is_label or self.is_jump:
            return False
        if self.is_call or other.is_call:
            return False
        if self.has_side_effect or other.has_side_effect:
            return False

        if self.uses & other.defines:
            return False
        if self.defines & other.uses:
            return False
        if self.defines & other.defines:
            return False

        return True


class LiveRangeScheduler:
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.instructions: List[IRInstruction] = []
        self.optimizations_applied = defaultdict(int)

    def schedule(self, assembly_lines: List[str],
                 variable_lifetimes: Optional[Dict[str, Tuple[int, int]]] = None) -> List[str]:
        self.instructions = self._parse_ir(assembly_lines)
        if self.debug:
            print(f"\n[SCHEDULER] Starting scheduling of {len(self.instructions)} instructions")
        self._build_dependencies()
        if variable_lifetimes:
            self._analyze_liveness(variable_lifetimes)
        self._schedule_instructions()
        result = self._generate_assembly()
        if self.debug:
            print(f"\n[SCHEDULER] Scheduling complete")
            for opt_name, count in sorted(self.optimizations_applied.items()):
                if count > 0:
                    print(f"  {opt_name}: {count}")
        return result

    def _parse_ir(self, assembly_lines: List[str]) -> List[IRInstruction]:
        instructions = []
        directive_prefixes = ('ORG', 'DEFSTR', 'DEFBYTE', 'DB', 'DW', 'DS', 'EQU')

        for idx, line in enumerate(assembly_lines):
            line = line.strip()
            if not line:
                continue
            if line.startswith(';'):
                instructions.append(IRInstruction(
                    index=idx, opcode='DIRECTIVE', operands=[],
                    has_side_effect=True, original_line=line))
                continue
            if line.endswith(':'):
                instructions.append(IRInstruction(
                    index=idx, opcode='LABEL', operands=[line[:-1]],
                    is_label=True, original_line=line))
                continue

            if ':' in line:
                _, remainder = line.split(':', 1)
                remainder = remainder.strip()
                if remainder and remainder.upper().startswith(directive_prefixes):
                    instructions.append(IRInstruction(
                        index=idx, opcode='DIRECTIVE', operands=[],
                        has_side_effect=True, original_line=line))
                    continue

            if line.upper().startswith(directive_prefixes):
                instructions.append(IRInstruction(
                    index=idx, opcode='DIRECTIVE', operands=[],
                    has_side_effect=True, original_line=line))
                continue

            parts = line.split()
            if not parts:
                continue

            opcode = parts[0]
            operands = []
            if len(parts) > 1:
                operand_str = ' '.join(parts[1:])
                operands = [op.strip() for op in operand_str.split(',')]

            defines, uses = self._analyze_operands(opcode, operands)
            is_jump = opcode in CONDITIONAL_JUMPS or opcode in UNCONDITIONAL_JUMPS
            is_call = opcode in CALLS or opcode in ('RET', 'RETN', 'HLT', 'INT', 'IRET')
            has_side_effect = (
                opcode in SIDE_EFFECT_OPCODES
                or any('[' in op or ']' in op for op in operands)
            )

            instructions.append(IRInstruction(
                index=idx, opcode=opcode, operands=operands,
                defines=defines, uses=uses,
                is_jump=is_jump, is_call=is_call,
                has_side_effect=has_side_effect, original_line=line))

        return instructions

    def _analyze_operands(self, opcode: str, operands: List[str]):
        defines = set()
        uses = set()
        for op in operands:
            if op.endswith(':'):
                op = op[:-1]
            # simple heuristics: registers and memory operands
            if op in REGISTER_NAMES:
                uses.add(op)
            if op.startswith('[') and op.endswith(']'):
                uses.add(op)
        return defines, uses

    def _build_dependencies(self):
        # simple placeholder for building dependency graph between instructions
        for i, inst in enumerate(self.instructions):
            inst.dependencies = set()
            inst.dependents = set()

    def _analyze_liveness(self, variable_lifetimes: Dict[str, Tuple[int, int]]):
        pass

    def _schedule_instructions(self):
        # naive scheduling placeholder: do nothing
        return

    def _generate_assembly(self) -> List[str]:
        return [inst.original_line for inst in self.instructions]
