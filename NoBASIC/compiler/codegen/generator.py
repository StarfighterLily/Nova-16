"""
NoBASIC Code Generator
Generates Nova-16 assembly code from AST.
"""

from typing import List, Dict, Tuple
from ..parser.ast import (
    Program, Statement, Expression, ClrDrawStmt, PxlOnStmt, PxlOffStmt,
    LineStmt, CircleStmt, TextStmt, SetLayerStmt, SpriteOnStmt, SpriteOffStmt,
    PlayToneStmt, PlayWaveStmt, StopSoundStmt, SetChannelStmt, GetKeyStmt,
    InputStmt, DispStmt, PauseStmt, AssignmentStmt, IfStmt, ForStmt,
    WhileStmt, RepeatStmt, GotoStmt, LabelStmt, LiteralExpr, VariableExpr,
    ListAccessExpr, MatrixAccessExpr, BinaryExpr, UnaryExpr, FunctionCallExpr,
    GroupingExpr
)


class CodeGenerator:
    """Code generator for NoBASIC to Nova-16 assembly."""

    def __init__(self):
        self.output: List[str] = []
        self.label_counter = 0
        self.variable_addresses: Dict[str, int] = {}
        self.next_address = 0x0120  # Start after interrupt vectors
        self.strings: List[Tuple[str, str]] = []  # List of (label, string_value)

    def generate(self, program: Program) -> str:
        """
        Generate assembly code from the AST.

        Args:
            program: The AST to generate code for

        Returns:
            Generated assembly code as a string
        """
        self.output = []
        self.label_counter = 0
        self.variable_addresses = {}
        self.next_address = 0x0120

        # Generate code for all statements
        for stmt in program.statements:
            self.generate_statement(stmt)

        # Add HLT at the end
        self.output.append("HLT")
        
        # Add string literals
        for label, string_value in self.strings:
            self.output.append(f"{label}: DEFSTR \"{string_value}\"")

        return "\n".join(self.output)

    def generate_statement(self, stmt: Statement):
        """Generate code for a statement."""
        if isinstance(stmt, ClrDrawStmt):
            self.generate_clr_draw()
        elif isinstance(stmt, PxlOnStmt):
            self.generate_pxl_on(stmt)
        elif isinstance(stmt, PxlOffStmt):
            self.generate_pxl_off(stmt)
        elif isinstance(stmt, LineStmt):
            self.generate_line(stmt)
        elif isinstance(stmt, CircleStmt):
            self.generate_circle(stmt)
        elif isinstance(stmt, TextStmt):
            self.generate_text(stmt)
        elif isinstance(stmt, SetLayerStmt):
            self.generate_set_layer(stmt)
        elif isinstance(stmt, SpriteOnStmt):
            self.generate_sprite_on(stmt)
        elif isinstance(stmt, SpriteOffStmt):
            self.generate_sprite_off(stmt)
        elif isinstance(stmt, PlayToneStmt):
            self.generate_play_tone(stmt)
        elif isinstance(stmt, PlayWaveStmt):
            self.generate_play_wave(stmt)
        elif isinstance(stmt, StopSoundStmt):
            self.generate_stop_sound()
        elif isinstance(stmt, SetChannelStmt):
            self.generate_set_channel(stmt)
        elif isinstance(stmt, GetKeyStmt):
            self.generate_get_key()
        elif isinstance(stmt, InputStmt):
            self.generate_input(stmt)
        elif isinstance(stmt, DispStmt):
            self.generate_disp(stmt)
        elif isinstance(stmt, PauseStmt):
            self.generate_pause()
        elif isinstance(stmt, AssignmentStmt):
            self.generate_assignment(stmt)
        elif isinstance(stmt, IfStmt):
            self.generate_if(stmt)
        elif isinstance(stmt, ForStmt):
            self.generate_for(stmt)
        elif isinstance(stmt, WhileStmt):
            self.generate_while(stmt)
        elif isinstance(stmt, RepeatStmt):
            self.generate_repeat(stmt)
        elif isinstance(stmt, GotoStmt):
            self.generate_goto(stmt)
        elif isinstance(stmt, LabelStmt):
            self.generate_label(stmt)

    def generate_clr_draw(self):
        """Generate ClrDraw code."""
        self.output.append("MOV VL, 0")  # Layer 0
        self.output.append("SFILL 0x00")

    def generate_pxl_on(self, stmt: PxlOnStmt):
        """Generate PxlOn(x, y, color) code."""
        x_reg = self.generate_expression(stmt.x, "R1")
        y_reg = self.generate_expression(stmt.y, "R2")
        color_reg = self.generate_expression(stmt.color, "R3")

        self.output.append(f"MOV VX, {x_reg}")
        self.output.append(f"MOV VY, {y_reg}")
        self.output.append(f"MOV VC, {color_reg}")
        self.output.append("SWRITE VC")

    def generate_pxl_off(self, stmt: PxlOffStmt):
        """Generate PxlOff(x, y) code."""
        x_reg = self.generate_expression(stmt.x)
        y_reg = self.generate_expression(stmt.y)

        self.output.append(f"MOV VX, {x_reg}")
        self.output.append(f"MOV VY, {y_reg}")
        self.output.append("MOV VC, 0")
        self.output.append("SWRITE VC")

    def generate_line(self, stmt: LineStmt):
        """Generate Line drawing code using SLINE opcode."""
        x1_reg = self.generate_expression(stmt.x1, "R1")
        y1_reg = self.generate_expression(stmt.y1, "R2")
        x2_reg = self.generate_expression(stmt.x2, "R3")
        y2_reg = self.generate_expression(stmt.y2, "R4")

        # Set up coordinates
        self.output.append(f"MOV VX, {x1_reg}")
        self.output.append(f"MOV VY, {y1_reg}")
        color_reg = self.generate_expression(stmt.color, "VC")

        # Use SLINE opcode
        self.output.append(f"SLINE {x2_reg}, {y2_reg}")

    def generate_circle(self, stmt: CircleStmt):
        """Generate Circle drawing code using SCIRC opcode."""
        x_reg = self.generate_expression(stmt.x, "VX")
        y_reg = self.generate_expression(stmt.y, "VY")
        radius_reg = self.generate_expression(stmt.radius, "R1")
        color_reg = self.generate_expression(stmt.color, "VC")

        # Use SCIRC opcode
        self.output.append(f"SCIRC {radius_reg}, 1")  # 1 for filled

    def generate_text(self, stmt: TextStmt):
        """Generate Text rendering code using TEXT opcode."""
        x_reg = self.generate_expression(stmt.x, "VX")
        y_reg = self.generate_expression(stmt.y, "VY")
        color_reg = self.generate_expression(stmt.color, "VC")

        # Handle text expression - for strings, create a label
        if isinstance(stmt.text, LiteralExpr) and stmt.text.data_type.name == "STRING":
            label = self.add_string_literal(stmt.text.value)
            self.output.append(f"TEXT {label}")
        else:
            # For other expressions, evaluate to register (not properly implemented)
            text_reg = self.generate_expression(stmt.text, "R1")
            self.output.append(f"TEXT {text_reg}")  # This won't work properly

    def generate_set_layer(self, stmt: SetLayerStmt):
        """Generate SetLayer(layer) code."""
        self.generate_expression(stmt.layer, "VL")
        # VL is already set by the expression generation

    def generate_sprite_on(self, stmt: SpriteOnStmt):
        """Generate SpriteOn(spriteId, x, y) code."""
        # Simplified - would need sprite control block manipulation
        self.output.append("; Sprite on - simplified")

    def generate_sprite_off(self, stmt: SpriteOffStmt):
        """Generate SpriteOff(spriteId) code."""
        # Simplified
        self.output.append("; Sprite off - simplified")

    def generate_play_tone(self, stmt: PlayToneStmt):
        """Generate optimized PlayTone code."""
        freq_reg = self.generate_expression(stmt.frequency, "SF")
        dur_reg = self.generate_expression(stmt.duration, "R1")
        vol_reg = self.generate_expression(stmt.volume, "SV")

        # Set waveform to default (0)
        self.output.append("MOV SW, 0")
        self.output.append("SPLAY")

        # Duration handling could use timer, but simplified for now
        self.output.append("; Duration handling - simplified")

    def generate_play_wave(self, stmt: PlayWaveStmt):
        """Generate optimized PlayWave code."""
        wave_reg = self.generate_expression(stmt.waveform, "SW")
        freq_reg = self.generate_expression(stmt.frequency, "SF")
        vol_reg = self.generate_expression(stmt.volume, "SV")

        self.output.append("SPLAY")

    def generate_stop_sound(self):
        """Generate StopSound code."""
        self.output.append("MOV SV, 0")  # Set volume to 0

    def generate_set_channel(self, stmt: SetChannelStmt):
        """Generate SetChannel(channel) code."""
        # Simplified - channel selection
        self.output.append("; Set channel - simplified")

    def generate_get_key(self):
        """Generate GetKey code."""
        self.output.append("KEYSTAT R0")  # Check if key available
        self.output.append("KEYIN R0")    # Read the key

    def generate_input(self, stmt: InputStmt):
        """Generate Input(prompt, variable) code."""
        # Simplified - would need text input handling
        self.output.append("; Input - simplified")

    def generate_disp(self, stmt: DispStmt):
        """Generate Disp "text" code."""
        # Simplified - would need text display
        self.output.append("; Display - simplified")

    def generate_pause(self):
        """Generate optimized Pause code."""
        # Use more efficient key checking
        pause_label = self.new_label()
        self.output.append(f"{pause_label}:")
        self.output.append("KEYSTAT R0")
        self.output.append("CMP R0, 0")
        self.output.append(f"JZ {pause_label}")  # Loop until key pressed

    def generate_assignment(self, stmt: AssignmentStmt):
        """Generate optimized assignment code."""
        value_reg = self.generate_expression(stmt.expression, "R1")
        var_addr = self.get_variable_address(stmt.variable)

        # Optimize: use direct register addressing when possible
        self.output.append(f"MOV P0, {var_addr}")
        self.output.append(f"MOV [P0], {value_reg}")

    def generate_if(self, stmt: IfStmt):
        """Generate optimized If-Then-Else code."""
        else_label = self.new_label()
        end_label = self.new_label()

        condition_reg = self.generate_expression(stmt.condition)

        # Test if condition is false (0)
        self.output.append(f"CMP {condition_reg}, 0")
        self.output.append(f"JZ {else_label}")

        for s in stmt.then_branch:
            self.generate_statement(s)

        if stmt.else_branch:
            self.output.append(f"JMP {end_label}")
            self.output.append(f"{else_label}:")

            for s in stmt.else_branch:
                self.generate_statement(s)

            self.output.append(f"{end_label}:")
        else:
            self.output.append(f"{else_label}:")

    def generate_for(self, stmt: ForStmt):
        """Generate optimized For loop code."""
        loop_label = self.new_label()
        end_label = self.new_label()

        # Initialize variable
        start_reg = self.generate_expression(stmt.start)
        var_addr = self.get_variable_address(stmt.variable)
        self.output.append(f"MOV P0, {var_addr}")
        self.output.append(f"MOV [P0], {start_reg}")

        self.output.append(f"{loop_label}:")

        # Load current value and check condition
        current_reg = self.load_variable(stmt.variable, "P1")
        end_reg = self.generate_expression(stmt.end, "P2")
        self.output.append(f"CMP {current_reg}, {end_reg}")

        # For ascending loops (default), exit when current > end
        self.output.append(f"JGT {end_label}")

        # Loop body
        for s in stmt.body:
            self.generate_statement(s)

        # Increment
        # Reload current value since it may have been overwritten
        current_reg = self.load_variable(stmt.variable, "P1")
        if stmt.step:
            step_reg = self.generate_expression(stmt.step, "P3")
            self.output.append(f"ADD {current_reg}, {current_reg}, {step_reg}")
        else:
            # Optimize: use INC for step=1
            self.output.append(f"INC {current_reg}")

        # Store back
        self.output.append(f"MOV P0, {var_addr}")
        self.output.append(f"MOV [P0], {current_reg}")

        self.output.append(f"JMP {loop_label}")
        self.output.append(f"{end_label}:")

    def generate_while(self, stmt: WhileStmt):
        """Generate optimized While loop code."""
        loop_label = self.new_label()
        end_label = self.new_label()

        self.output.append(f"{loop_label}:")

        condition_reg = self.generate_expression(stmt.condition)
        self.output.append(f"CMP {condition_reg}, 0")
        self.output.append(f"JZ {end_label}")

        for s in stmt.body:
            self.generate_statement(s)

        self.output.append(f"JMP {loop_label}")
        self.output.append(f"{end_label}:")

    def generate_repeat(self, stmt: RepeatStmt):
        """Generate optimized Repeat-Until loop code."""
        loop_label = self.new_label()

        self.output.append(f"{loop_label}:")

        for s in stmt.body:
            self.generate_statement(s)

        condition_reg = self.generate_expression(stmt.condition)
        self.output.append(f"CMP {condition_reg}, 0")
        self.output.append(f"JZ {loop_label}")  # Continue looping if condition is false

    def generate_goto(self, stmt: GotoStmt):
        """Generate Goto code."""
        self.output.append(f"JMP {stmt.label}")

    def generate_label(self, stmt: LabelStmt):
        """Generate Label code."""
        self.output.append(f"{stmt.label}:")

    def generate_expression(self, expr: Expression, target_reg: str = "R0") -> str:
        """Generate code for an expression and return the register containing the result."""
        if isinstance(expr, LiteralExpr):
            if expr.data_type.name == "NUMBER":  # Use .name to get enum name
                # Optimize for common values
                if expr.value == 0:
                    self.output.append(f"MOV {target_reg}, 0")  # Use MOV instead of XOR
                elif expr.value == 1:
                    self.output.append(f"MOV {target_reg}, 1")
                elif expr.value in [2, 4, 8, 16, 32, 64, 128, 256, 512, 1024]:
                    # Use shifts for powers of 2
                    shift_amount = expr.value.bit_length() - 1
                    self.output.append(f"MOV {target_reg}, 1")
                    self.output.append(f"SHL {target_reg}, {target_reg}, {shift_amount}")
                else:
                    self.output.append(f"MOV {target_reg}, {expr.value}")
                return target_reg
            else:
                # String literals would need to be stored in memory
                self.output.append(f"MOV {target_reg}, 0")  # Simplified
                return target_reg
        elif isinstance(expr, VariableExpr):
            return self.load_variable(expr.name, target_reg)
        elif isinstance(expr, BinaryExpr):
            return self.generate_binary_expression(expr, target_reg)
        elif isinstance(expr, UnaryExpr):
            return self.generate_unary_expression(expr, target_reg)
        elif isinstance(expr, FunctionCallExpr):
            return self.generate_function_call(expr, target_reg)
        else:
            self.output.append(f"MOV {target_reg}, 0")  # Default
            return target_reg

    def generate_binary_expression(self, expr: BinaryExpr, target_reg: str) -> str:
        """Generate optimized code for binary expressions."""
        left_reg = self.generate_expression(expr.left, "R1")
        right_reg = self.generate_expression(expr.right, "R2")

        if expr.operator == "+":
            self.output.append(f"ADD {target_reg}, {left_reg}, {right_reg}")
        elif expr.operator == "-":
            self.output.append(f"SUB {target_reg}, {left_reg}, {right_reg}")
        elif expr.operator == "*":
            self.output.append(f"MUL {target_reg}, {left_reg}, {right_reg}")
        elif expr.operator == "/":
            self.output.append(f"DIV {target_reg}, {left_reg}, {right_reg}")
        elif expr.operator == "%" or expr.operator == "MOD":
            self.output.append(f"MOD {target_reg}, {left_reg}, {right_reg}")
        elif expr.operator == "&" or expr.operator == "AND":
            self.output.append(f"AND {target_reg}, {left_reg}, {right_reg}")
        elif expr.operator == "|" or expr.operator == "OR":
            self.output.append(f"OR {target_reg}, {left_reg}, {right_reg}")
        elif expr.operator == "^" or expr.operator == "XOR":
            self.output.append(f"XOR {target_reg}, {left_reg}, {right_reg}")
        elif expr.operator == "<<" or expr.operator == "SHL":
            self.output.append(f"SHL {target_reg}, {left_reg}, {right_reg}")
        elif expr.operator == ">>" or expr.operator == "SHR":
            self.output.append(f"SHR {target_reg}, {left_reg}, {right_reg}")
        elif expr.operator == "<" or expr.operator == ">" or expr.operator == "=" or expr.operator == "<>" or expr.operator == "<=" or expr.operator == ">=":
            # Use CMP for comparisons and set target_reg based on result
            self.output.append(f"CMP {left_reg}, {right_reg}")
            
            true_label = self.new_label()
            end_label = self.new_label()
            
            # Set default to false
            self.output.append(f"MOV {target_reg}, 0")
            
            # Jump to set true if condition met
            if expr.operator == "<":
                self.output.append(f"JLT {true_label}")
            elif expr.operator == ">":
                self.output.append(f"JGT {true_label}")
            elif expr.operator == "=":
                self.output.append(f"JZ {true_label}")
            elif expr.operator == "<>":
                self.output.append(f"JNZ {true_label}")
            elif expr.operator == "<=":
                self.output.append(f"JLE {true_label}")
            elif expr.operator == ">=":
                self.output.append(f"JGE {true_label}")
            
            self.output.append(f"JMP {end_label}")
            self.output.append(f"{true_label}:")
            self.output.append(f"MOV {target_reg}, 1")
            self.output.append(f"{end_label}:")
        else:
            # Fallback
            self.output.append(f"MOV {target_reg}, #0")
        return target_reg

    def generate_unary_expression(self, expr: UnaryExpr, target_reg: str) -> str:
        """Generate code for unary expressions."""
        operand_reg = self.generate_expression(expr.expression, "R1")

        if expr.operator == "-":
            self.output.append(f"NEG {target_reg}, {operand_reg}")
        elif expr.operator == "NOT":
            self.output.append(f"NOT {target_reg}, {operand_reg}")
        elif expr.operator == "ABS":
            self.output.append(f"ABS {target_reg}, {operand_reg}")
        else:
            self.output.append(f"MOV {target_reg}, {operand_reg}")
        return target_reg

    def generate_function_call(self, expr: FunctionCallExpr, target_reg: str) -> str:
        """Generate optimized code for function calls."""
        func_name = expr.name.upper()

        if func_name == "SIN":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"SIN {target_reg}, {arg_reg}")
        elif func_name == "COS":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"COS {target_reg}, {arg_reg}")
        elif func_name == "TAN":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"TAN {target_reg}, {arg_reg}")
        elif func_name == "SQRT":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"SQRT {target_reg}, {arg_reg}")
        elif func_name == "ABS":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"ABS {target_reg}, {arg_reg}")
        elif func_name == "RND":
            self.output.append(f"RND {target_reg}")
        elif func_name == "LEN" or func_name == "LENGTH":
            # For string length - simplified
            self.output.append(f"MOV {target_reg}, #0")
        elif func_name == "MIN":
            left_reg = self.generate_expression(expr.arguments[0], "R1")
            right_reg = self.generate_expression(expr.arguments[1], "R2")
            self.output.append(f"MIN {target_reg}, {left_reg}, {right_reg}")
        elif func_name == "MAX":
            left_reg = self.generate_expression(expr.arguments[0], "R1")
            right_reg = self.generate_expression(expr.arguments[1], "R2")
            self.output.append(f"MAX {target_reg}, {left_reg}, {right_reg}")
        else:
            # Fallback for unimplemented functions
            self.output.append(f"MOV {target_reg}, #0")
        return target_reg

    def load_variable(self, name: str, target_reg: str = "R0") -> str:
        """Load a variable into a register."""
        addr = self.get_variable_address(name)
        self.output.append(f"MOV P0, {addr}")
        self.output.append(f"MOV {target_reg}, [P0]")
        return target_reg

    def get_variable_address(self, name: str) -> int:
        """Get the memory address for a variable."""
        if name not in self.variable_addresses:
            self.variable_addresses[name] = self.next_address
            self.next_address += 2  # 16-bit variables
        return self.variable_addresses[name]

    def add_string_literal(self, string_value: str) -> str:
        """Add a string literal and return its label."""
        # Check if we already have this string
        for label, value in self.strings:
            if value == string_value:
                return label
        
        # Create new label
        label = f"STR{self.label_counter}"
        self.label_counter += 1
        self.strings.append((label, string_value))
        return label

    def new_label(self) -> str:
        """Generate a new unique label."""
        self.label_counter += 1
        return f"L{self.label_counter}"