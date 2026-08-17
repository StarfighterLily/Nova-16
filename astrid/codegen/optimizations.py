"""
Astrid Optimization utilities (moved into astrid.codegen)
Contains ExpressionSimplifier and FunctionInliner adapted for Astrid AST
"""
from typing import Dict, Set, List, Tuple, Optional, Any
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from astrid.parser.parser import (
    BinaryOp, UnaryOp, Number, Identifier, StringLiteral, CharLiteral,
    FuncCall, Expression, Assignment, Return, If, While, DoWhile, For,
    Switch, Break, Continue, VarDecl, PostfixOp, FunctionDef,
)


def _num_value(expr: Any) -> Optional[int]:
    if isinstance(expr, Number):
        try:
            return int(expr.value, 0)
        except (ValueError, TypeError):
            return None
    return None


def _is_number_literal(expr: Any, expected: int) -> bool:
    val = _num_value(expr)
    return val is not None and val == expected


def _expression_key(expr: Any) -> str:
    if isinstance(expr, Number):
        return f"num:{_num_value(expr)}"
    if isinstance(expr, Identifier):
        return f"var:{expr.name}"
    if isinstance(expr, StringLiteral):
        return f"str:{expr.value}"
    if isinstance(expr, CharLiteral):
        return f"char:{expr.char_value}"
    if isinstance(expr, UnaryOp):
        return f"un:{expr.op}:{_expression_key(expr.right)}"
    if isinstance(expr, BinaryOp):
        left_key = _expression_key(expr.left)
        right_key = _expression_key(expr.right)
        if expr.op in {"+", "*", "&", "|", "^", "==", "!=", "&&", "||"} \
                and right_key < left_key:
            left_key, right_key = right_key, left_key
        return f"bin:{expr.op}:{left_key}:{right_key}"
    if isinstance(expr, PostfixOp):
        return f"post:{expr.op}:{_expression_key(expr.left)}"
    if isinstance(expr, FuncCall):
        args = ",".join(_expression_key(arg) for arg in expr.args)
        return f"call:{expr.name}({args})"
    return repr(expr)


