#!/usr/bin/env python3
"""
NoBASIC Compiler
Compiles NoBASIC source code to Nova-16 assembly and binary.
"""

import sys
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, List, Optional, Tuple

# Add the compiler directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'compiler'))

from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser
from compiler.semantic.analyzer import SemanticAnalyzer
from compiler.codegen.generator import CodeGenerator
from compiler.utils.error import CodeGenError, CompilerError


INCLUDE_PATTERN = re.compile(r'^\s*(?:#include|include)\s+"([^"]+)"\s*$', re.IGNORECASE)
MAX_INCLUDE_DEPTH = 32
SourceLineMap = List[Tuple[str, int]]


@dataclass
class FrontendPipelineResult:
    """Artifacts produced by the shared NoBASIC frontend pipeline."""

    resolved_source_file: Path
    source: str
    line_map: SourceLineMap
    tokens: List[Any]
    ast: Any
    analyzer: SemanticAnalyzer


def _is_legacy_output_file_arg(arg: str) -> bool:
    """Return True when a positional CLI argument looks like an assembly output path."""
    return Path(arg).suffix.lower() == '.asm'


def _strip_line_comment(line: str) -> str:
    """Remove trailing // comments while preserving quoted strings."""
    in_string = False
    escaped = False

    for index, char in enumerate(line):
        if escaped:
            escaped = False
            continue

        if char == '\\' and in_string:
            escaped = True
            continue

        if char == '"':
            in_string = not in_string
            continue

        if not in_string and char == '/' and index + 1 < len(line) and line[index + 1] == '/':
            return line[:index]

    return line


def _normalized_directive_line(line: str) -> str:
    """Return a trimmed directive line with trailing comments removed."""
    return _strip_line_comment(line).strip()


def resolve_source_file_path(source_file: str) -> Path:
    """Resolve top-level source file from cwd or NoBASIC directory."""
    source_path = Path(source_file)
    candidates = [source_path]

    if not source_path.is_absolute():
        compiler_dir = Path(__file__).resolve().parent
        candidates.append(compiler_dir / source_path)

    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()

    raise CompilerError(
        f"Source file not found: {source_file}",
        source_file,
        1,
        1,
    )


def _resolve_includes_from_file(
    file_path: Path,
    include_stack=None,
    max_depth: int = MAX_INCLUDE_DEPTH,
) -> Tuple[str, SourceLineMap]:
    """Resolve Include directives recursively and return flattened source text + line map."""
    if include_stack is None:
        include_stack = []

    resolved_path = file_path.resolve()

    if len(include_stack) >= max_depth:
        raise CompilerError(
            f"Maximum include depth ({max_depth}) exceeded while processing '{resolved_path.name}'",
            str(resolved_path),
            1,
            1,
        )

    if resolved_path in include_stack:
        cycle = " -> ".join([p.name for p in include_stack] + [resolved_path.name])
        raise CompilerError(
            f"Include cycle detected: {cycle}",
            str(resolved_path),
            1,
            1,
        )

    if not resolved_path.exists():
        raise CompilerError(
            f"Included file not found: {resolved_path}",
            str(file_path),
            1,
            1,
        )

    try:
        with open(resolved_path, 'r') as f:
            source = f.read()
    except OSError as exc:
        raise CompilerError(f"Failed to read include file: {exc}", str(resolved_path), 1, 1)

    include_stack.append(resolved_path)
    output_lines = []
    line_map: SourceLineMap = []
    in_asm_block = False

    try:
        for line_num, line in enumerate(source.splitlines(keepends=True), start=1):
            normalized = _normalized_directive_line(line)
            lowered = normalized.lower()

            if not in_asm_block:
                include_match = INCLUDE_PATTERN.match(normalized)
                if include_match:
                    include_target = include_match.group(1)
                    include_path = (resolved_path.parent / include_target).resolve()
                    if not include_path.exists():
                        raise CompilerError(
                            f"Included file not found: {include_target}",
                            str(resolved_path),
                            line_num,
                            1,
                        )
                    included_source, included_map = _resolve_includes_from_file(include_path, include_stack, max_depth)
                    output_lines.append(included_source)
                    line_map.extend(included_map)
                    # Preserve statement boundaries across include boundaries even when
                    # included files omit a trailing newline.
                    if included_source and not included_source.endswith("\n"):
                        output_lines.append("\n")
                        if included_map:
                            line_map.append(included_map[-1])
                        else:
                            line_map.append((str(include_path), 1))
                    continue

                if lowered == "asm":
                    in_asm_block = True
            else:
                if lowered == "end":
                    in_asm_block = False

            output_lines.append(line)
            line_map.append((str(resolved_path), line_num))

        return ''.join(output_lines), line_map
    finally:
        include_stack.pop()


