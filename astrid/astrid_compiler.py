# Astrid Compiler CLI: Compile Astrid source to Nova-16 assembly
import sys
import os

# Add parent directory to path so astrid package can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from astrid.lexer.lexer import Lexer
from astrid.parser.parser import Parser
from astrid.codegen.codegen import CodeGenerator
from astrid.errors import CompileError

def main():
    import argparse
    # Progress markers (✓/✗) are non-ASCII; when stdout is a pipe (CI, log
    # capture) Python falls back to the cp1252 locale codec and printing
    # them raises UnicodeEncodeError. Force UTF-8 with a safe fallback.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
    parser = argparse.ArgumentParser(description="Astrid Compiler: Compile Astrid source to Nova-16 assembly")
    parser.add_argument("source", nargs="?", help="Astrid source file (.as or .astrid)")
    parser.add_argument("-o", "--output", help="Output assembly file (.asm)")
    parser.add_argument("--traceback", action="store_true",
                        help="Show the full Python traceback even for "
                             "diagnosed compiler errors (useful when "
                             "reporting compiler bugs)")
    parser.add_argument("--enable-optimizations", action="store_true", dest="enable_optimizations",
                        default=True, help="Enable compiler optimizations (default: enabled)")
    parser.add_argument("--disable-optimizations", action="store_false", dest="enable_optimizations",
                        help="Disable compiler optimizations")
    parser.add_argument("--enable-peephole", action="store_true", dest="enable_peephole",
                        default=True, help="Enable peephole optimizer (default: enabled)")
    parser.add_argument("--disable-peephole", action="store_false", dest="enable_peephole",
                        help="Disable peephole optimizer")
    parser.add_argument("--enable-live-range-scheduling", action="store_true",
                        dest="enable_live_range_scheduling", default=True,
                        help="Enable live-range scheduling (default: enabled)")
    parser.add_argument("--disable-live-range-scheduling", action="store_false",
                        dest="enable_live_range_scheduling",
                        help="Disable live-range scheduling")
    parser.add_argument("--debug-optimizations", action="store_true",
                        help="Enable optimization debug output")
    parser.add_argument("--emit-all-builtins", action="store_true", dest="emit_all_builtins",
                        help="Emit every builtin implementation regardless of usage "
                             "(legacy behavior; default is lazy, usage-driven emission)")
    args = parser.parse_args()

    if args.debug_optimizations:
        args.enable_optimizations = True

    enable_peephole = bool(args.enable_peephole)
    enable_live_range_scheduling = bool(args.enable_live_range_scheduling)

    if args.source:
        with open(args.source, "r", encoding="utf-8") as f:
            source_code = f.read()
        out_file = args.output or os.path.splitext(args.source)[0] + ".asm"
    else:
        print("Reading Astrid source from stdin. Press Ctrl+D (Unix) or Ctrl+Z (Windows) to end input.")
        source_code = sys.stdin.read()
        out_file = args.output or "out.asm"

    print(f"=== ASTRID COMPILER ===")
    print(f"Compiling: {args.source or 'stdin'} -> {out_file}")

    try:
        lexer = Lexer(source_code)
        tokens = lexer.tokenize()
        print(f"✓ Lexer: Generated {len(tokens)} tokens")

        # source_path anchors include/inherits directives to the source
        # file's directory (stdin compiles resolve against the CWD).
        parser = Parser(tokens, source_path=args.source)
        ast = parser.parse()
        print(f"✓ Parser: Generated AST with {len(ast.functions)} functions, "
              f"{len(ast.globals)} globals")

        codegen = CodeGenerator(
            enable_optimizations=args.enable_optimizations,
            enable_peephole=enable_peephole,
            enable_live_range_scheduling=enable_live_range_scheduling,
            debug_optimizations=args.debug_optimizations,
            emit_all_builtins=args.emit_all_builtins,
        )
        assembly = codegen.generate(ast)
        print(f"✓ Code Generator: Successfully generated assembly code")
        if args.enable_optimizations:
            print("✓ Optimizations: ENABLED")
        else:
            print("✓ Optimizations: DISABLED")
        if enable_peephole:
            print(f"✓ Peephole Optimizer: ENABLED")
        else:
            print(f"✓ Peephole Optimizer: DISABLED")
        if enable_live_range_scheduling:
            print("✓ Live-range scheduling: ENABLED")
        else:
            print("✓ Live-range scheduling: DISABLED")

        with open(out_file, "w", encoding="utf-8") as f:
            f.write('\n'.join(assembly))
        print(f"✓ Assembly saved to {out_file}")

    except CompileError as e:
        # Diagnosed compiler error: the exception renders the full
        # diagnostic (message, file:line:col, source snippet, hint), so
        # print it cleanly instead of a Python traceback -- the user's
        # code is wrong, not the compiler (report bugs with --traceback).
        print(f"✗ Compilation failed:\n{e}", file=sys.stderr)
        # Return (not sys.exit) so in-process callers (tests, tools that
        # import main) can inspect the exit code without catching
        # SystemExit; the __main__ entry point turns it into a process
        # exit code.
        return 1

    except Exception as e:
        # Undiagnosed internal error: show a concise summary plus the
        # traceback (the compiler itself has a bug here; the traceback is
        # the minimal bug report).
        print(f"✗ Internal compiler error: {e}", file=sys.stderr)
        if args.traceback:
            import traceback
            traceback.print_exc()
        else:
            print("  (run with --traceback to see the full traceback)",
                  file=sys.stderr)
        return 2

    return 0

if __name__ == "__main__":
    sys.exit(main())
