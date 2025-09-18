# Astrid Parser Specification

## Overview

The Astrid parser is responsible for converting the token stream from the lexer into an Abstract Syntax Tree (AST) that represents the syntactic structure of the Astrid program. The parser implements a recursive descent parsing strategy with operator precedence handling and comprehensive error recovery.

**Key Responsibilities:**
- Parse token stream into AST nodes
- Handle operator precedence and associativity
- Implement indentation-based block parsing
- Provide detailed error messages with recovery
- Support all Astrid language constructs
- Generate AST suitable for semantic analysis

## Grammar Definition

### Top-Level Grammar

```
program         → statement* EOF

statement       → function_def
                | class_def
                | import_stmt
                | assignment
                | expression_stmt
                | if_stmt
                | for_stmt
                | while_stmt
                | return_stmt
                | break_stmt
                | continue_stmt
                | pass_stmt
                | try_stmt
                | with_stmt
                | assert_stmt

expression      → assignment_expr

assignment_expr → lambda_expr
                | IDENTIFIER '=' assignment_expr
                | IDENTIFIER '+=' assignment_expr
                | IDENTIFIER '-=' assignment_expr
                | IDENTIFIER '*=' assignment_expr
                | IDENTIFIER '/=' assignment_expr
                | IDENTIFIER '%=' assignment_expr

lambda_expr     → 'lambda' parameters ':' expression
                | conditional_expr

conditional_expr → or_expr ('if' or_expr 'else' conditional_expr)?

or_expr         → and_expr ('or' and_expr)*

and_expr        → not_expr ('and' not_expr)*

not_expr        → 'not' not_expr
                | comparison_expr

comparison_expr → bit_or_expr (comparison_op bit_or_expr)*

comparison_op   → '==' | '!=' | '<' | '<=' | '>' | '>='

bit_or_expr     → bit_xor_expr ('|' bit_xor_expr)*

bit_xor_expr    → bit_and_expr ('^' bit_and_expr)*

bit_and_expr    → shift_expr ('&' shift_expr)*

shift_expr      → add_expr (('<<' | '>>') add_expr)*

add_expr        → mul_expr (('+' | '-') mul_expr)*

mul_expr        → unary_expr (('*' | '/' | '%') unary_expr)*

unary_expr      → ('+' | '-' | '~') unary_expr
                | power_expr

power_expr      → postfix_expr ('**' power_expr)?

postfix_expr    → primary_expr (('++' | '--'))?

primary_expr    → literal
                | IDENTIFIER
                | '(' expression ')'
                | '[' list_expr ']'
                | '{' dict_expr '}'
                | primary_expr '.' IDENTIFIER
                | primary_expr '[' expression ']'
                | primary_expr '(' arguments? ')'
                | hardware_access

hardware_access → HW_VM | HW_VL | HW_VX | HW_VY
                | HW_SA | HW_SF | HW_SV | HW_SW
                | HW_TT | HW_TM | HW_TC | HW_TS
                | HW_SP | HW_FP

literal         → INTEGER_LITERAL
                | FLOAT_LITERAL
                | STRING_LITERAL
                | 'True' | 'False'
                | 'None'

parameters      → IDENTIFIER (',' IDENTIFIER)*

arguments       → expression (',' expression)*

list_expr       → expression (',' expression)*

dict_expr       → (expression ':' expression) (',' expression ':' expression)*
```

### Statement-Specific Grammars

```
function_def    → 'def' IDENTIFIER '(' parameters? ')' ':' block

class_def       → 'class' IDENTIFIER ('(' IDENTIFIER ')')? ':' block

import_stmt     → 'import' IDENTIFIER (',' IDENTIFIER)*
                | 'from' IDENTIFIER 'import' IDENTIFIER (',' IDENTIFIER)*

if_stmt         → 'if' expression ':' block
                ('elif' expression ':' block)*
                ('else' ':' block)?

for_stmt        → 'for' IDENTIFIER 'in' expression ':' block

while_stmt      → 'while' expression ':' block

return_stmt     → 'return' expression?

break_stmt      → 'break'

continue_stmt   → 'continue'

pass_stmt       → 'pass'

try_stmt        → 'try' ':' block
                ('except' expression? ('as' IDENTIFIER)? ':' block)*
                ('finally' ':' block)?

with_stmt       → 'with' expression ('as' IDENTIFIER)? ':' block

assert_stmt     → 'assert' expression (',' expression)?

block           → NEWLINE INDENT statement+ DEDENT
```

