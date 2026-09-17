import sys
from pathlib import Path
sys.path.insert(0, str(Path('.').resolve()))
sys.path.insert(0, str(Path('astrid').resolve()))
from astrid.lexer.lexer import Lexer
from astrid.parser.parser import Parser
from astrid.codegen.codegen import CodeGenerator
from astrid.compiler_api import compile_astrid
src = Path('astrid/NovaDOS/src/fs/_diag.ast')
src.write_text('include "ndf.ast";\nint count;\nint first_name_byte;\nvoid main() {\n    ndf_format(1);\n    ndf_add(1, 66, 83, 89, 116, 0, 12);\n    count = ndf_entry_count(1);\n    first_name_byte = ndf_name_byte(1, 0, 0);\n}\n', encoding='utf-8')
asm = src.with_suffix('.asm')
compile_astrid(str(src), str(asm), verbose=True, memory_layout='bank-safe', log=None)
for i, ln in enumerate(asm.read_text().splitlines()):
    if any(k in ln for k in ('ndf_add','ndf_name_byte','ndf_entry_base','ndf_window','gvar_','ndf_entry')):
        print(f'{i+1:4d}: {ln}')
