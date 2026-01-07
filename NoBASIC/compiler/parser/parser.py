"""
NoBASIC Parser Implementation
"""

from typing import List, Optional

from ..utils.error import ParserError
from ..lexer.tokens import Token, TokenType
from .ast import (
    Program, Statement, Expression, ClrDrawStmt, PxlOnStmt, PxlOffStmt,
    LineStmt, CircleStmt, TextStmt, SetLayerStmt, SpriteOnStmt, SpriteOffStmt,
    PlayToneStmt, PlayWaveStmt, StopSoundStmt, SetChannelStmt, GetKeyStmt,
    InputStmt, DispStmt, PauseStmt, FunctionCallStmt, ExpressionStmt, AssignmentStmt, IfStmt, ForStmt,
    WhileStmt, RepeatStmt, GotoStmt, LabelStmt, StructDeclarationStmt, VarDeclarationStmt,
    AsmBlockStmt, FunctionDefStmt, ReturnStmt, LiteralExpr, VariableExpr, ListAccessExpr, 
    MatrixAccessExpr, MemberAccessExpr, BinaryExpr, UnaryExpr, FunctionCallExpr, GroupingExpr, 
    DataType, VarScope
)


class Parser:
    """Recursive descent parser for NoBASIC."""

    def __init__(self):
        self.tokens = []
        self.current = 0
        self.filename = "<stdin>"

    def parse(self, tokens: List[Token], filename: str = "<stdin>") -> Program:
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
            statements.append(self.statement())

        return Program(statements)

    def statement(self) -> Statement:
        """Parse a statement."""
        token = self.peek()

        if token.type == TokenType.CLRDRAW:
            self.advance()
            return ClrDrawStmt()
        elif token.type == TokenType.GLOBAL:
            return self.var_declaration_statement(VarScope.GLOBAL)
        elif token.type == TokenType.LOCAL:
            return self.var_declaration_statement(VarScope.LOCAL)
        elif token.type == TokenType.FUNCTION:
            return self.function_definition()
        elif token.type == TokenType.RETURN:
            return self.return_statement()
        elif token.type == TokenType.ASM:
            return self.asm_block_statement()
        elif token.type == TokenType.PXLON:
            return self.pxl_on_statement()
        elif token.type == TokenType.PXLOFF:
            return self.pxl_off_statement()
        elif token.type == TokenType.LINE:
            return self.line_statement()
        elif token.type == TokenType.CIRCLE:
            return self.circle_statement()
        elif token.type == TokenType.TEXT:
            return self.text_statement()
        elif token.type == TokenType.SETLAYER:
            return self.set_layer_statement()
        elif token.type == TokenType.SPRITEON:
            return self.sprite_on_statement()
        elif token.type == TokenType.SPRITEOFF:
            return self.sprite_off_statement()
        elif token.type == TokenType.PLAYTONE:
            return self.play_tone_statement()
        elif token.type == TokenType.PLAYWAVE:
            return self.play_wave_statement()
        elif token.type == TokenType.STOPSOUND:
            self.advance()
            return StopSoundStmt()
        elif token.type == TokenType.SETCHANNEL:
            return self.set_channel_statement()
        elif token.type == TokenType.GETKEY:
            self.advance()
            return GetKeyStmt()
        elif token.type == TokenType.INPUT:
            return self.input_statement()
        elif token.type == TokenType.DISP:
            return self.disp_statement()
        elif token.type == TokenType.PAUSE:
            self.advance()
            return PauseStmt()
        elif token.type == TokenType.IF:
            return self.if_statement()
        elif token.type == TokenType.FOR:
            return self.for_statement()
        elif token.type == TokenType.WHILE:
            return self.while_statement()
        elif token.type == TokenType.REPEAT:
            return self.repeat_statement()
        elif token.type == TokenType.GOTO:
            return self.goto_statement()
        elif token.type == TokenType.STRUCT:
            return self.struct_declaration()
        elif token.type == TokenType.IDENTIFIER and self.check_next(TokenType.COLON):
            return self.label_statement()
        elif token.type == TokenType.IDENTIFIER and self._is_builtin_function_name(token.lexeme):
            return self.assignment_statement()
        elif token.type == TokenType.IDENTIFIER:
            return self.assignment_statement()
        elif self._is_function_token(token.type):
            # Handle built-in functions that can be called as statements (like randomize())
            return self.assignment_statement()
        else:
            raise self.error("Expected statement")

    def pxl_on_statement(self) -> PxlOnStmt:
        """Parse PxlOn(x, y, color)"""
        self.advance()  # consume PXLON
        self.consume(TokenType.LPAREN, "Expected '(' after PxlOn")
        x_expr = self.expression()
        self.consume(TokenType.COMMA, "Expected ',' after x")
        y_expr = self.expression()
        self.consume(TokenType.COMMA, "Expected ',' after y")
        color_expr = self.expression()
        self.consume(TokenType.RPAREN, "Expected ')' after color")
        return PxlOnStmt(x=x_expr, y=y_expr, color=color_expr)

    def pxl_off_statement(self) -> PxlOffStmt:
        """Parse PxlOff(x, y)"""
        self.advance()  # consume PXLOFF
        self.consume(TokenType.LPAREN, "Expected '(' after PxlOff")
        x = self.expression()
        self.consume(TokenType.COMMA, "Expected ',' after x")
        y = self.expression()
        self.consume(TokenType.RPAREN, "Expected ')' after y")
        return PxlOffStmt(x, y)

    def line_statement(self) -> LineStmt:
        """Parse Line(x1, y1, x2, y2, color)"""
        self.advance()  # consume LINE
        self.consume(TokenType.LPAREN, "Expected '(' after Line")
        x1 = self.expression()
        self.consume(TokenType.COMMA, "Expected ',' after x1")
        y1 = self.expression()
        self.consume(TokenType.COMMA, "Expected ',' after y1")
        x2 = self.expression()
        self.consume(TokenType.COMMA, "Expected ',' after x2")
        y2 = self.expression()
        self.consume(TokenType.COMMA, "Expected ',' after y2")
        color = self.expression()
        self.consume(TokenType.RPAREN, "Expected ')' after color")
        return LineStmt(x1, y1, x2, y2, color)

    def circle_statement(self) -> CircleStmt:
        """Parse Circle(x, y, radius, color)"""
        self.advance()  # consume CIRCLE
        self.consume(TokenType.LPAREN, "Expected '(' after Circle")
        x = self.expression()
        self.consume(TokenType.COMMA, "Expected ',' after x")
        y = self.expression()
        self.consume(TokenType.COMMA, "Expected ',' after y")
        radius = self.expression()
        self.consume(TokenType.COMMA, "Expected ',' after radius")
        color = self.expression()
        self.consume(TokenType.RPAREN, "Expected ')' after color")
        return CircleStmt(x, y, radius, color)

    def text_statement(self) -> TextStmt:
        """Parse Text(x, y, "string", color)"""
        self.advance()  # consume TEXT
        self.consume(TokenType.LPAREN, "Expected '(' after Text")
        x = self.expression()
        self.consume(TokenType.COMMA, "Expected ',' after x")
        y = self.expression()
        self.consume(TokenType.COMMA, "Expected ',' after y")
        text = self.expression()
        self.consume(TokenType.COMMA, "Expected ',' after text")
        color = self.expression()
        self.consume(TokenType.RPAREN, "Expected ')' after color")
        return TextStmt(x, y, text, color)

    def set_layer_statement(self) -> SetLayerStmt:
        """Parse SetLayer(layer)"""
        self.advance()  # consume SETLAYER
        self.consume(TokenType.LPAREN, "Expected '(' after SetLayer")
        layer = self.expression()
        self.consume(TokenType.RPAREN, "Expected ')' after layer")
        return SetLayerStmt(layer)

    def sprite_on_statement(self) -> SpriteOnStmt:
        """Parse SpriteOn(spriteId, x, y)"""
        self.advance()  # consume SPRITEON
        self.consume(TokenType.LPAREN, "Expected '(' after SpriteOn")
        sprite_id = self.expression()
        self.consume(TokenType.COMMA, "Expected ',' after spriteId")
        x = self.expression()
        self.consume(TokenType.COMMA, "Expected ',' after x")
        y = self.expression()
        self.consume(TokenType.RPAREN, "Expected ')' after y")
        return SpriteOnStmt(sprite_id, x, y)

    def sprite_off_statement(self) -> SpriteOffStmt:
        """Parse SpriteOff(spriteId)"""
        self.advance()  # consume SPRITEOFF
        self.consume(TokenType.LPAREN, "Expected '(' after SpriteOff")
        sprite_id = self.expression()
        self.consume(TokenType.RPAREN, "Expected ')' after spriteId")
        return SpriteOffStmt(sprite_id)

    def play_tone_statement(self) -> PlayToneStmt:
        """Parse PlayTone(frequency, duration, volume)"""
        self.advance()  # consume PLAYTONE
        self.consume(TokenType.LPAREN, "Expected '(' after PlayTone")
        frequency = self.expression()
        self.consume(TokenType.COMMA, "Expected ',' after frequency")
        duration = self.expression()
        self.consume(TokenType.COMMA, "Expected ',' after duration")
        volume = self.expression()
        self.consume(TokenType.RPAREN, "Expected ')' after volume")
        return PlayToneStmt(frequency, duration, volume)

    def play_wave_statement(self) -> PlayWaveStmt:
        """Parse PlayWave(waveform, frequency, volume)"""
        self.advance()  # consume PLAYWAVE
        self.consume(TokenType.LPAREN, "Expected '(' after PlayWave")
        waveform = self.expression()
        self.consume(TokenType.COMMA, "Expected ',' after waveform")
        frequency = self.expression()
        self.consume(TokenType.COMMA, "Expected ',' after frequency")
        volume = self.expression()
        self.consume(TokenType.RPAREN, "Expected ')' after volume")
        return PlayWaveStmt(waveform, frequency, volume)

    def set_channel_statement(self) -> SetChannelStmt:
        """Parse SetChannel(channel)"""
        self.advance()  # consume SETCHANNEL
        self.consume(TokenType.LPAREN, "Expected '(' after SetChannel")
        channel = self.expression()
        self.consume(TokenType.RPAREN, "Expected ')' after channel")
        return SetChannelStmt(channel)

    def input_statement(self) -> InputStmt:
        """Parse Input "prompt", variable or Input(prompt, variable) or Input variable"""
        self.advance()  # consume INPUT

        # Check if it's a function call syntax: input(prompt, variable)
        if self.check(TokenType.LPAREN):
            self.consume(TokenType.LPAREN, "Expected '(' after Input")
            prompt = self.expression()
            self.consume(TokenType.COMMA, "Expected ',' after prompt")
            var_token = self.consume(TokenType.IDENTIFIER, "Expected variable name")
            variable = var_token.lexeme
            self.consume(TokenType.RPAREN, "Expected ')' after variable")
            return InputStmt(prompt, variable)
        else:
            # TI-83/84 style: Input "prompt", variable or Input variable
            if self.check(TokenType.STRING_LITERAL):
                prompt = self.expression()  # Parse the string literal
                self.consume(TokenType.COMMA, "Expected ',' after prompt")
                var_token = self.consume(TokenType.IDENTIFIER, "Expected variable name")
                variable = var_token.lexeme
            else:
                # No prompt, just variable
                prompt = None
                var_token = self.consume(TokenType.IDENTIFIER, "Expected variable name")
                variable = var_token.lexeme

            return InputStmt(prompt, variable)

    def disp_statement(self) -> DispStmt:
        """Parse Disp "text" or Disp expression"""
        self.advance()  # consume DISP
        text = self.expression()
        return DispStmt(text)

    def assignment_statement(self) -> Statement:
        """Parse assignment, function call, or expression statement."""
        variable = self.assignable_expression()
        if isinstance(variable, FunctionCallExpr) and not self.check(TokenType.EQUAL):
            # This is actually a function call statement
            return FunctionCallStmt(variable)
        elif isinstance(variable, UnaryExpr) and variable.operator in ("++", "--"):
            # This is an increment/decrement expression statement
            return ExpressionStmt(variable)
        elif not self.check(TokenType.EQUAL):
            # Invalid statement - expected assignment or valid expression
            raise self.error("Expected '=' after variable or valid statement")
        else:
            self.consume(TokenType.EQUAL, "Expected '=' after variable")
            expression = self.expression()
            return AssignmentStmt(variable, expression)

    def if_statement(self, consume_end: bool = True) -> IfStmt:
        """Parse If condition Then statements [Else [If] statements] [End]"""
        self.advance()  # consume IF
        condition = self.expression()
        self.consume(TokenType.THEN, "Expected 'Then' after condition")

        then_branch = []
        while not self.check(TokenType.ELSE) and not self.check(TokenType.END):
            then_branch.append(self.statement())

        else_branch = None
        if self.match(TokenType.ELSE):
            if self.check(TokenType.IF):
                # Else if - parse as nested if statement without consuming end
                else_branch = [self.if_statement(consume_end=False)]
            else:
                # Regular else
                else_branch = []
                while not self.check(TokenType.END):
                    else_branch.append(self.statement())

        if consume_end:
            self.consume(TokenType.END, "Expected 'End' after if statement")
        return IfStmt(condition, then_branch, else_branch)

    def for_statement(self) -> ForStmt:
        """Parse For variable = start To end [Step step] statements Next"""
        self.advance()  # consume FOR
        var_token = self.consume(TokenType.IDENTIFIER, "Expected variable name")
        variable = var_token.lexeme
        self.consume(TokenType.EQUAL, "Expected '=' after variable")
        start = self.expression()
        self.consume(TokenType.TO, "Expected 'To' after start")
        end = self.expression()

        step = None
        if self.match(TokenType.STEP):
            step = self.expression()

        body = []
        while not self.check(TokenType.NEXT) and not self.check(TokenType.END):
            body.append(self.statement())

        if self.match(TokenType.NEXT):
            pass
        elif self.match(TokenType.END):
            pass
        else:
            raise self.error("Expected 'Next' or 'End' after for body")
        return ForStmt(variable, start, end, step, body)

    def while_statement(self) -> WhileStmt:
        """Parse While condition statements End"""
        self.advance()  # consume WHILE
        condition = self.expression()

        body = []
        while not self.check(TokenType.END):
            body.append(self.statement())

        self.consume(TokenType.END, "Expected 'End' after while body")
        return WhileStmt(condition, body)

    def repeat_statement(self) -> RepeatStmt:
        """Parse Repeat statements Until condition"""
        self.advance()  # consume REPEAT

        body = []
        while not self.check(TokenType.UNTIL):
            body.append(self.statement())

        self.consume(TokenType.UNTIL, "Expected 'Until' after repeat body")
        condition = self.expression()
        return RepeatStmt(body, condition)

    def goto_statement(self) -> GotoStmt:
        """Parse Goto label"""
        self.advance()  # consume GOTO
        label_token = self.consume(TokenType.IDENTIFIER, "Expected label name")
        label = label_token.lexeme
        return GotoStmt(label)

    def label_statement(self) -> LabelStmt:
        """Parse identifier:"""
        label_token = self.consume(TokenType.IDENTIFIER, "Expected label name")
        label = label_token.lexeme
        self.consume(TokenType.COLON, "Expected ':' after label")
        return LabelStmt(label)

    def struct_declaration(self) -> StructDeclarationStmt:
        """Parse STRUCT name field1 field2 ... END"""
        self.consume(TokenType.STRUCT, "Expected 'STRUCT'")
        name_token = self.consume(TokenType.IDENTIFIER, "Expected struct name")
        name = name_token.lexeme
        
        fields = []
        while not self.check(TokenType.END) and not self.is_at_end():
            field_token = self.consume(TokenType.IDENTIFIER, "Expected field name")
            fields.append(field_token.lexeme)
        
        self.consume(TokenType.END, "Expected 'END' after struct fields")
        
        # Enforce max 10 fields constraint
        if len(fields) > 10:
            raise self.error(f"Struct '{name}' has {len(fields)} fields, maximum is 10")
        
        if len(fields) == 0:
            raise self.error(f"Struct '{name}' must have at least one field")
        
        return StructDeclarationStmt(name, fields)

    def var_declaration_statement(self, scope: VarScope) -> VarDeclarationStmt:
        """Parse GLOBAL/LOCAL variable [, variable, ...]"""
        self.advance()  # consume GLOBAL or LOCAL
        
        variables = []
        # Parse first variable
        var_token = self.consume(TokenType.IDENTIFIER, "Expected variable name")
        variables.append(var_token.lexeme)
        
        # Parse additional variables separated by commas
        while self.match(TokenType.COMMA):
            var_token = self.consume(TokenType.IDENTIFIER, "Expected variable name")
            variables.append(var_token.lexeme)
        
        return VarDeclarationStmt(scope, variables)

    def asm_block_statement(self) -> AsmBlockStmt:
        """
        Parse inline assembly block: Asm <assembly code> End
        The lexer has already captured the ASM token, ASM_BLOCK token, and END token.
        """
        # Consume the ASM token
        self.consume(TokenType.ASM, "Expected 'Asm'")
        
        # Get the assembly code from the ASM_BLOCK token
        asm_token = self.consume(TokenType.ASM_BLOCK, "Expected assembly code block")
        assembly_code = asm_token.literal if asm_token.literal is not None else ""
        
        # Consume the END token
        self.consume(TokenType.END, "Expected 'End' after assembly block")
        
        return AsmBlockStmt(assembly_code=assembly_code)

    def expression(self) -> Expression:
        """Parse an expression."""
        return self.logical_or()

    def logical_or(self) -> Expression:
        """Parse logical OR expressions."""
        expr = self.logical_and()

        while self.match(TokenType.OR):
            operator = "or"
            right = self.logical_and()
            expr = BinaryExpr(expr, operator, right)

        return expr

    def logical_and(self) -> Expression:
        """Parse logical AND expressions."""
        expr = self.bitwise_or()

        while self.match(TokenType.AND):
            operator = "and"
            right = self.bitwise_or()
            expr = BinaryExpr(expr, operator, right)

        return expr

    def bitwise_or(self) -> Expression:
        """Parse bitwise OR expressions."""
        expr = self.bitwise_and()

        while self.match(TokenType.BITWISE_OR):
            operator = "|"
            right = self.bitwise_and()
            expr = BinaryExpr(expr, operator, right)

        return expr

    def bitwise_and(self) -> Expression:
        """Parse bitwise AND expressions."""
        expr = self.equality()

        while self.match(TokenType.BITWISE_AND):
            operator = "&"
            right = self.equality()
            expr = BinaryExpr(expr, operator, right)

        return expr

    def equality(self) -> Expression:
        """Parse equality expressions."""
        expr = self.comparison()

        while self.match(TokenType.EQUAL, TokenType.NOT_EQUAL):
            operator = self.previous().lexeme
            right = self.comparison()
            expr = BinaryExpr(expr, operator, right)

        return expr

    def comparison(self) -> Expression:
        """Parse comparison expressions."""
        expr = self.term()

        while self.match(TokenType.LESS, TokenType.LESS_EQUAL, TokenType.GREATER, TokenType.GREATER_EQUAL):
            operator = self.previous().lexeme
            right = self.term()
            expr = BinaryExpr(expr, operator, right)

        return expr

    def term(self) -> Expression:
        """Parse addition and subtraction."""
        expr = self.shift()

        while self.match(TokenType.PLUS, TokenType.MINUS):
            operator = self.previous().lexeme
            right = self.shift()
            expr = BinaryExpr(expr, operator, right)

        return expr

    def shift(self) -> Expression:
        """Parse shift operations."""
        expr = self.factor()

        while self.match(TokenType.SHIFT_LEFT, TokenType.SHIFT_RIGHT):
            operator = self.previous().lexeme
            right = self.factor()
            expr = BinaryExpr(expr, operator, right)

        return expr

    def factor(self) -> Expression:
        """Parse multiplication and division."""
        expr = self.power()

        while self.match(TokenType.MULTIPLY, TokenType.DIVIDE):
            operator = self.previous().lexeme
            right = self.power()
            expr = BinaryExpr(expr, operator, right)

        return expr

    def power(self) -> Expression:
        """Parse exponentiation."""
        expr = self.unary()

        if self.match(TokenType.POWER):
            operator = "^"
            right = self.power()
            expr = BinaryExpr(expr, operator, right)

        return expr

    def unary(self) -> Expression:
        """Parse unary expressions, including prefix ++/--."""
        # Prefix increment/decrement: '++x' or '--x'
        if self.match(TokenType.INCREMENT):
            expr = self.unary()
            return UnaryExpr("++", expr, is_post=False)
        if self.match(TokenType.DECREMENT):
            expr = self.unary()
            return UnaryExpr("--", expr, is_post=False)
        # Existing unary operators
        if self.match(TokenType.MINUS, TokenType.NOT):
            operator = self.previous().lexeme
            expr = self.unary()
            return UnaryExpr(operator, expr)

        return self.call()

    def call(self) -> Expression:
        """Parse function calls, array access, member access, and primary expressions."""
        expr = self.primary()

        # Handle member access (obj.field)
        while self.match(TokenType.DOT):
            member_token = self.consume(TokenType.IDENTIFIER, "Expected member name after '.'")
            expr = MemberAccessExpr(expr, member_token.lexeme)

        if self.match(TokenType.LPAREN):
            # Check if this is list or matrix access (TI-83/84 style)
            if isinstance(expr, VariableExpr):
                if self.is_list_name(expr.name):
                    # List access: L1(1)
                    index = self.expression()
                    self.consume(TokenType.RPAREN, "Expected ')' after list index")
                    return ListAccessExpr(expr.name, index)
                elif self.is_matrix_name(expr.name):
                    # Matrix access: MatA(1,2)
                    row = self.expression()
                    self.consume(TokenType.COMMA, "Expected ',' after row index")
                    col = self.expression()
                    self.consume(TokenType.RPAREN, "Expected ')' after matrix indices")
                    return MatrixAccessExpr(expr.name, row, col)
                else:
                    # Function call
                    arguments = []
                    if not self.check(TokenType.RPAREN):
                        arguments.append(self.expression())
                        while self.match(TokenType.COMMA):
                            arguments.append(self.expression())
                    self.consume(TokenType.RPAREN, "Expected ')' after arguments")
                    return FunctionCallExpr(expr.name if isinstance(expr, VariableExpr) else str(expr), arguments)
            else:
                # Function call on expression
                arguments = []
                if not self.check(TokenType.RPAREN):
                    arguments.append(self.expression())
                    while self.match(TokenType.COMMA):
                        arguments.append(self.expression())
                self.consume(TokenType.RPAREN, "Expected ')' after arguments")
                return FunctionCallExpr(expr.name if isinstance(expr, VariableExpr) else str(expr), arguments)
        elif self.match(TokenType.LBRACKET):
            # Array access
            indices = []
            indices.append(self.expression())
            if self.match(TokenType.COMMA):
                # Matrix access: mat[row, col]
                indices.append(self.expression())
                self.consume(TokenType.RBRACKET, "Expected ']' after matrix indices")
                return MatrixAccessExpr(expr.name if isinstance(expr, VariableExpr) else str(expr), indices[0], indices[1])
            else:
                # List access: arr[index]
                self.consume(TokenType.RBRACKET, "Expected ']' after array index")
                return ListAccessExpr(expr.name if isinstance(expr, VariableExpr) else str(expr), indices[0])

        # Postfix increment/decrement: 'x++' or 'x--'
        if self.match(TokenType.INCREMENT):
            return UnaryExpr("++", expr, is_post=True)
        if self.match(TokenType.DECREMENT):
            return UnaryExpr("--", expr, is_post=True)

        return expr

    def primary(self) -> Expression:
        """Parse primary expressions."""
        if self.match(TokenType.NUMBER_LITERAL):
            return LiteralExpr(self.previous().literal, DataType.NUMBER)
        elif self.match(TokenType.STRING_LITERAL):
            return LiteralExpr(self.previous().literal, DataType.STRING)
        elif self.match(TokenType.IDENTIFIER, TokenType.DIM, TokenType.GETKEY):
            name = self.previous().lexeme
            return self.parse_identifier_or_function(name)
        # Match all built-in function tokens
        elif self._is_function_token(self.peek().type):
            token = self.advance()
            name = token.lexeme
            return VariableExpr(name)
        elif self.match(TokenType.LPAREN):
            expr = self.expression()
            self.consume(TokenType.RPAREN, "Expected ')' after expression")
            return GroupingExpr(expr)

        raise self.error("Expected expression")

    def is_list_name(self, name: str) -> bool:
        """Check if name is a TI-83/84 style list name (L followed by digits)."""
        if not name.startswith('L'):
            return False
        try:
            int(name[1:])
            return True  # Any L\d+ is a potential list name
        except ValueError:
            return False

    def is_matrix_name(self, name: str) -> bool:
        """Check if name is a TI-83/84 style matrix name (Mat followed by letter)."""
        if not name.startswith('Mat'):
            return False
        letter = name[3:]
        return len(letter) == 1 and letter.isalpha()  # Any MatX is a potential matrix name

    def _is_function_token(self, token_type: TokenType) -> bool:
        """Check if token type is a built-in function."""
        function_tokens = {
            TokenType.SIN, TokenType.COS, TokenType.TAN, TokenType.SQRT,
            TokenType.ABS, TokenType.INT, TokenType.ROUND, TokenType.RAND,
            TokenType.RNDR, TokenType.RANDOMIZE,
            TokenType.LENGTH, TokenType.SUB, TokenType.CONCAT,
            TokenType.SUM, TokenType.MEAN, TokenType.MEMREAD, TokenType.MEMWRITE
        }
        return token_type in function_tokens

    def _is_builtin_function_name(self, name: str) -> bool:
        """Check if name is a built-in function name."""
        return name.upper() in [
            # Original math functions
            "SIN", "COS", "TAN", "SQRT", "ABS", "RND", "RNDR", "RANDOMIZE", "LEN", "LENGTH",
            "MIN", "MAX", "LOG", "LN", "EXP", "POW", "INT", "ROUND",
            # Extended math functions
            "ATAN", "ASIN", "ACOS", "DEG", "RAD", "FLOOR", "CEIL", "TRUNC", "FRAC", "INTGR", "POWR",
            # String functions
            "STRLEN", "STRCPY", "STRCAT", "STRCMP", "STRUPR", "STRLWR", "STRREV",
            "STRFIND", "STRFINDI", "STREXT", "STREXTI",
            "INSTRING", "UPSTRING", "LOWSTRING", "LENSTRING",
            # Bit manipulation functions
            "BTST", "BSET", "BCLR", "BFLIP", "CLZ", "CTZ", "POPCNT",
            # Memory functions
            "MEMCPY", "MEMSET", "MEMTEST", "MEMMOVE", "MEMCMP", "MEMSWAP",
            # Enhanced arithmetic
            "ADC", "SBC", "MULH", "DIVH", "SWAP", "XCHNG", "MOVZ", "MOVNZ", "LEA",
            # Type conversion
            "ITOB", "BTOI", "ITOS", "STOI",
            # Shift and rotate functions
            "SHL", "SHR", "SAL", "SAR", "ROL", "ROR", "RCL", "RCR",
            # Bitwise logical functions
            "BAND", "BOR", "BXOR", "BNOT"
        ]

    def parse_identifier_or_function(self, name: str) -> Expression:
        """Parse identifier - just return variable expression."""
        return VariableExpr(name)

    def assignable_expression(self) -> Expression:
        """Parse expressions that can be assigned to (variables, list/matrix access, member access)."""
        expr = self.call()

        # Handle member access (obj.field)
        while self.match(TokenType.DOT):
            member_token = self.consume(TokenType.IDENTIFIER, "Expected member name after '.'")
            expr = MemberAccessExpr(expr, member_token.lexeme)

        if self.match(TokenType.LPAREN):
            # Check if this is list or matrix access (TI-83/84 style)
            if isinstance(expr, VariableExpr):
                if self.is_list_name(expr.name):
                    # List access: L1(1)
                    index = self.expression()
                    self.consume(TokenType.RPAREN, "Expected ')' after list index")
                    return ListAccessExpr(expr.name, index)
                elif self.is_matrix_name(expr.name):
                    # Matrix access: MatA(1,2)
                    row = self.expression()
                    self.consume(TokenType.COMMA, "Expected ',' after row index")
                    col = self.expression()
                    self.consume(TokenType.RPAREN, "Expected ')' after matrix indices")
                    return MatrixAccessExpr(expr.name, row, col)
                else:
                    # Function call - not assignable
                    arguments = []
                    if not self.check(TokenType.RPAREN):
                        arguments.append(self.expression())
                        while self.match(TokenType.COMMA):
                            arguments.append(self.expression())
                    self.consume(TokenType.RPAREN, "Expected ')' after arguments")
                    return FunctionCallExpr(expr.name, arguments)
            else:
                # Function call on expression - not assignable
                arguments = []
                if not self.check(TokenType.RPAREN):
                    arguments.append(self.expression())
                    while self.match(TokenType.COMMA):
                        arguments.append(self.expression())
                self.consume(TokenType.RPAREN, "Expected ')' after arguments")
                return FunctionCallExpr(str(expr), arguments)

        # Check for array access with brackets: arr[index] or mat[row, col]
        if self.match(TokenType.LBRACKET):
            indices = [self.expression()]
            if self.match(TokenType.COMMA):
                # Matrix access: mat[row, col]
                indices.append(self.expression())
                self.consume(TokenType.RBRACKET, "Expected ']' after matrix indices")
                return MatrixAccessExpr(expr.name if isinstance(expr, VariableExpr) else str(expr), indices[0], indices[1])
            else:
                # List access: arr[index]
                self.consume(TokenType.RBRACKET, "Expected ']' after array index")
                return ListAccessExpr(expr.name if isinstance(expr, VariableExpr) else str(expr), indices[0])

        return expr

    def function_definition(self) -> FunctionDefStmt:
        """Parse Function Name(param1 [= default], param2 [= default], ...) ... End"""
        self.consume(TokenType.FUNCTION, "Expected 'Function'")
        
        name_token = self.consume(TokenType.IDENTIFIER, "Expected function name")
        name = name_token.lexeme.lower()
        
        self.consume(TokenType.LPAREN, "Expected '(' after function name")
        
        # Parse parameters with optional defaults
        params = []
        if not self.check(TokenType.RPAREN):
            param_name = self.consume(TokenType.IDENTIFIER, "Expected parameter name").lexeme.lower()
            default_value = None
            if self.match(TokenType.EQUAL):
                default_value = self.expression()
            params.append((param_name, default_value))
            
            while self.match(TokenType.COMMA):
                param_name = self.consume(TokenType.IDENTIFIER, "Expected parameter name").lexeme.lower()
                default_value = None
                if self.match(TokenType.EQUAL):
                    default_value = self.expression()
                params.append((param_name, default_value))
        
        self.consume(TokenType.RPAREN, "Expected ')' after parameters")
        
        # Parse function body
        body = []
        while not self.check(TokenType.END) and not self.is_at_end():
            body.append(self.statement())
        
        self.consume(TokenType.END, "Expected 'End' to close function definition")
        
        return FunctionDefStmt(name, params, body)

    def return_statement(self) -> ReturnStmt:
        """Parse Return [expression]"""
        self.advance()  # consume RETURN
        
        # Check if there's a value to return
        value = None
        # Only parse value if not at end of line or at another statement keyword
        if not self.is_at_end() and \
           not self.check(TokenType.EOF) and \
           self.peek().line == self.previous().line:  # Same line as Return keyword
            
            # Don't parse if next token is a statement keyword
            next_token = self.peek()
            if next_token.type not in [TokenType.END, TokenType.ELSE, TokenType.NEXT]:
                value = self.expression()
        
        return ReturnStmt(value)

    # Helper methods
    def advance(self) -> Token:
        """Advance to the next token."""
        if not self.is_at_end():
            self.current += 1
        return self.previous()

    def peek(self) -> Token:
        """Look at the current token."""
        return self.tokens[self.current]

    def previous(self) -> Token:
        """Look at the previous token."""
        return self.tokens[self.current - 1]

    def is_at_end(self) -> bool:
        """Check if we've reached the end."""
        return self.peek().type == TokenType.EOF

    def check(self, token_type: TokenType) -> bool:
        """Check if the current token matches the type."""
        if self.is_at_end():
            return False
        return self.peek().type == token_type

    def check_next(self, token_type: TokenType) -> bool:
        """Check if the next token matches the type."""
        if self.current + 1 >= len(self.tokens):
            return False
        return self.tokens[self.current + 1].type == token_type

    def match(self, *token_types: TokenType) -> bool:
        """Match and consume one of the token types."""
        for token_type in token_types:
            if self.check(token_type):
                self.advance()
                return True
        return False

    def consume(self, token_type: TokenType, message: str) -> Token:
        """Consume a token of the expected type."""
        if self.check(token_type):
            return self.advance()
        raise self.error(message)

    def error(self, message: str) -> ParserError:
        """Create a parser error."""
        token = self.peek()
        return ParserError(message, self.filename, token.line, token.column)