## AST Node Definitions

### Base AST Classes

```python
from abc import ABC
from dataclasses import dataclass
from typing import List, Optional, Any, Dict

@dataclass
class ASTNode(ABC):
    """Base class for all AST nodes"""
    line: int
    column: int

@dataclass
class Expression(ASTNode):
    """Base class for expressions"""
    pass

@dataclass
class Statement(ASTNode):
    """Base class for statements"""
    pass

@dataclass
class Program(ASTNode):
    """Root node of the AST"""
    statements: List[Statement]
    functions: List['FunctionDef']
    classes: List['ClassDef']
    imports: List['Import']
```

### Expression Nodes

```python
@dataclass
class Literal(Expression):
    """Literal values (numbers, strings, booleans)"""
    value: Any
    type_hint: Optional[str] = None

@dataclass
class Identifier(Expression):
    """Variable/function references"""
    name: str

@dataclass
class BinaryOp(Expression):
    """Binary operations (+, -, *, /, etc.)"""
    left: Expression
    operator: str
    right: Expression

@dataclass
class UnaryOp(Expression):
    """Unary operations (-, +, not, etc.)"""
    operator: str
    operand: Expression

@dataclass
class PostfixOp(Expression):
    """Postfix operations (++, --)"""
    operand: Expression
    operator: str

@dataclass
class Assignment(Expression):
    """Assignment operations (=, +=, -=, etc.)"""
    target: Expression
    operator: str
    value: Expression

@dataclass
class FunctionCall(Expression):
    """Function calls"""
    function: Expression
    arguments: List[Expression]

@dataclass
class AttributeAccess(Expression):
    """Object attribute access (obj.attr)"""
    object: Expression
    attribute: str

@dataclass
class IndexAccess(Expression):
    """Array/list indexing (arr[index])"""
    array: Expression
    index: Expression

@dataclass
class ListLiteral(Expression):
    """List literals [1, 2, 3]"""
    elements: List[Expression]

@dataclass
class DictLiteral(Expression):
    """Dictionary literals {key: value}"""
    pairs: List[tuple[Expression, Expression]]

@dataclass
class Lambda(Expression):
    """Lambda expressions"""
    parameters: List[str]
    body: Expression

@dataclass
class Conditional(Expression):
    """Conditional expressions (x if condition else y)"""
    condition: Expression
    true_expr: Expression
    false_expr: Expression

@dataclass
class HardwareAccess(Expression):
    """Hardware register access"""
    register: str  # 'VM', 'VL', 'VX', etc.
```

### Statement Nodes

```python
@dataclass
class FunctionDef(Statement):
    """Function definitions"""
    name: str
    parameters: List[str]
    body: List[Statement]
    return_type: Optional[str] = None
    decorators: List[str] = None

@dataclass
class ClassDef(Statement):
    """Class definitions"""
    name: str
    base_classes: List[str]
    body: List[Statement]

@dataclass
class Import(Statement):
    """Import statements"""
    module: str
    names: List[str]
    alias: Optional[str] = None

@dataclass
class If(Statement):
    """If statements"""
    condition: Expression
    then_branch: List[Statement]
    elif_branches: List[tuple[Expression, List[Statement]]] = None
    else_branch: Optional[List[Statement]] = None

@dataclass
class For(Statement):
    """For loops"""
    iterator: str
    iterable: Expression
    body: List[Statement]

@dataclass
class While(Statement):
    """While loops"""
    condition: Expression
    body: List[Statement]

@dataclass
class Return(Statement):
    """Return statements"""
    value: Optional[Expression] = None

@dataclass
class Break(Statement):
    """Break statements"""
    pass

@dataclass
class Continue(Statement):
    """Continue statements"""
    pass

@dataclass
class Pass(Statement):
    """Pass statements"""
    pass

@dataclass
class Try(Statement):
    """Try-except-finally blocks"""
    try_body: List[Statement]
    except_handlers: List[tuple[Optional[Expression], Optional[str], List[Statement]]]
    finally_body: Optional[List[Statement]] = None

@dataclass
class With(Statement):
    """With statements"""
    context: Expression
    variable: Optional[str]
    body: List[Statement]

@dataclass
class Assert(Statement):
    """Assert statements"""
    condition: Expression
    message: Optional[Expression] = None

@dataclass
class ExpressionStatement(Statement):
    """Expression used as a statement"""
    expression: Expression
```

