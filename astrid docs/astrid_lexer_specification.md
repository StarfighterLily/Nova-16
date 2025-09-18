# Astrid Lexer Specification

## Overview

The Astrid lexer (tokenizer) is the first phase of the compiler pipeline, responsible for converting Astrid source code into a stream of tokens that the parser can understand. The lexer handles lexical analysis, including token recognition, whitespace handling, comment processing, and error reporting.

**Key Responsibilities:**
- Convert source code characters into tokens
- Handle indentation-based block structure (Python-inspired)
- Process comments and whitespace
- Report lexical errors with precise location information
- Support Unicode identifiers and string literals
- Handle hardware register keywords

## Token Categories

### Keywords

```python
# Core language keywords
KEYWORDS = {
    'def':      TokenType.DEF,
    'if':       TokenType.IF,
    'elif':     TokenType.ELIF,
    'else':     TokenType.ELSE,
    'for':      TokenType.FOR,
    'in':       TokenType.IN,
    'while':    TokenType.WHILE,
    'return':   TokenType.RETURN,
    'break':    TokenType.BREAK,
    'continue': TokenType.CONTINUE,
    'pass':     TokenType.PASS,
    'lambda':   TokenType.LAMBDA,
    'and':      TokenType.AND,
    'or':       TokenType.OR,
    'not':      TokenType.NOT,
    'True':     TokenType.TRUE,
    'False':    TokenType.FALSE,
    'None':     TokenType.NONE,
    'class':    TokenType.CLASS,
    'import':   TokenType.IMPORT,
    'from':     TokenType.FROM,
    'as':       TokenType.AS,
    'try':      TokenType.TRY,
    'except':   TokenType.EXCEPT,
    'finally':  TokenType.FINALLY,
    'raise':    TokenType.RAISE,
    'with':     TokenType.WITH,
    'global':   TokenType.GLOBAL,
    'nonlocal': TokenType.NONLOCAL,
    'assert':   TokenType.ASSERT,
    'yield':    TokenType.YIELD,
}

# Hardware register keywords
HARDWARE_KEYWORDS = {
    'VM':       TokenType.HW_VM,      # Video Mode
    'VL':       TokenType.HW_VL,      # Video Layer
    'VX':       TokenType.HW_VX,      # Video X coordinate
    'VY':       TokenType.HW_VY,      # Video Y coordinate
    'SA':       TokenType.HW_SA,      # Sound Address
    'SF':       TokenType.HW_SF,      # Sound Frequency
    'SV':       TokenType.HW_SV,      # Sound Volume
    'SW':       TokenType.HW_SW,      # Sound Waveform
    'TT':       TokenType.HW_TT,      # Timer Value
    'TM':       TokenType.HW_TM,      # Timer Match
    'TC':       TokenType.HW_TC,      # Timer Control
    'TS':       TokenType.HW_TS,      # Timer Speed
    'SP':       TokenType.HW_SP,      # Stack Pointer
    'FP':       TokenType.HW_FP,      # Frame Pointer
}
```

### Operators and Punctuation

