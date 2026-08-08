
# Astrid Compiler CLI: Compile Astrid source to Nova-16 assembly
import sys
import os
from astrid_lexer import Lexer
from astrid_parser import Parser
from astrid_codegen import CodeGenerator

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Astrid Compiler: Compile Astrid source to Nova-16 assembly")
    parser.add_argument("source", nargs="?", help="Astrid source file (.as or .astrid)")
    parser.add_argument("-o", "--output", help="Output assembly file (.asm)")
    args = parser.parse_args()

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

        codegen = CodeGenerator()
        assembly = codegen.generate(ast)
        print(f"✓ Code Generator: Successfully generated assembly code")

        with open(out_file, "w", encoding="utf-8") as f:
            f.write('\n'.join(assembly))
        print(f"✓ Assembly saved to {out_file}")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