## Parser Architecture

### Core Parser Class

```python
class AstridParser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.current = 0
        self.errors = []
        self.indent_level = 0

    def parse(self) -> Program:
        """Main parsing entry point"""
        statements = []
        functions = []
        classes = []
        imports = []

        while not self.is_at_end():
            try:
                stmt = self.parse_statement()
                if isinstance(stmt, FunctionDef):
                    functions.append(stmt)
                elif isinstance(stmt, ClassDef):
                    classes.append(stmt)
                elif isinstance(stmt, Import):
                    imports.append(stmt)
                else:
                    statements.append(stmt)
            except ParseError as e:
                self.errors.append(e)
                self.synchronize()

        return Program(
            statements=statements,
            functions=functions,
            classes=classes,
            imports=imports,
            line=1,
            column=1
        )
```

### Token Consumption Methods

```python
def consume(self, token_type: TokenType, message: str) -> Token:
    """Consume a token of the expected type"""
    if self.check(token_type):
        return self.advance()
    else:
        self.error(message)
        return None

def consume_optional(self, token_type: TokenType) -> Optional[Token]:
    """Consume a token if it matches the expected type"""
    if self.check(token_type):
        return self.advance()
    return None

def check(self, token_type: TokenType) -> bool:
    """Check if the current token matches the expected type"""
    if self.is_at_end():
        return False
    return self.peek().type == token_type

def advance(self) -> Token:
    """Advance to the next token"""
    if not self.is_at_end():
        self.current += 1
    return self.previous()

def peek(self) -> Token:
    """Look at the current token without consuming it"""
    return self.tokens[self.current]

def previous(self) -> Token:
    """Get the previously consumed token"""
    return self.tokens[self.current - 1]

def is_at_end(self) -> bool:
    """Check if we've reached the end of tokens"""
    return self.peek().type == TokenType.EOF
```

## Expression Parsing

### Precedence Climbing Algorithm

```python
def parse_expression(self) -> Expression:
    """Parse an expression using precedence climbing"""
    return self.parse_assignment_expr()

def parse_assignment_expr(self) -> Expression:
    """Parse assignment expressions (=, +=, -=, etc.)"""
    expr = self.parse_lambda_expr()

    if self.match(TokenType.ASSIGN, TokenType.PLUS_ASSIGN, TokenType.MINUS_ASSIGN,
                  TokenType.MULTIPLY_ASSIGN, TokenType.DIVIDE_ASSIGN, TokenType.MODULO_ASSIGN):
        operator = self.previous().lexeme
        value = self.parse_assignment_expr()

        if not isinstance(expr, (Identifier, AttributeAccess, IndexAccess)):
            self.error("Invalid assignment target")

        return Assignment(
            target=expr,
            operator=operator,
            value=value,
            line=expr.line,
            column=expr.column
        )

    return expr

def parse_binary_expr(self, parse_next: Callable, operators: List[TokenType]) -> Expression:
    """Generic binary expression parser using precedence climbing"""
    expr = parse_next()

    while self.match(*operators):
        operator = self.previous().lexeme
        right = parse_next()
        expr = BinaryOp(
            left=expr,
            operator=operator,
            right=right,
            line=expr.line,
            column=expr.column
        )

    return expr
```

### Expression Parsing Hierarchy