```python
OPERATORS = {
    # Arithmetic
    '+':    TokenType.PLUS,
    '-':    TokenType.MINUS,
    '*':    TokenType.MULTIPLY,
    '/':    TokenType.DIVIDE,
    '%':    TokenType.MODULO,
    '**':   TokenType.POWER,
    '++':   TokenType.INCREMENT,
    '--':   TokenType.DECREMENT,

    # Comparison
    '==':   TokenType.EQUAL,
    '!=':   TokenType.NOT_EQUAL,
    '<':    TokenType.LESS,
    '<=':   TokenType.LESS_EQUAL,
    '>':    TokenType.GREATER,
    '>=':   TokenType.GREATER_EQUAL,

    # Assignment
    '=':    TokenType.ASSIGN,
    '+=':   TokenType.PLUS_ASSIGN,
    '-=':   TokenType.MINUS_ASSIGN,
    '*=':   TokenType.MULTIPLY_ASSIGN,
    '/=':   TokenType.DIVIDE_ASSIGN,
    '%=':   TokenType.MODULO_ASSIGN,

    # Bitwise
    '&':    TokenType.BIT_AND,
    '|':    TokenType.BIT_OR,
    '^':    TokenType.BIT_XOR,
    '~':    TokenType.BIT_NOT,
    '<<':   TokenType.SHIFT_LEFT,
    '>>':   TokenType.SHIFT_RIGHT,

    # Logical
    '&&':   TokenType.LOGICAL_AND,
    '||':   TokenType.LOGICAL_OR,

    # Other
    '.':    TokenType.DOT,
    ',':    TokenType.COMMA,
    ':':    TokenType.COLON,
    '(':    TokenType.LPAREN,
    ')':    TokenType.RPAREN,
    '[':    TokenType.LBRACKET,
    ']':    TokenType.RBRACKET,
    '{':    TokenType.LBRACE,
    '}':    TokenType.RBRACE,
    '@':    TokenType.AT,
    '->':   TokenType.ARROW,
}
```

### Literals and Identifiers

```python
# Literals
TokenType.INTEGER_LITERAL    # Decimal, hex (0x), binary (0b)
TokenType.FLOAT_LITERAL      # Floating point numbers
TokenType.STRING_LITERAL     # Single/double quoted strings
TokenType.CHAR_LITERAL       # Character literals

# Identifiers
TokenType.IDENTIFIER         # Variable/function names
TokenType.TYPE_IDENTIFIER    # Type names (start with capital)
```

## Lexer Architecture

### Core Components

