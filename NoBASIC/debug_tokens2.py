from compiler.lexer.lexer import Lexer

source = 'Disp "You pressed: " + str(key)'
lexer = Lexer()
tokens = lexer.tokenize(source)
for token in tokens:
    print(f"{token.type} {token.lexeme}")