```python
def parse_lambda_expr(self) -> Expression:
    """Parse lambda expressions"""
    if self.match(TokenType.LAMBDA):
        # Parse lambda parameters
        parameters = []
        if self.check(TokenType.IDENTIFIER):
            while True:
                param_token = self.consume(TokenType.IDENTIFIER, "Expected parameter name")
                parameters.append(param_token.lexeme)
                if not self.match(TokenType.COMMA):
                    break

        self.consume(TokenType.COLON, "Expected ':' after lambda parameters")
        body = self.parse_expression()

        return Lambda(
            parameters=parameters,
            body=body,
            line=self.previous().line,
            column=self.previous().column
        )

    return self.parse_conditional_expr()

def parse_conditional_expr(self) -> Expression:
    """Parse conditional expressions (x if condition else y)"""
    expr = self.parse_or_expr()

    if self.match(TokenType.IF):
        condition = self.parse_or_expr()
        self.consume(TokenType.ELSE, "Expected 'else' after conditional")
        else_expr = self.parse_conditional_expr()

        return Conditional(
            condition=condition,
            true_expr=expr,
            false_expr=else_expr,
            line=expr.line,
            column=expr.column
        )

    return expr

def parse_or_expr(self) -> Expression:
    """Parse logical OR expressions"""
    return self.parse_binary_expr(self.parse_and_expr, [TokenType.OR])

def parse_and_expr(self) -> Expression:
    """Parse logical AND expressions"""
    return self.parse_binary_expr(self.parse_not_expr, [TokenType.AND])

def parse_not_expr(self) -> Expression:
    """Parse logical NOT expressions"""
    if self.match(TokenType.NOT):
        operator = self.previous().lexeme
        operand = self.parse_not_expr()
        return UnaryOp(
            operator=operator,
            operand=operand,
            line=self.previous().line,
            column=self.previous().column
        )

    return self.parse_comparison_expr()

def parse_comparison_expr(self) -> Expression:
    """Parse comparison expressions"""
    return self.parse_binary_expr(
        self.parse_bit_or_expr,
        [TokenType.EQUAL, TokenType.NOT_EQUAL, TokenType.LESS,
         TokenType.LESS_EQUAL, TokenType.GREATER, TokenType.GREATER_EQUAL]
    )

def parse_bit_or_expr(self) -> Expression:
    """Parse bitwise OR expressions"""
    return self.parse_binary_expr(self.parse_bit_xor_expr, [TokenType.BIT_OR])

def parse_bit_xor_expr(self) -> Expression:
    """Parse bitwise XOR expressions"""
    return self.parse_binary_expr(self.parse_bit_and_expr, [TokenType.BIT_XOR])

def parse_bit_and_expr(self) -> Expression:
    """Parse bitwise AND expressions"""
    return self.parse_binary_expr(self.parse_shift_expr, [TokenType.BIT_AND])

def parse_shift_expr(self) -> Expression:
    """Parse shift expressions"""
    return self.parse_binary_expr(
        self.parse_add_expr,
        [TokenType.SHIFT_LEFT, TokenType.SHIFT_RIGHT]
    )

def parse_add_expr(self) -> Expression:
    """Parse addition/subtraction expressions"""
    return self.parse_binary_expr(self.parse_mul_expr, [TokenType.PLUS, TokenType.MINUS])

def parse_mul_expr(self) -> Expression:
    """Parse multiplication/division expressions"""
    return self.parse_binary_expr(
        self.parse_unary_expr,
        [TokenType.MULTIPLY, TokenType.DIVIDE, TokenType.MODULO]
    )

def parse_unary_expr(self) -> Expression:
    """Parse unary expressions"""
    if self.match(TokenType.PLUS, TokenType.MINUS, TokenType.BIT_NOT):
        operator = self.previous().lexeme
        operand = self.parse_unary_expr()
        return UnaryOp(
            operator=operator,
            operand=operand,
            line=self.previous().line,
            column=self.previous().column
        )

    return self.parse_power_expr()

def parse_power_expr(self) -> Expression:
    """Parse power expressions (** operator)"""
    expr = self.parse_postfix_expr()

    if self.match(TokenType.POWER):
        operator = self.previous().lexeme
        right = self.parse_power_expr()
        return BinaryOp(
            left=expr,
            operator=operator,
            right=right,
            line=expr.line,
            column=expr.column
        )

    return expr
```

