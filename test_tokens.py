from nobasic_lexer import Lexer
l = Lexer()
code = '''For X = 0 To 255
  For Y = 0 To 255
    COLOR_VAL = (X + Y) MOD 256
    PxlOn(Y, X, COLOR_VAL)
  Next Y
Next X'''
tokens = l.tokenize(code)
for i, t in enumerate(tokens):
    if t.type.name not in ['NEWLINE', 'EOF']:
        print(f'{i}: {t}')