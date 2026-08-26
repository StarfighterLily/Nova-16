"""Programmatic compile API for the Astrid language.

Mirrors ``nobasic_compiler.compile_nobasic`` so the MCP server can drive
Astrid compilation exactly like NoBASIC compilation: an optional log
callback for progress messages and an in-process assemble callback.
"""
import os
import sys

# The astrid package lives one level up from this file's directory; when
# imported as ``astrid.compiler_api`` the parent (repo root) is already on
# sys.path, but keep a direct-run fallback working too.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from astrid.lexer.lexer import Lexer  # noqa: E402
from astrid.parser.parser import Parser  # noqa: E402
from astrid.codegen.codegen import CodeGenerator  # noqa: E402

__all__ = ['compile_astrid']

ASTRID_EXTENSIONS = ('.ast', '.as', '.astrid')


def compile_astrid(source_file: str, output_file: str = None,
                   verbose: bool = False,
                   enable_optimizations: bool = True,
                   debug_optimizations: bool = False,
                   enable_peephole: bool = True,
                   enable_live_range_scheduling: bool = True,
                   emit_all_builtins: bool = False,
                   log=print,
                   assemble_callback=None) -> bool:
    """Compile an Astrid source file to Nova-16 assembly (and optionally binary).

    Args:
        source_file: Path to the .ast / .as / .astrid source file
        output_file: Path to the output assembly file (defaults to .asm)
        verbose: Enable verbose progress messages
        enable_optimizations: Master switch for the optimization passes
        debug_optimizations: Optimization debug output
        enable_peephole: Peephole optimizer toggle
        enable_live_range_scheduling: Live-range scheduler toggle
        emit_all_builtins: Emit every builtin stub regardless of usage
        log: Optional callback for compiler messages; defaults to print
        assemble_callback: Optional callback invoked as
            ``assemble_callback(assembly_path: Path, verbose: bool, emit)``
            to produce the .bin in-process (mirrors the NoBASIC contract).

    Returns:
        True on success. Raises on compile errors so callers can surface
        diagnostics (the CLI entry point catches and prints them itself).
    """
    from pathlib import Path

    def emit(message: str) -> None:
        if log is not None:
            log(message)

    source_path = Path(source_file)
    if not source_path.exists():
        raise FileNotFoundError(f"Astrid source not found: {source_path}")
    if source_path.suffix.lower() not in ASTRID_EXTENSIONS:
        raise ValueError(
            f"Source file must have one of {ASTRID_EXTENSIONS} extensions, "
            f"got '{source_path.suffix}'")

    if output_file is None:
        output_path = source_path.with_suffix('.asm')
    else:
        output_path = Path(output_file)

    with open(source_path, 'r', encoding='utf-8') as f:
        source_code = f.read()

    emit(f"Compiling {source_path} -> {output_path}")

    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    if verbose:
        emit(f"Lexer complete: {len(tokens)} tokens")

    # source_path anchors include/inherits directives to the source file's
    # directory (same rule as the CLI).
    parser = Parser(tokens, source_path=str(source_path))
    ast = parser.parse()
    if verbose:
        emit(f"Parser complete: {len(ast.functions)} functions, "
             f"{len(ast.globals)} globals")

    codegen = CodeGenerator(
        enable_optimizations=enable_optimizations,
        debug_optimizations=debug_optimizations,
        enable_peephole=enable_peephole,
        enable_live_range_scheduling=enable_live_range_scheduling,
        emit_all_builtins=emit_all_builtins,
    )
    assembly = codegen.generate(ast)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(assembly))
    emit(f"Assembly written to {output_path}")

    if assemble_callback is not None:
        ok = assemble_callback(output_path, verbose, emit)
        if not ok:
            raise RuntimeError(
                f"Assembler callback failed for {output_path}")
        binary_path = output_path.with_suffix('.bin')
        emit(f"Binary written to {binary_path}")

    return True