def preprocess_source(source_file: str) -> Tuple[str, SourceLineMap]:
    """Load source file and expand include directives, returning source + line map."""
    resolved_source_file = resolve_source_file_path(source_file)
    return _resolve_includes_from_file(resolved_source_file)


def run_frontend_pipeline(
    source_file: str,
    lexer_factory: Optional[Callable[[], Any]] = None,
    parser_factory: Optional[Callable[[], Any]] = None,
    analyzer_factory: Optional[Callable[[], SemanticAnalyzer]] = None,
) -> FrontendPipelineResult:
    """Run include preprocessing, lexing, parsing, and semantic analysis."""
    lexer_factory = lexer_factory or Lexer
    parser_factory = parser_factory or Parser
    analyzer_factory = analyzer_factory or SemanticAnalyzer

    resolved_source_file = resolve_source_file_path(source_file)
    source, line_map = _resolve_includes_from_file(resolved_source_file)

    try:
        lexer = lexer_factory()
        tokens = lexer.tokenize(source, str(resolved_source_file))

        parser = parser_factory()
        ast = parser.parse(tokens, str(resolved_source_file))

        analyzer = analyzer_factory()
        analyzer.analyze(ast, str(resolved_source_file))
    except CompilerError as error:
        raise remap_compiler_error(error, str(resolved_source_file), line_map) from error

    return FrontendPipelineResult(
        resolved_source_file=resolved_source_file,
        source=source,
        line_map=line_map,
        tokens=tokens,
        ast=ast,
        analyzer=analyzer,
    )


def _to_canonical_path(path_value: str) -> Optional[Path]:
    """Best-effort conversion of a path string into an absolute canonical Path."""
    if not path_value or path_value == "<stdin>":
        return None
    try:
        return Path(path_value).resolve()
    except (OSError, RuntimeError, ValueError):
        return None


def remap_compiler_error(error: CompilerError, source_file: str, line_map: SourceLineMap) -> CompilerError:
    """Map flattened-source diagnostics back to original include file/line locations."""
    if error.line <= 0 or error.line > len(line_map):
        return error

    main_file = _to_canonical_path(source_file)
    error_file = _to_canonical_path(error.filename)

    if main_file is None or error_file is None or error_file != main_file:
        return error

    mapped_file, mapped_line = line_map[error.line - 1]
    return error.__class__(error.message, mapped_file, mapped_line, error.column)


def generate_with_error_remapping(generator: Any, ast: Any, source_file: str, line_map: SourceLineMap) -> str:
    """Run code generation while mapping include-expanded diagnostics back to the source file."""
    try:
        return generator.generate(ast)
    except CodeGenError as error:
        line = error.line if error.line > 0 else 1
        column = error.column if error.column > 0 else 1
        normalized = error
        if error.filename == "<stdin>":
            normalized = CodeGenError(error.message, source_file, line, column)
        raise remap_compiler_error(normalized, source_file, line_map) from error
    except CompilerError as error:
        raise remap_compiler_error(error, source_file, line_map) from error
    except RuntimeError as error:
        raise CodeGenError(str(error), source_file, 1, 1) from error