### Primary Expression Parsing

```python
def parse_primary_expr(self) -> Expression:
    """Parse primary expressions (literals, identifiers, etc.)"""
    if self.match(TokenType.INTEGER_LITERAL, TokenType.FLOAT_LITERAL,
                  TokenType.STRING_LITERAL):
        return Literal(
            value=self.previous().literal,
            line=self.previous().line,
            column=self.previous().column
        )

    if self.match(TokenType.TRUE, TokenType.FALSE):
        return Literal(
            value=self.previous().type == TokenType.TRUE,
            line=self.previous().line,
            column=self.previous().column
        )

    if self.match(TokenType.NONE):
        return Literal(
            value=None,
            line=self.previous().line,
            column=self.previous().column
        )

    if self.match(TokenType.IDENTIFIER):
        return Identifier(
            name=self.previous().lexeme,
            line=self.previous().line,
            column=self.previous().column
        )

    # Hardware register access
    if self.match(TokenType.HW_VM, TokenType.HW_VL, TokenType.HW_VX, TokenType.HW_VY,
                  TokenType.HW_SA, TokenType.HW_SF, TokenType.HW_SV, TokenType.HW_SW,
                  TokenType.HW_TT, TokenType.HW_TM, TokenType.HW_TC, TokenType.HW_TS,
                  TokenType.HW_SP, TokenType.HW_FP):
        return HardwareAccess(
            register=self.previous().lexeme,
            line=self.previous().line,
            column=self.previous().column
        )

    if self.match(TokenType.LPAREN):
        expr = self.parse_expression()
        self.consume(TokenType.RPAREN, "Expected ')' after expression")
        return expr

    if self.match(TokenType.LBRACKET):
        return self.parse_list_literal()

    if self.match(TokenType.LBRACE):
        return self.parse_dict_literal()

    self.error("Expected expression")
    return None

def parse_postfix_expr(self) -> Expression:
    """Parse postfix expressions (++, --)"""
    expr = self.parse_primary_expr()

    if self.match(TokenType.INCREMENT, TokenType.DECREMENT):
        operator = self.previous().lexeme
        return PostfixOp(
            operand=expr,
            operator=operator,
            line=expr.line,
            column=expr.column
        )

    return expr
```

## Statement Parsing

### Function Definition Parsing

```python
def parse_function_def(self) -> FunctionDef:
    """Parse function definitions"""
    self.consume(TokenType.DEF, "Expected 'def'")
    name_token = self.consume(TokenType.IDENTIFIER, "Expected function name")

    self.consume(TokenType.LPAREN, "Expected '(' after function name")

    parameters = []
    if not self.check(TokenType.RPAREN):
        while True:
            param_token = self.consume(TokenType.IDENTIFIER, "Expected parameter name")
            parameters.append(param_token.lexeme)

            if not self.match(TokenType.COMMA):
                break

    self.consume(TokenType.RPAREN, "Expected ')' after parameters")
    self.consume(TokenType.COLON, "Expected ':' after function signature")

    body = self.parse_block()

    return FunctionDef(
        name=name_token.lexeme,
        parameters=parameters,
        body=body,
        line=name_token.line,
        column=name_token.column
    )
```

### Block Parsing with Indentation

```python
def parse_block(self) -> List[Statement]:
    """Parse indented block of statements"""
    self.consume(TokenType.NEWLINE, "Expected newline before block")
    self.consume(TokenType.INDENT, "Expected indentation")

    statements = []
    while not self.check(TokenType.DEDENT) and not self.is_at_end():
        stmt = self.parse_statement()
        if stmt:
            statements.append(stmt)

    self.consume(TokenType.DEDENT, "Expected dedentation")
    return statements
```

### Control Flow Parsing

