#!/usr/bin/env python3
"""
NoBASIC LLVM IR Generator
Converts the NoBASIC AST to standard LLVM IR (.ll format).

This enables NoBASIC programs to target any platform supported by LLVM,
as an alternative to the native Nova-16 assembly backend.

Usage:
    python nobasic_compiler.py program.nobasic --target llvm

Hardware-specific operations (graphics, sound, keyboard) are emitted as
'externally declared' functions that must be implemented per platform.
"""

from typing import List, Dict, Tuple, Optional, Set, Any
from dataclasses import dataclass, field
from enum import Enum, auto

from ..parser.ast import (
    Program, Statement, Expression, ClrDrawStmt, PxlOnStmt, PxlOffStmt,
    LineStmt, CircleStmt, TextStmt, SetLayerStmt, SRolStmt, SRotStmt, SShftStmt, SFlipStmt,
    SpriteOnStmt, SpriteOffStmt,
    PlayToneStmt, PlayWaveStmt, StopSoundStmt, SetChannelStmt, GetKeyStmt,
    SerOutStmt, SerInStmt, SerStatStmt, SerCtrlStmt,
    InputStmt, DispStmt, PauseStmt, FunctionCallStmt, ExpressionStmt, AssignmentStmt,
    IfStmt, ForStmt, WhileStmt, RepeatStmt, GotoStmt, LabelStmt, StructDeclarationStmt,
    VarDeclarationStmt, AsmBlockStmt, FunctionDefStmt, ReturnStmt,
    LiteralExpr, VariableExpr, ListAccessExpr, MatrixAccessExpr, MemberAccessExpr,
    BinaryExpr, UnaryExpr, FunctionCallExpr, GroupingExpr,
    StructType, VarScope, DataType
)
from ..utils.error import CodeGenError


class LLVMType(Enum):
    """LLVM IR primitive types used for NoBASIC values."""
    I16 = "i16"
    I8 = "i8"
    I1 = "i1"
    VOID = "void"
    I8_PTR = "i8*"


@dataclass
class BBInfo:
    """Bookkeeping for a single LLVM basic block."""
    name: str
    label: str  # e.g. "entry", "if.then.0", "for.body.3"