```python
class AstridLexer:
    def __init__(self, source_code: str, filename: str = "<string>"):
        self.source = source_code
        self.filename = filename
        self.position = 0
        self.line = 1
        self.column = 1
        self.start = 0  # Start of current token
        self.tokens = []
        self.errors = []

        # Indentation tracking
        self.indent_stack = [0]
        self.indent_tokens = []

    def tokenize(self) -> List[Token]:
        """Main tokenization entry point"""
        while not self.is_at_end():
            if self.peek() == '\n':
                self.handle_newline()
            elif self.peek().isspace():
                self.skip_whitespace()
            elif self.peek() == '#':
                self.skip_comment()
            else:
                self.scan_token()

        # Add EOF token
        self.add_token(TokenType.EOF)
        return self.tokens

    def scan_token(self):
        """Scan the next token"""
        self.start = self.position
        char = self.advance()

        # Single character tokens
        if char == '(': self.add_token(TokenType.LPAREN)
        elif char == ')': self.add_token(TokenType.RPAREN)
        elif char == '[': self.add_token(TokenType.LBRACKET)
        elif char == ']': self.add_token(TokenType.RBRACKET)
        elif char == '{': self.add_token(TokenType.LBRACE)
        elif char == '}': self.add_token(TokenType.RBRACE)
        elif char == ',': self.add_token(TokenType.COMMA)
        elif char == '.': self.add_token(TokenType.DOT)
        elif char == ':': self.add_token(TokenType.COLON)
        elif char == '+': 
            if self.match('='): self.add_token(TokenType.PLUS_ASSIGN)
            elif self.match('+'): self.add_token(TokenType.INCREMENT)
            else: self.add_token(TokenType.PLUS)
        elif char == '-':
            if self.match('='): self.add_token(TokenType.MINUS_ASSIGN)
            elif self.match('-'): self.add_token(TokenType.DECREMENT)
            else: self.add_token(TokenType.MINUS)
        elif char == '*':
            if self.match('='): self.add_token(TokenType.MULTIPLY_ASSIGN)
            elif self.match('*'): self.add_token(TokenType.POWER)
            else: self.add_token(TokenType.MULTIPLY)
        elif char == '/':
            if self.match('='): self.add_token(TokenType.DIVIDE_ASSIGN)
            else: self.add_token(TokenType.DIVIDE)
        elif char == '%':
            if self.match('='): self.add_token(TokenType.MODULO_ASSIGN)
            else: self.add_token(TokenType.MODULO)
        elif char == '=':
            if self.match('='): self.add_token(TokenType.EQUAL)
            else: self.add_token(TokenType.ASSIGN)
        elif char == '!':
            if self.match('='): self.add_token(TokenType.NOT_EQUAL)
            else: self.error("Unexpected character: !")
        elif char == '<':
            if self.match('='): self.add_token(TokenType.LESS_EQUAL)
            elif self.match('<'): self.add_token(TokenType.SHIFT_LEFT)
            else: self.add_token(TokenType.LESS)
        elif char == '>':
            if self.match('='): self.add_token(TokenType.GREATER_EQUAL)
            elif self.match('>'): self.add_token(TokenType.SHIFT_RIGHT)
            else: self.add_token(TokenType.GREATER)
        elif char == '&':
            if self.match('&'): self.add_token(TokenType.LOGICAL_AND)
            else: self.add_token(TokenType.BIT_AND)
        elif char == '|':
            if self.match('|'): self.add_token(TokenType.LOGICAL_OR)
            else: self.add_token(TokenType.BIT_OR)
        elif char == '^': self.add_token(TokenType.BIT_XOR)
        elif char == '~': self.add_token(TokenType.BIT_NOT)
        elif char == '@': self.add_token(TokenType.AT)
        elif char == '"': self.scan_string('"')
        elif char == "'": self.scan_string("'")
        elif char.isdigit(): self.scan_number()
        elif char.isalpha() or char == '_': self.scan_identifier()
        else: self.error(f"Unexpected character: {char}")

    def match(self, expected: str) -> bool:
        """Check if next character matches expected, consume if so"""
        if self.is_at_end() or self.source[self.position] != expected:
            return False
        self.position += 1
        self.column += 1
        return True

    def peek(self) -> str:
        """Look at the current character without consuming it"""
        if self.is_at_end():
            return '\0'
        return self.source[self.position]

    def peek_next(self) -> str:
        """Look at the next character without consuming it"""
        if self.position + 1 >= len(self.source):
            return '\0'
        return self.source[self.position + 1]

    def advance(self) -> str:
        """Consume and return the current character"""
        char = self.peek()
        self.position += 1
        self.column += 1
        return char

    def is_at_end(self) -> bool:
        """Check if we've reached the end of source"""
        return self.position >= len(self.source)

    def add_token(self, type: TokenType, literal: Any = None):
        """Add a token to the token list"""
        text = self.source[self.start:self.position]
        token = Token(type, text, literal, self.line, self.column, self.filename)
        self.tokens.append(token)
```
```

### Token Structure

```python
@dataclass
class Token:
    type: TokenType
    lexeme: str
    literal: Any
    line: int
    column: int
    filename: str

    def __repr__(self):
        return f"Token({self.type}, '{self.lexeme}', {self.literal}, {self.line}:{self.column})"