```python
def parse_if_stmt(self) -> If:
    """Parse if-elif-else statements"""
    self.consume(TokenType.IF, "Expected 'if'")
    condition = self.parse_expression()
    self.consume(TokenType.COLON, "Expected ':' after if condition")

    then_branch = self.parse_block()
    elif_branches = []
    else_branch = None

    # Parse elif branches
    while self.match(TokenType.ELIF):
        elif_condition = self.parse_expression()
        self.consume(TokenType.COLON, "Expected ':' after elif condition")
        elif_body = self.parse_block()
        elif_branches.append((elif_condition, elif_body))

    # Parse else branch
    if self.match(TokenType.ELSE):
        self.consume(TokenType.COLON, "Expected ':' after else")
        else_branch = self.parse_block()

    return If(
        condition=condition,
        then_branch=then_branch,
        elif_branches=elif_branches,
        else_branch=else_branch,
        line=condition.line,
        column=condition.column
    )
```

## Error Handling and Recovery

### Error Reporting

```python
@dataclass
class ParseError:
    message: str
    line: int
    column: int
    expected: Optional[List[str]] = None
    found: Optional[str] = None

def error(self, message: str):
    """Report a parsing error"""
    token = self.peek()
    error = ParseError(
        message=message,
        line=token.line,
        column=token.column,
        found=token.lexeme
    )
    self.errors.append(error)
    return error
```

### Error Recovery

```python
def synchronize(self):
    """Synchronize parser after an error"""
    self.advance()  # Skip the erroneous token

    # Skip tokens until we find a statement boundary
    while not self.is_at_end():
        if self.previous().type == TokenType.SEMICOLON:
            return

        if self.peek().type in [
            TokenType.CLASS, TokenType.FUNCTION, TokenType.VAR,
            TokenType.FOR, TokenType.IF, TokenType.WHILE,
            TokenType.PRINT, TokenType.RETURN
        ]:
            return

        self.advance()
```

## Testing and Validation

### Unit Tests

```python
def test_parser_basic_function():
    """Test parsing a simple function"""
    tokens = [
        Token(TokenType.DEF, "def", None, 1, 1),
        Token(TokenType.IDENTIFIER, "main", None, 1, 5),
        Token(TokenType.LPAREN, "(", None, 1, 9),
        Token(TokenType.RPAREN, ")", None, 1, 10),
        Token(TokenType.COLON, ":", None, 1, 11),
        Token(TokenType.NEWLINE, "\n", None, 1, 12),
        Token(TokenType.INDENT, "", None, 2, 1),
        Token(TokenType.RETURN, "return", None, 2, 5),
        Token(TokenType.INTEGER_LITERAL, "42", 42, 2, 12),
        Token(TokenType.NEWLINE, "\n", None, 2, 13),
        Token(TokenType.DEDENT, "", None, 3, 1),
        Token(TokenType.EOF, "", None, 3, 1)
    ]

    parser = AstridParser(tokens)
    ast = parser.parse()

    assert len(parser.errors) == 0
    assert len(ast.functions) == 1
    assert ast.functions[0].name == "main"
    assert len(ast.functions[0].parameters) == 0
    assert len(ast.functions[0].body) == 1
    assert isinstance(ast.functions[0].body[0], Return)
```

### Integration Tests

```python
def test_parser_complex_program():
    """Test parsing a complex program with multiple constructs"""
    source = '''
def factorial(n):
    if n <= 1:
        return 1
    else:
        return n * factorial(n - 1)

class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def distance(self):
        return (self.x ** 2 + self.y ** 2) ** 0.5

p = Point(3, 4)
result = factorial(5)
'''

    lexer = AstridLexer(source)
    tokens = lexer.tokenize()
    parser = AstridParser(tokens)
    ast = parser.parse()

    # Verify no errors
    assert len(lexer.errors) == 0
    assert len(parser.errors) == 0

    # Verify structure
    assert len(ast.functions) == 1
    assert len(ast.classes) == 1
    assert len(ast.statements) == 2
```

## Performance Considerations

### Optimization Strategies

1. **Token Buffering**: Pre-allocate AST node arrays
2. **Fast Path**: Optimize common patterns (variable access, function calls)
3. **Memory Pool**: Reuse AST node objects
4. **Lazy Parsing**: Parse only when needed for IDE features

### Benchmarking

