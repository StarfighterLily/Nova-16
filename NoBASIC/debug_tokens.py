from compiler.lexer.lexer import Lexer

source = "dim_val = dim(L1)"
lexer = Lexer()
tokens = lexer.tokenize(source)
for token in tokens:
    print(f"{token.type} {token.lexeme}")