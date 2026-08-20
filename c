import sys, os, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from astrid.lexer.lexer import Lexer
from astrid.parser.parser import Parser
from astrid.codegen.codegen import CodeGenerator

src = 'int main() { int x = 10; x *= 2; x /= 4; return x; }'

lexer = Lexer(src)
tokens = lexer.tokenize()
parser = Parser(tokens)
ast = parser.parse()

cg = CodeGenerator(enable_optimizations=True, enable_peephole=True, enable_live_range_scheduling=True)
asm = cg.generate(ast)
print('=== OPTIMIZED compound_assignment ===')
for i, line in enumerate(asm):
    print(f'{i:4d}: {line}')