@dataclass
class ExpressionSimplifier:
    debug: bool = False

    def __post_init__(self):
        self._cse_cache: Dict[str, Any] = {}

    def simplify(self, expr: Any) -> Any:
        self._cse_cache = {}
        result = self._simplify_node(expr)
        if self.debug and result is not expr:
            print(f"[EXPR_SIMP] {type(expr).__name__} -> {type(result).__name__}")
        return result

    def _simplify_node(self, expr: Any) -> Any:
        if isinstance(expr, Number):
            return expr
        if isinstance(expr, Identifier):
            return expr
        if isinstance(expr, StringLiteral):
            return expr
        if isinstance(expr, CharLiteral):
            return expr
        if isinstance(expr, UnaryOp):
            operand = self._simplify_node(expr.right)
            folded = self._fold_unary(expr.op, operand)
            if folded is not None:
                return folded
            if expr.op == "+":
                return operand
            return UnaryOp(expr.op, operand)
        if isinstance(expr, BinaryOp):
            left = self._simplify_node(expr.left)
            right = self._simplify_node(expr.right)
            folded = self._fold_binary(expr.op, left, right)
            if folded is not None:
                return folded
            algebraic = self._apply_algebraic_rules(expr.op, left, right)
            if algebraic is not None:
                return algebraic
            left, right = self._canonicalize_operands(expr.op, left, right)
            simplified = BinaryOp(left, expr.op, right)
            key = _expression_key(simplified)
            if key in self._cse_cache:
                return self._cse_cache[key]
            self._cse_cache[key] = simplified
            return simplified
        if isinstance(expr, PostfixOp):
            return expr
        if isinstance(expr, FuncCall):
            simplified_args = [self._simplify_node(arg) for arg in expr.args]
            folded = self._fold_builtin_call(expr.name, simplified_args)
            if folded is not None:
                return folded
            return FuncCall(expr.name, simplified_args)
        return expr

    def _fold_unary(self, operator: str, operand: Any) -> Optional[Number]:
        val = _num_value(operand)
        if val is None:
            return None
        try:
            if operator == "-":
                return Number(str(-val))
            if operator == "!":
                return Number("1" if val == 0 else "0")
            if operator == "~":
                return Number(str(~val & 0xFFFF))
        except (TypeError, ValueError):
            return None
        return None

    def _fold_binary(self, operator: str, left: Any, right: Any) -> Optional[Number]:
        left_val = _num_value(left)
        right_val = _num_value(right)
        if left_val is None or right_val is None:
            return None
        try:
            if operator == "+":
                return Number(str(left_val + right_val))
            if operator == "-":
                return Number(str(left_val - right_val))
            if operator == "*":
                return Number(str(left_val * right_val))
            if operator == "/":
                if right_val == 0:
                    return None
                return Number(str(left_val // right_val))
            if operator == "%":
                if right_val == 0:
                    return None
                return Number(str(left_val % right_val))
            if operator == "&":
                return Number(str(left_val & right_val))
            if operator == "|":
                return Number(str(left_val | right_val))
            if operator == "^":
                return Number(str(left_val ^ right_val))
            if operator == "<<":
                return Number(str(left_val << right_val))
            if operator == ">>":
                return Number(str(left_val >> right_val))
            if operator == "==":
                return Number("1" if left_val == right_val else "0")
            if operator == "!=":
                return Number("1" if left_val != right_val else "0")
            if operator == "<":
                return Number("1" if left_val < right_val else "0")
            if operator == ">":
                return Number("1" if left_val > right_val else "0")
            if operator == "<=":
                return Number("1" if left_val <= right_val else "0")
            if operator == ">=":
                return Number("1" if left_val >= right_val else "0")
            if operator == "&&":
                return Number("1" if (left_val != 0 and right_val != 0) else "0")
            if operator == "||":
                return Number("1" if (left_val != 0 or right_val != 0) else "0")
        except (TypeError, ValueError, ZeroDivisionError):
            return None
        return None

    def _apply_algebraic_rules(self, operator: str, left: Any, right: Any) -> Optional[Any]:
        if operator == "+":
            if _is_number_literal(right, 0):
                return left
            if _is_number_literal(left, 0):
                return right
        if operator == "-":
            if _is_number_literal(right, 0):
                return left
            if _expression_key(left) == _expression_key(right):
                return Number("0")
        if operator == "*":
            if _is_number_literal(right, 1):
                return left
            if _is_number_literal(left, 1):
                return right
            if _is_number_literal(right, 0) or _is_number_literal(left, 0):
                return Number("0")
        if operator == "/":
            if _is_number_literal(right, 1):
                return left
        if operator == "%":
            if _is_number_literal(right, 1):
                return Number("0")
        if operator == "&":
            if _is_number_literal(right, 0) or _is_number_literal(left, 0):
                return Number("0")
        if operator in {"|", "^"}:
            if _is_number_literal(right, 0):
                return left
            if _is_number_literal(left, 0):
                return right
        if operator in {"<<", ">>"}:
            if _is_number_literal(right, 0):
                return left
        if operator == "&&":
            if _is_number_literal(left, 0) or _is_number_literal(right, 0):
                return Number("0")
            if _is_number_literal(left, 1):
                return right
            if _is_number_literal(right, 1):
                return left
        if operator == "||":
            if _is_number_literal(left, 1) or _is_number_literal(right, 1):
                return Number("1")
            if _is_number_literal(left, 0):
                return right
            if _is_number_literal(right, 0):
                return left
        return None

    def _canonicalize_operands(self, operator: str, left: Any, right: Any) -> Tuple[Any, Any]:
        if operator not in {"+", "*", "&", "|", "^", "==", "!=", "&&", "||"}:
            return left, right
        left_key = _expression_key(left)
        right_key = _expression_key(right)
        if right_key < left_key:
            return right, left
        return left, right

    def _fold_builtin_call(self, func_name: str, args: List[Any]) -> Optional[Number]:
        name = func_name.lower()
        side_effect_builtins = {
            "set_mode", "set_vmode", "set_layer", "set_pos", "write_screen",
            "scroll_x", "scroll_y", "set_pointers", "write_text", "set_font",
            "sound_play", "sound_stop", "set_timer", "sti", "cli", "iret",
            "key_available", "key_read", "key_clear", "random", "random_range",
            "halt", "enable_interrupts", "disable_interrupts",
        }
        if name in side_effect_builtins:
            return None
        if not args:
            return None
        values = []
        for arg in args:
            val = _num_value(arg)
            if val is None:
                return None
            values.append(val)
        try:
            if name == "abs":
                return Number(str(abs(values[0])))
            if name == "min" and len(values) >= 2:
                return Number(str(min(values[0], values[1])))
            if name == "max" and len(values) >= 2:
                return Number(str(max(values[0], values[1])))
        except (TypeError, ValueError, ZeroDivisionError):
            return None
        return None


@dataclass
class FunctionInliner:
    max_statements: int = 8
    min_call_sites: int = 2
    debug: bool = False

    def __post_init__(self):
        self._inlineable: Dict[str, bool] = {}
        self._call_graph: Dict[str, Set[str]] = {}
        self._call_counts: Dict[str, int] = Counter()

    def analyze(self, functions: List[FunctionDef]) -> Set[str]:
        functions_dict = {f.name: f for f in functions}
        for func in functions:
            called = self._collect_callees(func)
            self._call_graph[func.name] = called
            for callee in called:
                self._call_counts[callee] += 1
        inlineable = set()
        for func in functions:
            if self._eligible(func, functions_dict):
                inlineable.add(func.name)
        return inlineable

    def _collect_callees(self, func: FunctionDef) -> Set[str]:
        callees = set()
        def walk(node):
            if isinstance(node, FuncCall):
                callees.add(node.name)
            elif isinstance(node, list):
                for n in node:
                    walk(n)
            elif hasattr(node, '__dict__'):
                for v in vars(node).values():
                    walk(v)
        walk(func.body)
        return callees

    def _eligible(self, func: FunctionDef, functions_dict: Dict[str, FunctionDef]) -> bool:
        stmt_count = len(func.body)
        if stmt_count > self.max_statements:
            return False
        callees = self._collect_callees(func)
        if func.name in callees:
            return False
        # simple control flow check
        return True
