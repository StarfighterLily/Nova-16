# String literal AST node
# Astrid Language Parser (Draft)
# File: astrid_parser.py
from __future__ import annotations

from typing import List, Optional
from astrid_lexer import Lexer, Token

# AST Node Classes
class ASTNode:
    pass

# Expression AST nodes
class Expression(ASTNode):
    pass

class StringLiteral(Expression):
    def __init__(self, value: str):
        self.value = value

class Number(Expression):
    def __init__(self, value):
        self.value = value

class Identifier(Expression):
    def __init__(self, name):
        self.name = name

class BinaryOp(Expression):
    def __init__(self, left: "Expression", op: str, right: "Expression"):
        self.left = left
        self.op = op
        self.right = right

class UnaryOp(Expression):
    def __init__(self, op: str, right: "Expression"):
        self.op = op
        self.right = right

class PostfixOp(Expression):
    def __init__(self, left: "Expression", op: str):
        self.left = left
        self.op = op

class Program(ASTNode):
    def __init__(self, functions: List["FunctionDef"]):
        self.functions = functions

class FunctionDef(ASTNode):
    def __init__(self, return_type: str, name: str, params: List["VarDecl"], body: List["ASTNode"]):
        self.return_type = return_type
        self.name = name
        self.params = params
        self.body = body

class VarDecl(ASTNode):
    def __init__(self, var_type: str, name: str, value: Optional["ASTNode"]):
        self.var_type = var_type
        self.name = name
        self.value = value

class Assignment(ASTNode):
    def __init__(self, name: str, value: "ASTNode"):
        self.name = name
        self.value = value

class Return(ASTNode):
    def __init__(self, value: Optional["ASTNode"]):
        self.value = value

class If(ASTNode):
    def __init__(self, cond: "Expression", then_body: List["ASTNode"], else_body: Optional[List["ASTNode"]]=None):
        self.cond = cond
        self.then_body = then_body
        self.else_body = else_body

class While(ASTNode):
    def __init__(self, cond: "Expression", body: List["ASTNode"]):
        self.cond = cond
        self.body = body

class For(ASTNode):
    def __init__(self, init: Optional["ASTNode"], cond: Optional["Expression"], update: Optional["ASTNode"], body: List["ASTNode"]):
        self.init = init
        self.cond = cond
        self.update = update
        self.body = body

class FuncCall(ASTNode):
    def __init__(self, name: str, args: List["Expression"]):
        self.name = name
        self.args = args

