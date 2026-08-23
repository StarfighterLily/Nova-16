# Astrid Language Parser
# File: astrid/parser/parser.py
"""Enhanced parser with do-while loops, switch/case statements, and char literals."""
from __future__ import annotations

from typing import List, Optional
from astrid.lexer.lexer import Lexer, Token

# AST Node Classes
class ASTNode:
    pass

# Expression AST nodes
class Expression(ASTNode):
    pass

class StringLiteral(Expression):
    def __init__(self, value: str):
        self.value = value

class CharLiteral(Expression):
    """Character literal expression node (e.g., 'A', '\\n')."""
    def __init__(self, char_value: int):
        self.char_value = char_value

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
    def __init__(self, functions: List["FunctionDef"], globals_: Optional[List["VarDecl"]] = None):
        self.functions = functions
        # Top-level (global) variable declarations. Empty for sources that
        # only define functions; populated when the source declares variables
        # outside of any function body.
        self.globals: List["VarDecl"] = globals_ or []

class FunctionDef(ASTNode):
    def __init__(self, return_type: str, name: str, params: List["VarDecl"], body: List["ASTNode"]):
        self.return_type = return_type
        self.name = name
        self.params = params
        self.body = body

class VarDecl(ASTNode):
    def __init__(self, var_type: str, name: str, value: Optional["ASTNode"],
                 array_size: Optional["Expression"] = None,
                 init_list: Optional[List["Expression"]] = None,
                 pointer_depth: int = 0,
                 is_array_param: bool = False):
        self.var_type = var_type
        self.name = name
        self.value = value
        # Array support: `int arr[10];` sets array_size to the constant size
        # expression. `int arr[] = {1, 2, 3};` leaves array_size None and
        # infers the count from init_list.
        self.array_size = array_size
        # Initializer list: `int arr[3] = {1, 2, 3};` or scalar `int x = 5;`
        # uses `value` instead. init_list is a list of expressions.
        self.init_list = init_list
        # Pointer declarations (`int *p`, `char **s`) record how many '*'
        # preceded the name. Pointers occupy 2 bytes (a 16-bit address).
        self.pointer_depth = pointer_depth
        # Array parameters (`void f(int arr[])`) decay to an address; the
        # parameter slot holds the caller's array base address (2 bytes).
        self.is_array_param = is_array_param

    @property
    def is_pointer(self) -> bool:
        return self.pointer_depth > 0

    @property
    def is_array(self) -> bool:
        return self.array_size is not None or self.init_list is not None

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

class DoWhile(ASTNode):
    """AST node for do-while loops: do { body } while (cond);"""
    def __init__(self, body: List["ASTNode"], cond: "Expression"):
        self.body = body
        self.cond = cond

class For(ASTNode):
    def __init__(self, init: Optional["ASTNode"], cond: Optional["Expression"], update: Optional["ASTNode"], body: List["ASTNode"]):
        self.init = init
        self.cond = cond
        self.update = update
        self.body = body

class Switch(ASTNode):
    """AST node for switch/case statements."""
    def __init__(self, expr: "Expression", cases: List["Case"], default_body: Optional[List["ASTNode"]]):
        self.expr = expr
        self.cases = cases
        self.default_body = default_body

class Case(ASTNode):
    """AST node for a single case label and its body."""
    def __init__(self, value: Optional["ASTNode"], body: List["ASTNode"]):
        self.value = value  # None for 'default' case
        self.body = body

class Break(ASTNode):
    """break statement - exits the innermost loop or switch."""

class Continue(ASTNode):
    """continue statement - skips to next loop iteration."""

class FuncCall(ASTNode):
    def __init__(self, name: str, args: List["Expression"]):
        self.name = name
        self.args = args

class Cast(Expression):
    """Type cast expression node: (int)expr, (char)expr, (string)expr, (binary)expr."""
    def __init__(self, target_type: str, expr: "Expression"):
        self.target_type = target_type
        self.expr = expr

class ArrayAccess(Expression):
    """Array element access: arr[index]."""
    def __init__(self, name: str, index: "Expression"):
        self.name = name
        self.index = index

