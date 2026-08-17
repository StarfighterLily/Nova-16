# Astrid Compiler CLI: Compile Astrid source to Nova-16 assembly
import sys
import os

# Add parent directory to path so astrid package can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from astrid.lexer.lexer import Lexer
from astrid.parser.parser import Parser
from astrid.codegen.codegen import CodeGenerator

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Astrid Compiler: Compile Astrid source to Nova-16 assembly")
    parser.add_argument("source", nargs="?", help="Astrid source file (.as or .astrid)")
    parser.add_argument("-o", "--output", help="Output assembly file (.asm)")
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

        parser = Parser(tokens)
        ast = parser.parse()
        print(f"✓ Parser: Generated AST with {len(ast.functions)} functions")

        codegen = CodeGenerator(
            enable_optimizations=args.enable_optimizations,
            enable_peephole=enable_peephole,
            enable_live_range_scheduling=enable_live_range_scheduling,
            debug_optimizations=args.debug_optimizations,
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

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