```python
def benchmark_parser():
    """Benchmark parser performance"""
    import time

    # Load test file
    with open("large_test_file.ast", "r") as f:
        source = f.read()

    lexer = AstridLexer(source)
    tokens = lexer.tokenize()

    start_time = time.time()
    parser = AstridParser(tokens)
    ast = parser.parse()
    end_time = time.time()

    print(f"Parsed AST with {count_nodes(ast)} nodes in {end_time - start_time:.3f} seconds")
    print(f"Parse speed: {len(tokens) / (end_time - start_time):.0f} tokens/second")
```

## Implementation Checklist

- [ ] AST node definitions
- [ ] Token consumption utilities
- [ ] Expression parsing (precedence climbing)
- [ ] Statement parsing (all statement types)
- [ ] Indentation-based block parsing
- [ ] Error reporting and recovery
- [ ] Hardware register parsing
- [ ] Function and class parsing
- [ ] Control flow parsing
- [ ] Import statement parsing
- [ ] Comprehensive test suite
- [ ] Performance optimizations
- [ ] Integration with lexer

## Production Process Details

### Important Implementation Notes

1. **Precedence Handling**: Implement operator precedence correctly using precedence climbing. Test all precedence levels thoroughly.

2. **AST Construction**: Ensure AST nodes include accurate line/column information for error reporting and debugging.

3. **Indentation Parsing**: Handle indentation-based blocks correctly. Maintain indentation stack and emit INDENT/DEDENT tokens properly.

4. **Error Recovery**: Implement synchronization points to recover from parse errors. Continue parsing after errors to find more issues.

5. **Hardware Integration**: Parse hardware register accesses correctly. Validate register names against known hardware registers.

6. **Memory Efficiency**: Use efficient data structures for AST nodes. Consider object pooling for frequently created nodes.

7. **Extensibility**: Design parser to easily add new language constructs without major refactoring.

### Testing Strategy

- **Unit Tests**: Test each parsing method individually
- **Integration Tests**: Test full AST construction from source
- **Error Recovery**: Test parser resilience to malformed input
- **Performance Tests**: Benchmark parsing speed on large files
- **Edge Cases**: Test complex expressions, nested blocks, error conditions

### Implementation Checklist

- [ ] AST node classes with proper inheritance
- [ ] Token consumption utilities
- [ ] Expression parsing with precedence
- [ ] Statement parsing for all constructs
- [ ] Indentation-aware block parsing
- [ ] Comprehensive error handling
- [ ] Hardware register support
- [ ] Integration with semantic analyzer

### Performance Considerations

- **Parsing Speed**: Optimize for fast parsing of typical code
- **Memory Usage**: Monitor AST memory consumption
- **Error Path**: Fast error detection and recovery
- **Large Files**: Handle files with thousands of lines efficiently

### Common Pitfalls

1. **Left Recursion**: Avoid left-recursive grammars; use precedence climbing
2. **Indentation Bugs**: Careful handling of INDENT/DEDENT token sequences
3. **Error Synchronization**: Choose good synchronization tokens (semicolons, newlines)
4. **AST Accuracy**: Ensure AST represents source code faithfully
5. **Token Peeking**: Use peek() carefully to avoid consuming tokens prematurely

### Integration Points

- **Lexer Integration**: Consume token stream from lexer
- **Semantic Analysis**: Produce AST for semantic analyzer
- **Error Reporting**: Provide detailed parse errors with context
- **IDE Support**: Enable incremental parsing for editor features

## Common Parse Errors

### Syntax Errors

1. **Missing Colon**: `def func()` → "Expected ':' after function signature"
2. **Unmatched Parentheses**: `func(a, b` → "Expected ')' after arguments"
3. **Invalid Indentation**: Mixed spaces/tabs → "Inconsistent indentation detected"
4. **Unexpected Token**: `x = 1 print` → "Unexpected token: print"
5. **Missing Expression**: `return` → "Expected expression after return"

### Error Context

```
Parse Error: Expected ':' after function signature
File: example.ast, Line 3, Column 15
    def calculate(x, y)
                      ^
    Expected ':' here
```

This parser specification provides a comprehensive guide for implementing the Astrid parser, with detailed AST structures, parsing algorithms, and error handling strategies to ensure robust and maintainable code.</content>
<parameter name="filePath">c:\Code\Nova\astrid docs\astrid_parser_specification.md