class ArrayAssignment(ASTNode):
    """Assignment to an array element: arr[index] = value (or compound op)."""
    def __init__(self, target: "ArrayAccess", value: "Expression"):
        self.target = target
        self.value = value

class TernaryOp(Expression):
    """Ternary conditional expression: cond ? then_expr : else_expr."""
    def __init__(self, cond: "Expression", then_expr: "Expression", else_expr: "Expression"):
        self.cond = cond
        self.then_expr = then_expr
        self.else_expr = else_expr

class PrefixOp(Expression):
    """Prefix increment/decrement: ++i or --i (yields the NEW value)."""
    def __init__(self, op: str, operand: "Expression"):
        self.op = op
        self.operand = operand

class AddressOf(Expression):
    """Unary & operator: address-of a variable or array element."""
    def __init__(self, operand: "Expression"):
        self.operand = operand

class Deref(Expression):
    """Unary * operator: dereference a pointer (load through an address)."""
    def __init__(self, operand: "Expression"):
        self.operand = operand

class DerefAssignment(ASTNode):
    """Assignment through a pointer: *ptr = value (or compound op)."""
    def __init__(self, target: "Deref", value: "Expression"):
        self.target = target
        self.value = value

class SizeofExpr(Expression):
    """sizeof(type) or sizeof(expr): compile-time size in bytes."""
    def __init__(self, target):
        # target is either a type-name string ('int', 'char', ...) or an
        # expression node whose inferred type determines the size.
        self.target = target

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

    def _skip_const(self):
        """Consume any leading 'const' qualifiers."""
        while self.current.type == 'KEYWORD' and self.current.value == 'const':
            self.advance()

    @staticmethod
    def _unescape_string(s: str) -> str:
        """Resolve backslash escapes in a raw string/char literal.

        Handles \\n \\t \\r \\\\ \\" \\' \\0 and \\xNN hex escapes. Unknown
        escapes keep the escaped character itself (lenient, like many C
        compilers' warnings).
        """
        out = []
        i = 0
        simple = {'n': '\n', 't': '\t', 'r': '\r', '\\': '\\',
                  '"': '"', "'": "'", '0': '\0'}
        while i < len(s):
            ch = s[i]
            if ch == '\\' and i + 1 < len(s):
                nxt = s[i + 1]
                if nxt in simple:
                    out.append(simple[nxt])
                    i += 2
                    continue
                if nxt in ('x', 'X') and i + 3 <= len(s):
                    try:
                        out.append(chr(int(s[i + 2:i + 4], 16)))
                        i += 4
                        continue
                    except ValueError:
                        pass
                out.append(nxt)
                i += 2
                continue
            out.append(ch)
            i += 1
        return ''.join(out)

    def parse(self) -> "Program":
        functions = []
        globals_: List[VarDecl] = []
        while self.current.type != 'EOF':
            # Top-level const qualifiers prefix either functions or globals.
            if self.current.type == 'KEYWORD' and self.current.value == 'const':
                self.advance()
                continue
            if (self.current.type == 'KEYWORD'
                    and self.current.value in {'int', 'char', 'string', 'binary', 'void'}):
                # Distinguish a function definition/prototype from a global
                # variable declaration by looking ahead past any pointer
                # stars: `type [*]* name(` is a function, anything else
                # (`type name;`, `type name[N];`, `type name = ...`) is a
                # global variable declaration.
                j = self.pos + 1
                while (j < len(self.tokens) and self.tokens[j].type == 'OPERATOR'
                       and self.tokens[j].value == '*'):
                    j += 1
                name_tok = self.tokens[j] if j < len(self.tokens) else None
                after_tok = self.tokens[j + 1] if j + 1 < len(self.tokens) else None
                if (name_tok is not None and name_tok.type == 'IDENTIFIER'
                        and after_tok is not None and after_tok.type == 'DELIMITER'
                        and after_tok.value == '('):
                    func = self.parse_function()
                    if func is not None:  # None => prototype-only declaration
                        functions.append(func)
                elif self.current.value == 'void':
                    raise SyntaxError(
                        f"Unexpected 'void' at top level (line {self.current.line})")
                else:
                    globals_.extend(self.parse_var_decl())
            else:
                functions.append(self.parse_function())
        return Program(functions, globals_)

    def parse_function(self) -> Optional["FunctionDef"]:
        return_type = self.current.value
        self.expect('KEYWORD')
        # Pointer-returning functions: `int *get_ptr() { ... }`
        pointer_depth = 0
        while self.current.type == 'OPERATOR' and self.current.value == '*':
            pointer_depth += 1
            self.advance()
        name = self.current.value
        self.expect('IDENTIFIER')
        self.expect('DELIMITER', '(')
        params = self.parse_params()
        self.expect('DELIMITER', ')')
        # Prototype declaration: `int add(int a, int b);` — no body. The
        # definition elsewhere provides the implementation; forward calls
        # resolve because the code generator pre-registers all functions.
        if self.current.type == 'DELIMITER' and self.current.value == ';':
            self.advance()
            return None
        self.expect('DELIMITER', '{')
        body = self.parse_block()
        self.expect('DELIMITER', '}')
        return FunctionDef(return_type, name, params, body)

    def parse_params(self) -> List["VarDecl"]:
        params = []
        # Empty parameter list: f() or f(void)
        if self.current.type == 'DELIMITER' and self.current.value == ')':
            return params
        if self.current.type == 'KEYWORD' and self.current.value == 'void':
            nxt = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
            if nxt is not None and nxt.type == 'DELIMITER' and nxt.value == ')':
                self.advance()  # consume 'void'; caller consumes ')'
                return params
        while True:
            self._skip_const()
            var_type = self.current.value
            self.expect('KEYWORD')
            pointer_depth = 0
            while self.current.type == 'OPERATOR' and self.current.value == '*':
                pointer_depth += 1
                self.advance()
            name = self.current.value
            self.expect('IDENTIFIER')
            is_array_param = False
            if self.current.type == 'DELIMITER' and self.current.value == '[':
                # Array parameter: void f(int arr[], int n). Arrays decay to
                # the base address, so the parameter slot holds an address.
                self.advance()
                if not (self.current.type == 'DELIMITER' and self.current.value == ']'):
                    self.parse_expression()  # size ignored (decay semantics)
                self.expect('DELIMITER', ']')
                is_array_param = True
            params.append(VarDecl(var_type, name, None,
                                  pointer_depth=pointer_depth,
                                  is_array_param=is_array_param))
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
        # Empty statement: a lone ';' is valid C and produces no code.
        if self.current.type == 'DELIMITER' and self.current.value == ';':
            self.advance()
            return []
        # const-qualified declarations: `const int K = 5;` — consume the
        # qualifier, then fall through to the declaration handling below.
        if self.current.type == 'KEYWORD' and self.current.value == 'const':
            self.advance()
            self._skip_const()
        if self.current.type == 'KEYWORD' and self.current.value in {'int', 'char', 'void', 'string', 'binary'}:
            # int(x), char(x), string(x), binary(x) at statement start is a
            # function call, not a variable declaration. Peek for '(' after
            # the type keyword to distinguish.
            peek_pos = self.pos + 1
            if peek_pos < len(self.tokens) and self.tokens[peek_pos].value == '(':
                func_name = self.current.value
                self.advance()  # skip keyword
                self.expect('DELIMITER', '(')
                args = []
                if self.current.type != 'DELIMITER' or self.current.value != ')':
                    while True:
                        args.append(self.parse_expression())
                        if self.current.type == 'DELIMITER' and self.current.value == ',':
                            self.advance()
                        else:
                            break
                self.expect('DELIMITER', ')')
                self.expect('DELIMITER', ';')
                return [FuncCall(func_name, args)]
            return self.parse_var_decl()
        elif self.current.type == 'KEYWORD' and self.current.value == 'return':
            return [self.parse_return()]
        elif self.current.type == 'KEYWORD' and self.current.value == 'if':
            return [self.parse_if()]
        elif self.current.type == 'KEYWORD' and self.current.value == 'while':
            return [self.parse_while()]
        elif self.current.type == 'KEYWORD' and self.current.value == 'do':
            return [self.parse_do_while()]
        elif self.current.type == 'KEYWORD' and self.current.value == 'for':
            return [self.parse_for()]
        elif self.current.type == 'KEYWORD' and self.current.value == 'switch':
            return [self.parse_switch()]
        elif self.current.type == 'KEYWORD' and self.current.value == 'break':
            self.advance()
            self.expect('DELIMITER', ';')
            return [Break()]
        elif self.current.type == 'KEYWORD' and self.current.value == 'continue':
            self.advance()
            self.expect('DELIMITER', ';')
            return [Continue()]
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
            pointer_depth = 0
            while self.current.type == 'OPERATOR' and self.current.value == '*':
                pointer_depth += 1
                self.advance()
            name = self.current.value
            self.expect('IDENTIFIER')
            array_size = None
            init_list = None
            value = None
            is_array = False
            # Array declaration: int arr[SIZE]; or int arr[]; (size inferred)
            if self.current.type == 'DELIMITER' and self.current.value == '[':
                self.advance()
                is_array = True
                if not (self.current.type == 'DELIMITER' and self.current.value == ']'):
                    array_size = self.parse_expression()
                self.expect('DELIMITER', ']')
            if self.current.value == '=':
                self.advance()
                if self.current.type == 'DELIMITER' and self.current.value == '{':
                    # Initializer list: = { expr, expr, ... }
                    self.advance()
                    init_list = []
                    if not (self.current.type == 'DELIMITER' and self.current.value == '}'):
                        while True:
                            init_list.append(self.parse_expression())
                            if self.current.value == ',':
                                self.advance()
                            else:
                                break
                    self.expect('DELIMITER', '}')
                else:
                    value = self.parse_expression()
                    # C-style string initialization of char arrays:
                    #   char buf[] = "Hi";   /   char buf[16] = "Hi";
                    # Expands to per-character initializers plus a NUL
                    # terminator so strlen/strcpy-style builtins work.
                    if var_type == 'char' and is_array and isinstance(value, StringLiteral):
                        text = Parser._unescape_string(value.value)
                        init_list = [CharLiteral(ord(c)) for c in text]
                        init_list.append(CharLiteral(0))
                        if array_size is None:
                            array_size = Number(str(len(init_list)))
                        value = None
            decls.append(VarDecl(var_type, name, value, array_size, init_list,
                                 pointer_depth=pointer_depth))
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

    def parse_do_while(self):
        """Parse: do { body } while (cond);"""
        self.expect('KEYWORD', 'do')
        body = self.parse_statement()
        self.expect('KEYWORD', 'while')
        self.expect('DELIMITER', '(')
        cond = self.parse_expression()
        self.expect('DELIMITER', ')')
        self.expect('DELIMITER', ';')
        return DoWhile(body, cond)

    def parse_for(self):
        self.expect('KEYWORD', 'for')
        self.expect('DELIMITER', '(')

        init = None
        if self.current.value != ';':
            if self.current.type == 'KEYWORD' and self.current.value in {'int', 'char', 'string', 'binary'}:
                init = self.parse_var_decl(expect_semicolon=False)  # This returns a list of decls
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

    def parse_switch(self):
        """Parse: switch (expr) { case val1: ... case val2: ... default: ... }"""
        self.expect('KEYWORD', 'switch')
        self.expect('DELIMITER', '(')
        expr = self.parse_expression()
        self.expect('DELIMITER', ')')
        self.expect('DELIMITER', '{')

        cases: List[Case] = []
        default_body: Optional[List[ASTNode]] = None
        current_case: Optional[Case] = None

        while not (self.current.type == 'DELIMITER' and self.current.value == '}'):
            if self.current.type == 'KEYWORD' and self.current.value == 'case':
                self.advance()
                case_value = self.parse_expression()
                self.expect('DELIMITER', ':')
                current_case = Case(case_value, [])
                cases.append(current_case)
            elif self.current.type == 'KEYWORD' and self.current.value == 'default':
                self.advance()
                self.expect('DELIMITER', ':')
                current_case = Case(None, [])  # default case
                default_body = []
                current_case = None
            elif self.current.type == 'KEYWORD' and self.current.value == 'break':
                self.advance()
                self.expect('DELIMITER', ';')
                # break is a statement within a case body
                if current_case is not None:
                    current_case.body.append(Break())
                elif default_body is not None:
                    default_body.append(Break())
            elif self.current.value == '{':
                self.advance()
                # Allow block scope within a case
                block = self.parse_block()
                if current_case is not None:
                    current_case.body.extend(block)
                elif default_body is not None:
                    default_body.extend(block)
            else:
                # Regular statement
                stmt = self.parse_statement()
                # parse_statement returns a list of statements
                if current_case is not None:
                    current_case.body.extend(stmt)
                elif default_body is not None:
                    default_body.extend(stmt)

        self.expect('DELIMITER', '}')
        return Switch(expr, cases, default_body)

    def parse_expression(self):
        return self.parse_binary_op(1)  # Start with lowest precedence

    def get_precedence(self, op):
        if op in ['=', '+=', '-=', '*=', '/=', '%=', '&=', '|=', '^=', '<<=', '>>=']: return 1
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

            if op_prec == 1:  # Right-associative assignment
                right = self.parse_binary_op(op_prec)
            else:  # Left-associative
                right = self.parse_binary_op(op_prec + 1)

            # Handle assignment as a special kind of binary op
            if op_prec == 1:
                if isinstance(left, Identifier):
                    # Handle compound assignment: x += 2 becomes x = x + 2
                    if op in ['+=', '-=', '*=', '/=', '%=', '&=', '|=', '^=', '<<=', '>>=']:
                        base_op = op[:-1]  # Remove trailing '=': '+', '-', '*', '/', '%', '&', '|', '^', '<<', '>>'
                        right = BinaryOp(Identifier(left.name), base_op, right)
                    left = Assignment(left.name, right)
                elif isinstance(left, ArrayAccess):
                    # Array element assignment: arr[i] = v, with compound
                    # forms decomposed like scalars (arr[i] += v becomes
                    # arr[i] = arr[i] + v).
                    if op in ['+=', '-=', '*=', '/=', '%=', '&=', '|=', '^=', '<<=', '>>=']:
                        base_op = op[:-1]
                        right = BinaryOp(ArrayAccess(left.name, left.index), base_op, right)
                    left = ArrayAssignment(left, right)
                elif isinstance(left, Deref):
                    # Assignment through a pointer: *p = v. Compound forms
                    # decompose the same way (*p += v becomes *p = *p + v).
                    if op in ['+=', '-=', '*=', '/=', '%=', '&=', '|=', '^=', '<<=', '>>=']:
                        base_op = op[:-1]
                        right = BinaryOp(Deref(left.operand), base_op, right)
                    left = DerefAssignment(left, right)
                else:
                    raise SyntaxError("Invalid assignment target")
            else:
                left = BinaryOp(left, op, right)

        # Ternary conditional operator (?:). Binds tighter than assignment
        # but looser than ||, and is right-associative:
        #   a || b ? c : d  parses as (a || b) ? c : d
        #   a ? b : c ? d : e parses as a ? b : (c ? d : e)
        if (precedence <= 2 and self.current.value == '?'
                and self.current.type in ('OPERATOR', 'DELIMITER')):
            self.advance()
            then_expr = self.parse_binary_op(1)
            self.expect('DELIMITER', ':')
            else_expr = self.parse_binary_op(1)
            left = TernaryOp(left, then_expr, else_expr)

        return left

    def parse_unary(self):
        # Prefix increment/decrement: ++i / --i (C semantics: yields the
        # updated value, unlike postfix which yields the old value).
        if self.current.type == 'OPERATOR' and self.current.value in ('++', '--'):
            op = self.current.value
            self.advance()
            operand = self.parse_unary()
            if not isinstance(operand, Identifier):
                raise SyntaxError(f"Prefix '{op}' requires a variable operand")
            return PrefixOp(op, operand)

        if self.current.type == 'OPERATOR' and self.current.value in ('-', '+', '!', '~', '&', '*'):
            op = self.current.value
            self.advance()
            if op == '+':
                # Unary plus is a no-op in C.
                return self.parse_unary()
            if op == '&':
                operand = self.parse_unary()
                if not isinstance(operand, (Identifier, ArrayAccess)):
                    raise SyntaxError("'&' requires a variable or array element operand")
                return AddressOf(operand)
            if op == '*':
                return Deref(self.parse_unary())
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
        elif token.type == 'CHAR':
            self.advance()
            # Parse char literal value, resolving all escape sequences
            # (\n, \t, \r, \0, \\, \', \xNN) via the shared unescaper.
            char_content = token.value.strip("'")
            unescaped = Parser._unescape_string(char_content)
            if len(unescaped) != 1:
                raise SyntaxError(f"Invalid char literal: {token.value}")
            return CharLiteral(ord(unescaped))
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
            # Array indexing: arr[expr] (chained indexing not needed for
            # 1-D arrays, but allow postfix on the result for future use).
            if self.current.type == 'DELIMITER' and self.current.value == '[':
                self.advance()
                index = self.parse_expression()
                self.expect('DELIMITER', ']')
                return ArrayAccess(token.value, index)
            return Identifier(token.value)
        elif token.type == 'KEYWORD' and token.value == 'sizeof':
            # sizeof(type) or sizeof(expr): compile-time byte size.
            self.advance()
            self.expect('DELIMITER', '(')
            if (self.current.type == 'KEYWORD'
                    and self.current.value in {'int', 'char', 'string', 'binary', 'void'}):
                type_name = self.current.value
                self.advance()
                # Allow pointer forms: sizeof(int*)
                while self.current.type == 'OPERATOR' and self.current.value == '*':
                    self.advance()
                self.expect('DELIMITER', ')')
                return SizeofExpr(type_name)
            inner = self.parse_expression()
            self.expect('DELIMITER', ')')
            return SizeofExpr(inner)
        elif token.type == 'KEYWORD' and token.value in {'int', 'char', 'string', 'binary'}:
            # Builtin conversion functions used inside expressions, e.g.
            # `int b = int(a);` or `return char(c);`. The lexer classifies
            # these names as KEYWORDs, so they never reach the IDENTIFIER
            # branch above. A type keyword directly followed by '(' is a
            # function call; anything else is a syntax error (casts like
            # `(int)x` are handled by the '(' delimiter branch below).
            next_token = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
            if next_token is not None and next_token.type == 'DELIMITER' and next_token.value == '(':
                func_name = token.value
                self.advance()          # consume type keyword
                self.expect('DELIMITER', '(')
                args = []
                if self.current.type != 'DELIMITER' or self.current.value != ')':
                    while True:
                        args.append(self.parse_expression())
                        if self.current.type == 'DELIMITER' and self.current.value == ',':
                            self.advance()
                        else:
                            break
                self.expect('DELIMITER', ')')
                return FuncCall(func_name, args)
            raise SyntaxError(f"Unexpected token in expression: {self.current}")
        elif token.type == 'DELIMITER' and token.value == '(':
            self.advance()
            # Check for type cast: (int)expr, (char)expr, (string)expr, (binary)expr
            if self.current.type == 'KEYWORD' and self.current.value in {'int', 'char', 'string', 'binary'}:
                target_type = self.current.value
                self.advance()
                self.expect('DELIMITER', ')')
                cast_expr = self.parse_unary()
                return Cast(target_type, cast_expr)
            expr = self.parse_expression()
            self.expect('DELIMITER', ')')
            return expr
        else:
            raise SyntaxError(f"Unexpected token in expression: {self.current}")