```

## Indentation Handling

### Indentation-Based Blocks

Astrid uses Python-style indentation for block structure:

```python
def process_indentation(self):
    """Handle indentation changes for block structure"""
    indent_level = 0

    # Count leading spaces/tabs
    while not self.is_at_end() and self.peek() in ' \t':
        if self.peek() == ' ':
            indent_level += 1
        elif self.peek() == '\t':
            # Convert tabs to spaces (4 spaces per tab)
            indent_level = (indent_level // 4 + 1) * 4
        self.advance()

    # Compare with current indent level
    current_indent = self.indent_stack[-1]

    if indent_level > current_indent:
        # Indent: push new level and emit INDENT token
        self.indent_stack.append(indent_level)
        self.add_token(TokenType.INDENT)
    elif indent_level < current_indent:
        # Dedent: pop levels and emit DEDENT tokens
        # Must dedent to a previously seen indentation level
        if indent_level not in self.indent_stack:
            self.error(f"Inconsistent indentation: {indent_level} spaces. Expected one of: {self.indent_stack}")
            return
        
        while self.indent_stack and indent_level < self.indent_stack[-1]:
            self.indent_stack.pop()
            self.add_token(TokenType.DEDENT)
            
        # After dedenting, level should match
        if self.indent_stack and indent_level != self.indent_stack[-1]:
            self.error(f"Inconsistent indentation: {indent_level} spaces does not match any previous level")
    else:
        # Same level: emit NEWLINE token
        self.add_token(TokenType.NEWLINE)
```

### Indentation Rules

1. **Consistent Indentation**: Use either spaces or tabs, not both
2. **Indent Size**: 4 spaces recommended, but any consistent size works
3. **Block Structure**: Functions, classes, loops, conditionals use indentation
4. **Continuation Lines**: Use backslash `\` for line continuation
5. **Empty Lines**: Ignored for indentation calculation

## Token Recognition

### Identifier and Keyword Recognition

```python
def scan_identifier(self):
    """Scan identifiers and keywords"""
    start = self.position

    # First character must be letter or underscore
    if not (self.peek().isalpha() or self.peek() == '_'):
        self.error("Invalid identifier start character")
        return

    # Subsequent characters can be letters, digits, or underscores
    while not self.is_at_end() and (self.peek().isalnum() or self.peek() == '_'):
        self.advance()

    text = self.source[start:self.position]

    # Check if it's a keyword
    if text in KEYWORDS:
        self.add_token(KEYWORDS[text])
    elif text in HARDWARE_KEYWORDS:
        self.add_token(HARDWARE_KEYWORDS[text])
    else:
        # Check if it's a type identifier (starts with capital)
        if text[0].isupper():
            self.add_token(TokenType.TYPE_IDENTIFIER, text)
        else:
            self.add_token(TokenType.IDENTIFIER, text)
```

### Number Literal Recognition

```python
def scan_number(self):
    """Scan integer and float literals"""
    start = self.position
    has_dot = False

    # Handle hex literals (0x...)
    if self.peek() == '0' and not self.is_at_end() and self.peek_next() == 'x':
        self.advance()  # consume '0'
        self.advance()  # consume 'x'
        return self.scan_hex_number()

    # Handle binary literals (0b...)
    if self.peek() == '0' and not self.is_at_end() and self.peek_next() == 'b':
        self.advance()  # consume '0'
        self.advance()  # consume 'b'
        return self.scan_binary_number()

    # Regular decimal number
    while not self.is_at_end() and self.peek().isdigit():
        self.advance()

    # Check for decimal point
    if not self.is_at_end() and self.peek() == '.' and not self.is_at_end() and self.peek_next().isdigit():
        has_dot = True
        self.advance()  # consume '.'

        while not self.is_at_end() and self.peek().isdigit():
            self.advance()

    text = self.source[start:self.position]

    if has_dot:
        try:
            value = float(text)
            self.add_token(TokenType.FLOAT_LITERAL, value)
        except ValueError:
            self.error(f"Invalid float literal: {text}")
    else:
        try:
            value = int(text)
            self.add_token(TokenType.INTEGER_LITERAL, value)
        except ValueError:
            self.error(f"Invalid integer literal: {text}")
```

### String Literal Recognition

```python
def scan_string(self, quote_char: str):
    """Scan string literals with escape sequences"""
    start = self.position
    self.advance()  # consume opening quote

    result = []
    while not self.is_at_end() and self.peek() != quote_char:
        if self.peek() == '\\':
            # Handle escape sequences
            self.advance()  # consume '\'
            if self.is_at_end():
                self.error("Unterminated escape sequence")
                return

            escape_char = self.peek()
            self.advance()

            if escape_char == 'n':
                result.append('\n')
            elif escape_char == 't':
                result.append('\t')
            elif escape_char == 'r':
                result.append('\r')
            elif escape_char == '\\':
                result.append('\\')
            elif escape_char == '"':
                result.append('"')
            elif escape_char == "'":
                result.append("'")
            else:
                self.error(f"Invalid escape sequence: \\{escape_char}")
                return
        else:
            result.append(self.peek())
            self.advance()

    if self.is_at_end():
        self.error("Unterminated string literal")
        return

    self.advance()  # consume closing quote
    string_value = ''.join(result)
    self.add_token(TokenType.STRING_LITERAL, string_value)
```

## Error Handling

### Error Reporting

```python
def error(self, message: str):
    """Report a lexical error"""
    error_info = {
        'message': message,
        'line': self.line,
        'column': self.column,
        'filename': self.filename,
        'context': self.get_error_context()
    }
    self.errors.append(error_info)

def get_error_context(self) -> str:
    """Get source context around the error"""
    line_start = self.source.rfind('\n', 0, self.position) + 1
    line_end = self.source.find('\n', self.position)
    if line_end == -1:
        line_end = len(self.source)

    line_content = self.source[line_start:line_end]
    arrow = ' ' * (self.position - line_start) + '^'
    return f"{line_content}\n{arrow}"
```

### Error Recovery

```python
def recover_from_error(self):
    """Attempt to recover from lexical errors"""
    # Skip to next whitespace or punctuation
    while not self.is_at_end():
        char = self.peek()
        if char.isspace() or char in '+-*/=<>(){}[],.;:':
            break
        self.advance()

    # Continue tokenization
    if not self.is_at_end():
        self.scan_token()
```

## Testing and Validation

### Unit Tests

```python
def test_lexer_basic_tokens():
    """Test basic token recognition"""
    source = "def main():\n    x = 42\n    return x"
    lexer = AstridLexer(source)
    tokens = lexer.tokenize()

    expected_types = [
        TokenType.DEF, TokenType.IDENTIFIER, TokenType.LPAREN,
        TokenType.RPAREN, TokenType.COLON, TokenType.NEWLINE,
        TokenType.INDENT, TokenType.IDENTIFIER, TokenType.ASSIGN,
        TokenType.INTEGER_LITERAL, TokenType.NEWLINE,
        TokenType.RETURN, TokenType.IDENTIFIER, TokenType.NEWLINE,
        TokenType.DEDENT, TokenType.EOF
    ]

    assert len(tokens) == len(expected_types)
    for i, (token, expected) in enumerate(zip(tokens, expected_types)):
        assert token.type == expected, f"Token {i}: expected {expected}, got {token.type}"

def test_lexer_string_literals():
    """Test string literal handling"""
    source = '"hello world" \'single quotes\' "escape\\nsequences"'
    lexer = AstridLexer(source)
    tokens = lexer.tokenize()

    assert tokens[0].type == TokenType.STRING_LITERAL
    assert tokens[0].literal == "hello world"
    assert tokens[1].type == TokenType.STRING_LITERAL
    assert tokens[1].literal == "single quotes"
    assert tokens[2].type == TokenType.STRING_LITERAL
    assert tokens[2].literal == "escape\nsequences"
```

### Integration Tests

```python
def test_lexer_parser_integration():
    """Test lexer output works with parser"""
    source = """
def fibonacci(n):
    if n <= 1:
        return n
    else:
        return fibonacci(n-1) + fibonacci(n-2)

result = fibonacci(10)
"""
    lexer = AstridLexer(source)
    tokens = lexer.tokenize()

    # Verify no errors
    assert len(lexer.errors) == 0

    # Verify token stream is valid for parser
    parser = AstridParser(tokens)
    ast = parser.parse()

    # Verify AST structure
    assert isinstance(ast, Program)
    assert len(ast.functions) == 1
    assert ast.functions[0].name == "fibonacci"
```

## Performance Considerations

### Optimization Strategies

1. **String Interning**: Cache frequently used strings
2. **Token Buffering**: Pre-allocate token arrays
3. **Fast Path**: Optimize common token patterns
4. **Memory Pool**: Reuse token objects

### Benchmarking

```python
def benchmark_lexer():
    """Benchmark lexer performance"""
    import time

    # Load test file
    with open("large_test_file.ast", "r") as f:
        source = f.read()

    start_time = time.time()
    lexer = AstridLexer(source)
    tokens = lexer.tokenize()
    end_time = time.time()

    print(f"Lexed {len(tokens)} tokens in {end_time - start_time:.3f} seconds")
    print(f"Tokens per second: {len(tokens) / (end_time - start_time):.0f}")
```

## Implementation Checklist

- [ ] Token type definitions
- [ ] Basic character scanning
- [ ] Identifier recognition
- [ ] Number literal parsing (decimal, hex, binary)
- [ ] String literal parsing with escapes
- [ ] Operator recognition
- [ ] Indentation handling
- [ ] Comment processing
- [ ] Error reporting and recovery
- [ ] Unicode support
- [ ] Performance optimizations
- [ ] Comprehensive test suite
- [ ] Integration with parser

## Production Process Details

### Important Implementation Notes

1. **Indentation Consistency**: Enforce consistent indentation (spaces or tabs) within a file. Convert tabs to spaces for internal processing.

2. **Token Buffering**: Pre-allocate token arrays for performance. Use efficient data structures for token storage.

3. **Error Recovery**: Implement robust error recovery to continue parsing after lexical errors. Skip to safe recovery points.

4. **Unicode Handling**: Support UTF-8 encoding. Handle multi-byte characters correctly in identifiers and strings.

5. **Hardware Keywords**: Ensure hardware register keywords are case-sensitive and match Nova-16 specifications exactly.

6. **Performance Optimization**: Optimize hot paths (identifier recognition, number parsing). Use lookup tables for keywords.

7. **Memory Management**: Minimize memory allocations during lexing. Reuse string buffers where possible.

### Testing Strategy

- **Unit Tests**: Test each token type recognition individually
- **Integration Tests**: Test lexer output with parser
- **Error Handling**: Test error recovery and reporting
- **Performance Tests**: Benchmark lexing speed on large files
- **Edge Cases**: Test indentation edge cases, Unicode, long strings

### Implementation Checklist

- [ ] Core token recognition (identifiers, numbers, strings, operators)
- [ ] Indentation stack management
- [ ] Hardware register keyword support
- [ ] Error reporting with context
- [ ] Unicode identifier support
- [ ] Performance optimizations
- [ ] Comprehensive test coverage
- [ ] Integration testing with parser

### Performance Metrics

- **Lexing Speed**: Tokens per second
- **Memory Usage**: Peak memory during lexing
- **Error Recovery**: Time to recover from errors
- **Large File Handling**: Performance on files >10MB

### Common Pitfalls

1. **Off-by-One Errors**: Careful with position tracking, especially for multi-byte characters
2. **Indentation Stack**: Properly manage indent/dedent tokens
3. **String Escapes**: Handle all escape sequences correctly
4. **Keyword Lookup**: Efficient keyword recognition without false positives
5. **Error Context**: Provide accurate line/column information

## Error Messages

### Common Lexical Errors

1. **Unterminated String**: `"hello world` → "Unterminated string literal"
2. **Invalid Escape**: `"hello\z"` → "Invalid escape sequence: \z"
3. **Invalid Character**: `x = @var` → "Unexpected character: @"
4. **Indentation Error**: Mixed spaces/tabs → "Inconsistent indentation"
5. **Invalid Number**: `123abc` → "Invalid integer literal: 123abc"

### Error Context

```
Error: Unterminated string literal
File: example.ast, Line 5, Column 12
    message = "hello world
                      ^
```

This lexer specification provides a solid foundation for implementing the Astrid lexical analyzer, with clear guidelines for token recognition, error handling, and integration with the parser.</content>
<parameter name="filePath">c:\Code\Nova\astrid docs\astrid_lexer_specification.md