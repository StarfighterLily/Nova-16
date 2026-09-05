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
    Switch, Break, Continue, VarDecl, PostfixOp, FunctionDef, Cast,
)


def _num_value(expr: Any) -> Optional[int]:
    if isinstance(expr, Number):
        try:
            return int(expr.value, 0)
        except (ValueError, TypeError):
            return None
    if isinstance(expr, CharLiteral):
        # Char literals are integer constants too, so folds like 'A' + 1
        # and (int)'A' keep working after a cast folded to a CharLiteral.
        return expr.char_value & 0xFFFF
    return None


def _is_number_literal(expr: Any, expected: int) -> bool:
    val = _num_value(expr)
    return val is not None and val == expected


def _expression_key(expr: Any) -> str:
    if isinstance(expr, Number):
        # Floats have no int form (_num_value -> None); use the raw literal
        # so distinct float literals don't collide in the CSE cache.
        iv = _num_value(expr)
        return f"num:{iv}" if iv is not None else f"numF:{expr.value}"
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
    if isinstance(expr, Cast):
        return f"cast:{expr.target_type}:{_expression_key(expr.expr)}"
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
        if isinstance(expr, Cast):
            simplified_inner = self._simplify_node(expr.expr)
            # Compile-time fold: (char)CONST, (int)CONST are constant folds.
            num_val = _num_value(simplified_inner)
            if num_val is not None:
                if expr.target_type == 'char':
                    # Fold to a CharLiteral (not a Number) so the result
                    # stays char-TYPED: downstream consumers such as the
                    # write_text conversion check _cast_source_type and
                    # must see 'char' to render a glyph instead of the
                    # decimal digits of the character code.
                    return CharLiteral(num_val & 0xFF)
                if expr.target_type == 'int':
                    return Number(str(num_val & 0xFFFF))
            return Cast(expr.target_type, simplified_inner)
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
        """Fold built-in function calls where all arguments are numeric literals.

        The formulas below must match core/exec_handlers.py's runtime opcode
        handlers (_sin, _cos, _tan, etc.) EXACTLY. This fold is purely an
        optimization: Astrid source that happens to have a constant-foldable
        argument must produce the identical result to the same source with a
        non-foldable argument, which falls through to the real opcode at
        runtime.
        """
        name = func_name.lower()
        side_effect_builtins = {
            "set_mode", "set_vmode", "set_layer", "set_pos", "write_screen",
            "scroll_x", "scroll_y", "set_pointers", "write_text", "set_font",
            "sound_play", "sound_stop", "set_timer", "sti", "cli", "iret",
            "key_available", "key_read", "key_clear", "random", "random_range",
            "halt", "enable_interrupts", "disable_interrupts",
            "screen_rotate", "screen_shift", "screen_flip", "draw_line",
            "draw_circle", "screen_invert", "screen_blit", "set_blend_mode",
            "draw_char", "layer_swap", "layer_move", "layer_copy",
            "sound_trigger", "key_count", "key_ctrl",
            "ser_out", "ser_in", "ser_stat", "ser_ctrl",
            "memcpy", "memset", "memmove", "memcmp", "memtest", "memswap",
            "btst", "bset", "bclr", "bflip",
            "xchng", "nop", "pushf", "popf", "pusha", "popa",
            "sed", "cld", "cla", "bcd2bin", "bin2bcd",
            "bcdadd", "bcdsub", "bcda", "bcds", "bcdcmp",
            "mouse_ctrl",
            "mouse_read", "mouse_pos",
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
            # Unary math functions.
            #
            # These formulas must match core/exec_handlers.py's runtime
            # opcode handlers (_sin, _cos, _tan, etc) EXACTLY. This fold is
            # purely an optimization: Astrid source that happens to have a
            # constant-foldable argument must produce the identical result
            # to the same source with a non-foldable argument, which falls
            # through to the real SIN/COS/.../opcode at runtime.
            if name in ("sin", "cos", "tan", "sqrt", "abs", "atan", "asin", "acos",
                        "deg", "rad", "floor", "ceil", "round", "trunc", "frac",
                        "intgr", "int", "log", "exp"):
                # NOTE: int() is an identity conversion on 16-bit integer
                # values (see builtin_int in codegen.py); it is NOT the
                # fixed-point truncation that intgr() performs.
                import math
                v = values[0]
                if name == "sin":
                    return Number(str(int(math.sin(v / 256.0) * 256)))
                if name == "cos":
                    return Number(str(int(math.cos(v / 256.0) * 256)))
                if name == "tan":
                    # _tan takes its operand as raw radians (no /256 scaling)
                    # and scales the result by 1000, not 256.
                    try:
                        return Number(str(int(math.tan(v) * 1000)))
                    except (ValueError, OverflowError):
                        return None  # can't fold; runtime handler falls back to 0
                if name == "sqrt":
                    if v < 0: return None
                    return Number(str(int(v ** 0.5)))
                if name == "abs":
                    return Number(str(abs(v)))
                if name == "atan":
                    return Number(str(int(math.atan(v / 256.0) * 256)))
                if name == "asin":
                    try:
                        return Number(str(int(math.asin(v / 256.0) * 256)))
                    except ValueError:
                        return None  # out of [-1, 1] domain; runtime handler falls back to 0
                if name == "acos":
                    try:
                        return Number(str(int(math.acos(v / 256.0) * 256)))
                    except ValueError:
                        return None  # out of [-1, 1] domain; runtime handler falls back to 0
                if name == "deg":
                    # _deg converts plain degrees -> fixed-point (x256) radians.
                    return Number(str(int((v * math.pi / 180.0) * 256)))
                if name == "rad":
                    # _rad converts fixed-point (x256) radians -> plain degrees.
                    return Number(str(int((v / 256.0) * 180.0 / math.pi)))
                if name == "floor":
                    return Number(str(int(math.floor(v / 256.0))))
                if name == "ceil":
                    return Number(str(int(math.ceil(v / 256.0))))
                if name == "round":
                    return Number(str(int(round(v / 256.0))))
                if name == "trunc":
                    # Truncate toward zero (matches _trunc: int(v / 256.0),
                    # not v // 256 which floors toward -infinity).
                    return Number(str(int(v / 256.0)))
                if name == "frac":
                    # Same sign as v, consistent with TRUNC (matches _frac's
                    # math.fmod, not v % 256 which floors).
                    return Number(str(int(math.fmod(v, 256))))
                if name == "intgr":
                    return Number(str(int(v / 256.0)))
                if name == "int":
                    # Identity: Astrid values are already 16-bit integers.
                    return Number(str(v & 0xFFFF))
                if name == "log":
                    if v <= 0: return None
                    return Number(str(int(math.log(v / 256.0) * 256)))
                if name == "exp":
                    result = int(math.exp(v / 256.0) * 256)
                    return Number(str(max(0, min(65535, result))))

            # Binary math functions
            if name in ("min", "max") and len(values) >= 2:
                v0, v1 = values[0], values[1]
                fn = min if name == "min" else max
                return Number(str(fn(v0, v1)))
            if name == "powr" and len(values) >= 2:
                v0, v1 = values[0], values[1]
                if v1 < 0: return None
                return Number(str(int(v0 ** v1)))

            # CLZ / CTZ / POPCNT on constants
            if name == "clz":
                v = values[0]
                count = 0
                for i in range(15, -1, -1):
                    if v & (1 << i): break
                    count += 1
                return Number(str(count))
            if name == "ctz":
                v = values[0]
                count = 0
                for i in range(16):
                    if v & (1 << i): break
                    count += 1
                return Number(str(count))
            if name == "popcnt":
                return Number(str(values[0].bit_count()))

            # SWAP (byte swap)
            if name == "swap":
                v = values[0]
                return Number(str(((v & 0xFF) << 8) | ((v >> 8) & 0xFF)))
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

    def inline_functions(self, functions: List[FunctionDef], inlineable_names: Optional[Set[str]] = None) -> List[FunctionDef]:
        """Return a copy of the function list with a conservative set of calls inlined.

        Only void functions are inlined in statement position. This keeps the
        expansion safe and avoids rewriting value-producing expression calls.
        """
        if inlineable_names is None:
            inlineable_names = self.analyze(functions)
        if not functions or not inlineable_names:
            return functions

        function_map = {fn.name: fn for fn in functions}
        result: List[FunctionDef] = []
        for func in functions:
            if func.name in inlineable_names:
                result.append(func)
                continue
            result.append(self._inline_function(func, inlineable_names, function_map))
        return result

    def _inline_function(self, func: FunctionDef, inlineable_names: Set[str], function_map: Dict[str, FunctionDef]) -> FunctionDef:
        def rewrite(node):
            if isinstance(node, list):
                rewritten: List[Any] = []
                for item in node:
                    rewritten.extend(rewrite(item))
                return rewritten
            if isinstance(node, FuncCall) and node.name in inlineable_names:
                callee = function_map.get(node.name)
                if callee is None or callee.return_type != 'void':
                    return [node]
                mapping = {param.name: arg for param, arg in zip(callee.params, node.args)}
                expanded: List[Any] = []
                for stmt in callee.body:
                    expanded.extend(self._substitute(stmt, mapping))
                return expanded
            if isinstance(node, VarDecl):
                if node.value is not None:
                    node.value = self._substitute(node.value, {})
                return [node]
            if isinstance(node, Assignment):
                node.value = self._substitute(node.value, {})
                return [node]
            if isinstance(node, Return):
                if node.value is not None:
                    node.value = self._substitute(node.value, {})
                return [node]
            if isinstance(node, If):
                node.cond = self._substitute(node.cond, {})
                node.then_body = rewrite(node.then_body)
                if node.else_body:
                    node.else_body = rewrite(node.else_body)
                return [node]
            if isinstance(node, While):
                node.cond = self._substitute(node.cond, {})
                node.body = rewrite(node.body)
                return [node]
            if isinstance(node, DoWhile):
                node.cond = self._substitute(node.cond, {})
                node.body = rewrite(node.body)
                return [node]
            if isinstance(node, For):
                if node.init is not None:
                    node.init = self._substitute(node.init, {})
                if node.cond is not None:
                    node.cond = self._substitute(node.cond, {})
                if node.update is not None:
                    node.update = self._substitute(node.update, {})
                node.body = rewrite(node.body)
                return [node]
            if isinstance(node, Switch):
                node.expr = self._substitute(node.expr, {})
                for case in node.cases:
                    case.value = self._substitute(case.value, {})
                    case.body = rewrite(case.body)
                if node.default_body:
                    node.default_body = rewrite(node.default_body)
                return [node]
            return [node]

        func.body = rewrite(func.body)
        return func

    def _substitute(self, node: Any, mapping: Dict[str, Any]) -> Any:
        if isinstance(node, list):
            return [self._substitute(item, mapping) for item in node]
        if isinstance(node, Identifier) and node.name in mapping:
            return mapping[node.name]
        if isinstance(node, BinaryOp):
            node.left = self._substitute(node.left, mapping)
            node.right = self._substitute(node.right, mapping)
            return node
        if isinstance(node, UnaryOp):
            node.right = self._substitute(node.right, mapping)
            return node
        if isinstance(node, PostfixOp):
            node.left = self._substitute(node.left, mapping)
            return node
        if isinstance(node, FuncCall):
            node.args = [self._substitute(arg, mapping) for arg in node.args]
            return node
        if isinstance(node, Cast):
            node.expr = self._substitute(node.expr, mapping)
            return node
        return node


@dataclass
class RegisterColoringPass:
    """Greedy graph-coloring pass for local variable register assignment."""
    interference_graph: Dict[str, Set[str]]
    available_registers: List[str]
    debug: bool = False

    def __post_init__(self):
        self.color_map: Dict[str, str] = {}
        self.color_usage: Dict[str, int] = defaultdict(int)

    def color_graph(self) -> Dict[str, str]:
        var_degrees = sorted(
            self.interference_graph.items(),
            key=lambda item: (-len(item[1]), item[0]),
        )

        for var, neighbors in var_degrees:
            used_colors = {self.color_map[n] for n in neighbors if n in self.color_map}
            for reg in self.available_registers:
                if reg in used_colors:
                    continue
                self.color_map[var] = reg
                self.color_usage[reg] += 1
                break

        if self.debug:
            print(f"[COLORING] colored {len(self.color_map)} variables")

        return self.color_map


@dataclass
class HotSpillAnalyzer:
    """Identify high-frequency spilled variables for zero-page placement."""
    spill_slots: Dict[str, int]
    access_counts: Dict[str, int] = field(default_factory=Counter)
    debug: bool = False
    zero_page_base: int = 0x0080
    zero_page_size: int = 128

    def __post_init__(self):
        self.hot_spills: Dict[str, int] = {}
        self.zp_allocation: List[Tuple[str, int]] = []
        self.next_zp_addr = self.zero_page_base

    def identify_hot_spills(self, threshold_percentile: float = 75.0) -> Dict[str, int]:
        if not self.access_counts:
            return {}

        sorted_counts = sorted(self.access_counts.values(), reverse=True)
        threshold_idx = max(0, int(len(sorted_counts) * (1 - threshold_percentile / 100.0)))
        threshold = sorted_counts[threshold_idx] if sorted_counts else 0

        candidates = [
            (var, count) for var, count in self.access_counts.items()
            if var in self.spill_slots and count >= threshold
        ]
        candidates.sort(key=lambda item: item[1], reverse=True)

        for var, count in candidates:
            if self.next_zp_addr + 2 > self.zero_page_base + self.zero_page_size:
                break
            zp_addr = self.next_zp_addr
            self.hot_spills[var] = zp_addr
            self.zp_allocation.append((var, zp_addr))
            self.next_zp_addr += 2

        if self.debug:
            print(f"[HOT_SPILL] migrated {len(self.hot_spills)} variables to zero page")
        return self.hot_spills

    def should_use_zero_page(self, var: str) -> bool:
        return var in self.hot_spills

    def get_zero_page_address(self, var: str) -> Optional[int]:
        return self.hot_spills.get(var)


@dataclass
class RegisterPressureMonitor:
    """Monitor live-variable pressure and identify likely register-allocation bottlenecks."""
    live_at_point: Dict[int, Set[str]]
    available_registers: int
    debug: bool = False

    def __post_init__(self):
        self.pressure_history: List[Tuple[int, int]] = []
        self.pressure_peaks: List[Tuple[int, int]] = []
        self.bottleneck_regions: List[Tuple[int, int, int]] = []

    def analyze_pressure(self) -> Dict[str, Any]:
        pressure_by_point: Dict[int, int] = {}
        max_pressure = 0
        max_pressure_point = 0

        for point, live_vars in self.live_at_point.items():
            pressure = len(live_vars)
            pressure_by_point[point] = pressure
            self.pressure_history.append((point, pressure))

            if pressure > max_pressure:
                max_pressure = pressure
                max_pressure_point = point

            if pressure > self.available_registers:
                self.pressure_peaks.append((point, pressure))

        self.pressure_history.sort(key=lambda item: item[0])
        self.pressure_peaks.sort(key=lambda item: item[0])
        self._identify_bottlenecks()

        stats = {
            'max_pressure': max_pressure,
            'max_pressure_point': max_pressure_point,
            'available_registers': self.available_registers,
            'pressure_exceeds_available': len(self.pressure_peaks),
            'avg_pressure': (
                sum(value for _, value in self.pressure_history) / len(self.pressure_history)
                if self.pressure_history else 0
            ),
            'bottleneck_regions': self.bottleneck_regions,
        }

        if self.debug:
            print(f"\n[PRESSURE] Register Pressure Analysis:")
            print(f"  Maximum pressure: {max_pressure}/{self.available_registers} (at point {max_pressure_point})")
            print(f"  Average pressure: {stats['avg_pressure']:.1f}")
            print(f"  Exceeds available: {len(self.pressure_peaks)} program points")
            print(f"  Bottleneck regions: {len(self.bottleneck_regions)}")

        return stats

    def _identify_bottlenecks(self):
        if not self.pressure_peaks:
            self.bottleneck_regions = []
            return

        regions: List[Tuple[int, int, int]] = []
        current_start = self.pressure_peaks[0][0]
        current_peak = self.pressure_peaks[0][1]

        for i in range(1, len(self.pressure_peaks)):
            point, pressure = self.pressure_peaks[i]
            prev_point = self.pressure_peaks[i - 1][0]
            if point - prev_point > 10:
                regions.append((current_start, prev_point, current_peak))
                current_start = point
                current_peak = pressure
            else:
                current_peak = max(current_peak, pressure)

        regions.append((current_start, self.pressure_peaks[-1][0], current_peak))
        self.bottleneck_regions = regions

    def get_pressure_report(self) -> str:
        stats = self.analyze_pressure()
        return (
            "\nRegister Pressure Report\n"
            "========================\n"
            f"Maximum Pressure:       {stats['max_pressure']}/{stats['available_registers']}\n"
            f"Average Pressure:       {stats['avg_pressure']:.1f}\n"
            f"Pressure Exceeded At:   {stats['pressure_exceeds_available']} points\n"
            f"Bottleneck Regions:     {len(self.bottleneck_regions)}\n\n"
            "Recommendations:\n"
            "- High pressure often indicates the need to split larger expressions\n"
            "- Prefer smaller variable lifetimes and reuse registers when possible\n"
            "- Consider hot-spill placement for loop-heavy code\n"
        )


@dataclass
class DynamicSpillAllocator:
    """Conservative spill-slot allocator that matches the NoBASIC compiler's spill policy."""
    spill_slots: Dict[str, int]
    access_counts: Dict[str, int] = field(default_factory=Counter)
    debug: bool = False
    zero_page_base: int = 0x0080
    zero_page_size: int = 128

    def __post_init__(self):
        self.allocations: Dict[str, int] = {}
        self.next_zp_addr = self.zero_page_base

    def allocate(self) -> Dict[str, int]:
        if not self.access_counts:
            return {}

        ranked = sorted(self.access_counts.items(), key=lambda item: item[1], reverse=True)
        for var, _ in ranked:
            if var not in self.spill_slots:
                continue
            if self.next_zp_addr + 2 > self.zero_page_base + self.zero_page_size:
                break
            self.allocations[var] = self.next_zp_addr
            self.next_zp_addr += 2

        if self.debug:
            print(f"[SPILL] allocated {len(self.allocations)} hot spill slots")
        return self.allocations

    def get_address(self, var: str) -> Optional[int]:
        return self.allocations.get(var)


@dataclass
class StrengthReducer:
    """Reduce multiplication by powers of 2 to left shifts for better performance."""
    debug: bool = False

    @staticmethod
    def _is_power_of_two(n: int) -> bool:
        """Check if n is a power of 2."""
        return n > 0 and (n & (n - 1)) == 0

    @staticmethod
    def _log2(n: int) -> int:
        """Calculate log2 of a power of 2."""
        return (n - 1).bit_length()

    def reduce(self, expr: Any) -> Any:
        """Reduce multiplication by powers of 2 to shifts in the AST."""
        result = self._reduce_node(expr)
        if self.debug and result is not expr:
            print(f"[STRENGTH_RED] Reduced multiplication by power of 2")
        return result

    def _reduce_node(self, expr: Any) -> Any:
        """Recursively reduce expressions in the AST."""
        if isinstance(expr, BinaryOp):
            left = self._reduce_node(expr.left)
            right = self._reduce_node(expr.right)

            # Try strength reduction on multiplication by powers of 2
            if expr.op == '*':
                reduction = self._try_reduce_multiply(left, right)
                if reduction is not None:
                    return reduction

            return BinaryOp(left, expr.op, right)

        elif isinstance(expr, UnaryOp):
            return UnaryOp(expr.op, self._reduce_node(expr.right))

        elif isinstance(expr, PostfixOp):
            return PostfixOp(self._reduce_node(expr.left), expr.op)

        elif isinstance(expr, FuncCall):
            return FuncCall(expr.name, [self._reduce_node(arg) for arg in expr.args])

        elif isinstance(expr, Cast):
            return Cast(expr.target_type, self._reduce_node(expr.expr))

        elif isinstance(expr, list):
            return [self._reduce_node(item) for item in expr]

        elif isinstance(expr, VarDecl):
            if expr.value is not None:
                expr.value = self._reduce_node(expr.value)
            return expr

        elif isinstance(expr, Assignment):
            expr.value = self._reduce_node(expr.value)
            return expr

        elif isinstance(expr, Return):
            if expr.value is not None:
                expr.value = self._reduce_node(expr.value)
            return expr

        elif isinstance(expr, If):
            expr.cond = self._reduce_node(expr.cond)
            expr.then_body = self._reduce_node(expr.then_body)
            if expr.else_body:
                expr.else_body = self._reduce_node(expr.else_body)
            return expr

        elif isinstance(expr, While):
            expr.cond = self._reduce_node(expr.cond)
            expr.body = self._reduce_node(expr.body)
            return expr

        elif isinstance(expr, DoWhile):
            expr.cond = self._reduce_node(expr.cond)
            expr.body = self._reduce_node(expr.body)
            return expr

        elif isinstance(expr, For):
            if expr.init is not None:
                expr.init = self._reduce_node(expr.init)
            if expr.cond is not None:
                expr.cond = self._reduce_node(expr.cond)
            if expr.update is not None:
                expr.update = self._reduce_node(expr.update)
            expr.body = self._reduce_node(expr.body)
            return expr

        elif isinstance(expr, Switch):
            expr.expr = self._reduce_node(expr.expr)
            for case in expr.cases:
                case.value = self._reduce_node(case.value)
                case.body = self._reduce_node(case.body)
            if expr.default_body:
                expr.default_body = self._reduce_node(expr.default_body)
            return expr

        return expr

    def _try_reduce_multiply(self, left: Any, right: Any) -> Optional[BinaryOp]:
        """Try to reduce left * right to left << log2(right) when right is a power of 2."""
        # Check if right operand is a power of 2 literal
        right_val = _num_value(right)
        if right_val is not None and self._is_power_of_two(right_val):
            shift_amount = self._log2(right_val)
            return BinaryOp(left, "<<", Number(str(shift_amount)))

        # Check if left operand is a power of 2 literal (commutative)
        left_val = _num_value(left)
        if left_val is not None and self._is_power_of_two(left_val):
            shift_amount = self._log2(left_val)
            return BinaryOp(right, "<<", Number(str(shift_amount)))

        return None


def get_optimization_config() -> Dict[str, Any]:
    """Get default optimization configuration matching the NoBASIC compiler."""
    return {
        'enable_graph_coloring': True,
        'enable_hot_spill_migration': True,
        'enable_register_pressure_monitoring': True,
        'enable_dynamic_spill_allocation': True,
        'enable_expression_simplification': True,
        'enable_function_inlining': True,
        'enable_strength_reduction': True,
        'inlining_max_statements': 8,
        'inlining_min_call_sites': 2,
        'debug_optimizations': False,
        'pressure_threshold_percentile': 75.0,
        'zero_page_base': 0x0080,
        'zero_page_size': 128,
        'spill_base': 0x7000,
        'spill_size': 512,
    }