class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        self.current = self.tokens[self.pos]

    def advance(self):
        self.pos += 1
        if self.pos < len(self.tokens):
            self.current = self.tokens[self.pos]
        else:
            self.current = Token('EOF', '', self.current.line, self.current.column)

    def expect(self, type_, value=None):
        if self.current.type != type_ or (value is not None and self.current.value != value):
            raise SyntaxError(f"Expected {type_} {value}, got {self.current.type} {self.current.value}")
        self.advance()

    def parse(self) -> "Program":
        functions = []
        while self.current.type != 'EOF':
            functions.append(self.parse_function())
        return Program(functions)

    def parse_function(self) -> "FunctionDef":
        return_type = self.current.value
        self.expect('KEYWORD')
        name = self.current.value
        self.expect('IDENTIFIER')
        self.expect('DELIMITER', '(')
        params = self.parse_params()
        self.expect('DELIMITER', ')')
        self.expect('DELIMITER', '{')
        body = self.parse_block()
        self.expect('DELIMITER', '}')
        return FunctionDef(return_type, name, params, body)

    def parse_params(self) -> List["VarDecl"]:
        params = []
        if self.current.type == 'KEYWORD':
            while True:
                var_type = self.current.value
                self.expect('KEYWORD')
                name = self.current.value
                self.expect('IDENTIFIER')
                params.append(VarDecl(var_type, name, None))
                if self.current.type == 'DELIMITER' and self.current.value == ',':
                    self.advance()
                else:
                    break
        return params

    def parse_block(self) -> List[ASTNode]:
        stmts = []
        while self.current.type != 'DELIMITER' or self.current.value != '}':
            stmts.extend(self.parse_statement())
        return stmts
    
    def parse_statement(self):
        if self.current.type == 'KEYWORD' and self.current.value in {'int', 'char', 'void'}:
            return self.parse_var_decl()
        elif self.current.type == 'KEYWORD' and self.current.value == 'return':
            return [self.parse_return()]
        elif self.current.type == 'KEYWORD' and self.current.value == 'if':
            return [self.parse_if()]
        elif self.current.type == 'KEYWORD' and self.current.value == 'while':
            return [self.parse_while()]
        elif self.current.type == 'KEYWORD' and self.current.value == 'for':
            return [self.parse_for()]
        elif self.current.value == '{':
             self.advance()
             block = self.parse_block()
             self.expect('DELIMITER', '}')
             return block
        else:
            # Fallback to expression statement
            expr = self.parse_expression()
            self.expect('DELIMITER', ';')
            return [expr]

    def parse_var_decl(self, expect_semicolon=True):
        var_type = self.current.value
        self.expect('KEYWORD')
        decls = []
        while True:
            name = self.current.value
            self.expect('IDENTIFIER')
            value = None
            if self.current.value == '=':
                self.advance()
                value = self.parse_expression()
            decls.append(VarDecl(var_type, name, value))
            if self.current.value == ',':
                self.advance()
            else:
                break
        if expect_semicolon:
            self.expect('DELIMITER', ';')
        return decls

    def parse_return(self):
        self.expect('KEYWORD', 'return')
        value = None
        if self.current.value != ';':
            value = self.parse_expression()
        self.expect('DELIMITER', ';')
        return Return(value)

    def parse_if(self):
        self.expect('KEYWORD', 'if')
        self.expect('DELIMITER', '(')
        cond = self.parse_expression()
        self.expect('DELIMITER', ')')
        then_body = self.parse_statement()
        else_body = None
        if self.current.value == 'else':
            self.advance()
            else_body = self.parse_statement()
        return If(cond, then_body, else_body)

    def parse_while(self):
        self.expect('KEYWORD', 'while')
        self.expect('DELIMITER', '(')
        cond = self.parse_expression()
        self.expect('DELIMITER', ')')
        body = self.parse_statement()
        return While(cond, body)

    def parse_for(self):
        self.expect('KEYWORD', 'for')
        self.expect('DELIMITER', '(')
        
        init = None
        if self.current.value != ';':
            if self.current.type == 'KEYWORD' and self.current.value in {'int', 'char'}:
                init = self.parse_var_decl(expect_semicolon=False) # This returns a list of decls
            else:
                init = self.parse_expression()
        self.expect('DELIMITER', ';')

        cond = None
        if self.current.value != ';':
            cond = self.parse_expression()
        self.expect('DELIMITER', ';')

        update = None
        if self.current.value != ')':
            update = self.parse_expression()
        self.expect('DELIMITER', ')')
        
        body = self.parse_statement()
        return For(init, cond, update, body)

    def parse_expression(self):
        return self.parse_binary_op(1) # Start with lowest precedence

    def get_precedence(self, op):
        if op in ['=', '+=', '-=']: return 1
        if op in ['||']: return 2
        if op in ['&&']: return 3
        if op in ['|']: return 4
        if op in ['^']: return 5
        if op in ['&']: return 6
        if op in ['==', '!=']: return 7
        if op in ['<', '>', '<=', '>=']: return 8
        if op in ['<<', '>>']: return 9
        if op in ['+', '-']: return 10
        if op in ['*', '/', '%']: return 11
        return 0

    def parse_binary_op(self, precedence=0):
        left = self.parse_unary()
        while True:
            op = self.current.value
            op_prec = self.get_precedence(op)
            if self.current.type != 'OPERATOR' or op_prec < precedence:
                break
            
            self.advance()

            if op_prec == 1: # Right-associative assignment
                right = self.parse_binary_op(op_prec)
            else: # Left-associative
                right = self.parse_binary_op(op_prec + 1)

            # Handle assignment as a special kind of binary op
            if op_prec == 1:
                if not isinstance(left, Identifier):
                    raise SyntaxError("Invalid assignment target")
                # Create an Assignment node instead of a generic BinaryOp
                left = Assignment(left.name, right)
            else:
                left = BinaryOp(left, op, right)

        return left

    def parse_unary(self):
        if self.current.value in ['-', '!', '~']:
            op = self.current.value
            self.advance()
            right = self.parse_unary()
            return UnaryOp(op, right)
        
        expr = self.parse_primary()
        # Handle postfix operators
        while self.current.value in ['++', '--']:
            op = self.current.value
            self.advance()
            expr = PostfixOp(expr, op)
        return expr

    def parse_primary(self):
        token = self.current
        if token.type == 'NUMBER':
            self.advance()
            return Number(token.value)
        elif token.type == 'STRING':
            self.advance()
            return StringLiteral(token.value.strip('"'))
        elif token.type == 'IDENTIFIER':
            self.advance()
            if self.current.type == 'DELIMITER' and self.current.value == '(': 
                self.advance()
                args = []
                if self.current.type != 'DELIMITER' or self.current.value != ')':
                    while True:
                        args.append(self.parse_expression())
                        if self.current.type == 'DELIMITER' and self.current.value == ',':
                            self.advance()
                        else:
                            break
                self.expect('DELIMITER', ')')
                return FuncCall(token.value, args)
            return Identifier(token.value)
        elif token.type == 'DELIMITER' and token.value == '(': 
            self.advance()
            expr = self.parse_expression()
            self.expect('DELIMITER', ')')
            return expr
        else:
            raise SyntaxError(f"Unexpected token in expression: {self.current}")
