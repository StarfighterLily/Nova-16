from compiler.lexer.lexer import Lexer
from compiler.lexer.tokens import TokenType
from compiler.utils.error import LexerError

lexer = Lexer()
try:
    tokens = lexer.tokenize('12.34.56')
    print("Tokens:")
    for token in tokens:
        print(f'{token.type}: {repr(token.lexeme)} {repr(token.literal)}')
except LexerError as e:
    print(f"Error: {e}")