#!/usr/bin/env python3
"""
NoBASIC Parser
Builds an Abstract Syntax Tree (AST) from tokens.
"""

from typing import List
from nobasic_utils import (
    Token, TokenType, Program, Statement, Expression,
    ClrHomeStmt, DispStmt, InputStmt, AssignmentStmt, DimStmt,
    BreakStmt, ContinueStmt, IfStmt, ElifClause, ForStmt, WhileStmt, DoLoopStmt,
    RepeatUntilStmt, SelectStmt, CaseClause, CallStmt, ReturnStmt, PauseStmt,
    DefineStmt, GotoStmt, LabelStmt, TryCatchStmt, StructStmt, StructField, StructFieldStmt, StructInstanceStmt,
    BinaryExpr, UnaryExpr, LiteralExpr, VariableExpr,
    ArrayAccessExpr, FunctionCallExpr, ArrayLiteralExpr, StructFieldAccessExpr
)
from nobasic_errors import ParserError


class Parser:
    """Recursive descent parser for NoBASIC."""

    def __init__(self):
        self.tokens: List[Token] = []
        self.current = 0

    def parse(self, tokens: List[Token], filename: str = "<unknown>") -> Program:
        """
        Parse tokens into an AST.

        Args:
            tokens: List of tokens from the lexer
            filename: Source filename for error reporting

        Returns:
            Program AST node

        Raises:
            ParserError: If parsing fails
        """
        self.tokens = tokens
        self.current = 0
        self.filename = filename

        statements = []
        while not self.is_at_end():
            if self.peek().type == TokenType.NEWLINE:
                self.advance()
                continue
            if self.peek().type == TokenType.END:
                break  # END terminates the program
            stmt = self.parse_statement()
            if stmt:
                statements.append(stmt)

        return Program(statements)

    def parse_statement(self) -> Statement:
        """Parse a statement."""
        token = self.peek()

        if token.type == TokenType.CLRHOME:
            return self.parse_clrhome()
        elif token.type == TokenType.DISP:
            return self.parse_disp()
        elif token.type == TokenType.INPUT:
            return self.parse_input()
        elif token.type == TokenType.PROMPT:
            return self.parse_prompt()
        elif token.type == TokenType.DIM:
            return self.parse_dim()
        elif token.type == TokenType.IDENTIFIER:
            return self.parse_assignment_or_call()
        elif token.type == TokenType.IF:
            return self.parse_if()
        elif token.type == TokenType.FOR:
            return self.parse_for()
        elif token.type == TokenType.WHILE:
            return self.parse_while()
        elif token.type == TokenType.DO:
            return self.parse_do_loop()
        elif token.type == TokenType.REPEAT:
            return self.parse_repeat_until()
        elif token.type == TokenType.SELECT:
            return self.parse_select()
        elif token.type == TokenType.CALL:
            return self.parse_call()
        elif token.type == TokenType.RETURN:
            return self.parse_return()
        elif token.type == TokenType.PAUSE:
            return self.parse_pause()
        elif token.type == TokenType.BREAK:
            return self.parse_break()
        elif token.type == TokenType.CONTINUE:
            return self.parse_continue()
        elif token.type == TokenType.DEFINE:
            return self.parse_define()
        elif token.type == TokenType.GOTO:
            return self.parse_goto()
        elif token.type == TokenType.LBL:
            return self.parse_label()
        elif token.type == TokenType.TRY:
            return self.parse_try_catch()
        elif token.type == TokenType.STRUCT:
            return self.parse_struct()
        elif token.type == TokenType.SPLAY:
            return self.parse_splay()
        elif token.type == TokenType.PLAY:
            return self.parse_play()
        elif token.type == TokenType.STOP:
            return self.parse_stop()
        else:
            raise self.error(f"Unexpected token: {token.type}")

    def parse_clrhome(self) -> ClrHomeStmt:
        """Parse ClrHome statement."""
        self.consume(TokenType.CLRHOME, "Expected 'ClrHome'")
        return ClrHomeStmt()

    def parse_dim(self) -> Statement:
        """Parse DIM statement (array or struct instance)."""
        self.consume(TokenType.DIM, "Expected 'DIM'")
        var_name = self.consume(TokenType.IDENTIFIER, "Expected variable name").value
        
        if self.match(TokenType.AS):
            # Struct instance: DIM var AS type
            struct_name = self.consume(TokenType.IDENTIFIER, "Expected struct type name").value
            return StructInstanceStmt(var_name, struct_name)
        else:
            # Array declaration: DIM array(size)
            self.consume(TokenType.LPAREN, "Expected '(' after array name")
            size = self.parse_expression()
            self.consume(TokenType.RPAREN, "Expected ')' after array size")
            return DimStmt(var_name, size)

    def parse_disp(self) -> DispStmt:
        """Parse Disp statement."""
        self.consume(TokenType.DISP, "Expected 'Disp'")
        expressions = []

        # Parse expressions separated by commas
        while not self.check(TokenType.NEWLINE) and not self.is_at_end():
            expr = self.parse_expression()
            expressions.append(expr)
            if self.match(TokenType.COMMA):
                continue
            else:
                break

        return DispStmt(expressions)

    def parse_input(self) -> InputStmt:
        """Parse Input statement."""
        self.consume(TokenType.INPUT, "Expected 'Input'")
        prompt = None

        # Optional string prompt
        if self.check(TokenType.STRING):
            prompt = self.advance().value

        # Variable to store input
        if not self.check(TokenType.IDENTIFIER):
            raise self.error("Expected variable name after Input")
        variable = self.advance().value

        return InputStmt(prompt, variable)

    def parse_prompt(self) -> InputStmt:
        """Parse Prompt statement."""
        self.consume(TokenType.PROMPT, "Expected 'Prompt'")
        
        # Variable to store input
        if not self.check(TokenType.IDENTIFIER):
            raise self.error("Expected variable name after Prompt")
        variable = self.advance().value

        return InputStmt(None, variable)

    def parse_assignment_or_call(self) -> Statement:
        """Parse assignment or subroutine call."""
        # Parse variable or array access
        if self.peek().type == TokenType.IDENTIFIER:
            name = self.advance().value
            if self.match(TokenType.LBRACKET):
                # Array access with brackets: A[1]
                index = self.parse_expression()
                self.consume(TokenType.RBRACKET, "Expected ']' after array index")
                target = ArrayAccessExpr(name, index)
            elif self.match(TokenType.DOT):
                # Struct field access: var.field
                field_name = self.consume(TokenType.IDENTIFIER, "Expected field name after '.'").value
                target = StructFieldAccessExpr(name, field_name)
            elif self.match(TokenType.LPAREN):
                # Check if this is a function call or array access with parentheses
                known_functions = {'ABS', 'INT', 'STR', 'LEN', 'VAL', 'ASC', 'CHR', 'SIN', 'COS', 'TAN', 'SQRT', 'LOG', 'EXP', 'RND', 'MIN', 'MAX', 'COLOR', 'RAMP', 'SHADE', 'KEYIN', 'KEYSTAT', 'LOWER', 'UPPER', 'LEFT', 'RIGHT', 'MID', 'INSTR', 'MEMSET', 'MEMCPY', 'MEMTEST', 'MEMMOVE', 'MEMSWAP', 'TRIM', 'REPLACE', 'SPLIT', 'JOIN', 'PXLON', 'PXLOFF', 'PXLCHANGE', 'PTON', 'PTOFF', 'PTCHANGE', 'PLAY', 'SOUND', 'LINE', 'CIRCLE', 'RECT', 'FILL', 'POW', 'SPLAY', 'STOP', 'INVALID_FUNCTION'}
                if name.upper() in known_functions:
                    # Function call
                    args = [self.parse_expression()]  # Already consumed the first arg start
                    while self.match(TokenType.COMMA):
                        args.append(self.parse_expression())
                    self.consume(TokenType.RPAREN, "Expected ')' after function arguments")
                    return CallStmt(name, args)
                else:
                    # Array access with parentheses: A(1)
                    index = self.parse_expression()
                    self.consume(TokenType.RPAREN, "Expected ')' after array index")
                    target = ArrayAccessExpr(name, index)
            else:
                target = VariableExpr(name)
        else:
            raise self.error("Expected identifier")

        if self.match(TokenType.EQUALS):
            # Assignment: var = expr or array[index] = expr or struct.field = expr
            expr = self.parse_expression()
            return AssignmentStmt(target, expr)
        elif self.match(TokenType.LPAREN):
            # Function call on variable (rare)
            args = []
            if not self.check(TokenType.RPAREN):
                args.append(self.parse_expression())
                while self.match(TokenType.COMMA):
                    args.append(self.parse_expression())
            self.consume(TokenType.RPAREN, "Expected ')' after function arguments")
            if isinstance(target, VariableExpr):
                return CallStmt(target.name, args)
            else:
                raise self.error("Cannot call function on array access")
        else:
            raise self.error("Expected '=' for assignment or '(' for function call")

    def parse_if(self) -> IfStmt:
        """Parse If statement."""
        self.consume(TokenType.IF, "Expected 'If'")
        condition = self.parse_expression()
        
        # THEN is optional in NoBASIC
        self.match(TokenType.THEN)

        then_stmts = []
        elif_clauses = []
        else_stmts = []

        # Parse Then block
        while not self.check(TokenType.ELSE) and not self.check(TokenType.ELSEIF) and not self.check(TokenType.END):
            if self.check(TokenType.NEWLINE):
                self.advance()
                continue
            then_stmts.append(self.parse_statement())

        # Parse Elif clauses
        while self.match(TokenType.ELSEIF):
            elif_condition = self.parse_expression()
            # THEN is optional in NoBASIC
            self.match(TokenType.THEN)
            elif_statements = []
            while not self.check(TokenType.ELSE) and not self.check(TokenType.ELSEIF) and not self.check(TokenType.END):
                if self.check(TokenType.NEWLINE):
                    self.advance()
                    continue
                elif_statements.append(self.parse_statement())
            elif_clauses.append(ElifClause(elif_condition, elif_statements))

        # Parse Else block
        if self.match(TokenType.ELSE):
            while not self.check(TokenType.END):
                if self.check(TokenType.NEWLINE):
                    self.advance()
                    continue
                else_stmts.append(self.parse_statement())

        # Expect END IF (not just END)
        self.consume(TokenType.END, "Expected 'End' to close If statement")
        if not self.match(TokenType.IF):
            # Allow just END for backward compatibility, but warn
            pass

        return IfStmt(condition, then_stmts, elif_clauses, else_stmts)

    def parse_for(self) -> ForStmt:
        """Parse For loop."""
        self.consume(TokenType.FOR, "Expected 'For'")
        variable = self.consume(TokenType.IDENTIFIER, "Expected variable name").value
        self.consume(TokenType.EQUALS, "Expected '=' in For loop")
        start = self.parse_expression()
        self.consume(TokenType.TO, "Expected 'To' in For loop")
        end = self.parse_expression()
        step = None
        if self.match(TokenType.STEP):
            step = self.parse_expression()

        statements = []
        while not self.check(TokenType.NEXT) and not self.check(TokenType.END):
            if self.check(TokenType.NEWLINE):
                self.advance()
                continue
            statements.append(self.parse_statement())

        if self.check(TokenType.END):
            self.consume(TokenType.END, "Unexpected 'End' in For loop")
        else:
            self.consume(TokenType.NEXT, "Expected 'Next' to close For loop")
            # Optional variable name after Next
            if self.check(TokenType.IDENTIFIER):
                self.advance()

        return ForStmt(variable, start, end, step, statements)

    def parse_while(self) -> WhileStmt:
        """Parse While loop."""
        self.consume(TokenType.WHILE, "Expected 'While'")
        condition = self.parse_expression()

        statements = []
        while not self.check(TokenType.WEND):
            if self.check(TokenType.NEWLINE):
                self.advance()
                continue
            statements.append(self.parse_statement())

        self.consume(TokenType.WEND, "Expected 'Wend' to close While loop")

        return WhileStmt(condition, statements)

    def parse_do_loop(self) -> DoLoopStmt:
        """Parse Do/Loop."""
        self.consume(TokenType.DO, "Expected 'Do'")

        # Check for initial condition (DO WHILE/DO UNTIL)
        initial_condition = None
        initial_type = None
        if self.match(TokenType.WHILE):
            initial_condition = self.parse_expression()
            initial_type = "while"
        elif self.match(TokenType.UNTIL):
            initial_condition = self.parse_expression()
            initial_type = "until"

        statements = []
        while not self.check(TokenType.LOOP):
            if self.check(TokenType.NEWLINE):
                self.advance()
                continue
            statements.append(self.parse_statement())

        self.consume(TokenType.LOOP, "Expected 'Loop' to close Do loop")

        # Check for ending condition (LOOP WHILE/LOOP UNTIL)
        end_condition = None
        end_type = None
        if self.match(TokenType.WHILE):
            end_condition = self.parse_expression()
            end_type = "while"
        elif self.match(TokenType.UNTIL):
            end_condition = self.parse_expression()
            end_type = "until"

        # Determine which condition to use (prefer ending condition if both present)
        condition = end_condition or initial_condition
        loop_type = end_type or initial_type or "unconditional"

        return DoLoopStmt(statements, condition, loop_type)

    def parse_repeat_until(self) -> RepeatUntilStmt:
        """Parse Repeat/Until."""
        self.consume(TokenType.REPEAT, "Expected 'Repeat'")

        statements = []
        while not self.check(TokenType.UNTIL):
            if self.check(TokenType.NEWLINE):
                self.advance()
                continue
            statements.append(self.parse_statement())

        self.consume(TokenType.UNTIL, "Expected 'Until'")
        condition = self.parse_expression()

        return RepeatUntilStmt(statements, condition)

    def parse_try_catch(self) -> TryCatchStmt:
        """Parse Try/Catch statement."""
        self.consume(TokenType.TRY, "Expected 'Try'")
        
        try_stmts = []
        while not self.check(TokenType.CATCH) and not self.check(TokenType.END):
            if self.check(TokenType.NEWLINE):
                self.advance()
                continue
            try_stmts.append(self.parse_statement())
        
        self.consume(TokenType.CATCH, "Expected 'Catch' after Try block")
        
        catch_stmts = []
        while not self.check(TokenType.END):
            if self.check(TokenType.NEWLINE):
                self.advance()
                continue
            catch_stmts.append(self.parse_statement())
        
        self.consume(TokenType.END, "Expected 'End' to close Try statement")
        if not self.match(TokenType.TRY):
            # Allow just END for backward compatibility
            pass
        
        return TryCatchStmt(try_stmts, catch_stmts)

    def parse_struct(self) -> StructStmt:
        """Parse Struct definition."""
        self.consume(TokenType.STRUCT, "Expected 'Struct'")
        name = self.consume(TokenType.IDENTIFIER, "Expected struct name").value
        
        fields = []
        while not self.check(TokenType.END):
            if self.check(TokenType.NEWLINE):
                self.advance()
                continue
            # Parse field name
            field_name = self.consume(TokenType.IDENTIFIER, "Expected field name").value
            # For now, assume all fields are integers (we can extend this later)
            field_type = "integer"
            fields.append(StructField(field_name, field_type))
        
        self.consume(TokenType.END, "Expected 'End' to close Struct definition")
        # Optional "Struct" after End
        self.match(TokenType.STRUCT)
        
        return StructStmt(name, fields)

    def parse_struct_field(self) -> StructField:
        """Parse a field in a struct."""
        name = self.consume(TokenType.IDENTIFIER, "Expected field name").value
        self.consume(TokenType.COLON, "Expected ':' after field name")
        type_name = self.consume(TokenType.IDENTIFIER, "Expected type name").value
        return StructField(name, type_name)

    def parse_splay(self) -> CallStmt:
        """Parse SPLAY statement."""
        self.consume(TokenType.SPLAY, "Expected 'SPLAY'")
        return CallStmt("SPLAY", [])

    def parse_play(self) -> CallStmt:
        """Parse PLAY statement or function call."""
        self.consume(TokenType.PLAY, "Expected 'PLAY'")
        if self.match(TokenType.LPAREN):
            # Function call with arguments
            args = []
            if not self.check(TokenType.RPAREN):
                args.append(self.parse_expression())
                while self.match(TokenType.COMMA):
                    args.append(self.parse_expression())
            self.consume(TokenType.RPAREN, "Expected ')' after PLAY arguments")
            return CallStmt("PLAY", args)
        else:
            # Statement with no arguments
            return CallStmt("PLAY", [])

    def parse_stop(self) -> CallStmt:
        """Parse STOP statement."""
        self.consume(TokenType.STOP, "Expected 'STOP'")
        return CallStmt("STOP", [])

    def parse_select(self) -> SelectStmt:
        """Parse Select Case statement."""
        self.consume(TokenType.SELECT, "Expected 'Select'")
        self.consume(TokenType.CASE, "Expected 'Case' after Select")
        expression = self.parse_expression()

        cases = []
        else_stmts = []

        while not self.check(TokenType.END):
            if self.check(TokenType.NEWLINE):
                self.advance()
                continue
            if self.match(TokenType.CASE):
                # Parse case values
                values = []
                if not self.check(TokenType.NEWLINE) and not self.check(TokenType.END) and not self.check(TokenType.ELSE):
                    values.append(self.parse_expression())
                    while self.match(TokenType.COMMA):
                        values.append(self.parse_expression())

                # Parse case statements
                case_stmts = []
                while not self.check(TokenType.CASE) and not self.check(TokenType.END) and not self.check(TokenType.ELSE):
                    if self.check(TokenType.NEWLINE):
                        self.advance()
                        continue
                    case_stmts.append(self.parse_statement())

                cases.append(CaseClause(values, case_stmts))
            elif self.match(TokenType.ELSE):
                # Parse else statements
                while not self.check(TokenType.END):
                    if self.check(TokenType.NEWLINE):
                        self.advance()
                        continue
                    else_stmts.append(self.parse_statement())
            else:
                break

        self.consume(TokenType.END, "Expected 'End' to close Select statement")
        if not self.match(TokenType.SELECT):
            # Allow just END for backward compatibility
            pass

        return SelectStmt(expression, cases, else_stmts)

    def parse_call(self) -> CallStmt:
        """Parse Call statement."""
        self.consume(TokenType.CALL, "Expected 'Call'")
        subroutine = self.consume(TokenType.IDENTIFIER, "Expected subroutine name").value
        return CallStmt(subroutine)

    def parse_return(self) -> ReturnStmt:
        """Parse Return statement."""
        self.consume(TokenType.RETURN, "Expected 'Return'")
        return ReturnStmt()

    def parse_pause(self) -> Statement:
        """Parse Pause statement."""
        self.consume(TokenType.PAUSE, "Expected 'Pause'")
        # Optional delay argument
        delay = None
        if self.check(TokenType.NUMBER):
            delay = self.parse_expression()
        return PauseStmt()

    def parse_break(self) -> BreakStmt:
        """Parse Break statement."""
        self.consume(TokenType.BREAK, "Expected 'Break'")
        return BreakStmt()

    def parse_continue(self) -> ContinueStmt:
        """Parse Continue statement."""
        self.consume(TokenType.CONTINUE, "Expected 'Continue'")
        return ContinueStmt()

    def parse_expression(self) -> Expression:
        """Parse an expression with binary operators."""
        return self.parse_binary_expression()

    def parse_binary_expression(self, precedence: int = 0) -> Expression:
        """Parse binary expression with precedence."""
        left = self.parse_primary()

        while True:
            token = self.peek()
            if token.type not in (TokenType.PLUS, TokenType.MINUS, TokenType.MULTIPLY, 
                                  TokenType.DIVIDE, TokenType.POWER, TokenType.EQUALS,
                                  TokenType.NOT_EQUALS, TokenType.LESS, TokenType.GREATER,
                                  TokenType.LESS_EQUAL, TokenType.GREATER_EQUAL,
                                  TokenType.AND, TokenType.OR, TokenType.XOR,
                                  TokenType.MOD, TokenType.SHL, TokenType.SHR,
                                  TokenType.AMPERSAND):
                break

            # Get precedence
            op_precedence = self.get_precedence(token.type)
            if op_precedence < precedence:
                break

            # Consume operator
            op = token.value
            self.advance()

            # Parse right operand
            right = self.parse_binary_expression(op_precedence + 1)

            left = BinaryExpr(left, op, right)

        return left

    def get_precedence(self, token_type: TokenType) -> int:
        """Get operator precedence."""
        precedences = {
            TokenType.OR: 1,
            TokenType.AND: 2,
            TokenType.XOR: 3,
            TokenType.EQUALS: 4,
            TokenType.NOT_EQUALS: 4,
            TokenType.LESS: 4,
            TokenType.GREATER: 4,
            TokenType.LESS_EQUAL: 4,
            TokenType.GREATER_EQUAL: 4,
            TokenType.AMPERSAND: 5,
            TokenType.SHL: 5,
            TokenType.SHR: 5,
            TokenType.PLUS: 6,
            TokenType.MINUS: 6,
            TokenType.MULTIPLY: 7,
            TokenType.DIVIDE: 7,
            TokenType.MOD: 7,
            TokenType.POWER: 8,
        }
        return precedences.get(token_type, 0)

    def parse_primary(self) -> Expression:
        token = self.peek()

        # Handle unary operators
        if self.match(TokenType.MINUS):
            # Unary minus
            operand = self.parse_primary()
            return UnaryExpr("-", operand)
        elif self.match(TokenType.NOT):
            # Unary NOT
            operand = self.parse_primary()
            return UnaryExpr("NOT", operand)

        if self.match(TokenType.LBRACKET):
            # Array literal
            elements = []
            if not self.check(TokenType.RBRACKET):
                elements.append(self.parse_expression())
                while self.match(TokenType.COMMA):
                    elements.append(self.parse_expression())
            self.consume(TokenType.RBRACKET, "Expected ']' after array elements")
            return ArrayLiteralExpr(elements)
        elif self.match(TokenType.LPAREN):
            # Parenthesized expression
            expr = self.parse_expression()
            self.consume(TokenType.RPAREN, "Expected ')' after expression")
            return expr
        elif token.type == TokenType.NUMBER:
            self.advance()
            return LiteralExpr(int(token.value, 0))
        elif token.type == TokenType.STRING:
            self.advance()
            return LiteralExpr(token.value)
        elif token.type == TokenType.TRUE:
            self.advance()
            return LiteralExpr(1)  # TRUE = 1
        elif token.type == TokenType.FALSE:
            self.advance()
            return LiteralExpr(0)  # FALSE = 0
        elif token.type == TokenType.IDENTIFIER:
            self.advance()
            name = token.value
            if self.match(TokenType.LPAREN):
                # Could be function call or array access with parentheses
                args = []
                if not self.check(TokenType.RPAREN):
                    args.append(self.parse_expression())
                    while self.match(TokenType.COMMA):
                        args.append(self.parse_expression())
                self.consume(TokenType.RPAREN, "Expected ')' after arguments")
                
                # Check if this looks like a function call (multiple args or specific function names)
                # For now, if it's a single argument and not a known function, treat as array access
                known_functions = {'ABS', 'INT', 'STR', 'LEN', 'VAL', 'ASC', 'CHR', 'SIN', 'COS', 'TAN', 'SQRT', 'LOG', 'EXP', 'RND', 'MIN', 'MAX', 'COLOR', 'RAMP', 'SHADE', 'KEYIN', 'KEYSTAT', 'LOWER', 'UPPER', 'LEFT', 'RIGHT', 'MID', 'INSTR', 'MEMSET', 'MEMCPY', 'MEMTEST', 'MEMMOVE', 'MEMSWAP', 'TRIM', 'REPLACE', 'SPLIT', 'JOIN', 'PXLON', 'PXLOFF', 'PXLCHANGE', 'PTON', 'PTOFF', 'PTCHANGE', 'PLAY', 'SOUND', 'LINE', 'CIRCLE', 'RECT', 'FILL', 'POW'}
                if len(args) == 1 and name.upper() not in known_functions:
                    return ArrayAccessExpr(name, args[0])
                else:
                    return FunctionCallExpr(name, args)
            elif self.match(TokenType.LBRACKET):
                # Array access
                index = self.parse_expression()
                self.consume(TokenType.RBRACKET, "Expected ']' after array index")
                return ArrayAccessExpr(name, index)
            elif self.match(TokenType.DOT):
                # Struct field access
                field_name = self.consume(TokenType.IDENTIFIER, "Expected field name after '.'").value
                return StructFieldAccessExpr(name, field_name)
            else:
                return VariableExpr(name)
        else:
            raise self.error(f"Unexpected token in expression: {token.type}")

    # Helper methods
    def advance(self) -> Token:
        """Consume and return the current token."""
        if not self.is_at_end():
            self.current += 1
        return self.previous()

    def peek(self) -> Token:
        """Look at the current token without consuming it."""
        return self.tokens[self.current]

    def previous(self) -> Token:
        """Return the most recently consumed token."""
        return self.tokens[self.current - 1]

    def is_at_end(self) -> bool:
        """Check if we've reached the end of tokens."""
        return self.current >= len(self.tokens) or self.peek().type == TokenType.EOF

    def check(self, type: TokenType) -> bool:
        """Check if the current token matches the given type."""
        if self.is_at_end():
            return False
        return self.peek().type == type

    def match(self, *types: TokenType) -> bool:
        """Consume the current token if it matches any of the given types."""
        for type in types:
            if self.check(type):
                self.advance()
                return True
        return False

    def consume(self, type: TokenType, message: str) -> Token:
        """Consume a token of the given type or raise an error."""
        if self.check(type):
            return self.advance()
        raise self.error(message)

    def parse_define(self) -> DefineStmt:
        """Parse Define statement."""
        self.consume(TokenType.DEFINE, "Expected 'Define'")
        name = self.consume(TokenType.IDENTIFIER, "Expected subroutine name").value
        
        statements = []
        while not self.check(TokenType.RETURN) and not self.check(TokenType.END):
            if self.check(TokenType.NEWLINE):
                self.advance()
                continue
            statements.append(self.parse_statement())
        
        # Parse the Return statement
        if self.match(TokenType.RETURN):
            statements.append(ReturnStmt())
        
        return DefineStmt(name, statements)

    def parse_goto(self) -> GotoStmt:
        """Parse Goto statement."""
        self.consume(TokenType.GOTO, "Expected 'Goto'")
        label = self.consume(TokenType.IDENTIFIER, "Expected label name").value
        return GotoStmt(label)

    def parse_label(self) -> LabelStmt:
        """Parse Label statement."""
        self.consume(TokenType.LBL, "Expected 'Lbl'")
        name = self.consume(TokenType.IDENTIFIER, "Expected label name").value
        return LabelStmt(name)

    def error(self, message: str) -> ParserError:
        """Create a parser error."""
        token = self.peek()
        return ParserError(message, token.filename, token.line, token.column)