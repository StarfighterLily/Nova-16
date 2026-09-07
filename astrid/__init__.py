# Astrid Language for Nova-16
# A high-level language compiler targeting the Nova-16 CPU

__version__ = "0.1.0"

# Re-export key components for a tidy package API
from .lexer.lexer import Lexer, Token  # type: ignore
from .parser.parser import Parser, Program  # type: ignore
from .errors import (  # type: ignore
    CompileError, LexerError, ParserError, CodeGenError,
    did_you_mean, levenshtein,
)
from .codegen.codegen import CodeGenerator  # type: ignore
from .codegen.peephole import PeepholeOptimizer  # type: ignore
from .codegen.optimizations import (
    ExpressionSimplifier,
    FunctionInliner,
    RegisterColoringPass,
    HotSpillAnalyzer,
    RegisterPressureMonitor,
    DynamicSpillAllocator,
    get_optimization_config,
)  # type: ignore
from .codegen.live_range_scheduler import LiveRangeScheduler  # type: ignore

__all__ = [
    'Lexer', 'Token', 'Parser', 'Program', 'CodeGenerator',
    'CompileError', 'LexerError', 'ParserError', 'CodeGenError',
    'did_you_mean', 'levenshtein',
    'PeepholeOptimizer', 'ExpressionSimplifier', 'FunctionInliner',
    'RegisterColoringPass', 'HotSpillAnalyzer', 'RegisterPressureMonitor',
    'DynamicSpillAllocator', 'LiveRangeScheduler', 'get_optimization_config',
]