def _remove_stale_binary(binary_file: Path) -> None:
    """Ensure the assembler must produce a fresh binary for the current compile."""
    try:
        binary_file.unlink(missing_ok=True)
    except OSError as exc:
        raise CompilerError(f"Failed to remove stale binary '{binary_file}': {exc}", str(binary_file), 1, 1)


def _prepare_output_file_path(output_file: Optional[str], resolved_source_file: Path) -> Path:
    """Resolve the assembly output path and create its parent directory when needed."""
    output_path = resolved_source_file.with_suffix('.asm') if output_file is None else Path(output_file)

    if output_path.suffix.lower() != '.asm':
        raise CompilerError(
            f"Output file must have .asm extension: {output_path}",
            str(output_path),
            1,
            1,
        )

    parent_dir = output_path.parent
    if parent_dir and not parent_dir.exists():
        try:
            parent_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise CompilerError(f"Failed to create output directory '{parent_dir}': {exc}", str(output_path), 1, 1)

    return output_path


def compile_nobasic(source_file: str, output_file: str = None, verbose: bool = False, 
                    enable_optimizations: bool = True, debug_optimizations: bool = False,
                    enable_peephole: bool = False, enable_live_range_scheduling: bool = False,
                    log: Optional[Callable[[str], None]] = print,
                    assemble_callback: Optional[Callable[[Path, bool, Callable[[str], None]], bool]] = None):
    """
    Compile a NoBASIC source file to Nova-16 assembly and binary.

    Args:
        source_file: Path to the .nobasic source file
        output_file: Path to the output .asm file (optional)
        verbose: Enable verbose output
        enable_optimizations: Enable compiler optimizations (default: True)
        debug_optimizations: Enable optimization debug output (default: False)
        enable_peephole: Enable peephole optimizer (default: False)
        enable_live_range_scheduling: Enable live range scheduler (default: False)
        log: Optional callback for compiler messages; defaults to print
        assemble_callback: Optional callback to assemble the generated .asm file in-process
    """
    line_map: SourceLineMap = []
    resolved_source_file: Optional[Path] = None

    def emit(message: str) -> None:
        if log is not None:
            log(message)

    try:
        pipeline = run_frontend_pipeline(source_file)
        resolved_source_file = pipeline.resolved_source_file
        line_map = pipeline.line_map

        if verbose:
            emit(f"Compiling {source_file}...")
            if enable_optimizations:
                emit("Optimizations: ENABLED")
                if enable_peephole:
                    emit("  - Peephole optimization: ENABLED")
                if enable_live_range_scheduling:
                    emit("  - Live range scheduling: ENABLED")
            else:
                emit("Optimizations: DISABLED")

        if verbose:
            emit(f"Lexical analysis complete: {len(pipeline.tokens)} tokens")

        if verbose:
            emit("Parsing complete")

        if verbose:
            emit("Semantic analysis complete")

        # Code generation with optimizations configuration
        generator = CodeGenerator(
            debug_allocation=debug_optimizations,
            enable_optimizations=enable_optimizations,
            enable_peephole=enable_peephole,
            enable_live_range_scheduling=enable_live_range_scheduling
        )
        if debug_optimizations:
            generator.opt_config['debug_optimizations'] = True
        assembly = generate_with_error_remapping(
            generator,
            pipeline.ast,
            str(resolved_source_file),
            line_map,
        )

        if verbose:
            emit("Code generation complete")

        # Determine output file and ensure the destination exists.
        output_path = _prepare_output_file_path(output_file, resolved_source_file)

        # Write assembly
        with open(output_path, 'w') as f:
            f.write(assembly)

        if verbose:
            emit(f"Assembly written to {output_path}")

        binary_file = output_path.with_suffix('.bin')
        _remove_stale_binary(binary_file)

        if verbose:
            emit(f"Assembling {output_path} to {binary_file}...")

        if assemble_callback is not None:
            assembly_succeeded = assemble_callback(output_path, verbose, emit)
            if not assembly_succeeded:
                emit(f"Assembly failed for {output_path}")
                sys.exit(1)
        else:
            # Assemble to binary using nova_assembler.py
            assembler_path = os.path.join(os.path.dirname(__file__), '..', 'nova_assembler.py')

            # Run the assembler
            try:
                result = subprocess.run([
                    sys.executable, assembler_path, str(output_path)
                ], capture_output=True, text=True)
            except OSError as exc:
                emit(f"Assembly failed: could not execute assembler '{assembler_path}': {exc}")
                sys.exit(1)

            return_code = getattr(result, 'returncode', 0)
            if return_code != 0:
                emit(f"Assembly failed with exit code {return_code}")
                if result.stderr:
                    emit(f"Assembler stderr: {result.stderr}")
                if result.stdout:
                    emit(f"Assembler output: {result.stdout}")
                sys.exit(1)

            # Check if binary was created (assembler may output to stdout/stderr but still succeed)
            if not binary_file.exists():
                emit(f"Assembly failed: {result.stderr}")
                if result.stdout:
                    emit(f"Assembler output: {result.stdout}")
                sys.exit(1)

        if not binary_file.exists():
            emit(f"Binary file not created at {binary_file}")
            sys.exit(1)

        if verbose:
            emit(f"Binary written to {binary_file}")

        emit(f"Compilation successful: {output_path} and {binary_file}")

    except CompilerError as e:
        main_source_for_remap = str(resolved_source_file) if resolved_source_file is not None else source_file
        mapped_error = remap_compiler_error(e, main_source_for_remap, line_map)
        emit(f"Compilation error: {mapped_error}")
        sys.exit(1)
    except Exception as e:
        import traceback
        emit(f"Unexpected error: {e}")
        emit(traceback.format_exc())
        sys.exit(1)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python nobasic_compiler.py <source.nobasic> [options]")
        print()
        print("Options:")
        print("  --output <file.asm>        Output assembly file (default: same as source with .asm)")
        print("  --verbose                  Enable verbose output")
        print("  --enable-optimizations     Enable compiler optimizations (default: enabled)")
        print("  --disable-optimizations    Disable compiler optimizations")
        print("  --enable-peephole          Enable peephole optimizer (default: disabled)")
        print("  --disable-peephole         Disable peephole optimizer")
        print("  --enable-live-range        Enable live range scheduling (default: disabled)")
        print("  --disable-live-range       Disable live range scheduling")
        print("  --debug-optimizations      Enable optimization debug output")
        sys.exit(1)

    source_file = sys.argv[1]
    output_file = None
    verbose = False
    enable_optimizations = True
    debug_optimizations = False
    enable_peephole = False
    enable_live_range_scheduling = False

    # Parse command line arguments
    i = 2
    while i < len(sys.argv):
        arg = sys.argv[i]
        
        if arg == "--verbose":
            verbose = True
        elif arg == "--enable-optimizations":
            enable_optimizations = True
        elif arg == "--disable-optimizations":
            enable_optimizations = False
        elif arg == "--enable-peephole":
            enable_peephole = True
        elif arg == "--disable-peephole":
            enable_peephole = False
        elif arg == "--enable-live-range":
            enable_live_range_scheduling = True
        elif arg == "--disable-live-range":
            enable_live_range_scheduling = False
        elif arg == "--debug-optimizations":
            debug_optimizations = True
            enable_optimizations = True  # Debug implies optimizations enabled
        elif arg == "--output":
            if i + 1 < len(sys.argv):
                output_file = sys.argv[i + 1]
                i += 1
            else:
                print("Error: --output requires an argument")
                sys.exit(1)
        elif _is_legacy_output_file_arg(arg):
            # Legacy support for positional output file
            output_file = arg
        else:
            print(f"Unknown option: {arg}")
            sys.exit(1)
        
        i += 1

    if debug_optimizations:
        enable_optimizations = True

    compile_nobasic(source_file, output_file, verbose, enable_optimizations, debug_optimizations,
                    enable_peephole, enable_live_range_scheduling)


if __name__ == "__main__":
    main()