class LLVMIRGenerator:
    """
    Generates LLVM IR text from a NoBASIC AST.

    Strategy:
    - Each NoBASIC variable becomes an LLVM alloca (local) or global.
    - Nova-16 hardware calls become extern function declarations.
    - Control flow uses LLVM basic blocks and branch instructions.
    - All numeric values are i16 (16-bit signed).
    """

    # Reserved for internal temporaries
    _temp_counter = 0
    _label_counter = 0

    def __init__(self, debug: bool = False):
        self.output_lines: List[str] = []
        self.indent_level = 0

        # Global tracking
        self.global_vars: Dict[str, str] = {}   # name -> llvm_id (e.g. "@g_x")
        self.local_vars: Dict[str, str] = {}     # name -> llvm_id in current function
        self.string_constants: List[Tuple[str, str, str]] = []  # (llvm_id, label_hint, value)
        self.struct_types: Dict[str, StructType] = {}
        self.struct_instances: Dict[str, str] = {}  # var_name -> struct_name
        self.struct_bases: Dict[str, str] = {}       # var_name -> llvm alloca id

        # Function tracking
        self.functions: Dict[str, Tuple[str, List[str], FunctionDefStmt]] = {}
        self.function_labels: Dict[str, str] = {}
        self.current_function: Optional[str] = None
        self.function_output: List[str] = []
        self.function_has_return: Set[str] = set()

        # LLVM temporary SSA names (per function)
        self.temp_ssa_counter = 0
        self.bb_counter = 0
        self.current_bb_label: Optional[str] = None

        # Track which externs have been declared
        self.emitted_externs: Set[str] = set()

        # Debug
        self.debug = debug

    # ============== LLVM Text Helpers ==============

    def _llvm_id(self, name: str) -> str:
        """Convert a NoBASIC identifier to a safe LLVM identifier."""
        safe = name.replace('.', '_').replace('-', '_').replace(' ', '_')
        if safe and safe[0].isdigit():
            safe = '_' + safe
        return safe

    def _global_ref(self, name: str) -> str:
        """Return the LLVM global reference for a global variable."""
        return f"@{self._llvm_id('g_' + name)}"

    def _local_ref(self, name: str) -> str:
        """Return the LLVM local reference for a local variable (alloca pointer)."""
        return f"%{self._llvm_id('l_' + name)}"

    def _temp(self) -> str:
        """Generate a fresh SSA temporary name."""
        name = f"%t_{self.temp_ssa_counter}"
        self.temp_ssa_counter += 1
        return name

    def _new_bb_label(self, prefix: str = "bb") -> str:
        """Generate a fresh basic block label."""
        name = f"{prefix}.{self.bb_counter}"
        self.bb_counter += 1
        return name

    def _indent(self) -> str:
        return "  " * self.indent_level

    def _emit(self, line: str = ""):
        if line:
            self.output_lines.append(self._indent() + line)
        else:
            self.output_lines.append("")

    def _emit_func(self, line: str = ""):
        """Emit to function output (used while generating a function body)."""
        if line:
            self.function_output.append("  " + line)
        else:
            self.function_output.append("")

    def _reset(self):
        """Reset all per-compilation state."""
        self.output_lines = []
        self.indent_level = 0
        self.global_vars = {}
        self.local_vars = {}
        self.string_constants = []
        self.struct_types = {}
        self.struct_instances = {}
        self.struct_bases = {}
        self.functions = {}
        self.function_labels = {}
        self.current_function = None
        self.function_output = []
        self.function_has_return = set()
        self.temp_ssa_counter = 0
        self.bb_counter = 0
        self.current_bb_label = None
        self.emitted_externs = set()

    # ============== Nova-16 Hardware Extern Declarations ==============

    HARDWARE_EXTERNS = {
        # Graphics
        "clrdraw":        ("void", []),
        "pxlon":          ("void", ["i16", "i16", "i16"]),
        "pxloff":         ("void", ["i16", "i16"]),
        "line":           ("void", ["i16", "i16", "i16", "i16", "i16"]),
        "circle":         ("void", ["i16", "i16", "i16", "i16"]),
        "text":           ("void", ["i16", "i16", "i8*", "i16"]),
        "setlayer":       ("void", ["i16"]),
        "scrroll":        ("void", ["i16", "i16"]),
        "scrrotate":      ("void", ["i16", "i16"]),
        "scrshift":       ("void", ["i16", "i16"]),
        "scrflip":        ("void", ["i16"]),
        "spriteon":       ("void", ["i16", "i16", "i16"]),
        "spriteoff":      ("void", ["i16"]),
        # Sound
        "playtone":       ("void", ["i16", "i16", "i16"]),
        "playwave":       ("void", ["i16", "i16", "i16"]),
        "stopsound":      ("void", []),
        "setchannel":     ("void", ["i16"]),
        # Input
        "getkey":         ("i16", []),
        # Serial
        "serout":         ("void", ["i16"]),
        "serin":          ("i16", []),
        "serstat":        ("i16", []),
        "serctrl":        ("void", ["i16"]),
        # System
        "input":          ("void", ["i8*", "i16*"]),
        "disp":           ("void", ["i8*"]),
        "pause":          ("void", []),
        # Math functions
        "sin":            ("i16", ["i16"]),
        "cos":            ("i16", ["i16"]),
        "tan":            ("i16", ["i16"]),
        "sqrt":           ("i16", ["i16"]),
        "abs":            ("i16", ["i16"]),
        "intgr":          ("i16", ["i16"]),
        "round":          ("i16", ["i16"]),
        "powr":           ("i16", ["i16", "i16"]),
        "log":            ("i16", ["i16"]),
        "min":            ("i16", ["i16", "i16"]),
        "max":            ("i16", ["i16", "i16"]),
        "itoa":           ("void", ["i16", "i8*"]),
        # String functions
        "strlen":         ("i16", ["i8*"]),
        "strcpy":         ("void", ["i8*", "i8*"]),
        "strcat":         ("void", ["i8*", "i8*"]),
        "strcmp":         ("i16", ["i8*", "i8*", "i16"]),
        "strupr":         ("i16", ["i8*"]),
        "strlwr":         ("i16", ["i8*"]),
        "strrev":         ("i16", ["i8*"]),
        "strfind":        ("i16", ["i8*", "i8*"]),
        "strfindi":       ("i16", ["i8*", "i8*"]),
        "strext":         ("void", ["i8*", "i16", "i16", "i8*"]),
        # Random functions
        "rand":           ("i16", []),
        "rndr":           ("i16", ["i16", "i16"]),
        "randomize":      ("void", ["i16"]),
        # Memory access
        "memread":        ("i16", ["i16"]),
        "memwrite":       ("void", ["i16", "i16"]),
    }

    def _emit_extern_if_needed(self, name: str):
        """Emit a declare for a Nova-16 hardware function if not already emitted."""
        lowered = name.lower()
        if lowered in self.emitted_externs:
            return
        self.emitted_externs.add(lowered)

        signature = self.HARDWARE_EXTERNS.get(lowered)
        if signature is None:
            # It might be a user function, skip
            return

        ret_type, param_types = signature
        params = ", ".join(param_types)
        self.output_lines.append(
            f"declare {ret_type} @{lowered}({params})"
        )

    # ============== Main Generate Entry Point ==============

    def _is_nova_hardware_call(self, name: str) -> bool:
        """Check if a function name matches a built-in Nova-16 hardware operation."""
        lowered = name.lower()
        # All HARDWARE_EXTERNS are valid hardware calls
        return lowered in self.HARDWARE_EXTERNS

    def generate(self, program: Program) -> str:
        """
        Generate LLVM IR from a NoBASIC AST.

        Args:
            program: The parsed and semantically analyzed AST

        Returns:
            LLVM IR source as a string
        """
        self._reset()

        # Pre-pass: collect struct declarations
        for stmt in program.statements:
            if isinstance(stmt, StructDeclarationStmt):
                self.struct_types[stmt.name.lower()] = StructType(
                    stmt.name,
                    [field.lower() for field in stmt.fields],
                )

        # Pre-pass: collect function definitions and compute globals/locals
        for stmt in program.statements:
            if isinstance(stmt, FunctionDefStmt):
                func_key = stmt.name.lower()
                label = f"_func_{self._llvm_id(stmt.name)}"
                self.function_labels[func_key] = label
                param_names = [pn for pn, _ in stmt.params]
                self.functions[func_key] = (label, param_names, stmt)

        # First pass: determine which variables are global vs local
        # In NoBASIC, variables at top level are global; inside functions they're local
        self._classify_variables(program)

        # Pre-pass: collect all string literals for module-level declaration
        self._collect_strings_pre_pass(program)

        # Emit module header
        self._emit("; NoBASIC to LLVM IR")
        self._emit(f"; Source: {getattr(program, 'source_file', '<unknown>')}")
        self._emit(f"target triple = \"x86_64-pc-windows-msvc\"")
        self._emit("")

        # Emit global variable declarations
        for var_name in sorted(self.global_vars.keys()):
            gid = self._global_ref(var_name)
            self._emit(f"{gid} = global i16 0")

        # Emit string constants
        for str_id, label_hint, value in self.string_constants:
            escaped = self._escape_llvm_string(value)
            self._emit(f"{str_id} = private unnamed_addr constant [{len(value) + 1} x i8] c\"{escaped}\\00\"")

        if self.global_vars or self.string_constants:
            self._emit("")

        # Emit Nova-16 hardware extern declarations for functions used
        self._collect_hardware_externs(program)

        if self.emitted_externs:
            self._emit("")

        # Emit user function definitions
        for stmt in program.statements:
            if isinstance(stmt, FunctionDefStmt):
                self._generate_function(stmt)

        # Emit main entry function (top-level statements) - renamed to nobasic_main for SDL runtime linking
        self._emit("define i32 @nobasic_main() {")
        self.indent_level = 1
        self.current_function = "__main__"
        self.local_vars = {}
        self.temp_ssa_counter = 0
        self.bb_counter = 0

        self._emit("entry:")
        self.current_bb_label = "entry"

        # Note: global variable allocas and initialization are done lazily
        # by _get_or_create_var_ref on first use, so we don't pre-allocate here.

        # Generate all non-function statements
        for stmt in program.statements:
            if not isinstance(stmt, (FunctionDefStmt, StructDeclarationStmt)):
                self._generate_statement(stmt)

        # Terminate main with ret 0
        self._emit("ret i32 0")
        self.indent_level = 0
        self._emit("}")

        # Flush function output
        if self.function_output:
            self._emit("")
            self._emit("; --- Function definitions above already emitted ---")

        result = "\n".join(self.output_lines)
        return result

    # ============== Variable Classification ==============

    def _classify_variables(self, program: Program):
        """Determine which top-level variables are globals vs locals."""
        # Recursively scan all statements to find variable assignments
        def scan_stmts(stmts):
            for stmt in stmts:
                if isinstance(stmt, VarDeclarationStmt):
                    for v in stmt.variables:
                        self.global_vars[v.lower()] = "global"
                elif isinstance(stmt, AssignmentStmt):
                    if isinstance(stmt.variable, VariableExpr):
                        name = stmt.variable.name.lower()
                        if name not in self.global_vars:
                            self.global_vars[name] = "global"
                elif isinstance(stmt, ForStmt):
                    name = stmt.variable.lower()
                    if name not in self.global_vars:
                        self.global_vars[name] = "global"
                    # Recurse into for body and expressions
                    if stmt.start:
                        scan_expr(stmt.start)
                    if stmt.end:
                        scan_expr(stmt.end)
                    if stmt.step:
                        scan_expr(stmt.step)
                    scan_stmts(stmt.body)
                elif isinstance(stmt, IfStmt):
                    scan_stmts(stmt.then_branch)
                    if stmt.else_branch:
                        scan_stmts(stmt.else_branch)
                elif isinstance(stmt, (WhileStmt, RepeatStmt)):
                    scan_stmts(stmt.body)
                elif isinstance(stmt, FunctionDefStmt):
                    scan_stmts(stmt.body)

        def scan_expr(expr):
            if isinstance(expr, VariableExpr):
                name = expr.name.lower()
                if name not in self.global_vars:
                    self.global_vars[name] = "global"
            elif isinstance(expr, BinaryExpr):
                scan_expr(expr.left)
                scan_expr(expr.right)
            elif isinstance(expr, UnaryExpr):
                scan_expr(expr.expression)
            elif isinstance(expr, GroupingExpr):
                scan_expr(expr.expression)
            elif isinstance(expr, FunctionCallExpr):
                for arg in expr.arguments:
                    scan_expr(arg)

        # Everything at top-level scope is global in NoBASIC (by default)
        scan_stmts(program.statements)

    # ============== String Collection (Pre-pass) ==============

    def _collect_strings_pre_pass(self, program: Program) -> None:
        """Pre-pass: collect all string literals for module-level declaration."""
        def scan_stmt(stmt):
            if isinstance(stmt, DispStmt):
                scan_expr(stmt.text)
            elif isinstance(stmt, TextStmt):
                scan_expr(stmt.text)
            elif isinstance(stmt, InputStmt):
                if stmt.prompt is not None:
                    scan_expr(stmt.prompt)
            elif isinstance(stmt, IfStmt):
                for s in stmt.then_branch:
                    scan_stmt(s)
                if stmt.else_branch:
                    for s in stmt.else_branch:
                        scan_stmt(s)
            elif isinstance(stmt, ForStmt):
                for s in stmt.body:
                    scan_stmt(s)
            elif isinstance(stmt, WhileStmt):
                for s in stmt.body:
                    scan_stmt(s)
            elif isinstance(stmt, RepeatStmt):
                for s in stmt.body:
                    scan_stmt(s)
            elif isinstance(stmt, FunctionDefStmt):
                for s in stmt.body:
                    scan_stmt(s)
            elif isinstance(stmt, AssignmentStmt):
                scan_expr(stmt.expression)

        def scan_expr(expr):
            if isinstance(expr, LiteralExpr) and expr.data_type == DataType.STRING:
                str_id = f"@.str.{len(self.string_constants)}"
                self.string_constants.append((str_id, None, expr.value))
            elif isinstance(expr, BinaryExpr):
                scan_expr(expr.left)
                scan_expr(expr.right)
            elif isinstance(expr, UnaryExpr):
                scan_expr(expr.expression)
            elif isinstance(expr, GroupingExpr):
                scan_expr(expr.expression)
            elif isinstance(expr, FunctionCallExpr):
                for arg in expr.arguments:
                    scan_expr(arg)

        for stmt in program.statements:
            if not isinstance(stmt, StructDeclarationStmt):
                scan_stmt(stmt)

    # ============== Hardware Extern Collection ==============

    def _collect_hardware_externs(self, program: Program):
        """Walk AST to find all Nova-16 hardware calls and emit externs."""
        for stmt in program.statements:
            self._collect_externs_from_stmt(stmt)

    def _collect_externs_from_stmt(self, stmt: Statement):
        """Recursively find hardware call names in a statement."""
        if isinstance(stmt, (ClrDrawStmt,)):
            self._emit_extern_if_needed("clrdraw")
        elif isinstance(stmt, PxlOnStmt):
            self._emit_extern_if_needed("pxlon")
        elif isinstance(stmt, PxlOffStmt):
            self._emit_extern_if_needed("pxloff")
        elif isinstance(stmt, LineStmt):
            self._emit_extern_if_needed("line")
        elif isinstance(stmt, CircleStmt):
            self._emit_extern_if_needed("circle")
        elif isinstance(stmt, TextStmt):
            self._emit_extern_if_needed("text")
        elif isinstance(stmt, SetLayerStmt):
            self._emit_extern_if_needed("setlayer")
        elif isinstance(stmt, SRolStmt):
            self._emit_extern_if_needed("scrroll")
        elif isinstance(stmt, SRotStmt):
            self._emit_extern_if_needed("scrrotate")
        elif isinstance(stmt, SShftStmt):
            self._emit_extern_if_needed("scrshift")
        elif isinstance(stmt, SFlipStmt):
            self._emit_extern_if_needed("scrflip")
        elif isinstance(stmt, SpriteOnStmt):
            self._emit_extern_if_needed("spriteon")
        elif isinstance(stmt, SpriteOffStmt):
            self._emit_extern_if_needed("spriteoff")
        elif isinstance(stmt, PlayToneStmt):
            self._emit_extern_if_needed("playtone")
        elif isinstance(stmt, PlayWaveStmt):
            self._emit_extern_if_needed("playwave")
        elif isinstance(stmt, StopSoundStmt):
            self._emit_extern_if_needed("stopsound")
        elif isinstance(stmt, SetChannelStmt):
            self._emit_extern_if_needed("setchannel")
        elif isinstance(stmt, GetKeyStmt):
            self._emit_extern_if_needed("getkey")
        elif isinstance(stmt, SerOutStmt):
            self._emit_extern_if_needed("serout")
        elif isinstance(stmt, SerInStmt):
            self._emit_extern_if_needed("serin")
        elif isinstance(stmt, SerStatStmt):
            self._emit_extern_if_needed("serstat")
        elif isinstance(stmt, SerCtrlStmt):
            self._emit_extern_if_needed("serctrl")
        elif isinstance(stmt, InputStmt):
            self._emit_extern_if_needed("input")
        elif isinstance(stmt, DispStmt):
            self._emit_extern_if_needed("disp")
        elif isinstance(stmt, PauseStmt):
            self._emit_extern_if_needed("pause")
        elif isinstance(stmt, FunctionCallStmt):
            self._collect_externs_from_expr(stmt.function_call)
        elif isinstance(stmt, FunctionDefStmt):
            for s in stmt.body:
                self._collect_externs_from_stmt(s)
        elif isinstance(stmt, IfStmt):
            for s in stmt.then_branch:
                self._collect_externs_from_stmt(s)
            if stmt.else_branch:
                for s in stmt.else_branch:
                    self._collect_externs_from_stmt(s)
        elif isinstance(stmt, ForStmt):
            for s in stmt.body:
                self._collect_externs_from_stmt(s)
        elif isinstance(stmt, WhileStmt):
            for s in stmt.body:
                self._collect_externs_from_stmt(s)
        elif isinstance(stmt, RepeatStmt):
            for s in stmt.body:
                self._collect_externs_from_stmt(s)
        elif isinstance(stmt, AssignmentStmt):
            self._collect_externs_from_expr(stmt.expression)
        elif isinstance(stmt, ExpressionStmt):
            self._collect_externs_from_expr(stmt.expression)
        elif isinstance(stmt, ReturnStmt):
            if stmt.value:
                self._collect_externs_from_expr(stmt.value)

    def _collect_externs_from_expr(self, expr: Expression):
        """Recursively find hardware call names in an expression."""
        if isinstance(expr, FunctionCallExpr):
            if self._is_nova_hardware_call(expr.name):
                self._emit_extern_if_needed(expr.name.lower())
            for arg in expr.arguments:
                self._collect_externs_from_expr(arg)
        elif isinstance(expr, BinaryExpr):
            self._collect_externs_from_expr(expr.left)
            self._collect_externs_from_expr(expr.right)
        elif isinstance(expr, UnaryExpr):
            self._collect_externs_from_expr(expr.expression)
        elif isinstance(expr, GroupingExpr):
            self._collect_externs_from_expr(expr.expression)
        elif isinstance(expr, ListAccessExpr):
            self._collect_externs_from_expr(expr.index)
        elif isinstance(expr, MatrixAccessExpr):
            self._collect_externs_from_expr(expr.row)
            self._collect_externs_from_expr(expr.col)
        elif isinstance(expr, MemberAccessExpr):
            self._collect_externs_from_expr(expr.object)

    # ============== Statement Generation ==============

    def _generate_statement(self, stmt: Statement):
        """Generate LLVM IR for a single statement."""
        if isinstance(stmt, AssignmentStmt):
            self._generate_assignment(stmt)
        elif isinstance(stmt, IfStmt):
            self._generate_if(stmt)
        elif isinstance(stmt, ForStmt):
            self._generate_for(stmt)
        elif isinstance(stmt, WhileStmt):
            self._generate_while(stmt)
        elif isinstance(stmt, RepeatStmt):
            self._generate_repeat(stmt)
        elif isinstance(stmt, GotoStmt):
            self._generate_goto(stmt)
        elif isinstance(stmt, LabelStmt):
            self._generate_label(stmt)
        elif isinstance(stmt, FunctionCallStmt):
            self._generate_function_call(stmt.function_call)
        elif isinstance(stmt, ExpressionStmt):
            self._generate_expression_stmt(stmt)
        elif isinstance(stmt, ReturnStmt):
            self._generate_return(stmt)
        elif isinstance(stmt, VarDeclarationStmt):
            self._generate_var_decl(stmt)
        elif isinstance(stmt, StructDeclarationStmt):
            pass  # handled in pre-pass
        elif isinstance(stmt, AsmBlockStmt):
            # Inline assembly is Nova-16 specific — emit as a comment
            for line in stmt.assembly_code.splitlines():
                self._emit(f"; [inline asm] {line.strip()}")
        elif isinstance(stmt, ClrDrawStmt):
            self._emit_extern_if_needed("clrdraw")
            self._emit("call void @clrdraw()")
        elif isinstance(stmt, PxlOnStmt):
            x_reg = self._generate_expression(stmt.x)
            y_reg = self._generate_expression(stmt.y)
            c_reg = self._generate_expression(stmt.color)
            self._emit(f"call void @pxlon(i16 {x_reg}, i16 {y_reg}, i16 {c_reg})")
        elif isinstance(stmt, PxlOffStmt):
            x_reg = self._generate_expression(stmt.x)
            y_reg = self._generate_expression(stmt.y)
            self._emit(f"call void @pxloff(i16 {x_reg}, i16 {y_reg})")
        elif isinstance(stmt, LineStmt):
            args = [self._generate_expression(a) for a in
                    [stmt.x1, stmt.y1, stmt.x2, stmt.y2, stmt.color]]
            self._emit(f"call void @line(i16 {args[0]}, i16 {args[1]}, i16 {args[2]}, i16 {args[3]}, i16 {args[4]})")
        elif isinstance(stmt, CircleStmt):
            args = [self._generate_expression(a) for a in
                    [stmt.x, stmt.y, stmt.radius, stmt.color]]
            self._emit(f"call void @circle(i16 {args[0]}, i16 {args[1]}, i16 {args[2]}, i16 {args[3]})")
        elif isinstance(stmt, TextStmt):
            x_reg = self._generate_expression(stmt.x)
            y_reg = self._generate_expression(stmt.y)
            c_reg = self._generate_expression(stmt.color)
            # Text can be a string literal or expression
            text_reg = self._generate_expression(stmt.text)
            self._emit(f"call void @text(i16 {x_reg}, i16 {y_reg}, i8* {text_reg}, i16 {c_reg})")
        elif isinstance(stmt, SetLayerStmt):
            l_reg = self._generate_expression(stmt.layer)
            self._emit(f"call void @setlayer(i16 {l_reg})")
        elif isinstance(stmt, SRolStmt):
            a_reg = self._generate_expression(stmt.axis)
            amt_reg = self._generate_expression(stmt.amount)
            self._emit(f"call void @scrroll(i16 {a_reg}, i16 {amt_reg})")
        elif isinstance(stmt, SRotStmt):
            d_reg = self._generate_expression(stmt.direction)
            amt_reg = self._generate_expression(stmt.amount)
            self._emit(f"call void @scrrotate(i16 {d_reg}, i16 {amt_reg})")
        elif isinstance(stmt, SShftStmt):
            a_reg = self._generate_expression(stmt.axis)
            amt_reg = self._generate_expression(stmt.amount)
            self._emit(f"call void @scrshift(i16 {a_reg}, i16 {amt_reg})")
        elif isinstance(stmt, SFlipStmt):
            a_reg = self._generate_expression(stmt.axis)
            self._emit(f"call void @scrflip(i16 {a_reg})")
        elif isinstance(stmt, SpriteOnStmt):
            s_reg = self._generate_expression(stmt.sprite_id)
            x_reg = self._generate_expression(stmt.x)
            y_reg = self._generate_expression(stmt.y)
            self._emit(f"call void @spriteon(i16 {s_reg}, i16 {x_reg}, i16 {y_reg})")
        elif isinstance(stmt, SpriteOffStmt):
            s_reg = self._generate_expression(stmt.sprite_id)
            self._emit(f"call void @spriteoff(i16 {s_reg})")
        elif isinstance(stmt, PlayToneStmt):
            f_reg = self._generate_expression(stmt.frequency)
            d_reg = self._generate_expression(stmt.duration)
            v_reg = self._generate_expression(stmt.volume)
            self._emit(f"call void @playtone(i16 {f_reg}, i16 {d_reg}, i16 {v_reg})")
        elif isinstance(stmt, PlayWaveStmt):
            w_reg = self._generate_expression(stmt.waveform)
            f_reg = self._generate_expression(stmt.frequency)
            v_reg = self._generate_expression(stmt.volume)
            self._emit(f"call void @playwave(i16 {w_reg}, i16 {f_reg}, i16 {v_reg})")
        elif isinstance(stmt, StopSoundStmt):
            self._emit("call void @stopsound()")
        elif isinstance(stmt, SetChannelStmt):
            c_reg = self._generate_expression(stmt.channel)
            self._emit(f"call void @setchannel(i16 {c_reg})")
        elif isinstance(stmt, GetKeyStmt):
            tmp = self._temp()
            self._emit(f"{tmp} = call i16 @getkey()")
        elif isinstance(stmt, SerOutStmt):
            v_reg = self._generate_expression(stmt.value)
            self._emit(f"call void @serout(i16 {v_reg})")
        elif isinstance(stmt, SerInStmt):
            tmp = self._temp()
            self._emit(f"{tmp} = call i16 @serin()")
            lid = self._get_or_create_var_ref(stmt.variable)
            self._emit(f"store i16 {tmp}, i16* {lid}")
        elif isinstance(stmt, SerStatStmt):
            tmp = self._temp()
            self._emit(f"{tmp} = call i16 @serstat()")
            lid = self._get_or_create_var_ref(stmt.variable)
            self._emit(f"store i16 {tmp}, i16* {lid}")
        elif isinstance(stmt, SerCtrlStmt):
            v_reg = self._generate_expression(stmt.value)
            self._emit(f"call void @serctrl(i16 {v_reg})")
        elif isinstance(stmt, InputStmt):
            pr_reg = self._generate_expression(stmt.prompt) if stmt.prompt else "null"
            # Input variable is an i16* pointer
            lid = self._get_or_create_var_ref(stmt.variable)
            self._emit(f"call void @input(i8* {pr_reg}, i16* {lid})")
        elif isinstance(stmt, DispStmt):
            t_reg = self._generate_expression(stmt.text)
            self._emit(f"call void @disp(i8* {t_reg})")
        elif isinstance(stmt, PauseStmt):
            self._emit("call void @pause()")
        else:
            # Skip unknown statement types with a comment
            self._emit(f"; (unsupported statement: {type(stmt).__name__})")

    def _generate_expression_stmt(self, stmt: ExpressionStmt):
        """Generate code for a standalone expression (e.g. ++/--)."""
        self._generate_expression(stmt.expression)

    # ============== Expression Generation ==============

    def _generate_expression(self, expr: Expression) -> str:
        """
        Generate LLVM IR that computes an expression and returns the SSA register
        containing the result value.
        """
        if isinstance(expr, LiteralExpr):
            return self._generate_literal(expr)
        elif isinstance(expr, VariableExpr):
            return self._generate_variable_read(expr)
        elif isinstance(expr, BinaryExpr):
            return self._generate_binary(expr)
        elif isinstance(expr, UnaryExpr):
            return self._generate_unary(expr)
        elif isinstance(expr, FunctionCallExpr):
            return self._generate_call_expr(expr)
        elif isinstance(expr, GroupingExpr):
            return self._generate_expression(expr.expression)
        elif isinstance(expr, MemberAccessExpr):
            return self._generate_member_access(expr)
        elif isinstance(expr, ListAccessExpr):
            # Fallback: emit extern call (simplified stub)
            self._emit(f"; [unsupported] list access {expr.list_name}")
            tmp = self._temp()
            self._emit(f"{tmp} = add i16 0, 0")
            return tmp
        elif isinstance(expr, MatrixAccessExpr):
            tmp = self._temp()
            self._emit(f"{tmp} = add i16 0, 0")
            return tmp
        else:
            tmp = self._temp()
            self._emit(f"{tmp} = add i16 0, 0")
            return tmp

    def _generate_literal(self, expr: LiteralExpr) -> str:
        """Generate a literal value."""
        if expr.data_type == DataType.STRING:
            return self._generate_string_literal(expr.value)
        else:
            # Numeric literal
            val = int(expr.value) if expr.value is not None else 0
            tmp = self._temp()
            self._emit(f"{tmp} = add i16 0, {val}")
            return tmp

    def _generate_string_literal(self, value: str) -> str:
        """Find the pre-collected string constant and return an i8* to it."""
        # Find the string that was collected in pre-pass
        for str_id, _, str_val in self.string_constants:
            if str_val == value:
                tmp = self._temp()
                # Use getelementptr inbounds for cleaner LLVM IR
                self._emit(f"{tmp} = getelementptr inbounds [{len(value) + 1} x i8], [{len(value) + 1} x i8]* {str_id}, i32 0, i32 0")
                return tmp
        # Fallback: if string wasn't collected (shouldn't happen), create it inline
        str_id = f"@.str.{len(self.string_constants)}"
        escaped = self._escape_llvm_string(value)
        self._emit(f"{str_id} = private unnamed_addr constant [{len(value) + 1} x i8] c\"{escaped}\\00\"")
        tmp = self._temp()
        self._emit(f"{tmp} = getelementptr inbounds [{len(value) + 1} x i8], [{len(value) + 1} x i8]* {str_id}, i32 0, i32 0")
        return tmp

    def _generate_variable_read(self, expr: VariableExpr) -> str:
        """Load a variable's value into an SSA register."""
        name = expr.name.lower()
        lid = self._get_or_create_var_ref(name)
        tmp = self._temp()
        self._emit(f"{tmp} = load i16, i16* {lid}")
        return tmp

    def _get_or_create_var_ref(self, name: str) -> str:
        """Get the alloca reference for a variable, creating it if needed."""
        lowered = name.lower()
        # Check local first
        if lowered in self.local_vars:
            return self._local_ref(lowered)
        # Fall back to global
        if lowered not in self.global_vars:
            self.global_vars[lowered] = "global"
            # Need to emit the global at top level
        # Create local alloca in current function
        lid = self._local_ref(lowered)
        self.local_vars[lowered] = lid
        # Emit alloca in current block
        self._emit(f"{lid} = alloca i16")
        # Initialize from global if it exists
        gid = self._global_ref(lowered)
        tmp = self._temp()
        self._emit(f"{tmp} = load i16, i16* {gid}")
        self._emit(f"store i16 {tmp}, i16* {lid}")
        return lid

    def _generate_binary(self, expr: BinaryExpr) -> str:
        """Generate LLVM IR for a binary expression."""
        left = self._generate_expression(expr.left)
        right = self._generate_expression(expr.right)
        op = expr.operator
        tmp = self._temp()

        # Map NoBASIC operators to LLVM instructions
        if op == "+":
            self._emit(f"{tmp} = add i16 {left}, {right}")
        elif op == "-":
            self._emit(f"{tmp} = sub i16 {left}, {right}")
        elif op == "*":
            self._emit(f"{tmp} = mul i16 {left}, {right}")
        elif op == "/":
            self._emit(f"{tmp} = sdiv i16 {left}, {right}")
        elif op == "%":
            self._emit(f"{tmp} = srem i16 {left}, {right}")
        elif op == "&":
            self._emit(f"{tmp} = and i16 {left}, {right}")
        elif op == "|":
            self._emit(f"{tmp} = or i16 {left}, {right}")
        elif op == "^":
            self._emit(f"{tmp} = xor i16 {left}, {right}")
        elif op == "<<":
            self._emit(f"{tmp} = shl i16 {left}, {right}")
        elif op == ">>":
            self._emit(f"{tmp} = ashr i16 {left}, {right}")
        elif op == "=":
            cmp_reg = self._temp()
            self._emit(f"{cmp_reg} = icmp eq i16 {left}, {right}")
            self._emit(f"{tmp} = zext i1 {cmp_reg} to i16")
        elif op == "<>":
            cmp_reg = self._temp()
            self._emit(f"{cmp_reg} = icmp ne i16 {left}, {right}")
            self._emit(f"{tmp} = zext i1 {cmp_reg} to i16")
        elif op == "<":
            cmp_reg = self._temp()
            self._emit(f"{cmp_reg} = icmp slt i16 {left}, {right}")
            self._emit(f"{tmp} = zext i1 {cmp_reg} to i16")
        elif op == ">":
            cmp_reg = self._temp()
            self._emit(f"{cmp_reg} = icmp sgt i16 {left}, {right}")
            self._emit(f"{tmp} = zext i1 {cmp_reg} to i16")
        elif op == "<=":
            cmp_reg = self._temp()
            self._emit(f"{cmp_reg} = icmp sle i16 {left}, {right}")
            self._emit(f"{tmp} = zext i1 {cmp_reg} to i16")
        elif op == ">=":
            cmp_reg = self._temp()
            self._emit(f"{cmp_reg} = icmp sge i16 {left}, {right}")
            self._emit(f"{tmp} = zext i1 {cmp_reg} to i16")
        elif op == "&&":
            # Logical AND: convert to i1, and, then back
            l1 = self._temp()
            r1 = self._temp()
            self._emit(f"{l1} = icmp ne i16 {left}, 0")
            self._emit(f"{r1} = icmp ne i16 {right}, 0")
            and_reg = self._temp()
            self._emit(f"{and_reg} = and i1 {l1}, {r1}")
            self._emit(f"{tmp} = zext i1 {and_reg} to i16")
        elif op == "||":
            l1 = self._temp()
            r1 = self._temp()
            self._emit(f"{l1} = icmp ne i16 {left}, 0")
            self._emit(f"{r1} = icmp ne i16 {right}, 0")
            or_reg = self._temp()
            self._emit(f"{or_reg} = or i1 {l1}, {r1}")
            self._emit(f"{tmp} = zext i1 {or_reg} to i16")
        else:
            # Unknown operator, emit add as fallback
            self._emit(f"{tmp} = add i16 {left}, {right}")
            self._emit(f"; WARNING: unknown operator '{op}', used add as fallback")

        return tmp

    def _generate_unary(self, expr: UnaryExpr) -> str:
        """Generate LLVM IR for a unary expression."""
        inner = self._generate_expression(expr.expression)
        op = expr.operator
        tmp = self._temp()

        if op == "-":
            self._emit(f"{tmp} = sub i16 0, {inner}")
        elif op == "!" or op.lower() == "not":
            cmp_reg = self._temp()
            self._emit(f"{cmp_reg} = icmp eq i16 {inner}, 0")
            self._emit(f"{tmp} = zext i1 {cmp_reg} to i16")
        elif op == "++" and expr.is_post:
            # Post-increment: return old value, then increment
            # inner already has the old value; we need to write back +1
            lid = self._find_var_lid(expr.expression)
            if lid:
                inc = self._temp()
                self._emit(f"{inc} = add i16 {inner}, 1")
                self._emit(f"store i16 {inc}, i16* {lid}")
            self._emit(f"{tmp} = add i16 {inner}, 0")  # return old value
        elif op == "++":
            # Pre-increment
            inc = self._temp()
            self._emit(f"{inc} = add i16 {inner}, 1")
            lid = self._find_var_lid(expr.expression)
            if lid:
                self._emit(f"store i16 {inc}, i16* {lid}")
            self._emit(f"{tmp} = add i16 {inc}, 0")
        elif op == "--" and expr.is_post:
            lid = self._find_var_lid(expr.expression)
            if lid:
                dec = self._temp()
                self._emit(f"{dec} = sub i16 {inner}, 1")
                self._emit(f"store i16 {dec}, i16* {lid}")
            self._emit(f"{tmp} = add i16 {inner}, 0")
        elif op == "--":
            dec = self._temp()
            self._emit(f"{dec} = sub i16 {inner}, 1")
            lid = self._find_var_lid(expr.expression)
            if lid:
                self._emit(f"store i16 {dec}, i16* {lid}")
            self._emit(f"{tmp} = add i16 {dec}, 0")
        else:
            self._emit(f"{tmp} = add i16 0, {inner}")

        return tmp

    def _find_var_lid(self, expr: Expression) -> Optional[str]:
        """If expression is a variable, return its alloca reference."""
        if isinstance(expr, VariableExpr):
            name = expr.name.lower()
            if name in self.local_vars:
                return self._local_ref(name)
            if name in self.global_vars:
                return self._get_or_create_var_ref(name)
        return None

    def _generate_call_expr(self, expr: FunctionCallExpr) -> str:
        """Generate LLVM IR for a function call expression."""
        name = expr.name.lower()
        
        # Get the parameter types for this hardware function
        signature = self.HARDWARE_EXTERNS.get(expr.name.lower(), (None, None))
        param_types = signature[1] if signature else None

        if self._is_nova_hardware_call(expr.name):
            # Hardware function call - generate arguments with proper types
            args_with_types = []
            for i, arg in enumerate(expr.arguments):
                arg_val = self._generate_expression(arg)
                # Handle i8* (string pointer) parameters
                if param_types and i < len(param_types) and param_types[i] == "i8*":
                    args_with_types.append(f"i8* {arg_val}")
                else:
                    args_with_types.append(f"i16 {arg_val}")
            args_str = ", ".join(args_with_types)

            if signature[0] == "void":
                self._emit(f"call void @{name}({args_str})")
                tmp = self._temp()
                self._emit(f"{tmp} = add i16 0, 0")
                return tmp
            else:
                tmp = self._temp()
                self._emit(f"{tmp} = call i16 @{name}({args_str})")
                return tmp
        else:
            # User function call
            args = [self._generate_expression(arg) for arg in expr.arguments]
            args_str = ", ".join(f"i16 {a}" for a in args)
            label = self.function_labels.get(name, name)
            tmp = self._temp()
            self._emit(f"{tmp} = call i16 @{label}({args_str})")
            return tmp

    def _generate_member_access(self, expr: MemberAccessExpr) -> str:
        """Generate code for struct member access (simplified)."""
        # For now, emit a simplified GEP pattern
        tmp = self._temp()
        self._emit(f"{tmp} = add i16 0, 0")
        self._emit(f"; [struct] member access: {expr.object}.{expr.member}")
        return tmp

    # ============== Assignment Generation ==============

    def _generate_assignment(self, stmt: AssignmentStmt):
        """Generate code for `variable = expression`."""
        if isinstance(stmt.variable, VariableExpr):
            name = stmt.variable.name.lower()
            value = self._generate_expression(stmt.expression)
            lid = self._get_or_create_var_ref(name)
            self._emit(f"store i16 {value}, i16* {lid}")
            # Also sync back to global if it's a global variable
            if name in self.global_vars:
                gid = self._global_ref(name)
                self._emit(f"store i16 {value}, i16* {gid}")
        elif isinstance(stmt.variable, MemberAccessExpr):
            val = self._generate_expression(stmt.expression)
            self._emit(f"; [struct] assign to {stmt.variable.object}.{stmt.variable.member} = {val}")
        else:
            val = self._generate_expression(stmt.expression)
            self._emit(f"; [unsupported] assignment target: {type(stmt.variable).__name__}")

    # ============== Control Flow Generation ==============

    def _generate_if(self, stmt: IfStmt):
        """Generate if/then/else using LLVM basic blocks."""
        cond_val = self._generate_expression(stmt.condition)
        # Convert i16 to i1 for branch
        cmp_result = self._temp()
        self._emit(f"{cmp_result} = icmp ne i16 {cond_val}, 0")

        then_label = self._new_bb_label("if.then")
        else_label = self._new_bb_label("if.else")
        merge_label = self._new_bb_label("if.end")

        if stmt.else_branch:
            self._emit(f"br i1 {cmp_result}, label %{then_label}, label %{else_label}")
        else:
            self._emit(f"br i1 {cmp_result}, label %{then_label}, label %{merge_label}")

        # Then branch
        self._emit(f"")
        self._emit(f"{then_label}:")
        self.current_bb_label = then_label
        for s in stmt.then_branch:
            self._generate_statement(s)
        self._emit(f"br label %{merge_label}")

        # Else branch
        if stmt.else_branch:
            self._emit(f"")
            self._emit(f"{else_label}:")
            self.current_bb_label = else_label
            for s in stmt.else_branch:
                self._generate_statement(s)
            self._emit(f"br label %{merge_label}")

        # Merge point
        self._emit(f"")
        self._emit(f"{merge_label}:")
        self.current_bb_label = merge_label

    def _generate_for(self, stmt: ForStmt):
        """Generate For loop: for var = start To end [Step step] ... Next"""
        var_name = stmt.variable.lower()

        # Initialize loop variable
        start_reg = self._generate_expression(stmt.start)
        lid = self._get_or_create_var_ref(var_name)
        self._emit(f"store i16 {start_reg}, i16* {lid}")

        # Evaluate end and step
        end_reg = self._generate_expression(stmt.end)
        end_lid = self._temp()
        self._emit(f"{end_lid} = alloca i16")
        self._emit(f"store i16 {end_reg}, i16* {end_lid}")

        step_reg = None
        step_lid = None
        if stmt.step:
            step_reg = self._generate_expression(stmt.step)
            step_lid = self._temp()
            self._emit(f"{step_lid} = alloca i16")
            self._emit(f"store i16 {step_reg}, i16* {step_lid}")
        else:
            step_lid = self._temp()
            self._emit(f"{step_lid} = alloca i16")
            self._emit(f"store i16 1, i16* {step_lid}")

        header_label = self._new_bb_label("for.cond")
        body_label = self._new_bb_label("for.body")
        end_label = self._new_bb_label("for.end")

        # Branch to header
        self._emit(f"br label %{header_label}")

        # Header/condition block
        self._emit(f"")
        self._emit(f"{header_label}:")
        self.current_bb_label = header_label

        var_val = self._temp()
        end_val = self._temp()
        step_val = self._temp()
        self._emit(f"{var_val} = load i16, i16* {lid}")
        self._emit(f"{end_val} = load i16, i16* {end_lid}")
        self._emit(f"{step_val} = load i16, i16* {step_lid}")

        # Check sign of step to determine comparison direction
        # Here we assume step > 0 for simplicity (standard NoBASIC default)
        cmp_res = self._temp()
        self._emit(f"{cmp_res} = icmp sle i16 {var_val}, {end_val}")
        self._emit(f"br i1 {cmp_res}, label %{body_label}, label %{end_label}")

        # Body block
        self._emit(f"")
        self._emit(f"{body_label}:")
        self.current_bb_label = body_label
        for s in stmt.body:
            self._generate_statement(s)

        # Increment
        cur_val = self._temp()
        step = self._temp()
        new_val = self._temp()
        self._emit(f"{cur_val} = load i16, i16* {lid}")
        self._emit(f"{step} = load i16, i16* {step_lid}")
        self._emit(f"{new_val} = add i16 {cur_val}, {step}")
        self._emit(f"store i16 {new_val}, i16* {lid}")

        self._emit(f"br label %{header_label}")

        # End block
        self._emit(f"")
        self._emit(f"{end_label}:")
        self.current_bb_label = end_label

    def _generate_while(self, stmt: WhileStmt):
        """Generate While loop."""
        header_label = self._new_bb_label("while.cond")
        body_label = self._new_bb_label("while.body")
        end_label = self._new_bb_label("while.end")

        self._emit(f"br label %{header_label}")

        # Header
        self._emit(f"")
        self._emit(f"{header_label}:")
        self.current_bb_label = header_label
        cond_val = self._generate_expression(stmt.condition)
        cmp_res = self._temp()
        self._emit(f"{cmp_res} = icmp ne i16 {cond_val}, 0")
        self._emit(f"br i1 {cmp_res}, label %{body_label}, label %{end_label}")

        # Body
        self._emit(f"")
        self._emit(f"{body_label}:")
        self.current_bb_label = body_label
        for s in stmt.body:
            self._generate_statement(s)
        self._emit(f"br label %{header_label}")

        # End
        self._emit(f"")
        self._emit(f"{end_label}:")
        self.current_bb_label = end_label

    def _generate_repeat(self, stmt: RepeatStmt):
        """Generate Repeat/Until loop."""
        body_label = self._new_bb_label("repeat.body")
        cond_label = self._new_bb_label("repeat.cond")
        end_label = self._new_bb_label("repeat.end")

        self._emit(f"br label %{body_label}")

        # Body
        self._emit(f"")
        self._emit(f"{body_label}:")
        self.current_bb_label = body_label
        for s in stmt.body:
            self._generate_statement(s)
        self._emit(f"br label %{cond_label}")

        # Condition check
        self._emit(f"")
        self._emit(f"{cond_label}:")
        self.current_bb_label = cond_label
        cond_val = self._generate_expression(stmt.condition)
        cmp_res = self._temp()
        self._emit(f"{cmp_res} = icmp ne i16 {cond_val}, 0")
        self._emit(f"br i1 {cmp_res}, label %{end_label}, label %{body_label}")

        # End
        self._emit(f"")
        self._emit(f"{end_label}:")
        self.current_bb_label = end_label

    def _generate_goto(self, stmt: GotoStmt):
        """Generate goto."""
        label_name = self._llvm_id(f"label_{stmt.label}")
        self._emit(f"br label %{label_name}")

    def _generate_label(self, stmt: LabelStmt):
        """Generate a label as a basic block."""
        label_name = self._llvm_id(f"label_{stmt.label}")
        self._emit(f"")
        self._emit(f"{label_name}:")
        self.current_bb_label = label_name

    def _generate_return(self, stmt: ReturnStmt):
        """Generate return statement."""
        if stmt.value:
            val = self._generate_expression(stmt.value)
            self._emit(f"ret i16 {val}")
        else:
            self._emit(f"ret i16 0")
        # Mark that this function has a return (so a terminal ret isn't needed)
        if self.current_function:
            self.function_has_return.add(self.current_function)

    def _generate_function_call(self, expr: FunctionCallExpr):
        """Generate a function call as a statement (discarding the return value)."""
        self._generate_call_expr(expr)

    def _generate_var_decl(self, stmt: VarDeclarationStmt):
        """Generate variable declaration."""
        # Variables are handled lazily by _get_or_create_var_ref
        # Just ensure they're registered
        for v in stmt.variables:
            name = v.lower()
            if stmt.scope == VarScope.LOCAL:
                if name not in self.local_vars:
                    lid = self._local_ref(name)
                    self.local_vars[name] = lid
                    self._emit(f"{lid} = alloca i16")
            else:
                if name not in self.global_vars:
                    self.global_vars[name] = "global"

    # ============== Function Generation ==============

    def _generate_function(self, stmt: FunctionDefStmt):
        """Generate an LLVM function definition."""
        func_key = stmt.name.lower()
        label = self.function_labels[func_key]
        param_names = [pn for pn, _ in stmt.params]

        # Build parameter list
        params = ", ".join([f"i16 %{self._llvm_id(p)}" for p in param_names])
        self._emit(f"")
        self._emit(f"define i16 @{label}({params}) {{")
        self.indent_level = 1
        self._emit("entry:")
        self.current_bb_label = "entry"

        # Save previous local state
        prev_locals = dict(self.local_vars)
        prev_function = self.current_function
        prev_temp = self.temp_ssa_counter

        self.current_function = func_key
        self.local_vars = {}
        self.temp_ssa_counter = 0

        # Create allocas for parameters (they come in as SSA values but need mutable slots)
        for p in param_names:
            pid = self._llvm_id(p)
            lid = f"%l_{pid}"
            self.local_vars[p.lower()] = lid
            self._emit(f"{lid} = alloca i16")
            self._emit(f"store i16 %{pid}, i16* {lid}")

        # Generate function body
        for s in stmt.body:
            self._generate_statement(s)

        # Only add default return if no explicit return was emitted
        if func_key not in self.function_has_return:
            self._emit(f"ret i16 0")

        # Restore state
        self.indent_level = 0
        self._emit("}")
        self._emit("")
        self.local_vars = prev_locals
        self.current_function = prev_function
        self.temp_ssa_counter = prev_temp

    # ============== Utility ==============

    @staticmethod
    def _escape_llvm_string(value: str) -> str:
        """Escape a string for inclusion in LLVM IR."""
        result = []
        for ch in value:
            if ch == '"':
                result.append('\\22')
            elif ch == '\\':
                result.append('\\5c')
            elif ch == '\n':
                result.append('\\0a')
            elif ch == '\r':
                result.append('\\0d')
            elif ch == '\t':
                result.append('\\09')
            elif 32 <= ord(ch) < 127:
                result.append(ch)
            else:
                result.append(f'\\{ord(ch):02x}')
        return ''.join(result)