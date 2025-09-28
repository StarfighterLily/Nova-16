"""
NoBASIC Code Generator
Generates Nova-16 assembly code from AST.
"""

from typing import List, Dict, Tuple
from ..parser.ast import (
    Program, Statement, Expression, ClrDrawStmt, PxlOnStmt, PxlOffStmt,
    LineStmt, CircleStmt, TextStmt, SetLayerStmt, SpriteOnStmt, SpriteOffStmt,
    PlayToneStmt, PlayWaveStmt, StopSoundStmt, SetChannelStmt, GetKeyStmt,
    InputStmt, DispStmt, PauseStmt, FunctionCallStmt, AssignmentStmt, IfStmt, ForStmt,
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
        elif isinstance(stmt, FunctionCallStmt):
            self.generate_function_call_statement(stmt)
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
        self.output.append("; ClrDraw - simplified")
        self.output.append("MOV VM, 0")  # Coordinate mode
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
        # Display prompt if provided
        if stmt.prompt is not None:
            # For now, just evaluate the prompt expression (simplified)
            self.generate_expression(stmt.prompt, "R0")
            self.output.append("; Display prompt - simplified")

        # Wait for and read input
        input_label = self.new_label()
        self.output.append(f"{input_label}:")
        self.output.append("KEYSTAT R0")
        self.output.append("CMP R0, 0")
        self.output.append(f"JZ {input_label}")  # Wait for key
        self.output.append("KEYIN R0")  # Read the key

        # Store in variable
        var_addr = self.get_variable_address(stmt.variable)
        self.output.append(f"MOV P0, {var_addr}")
        self.output.append(f"MOV [P0], R0")

    def generate_disp(self, stmt: DispStmt):
        """Generate Disp expression code."""
        # For now, just evaluate the expression - DISP is for console output
        # In a real implementation, this would output to a console
        self.generate_expression(stmt.text, "R1")
        # Could add TEXT call here, but for now just evaluate

    def generate_pause(self):
        """Generate optimized Pause code."""
        # Use more efficient key checking
        pause_label = self.new_label()
        self.output.append(f"{pause_label}:")
        self.output.append("KEYSTAT R0")
        self.output.append("CMP R0, 0")
        self.output.append(f"JZ {pause_label}")  # Loop until key pressed

    def generate_function_call_statement(self, stmt: FunctionCallStmt):
        """Generate code for a function call statement."""
        # Evaluate the function call but discard the result
        self.generate_expression(stmt.function_call, "R0")

    def generate_assignment(self, stmt: AssignmentStmt):
        """Generate optimized assignment code."""
        value_reg = self.generate_expression(stmt.expression, "R1")

        if isinstance(stmt.variable, VariableExpr):
            # Simple variable assignment
            var_addr = self.get_variable_address(stmt.variable)
            self.output.append(f"MOV P0, {var_addr}")
            self.output.append(f"MOV [P0], {value_reg}")
        elif isinstance(stmt.variable, ListAccessExpr):
            # Array element assignment
            self.generate_list_store(stmt.variable, value_reg)
        elif isinstance(stmt.variable, MatrixAccessExpr):
            # Matrix element assignment
            self.generate_matrix_store(stmt.variable, value_reg)
        else:
            raise TypeError(f"Unsupported assignment target: {type(stmt.variable)}")

    def generate_list_access(self, expr: ListAccessExpr, target_reg: str) -> str:
        """Generate code to load from a list element."""
        # For now, assume L1 starts at 0x1000, L2 at 0x1100, etc.
        list_num = int(expr.list_name[1])  # L1 -> 1
        base_addr = 0x1000 + (list_num - 1) * 0x100
        
        index_reg = self.generate_expression(expr.index, "R2")
        # Address = base_addr + index * 2 (since 16-bit values)
        self.output.append(f"MOV {target_reg}, {index_reg}")
        self.output.append(f"SHL {target_reg}, {target_reg}, 1")  # Multiply by 2
        self.output.append(f"ADD {target_reg}, {target_reg}, {base_addr}")
        self.output.append(f"MOV P0, {target_reg}")
        self.output.append(f"MOV {target_reg}, [P0]")
        return target_reg

    def generate_list_store(self, expr: ListAccessExpr, value_reg: str):
        """Generate code to store to a list element."""
        list_num = int(expr.list_name[1])  # L1 -> 1
        base_addr = 0x1000 + (list_num - 1) * 0x100
        
        index_reg = self.generate_expression(expr.index, "R2")
        # Address = base_addr + index * 2
        self.output.append(f"MOV P0, {index_reg}")
        self.output.append(f"SHL P0, P0, 1")  # Multiply by 2
        self.output.append(f"ADD P0, P0, {base_addr}")
        self.output.append(f"MOV [P0], {value_reg}")

    def generate_matrix_access(self, expr: MatrixAccessExpr, target_reg: str) -> str:
        """Generate code to load from a matrix element."""
        # Simplified: assume MatA starts at 0x2000
        base_addr = 0x2000
        # For now, just return 0
        self.output.append(f"MOV {target_reg}, 0")
        return target_reg

    def generate_matrix_store(self, expr: MatrixAccessExpr, value_reg: str):
        """Generate code to store to a matrix element."""
        # Simplified: do nothing for now
        pass

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
                    self.output.append(f"XOR {target_reg}, {target_reg}")  # Zero register
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
        elif isinstance(expr, ListAccessExpr):
            return self.generate_list_access(expr, target_reg)
        elif isinstance(expr, MatrixAccessExpr):
            return self.generate_matrix_access(expr, target_reg)
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
        elif expr.operator == "<<<" or expr.operator == "SAL":
            self.output.append(f"SAL {target_reg}, {left_reg}, {right_reg}")
        elif expr.operator == ">>>" or expr.operator == "SAR":
            self.output.append(f"SAR {target_reg}, {left_reg}, {right_reg}")
        elif expr.operator == "<@" or expr.operator == "ROL":
            self.output.append(f"ROL {target_reg}, {left_reg}, {right_reg}")
        elif expr.operator == "@>" or expr.operator == "ROR":
            self.output.append(f"ROR {target_reg}, {left_reg}, {right_reg}")
        elif expr.operator == "<@@" or expr.operator == "RCL":
            self.output.append(f"RCL {target_reg}, {left_reg}, {right_reg}")
        elif expr.operator == "@@>" or expr.operator == "RCR":
            self.output.append(f"RCR {target_reg}, {left_reg}, {right_reg}")
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
        elif func_name == "LEN" or func_name == "LENGTH" or func_name == "STRLEN":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"STRLEN {target_reg}, {arg_reg}")
        elif func_name == "STRCPY":
            dest_reg = self.generate_expression(expr.arguments[0], "R1")
            src_reg = self.generate_expression(expr.arguments[1], "R2")
            self.output.append(f"STRCPY {dest_reg}, {src_reg}")
            self.output.append(f"MOV {target_reg}, {dest_reg}")  # Return destination
        elif func_name == "STRCAT":
            dest_reg = self.generate_expression(expr.arguments[0], "R1")
            src_reg = self.generate_expression(expr.arguments[1], "R2")
            self.output.append(f"STRCAT {dest_reg}, {src_reg}")
            self.output.append(f"MOV {target_reg}, {dest_reg}")  # Return destination
        elif func_name == "STRCMP":
            str1_reg = self.generate_expression(expr.arguments[0], "R1")
            str2_reg = self.generate_expression(expr.arguments[1], "R2")
            len_reg = self.generate_expression(expr.arguments[2], "R3")
            self.output.append(f"STRCMP {target_reg}, {str1_reg}, {str2_reg}, {len_reg}")
        elif func_name == "STRUPR":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"STRUPR {target_reg}, {arg_reg}")
        elif func_name == "STRLWR":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"STRLWR {target_reg}, {arg_reg}")
        elif func_name == "STRREV":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"STRREV {target_reg}, {arg_reg}")
        elif func_name == "STRFIND":
            haystack_reg = self.generate_expression(expr.arguments[0], "R1")
            needle_reg = self.generate_expression(expr.arguments[1], "R2")
            self.output.append(f"STRFIND {target_reg}, {haystack_reg}, {needle_reg}")
        elif func_name == "STRFINDI":
            haystack_reg = self.generate_expression(expr.arguments[0], "R1")
            needle_reg = self.generate_expression(expr.arguments[1], "R2")
            self.output.append(f"STRFINDI {target_reg}, {haystack_reg}, {needle_reg}")
        elif func_name == "STREXT":
            dest_reg = self.generate_expression(expr.arguments[0], "R1")
            haystack_reg = self.generate_expression(expr.arguments[1], "R2")
            needle_reg = self.generate_expression(expr.arguments[2], "R3")
            len_reg = self.generate_expression(expr.arguments[3], "R4")
            self.output.append(f"STREXT {dest_reg}, {haystack_reg}, {needle_reg}, {len_reg}")
            self.output.append(f"MOV {target_reg}, {dest_reg}")  # Return destination
        elif func_name == "STREXTI":
            dest_reg = self.generate_expression(expr.arguments[0], "R1")
            haystack_reg = self.generate_expression(expr.arguments[1], "R2")
            needle_reg = self.generate_expression(expr.arguments[2], "R3")
            len_reg = self.generate_expression(expr.arguments[3], "R4")
            self.output.append(f"STREXTI {dest_reg}, {haystack_reg}, {needle_reg}, {len_reg}")
            self.output.append(f"MOV {target_reg}, {dest_reg}")  # Return destination
        elif func_name == "MIN":
            left_reg = self.generate_expression(expr.arguments[0], "R1")
            right_reg = self.generate_expression(expr.arguments[1], "R2")
            self.output.append(f"MIN {target_reg}, {left_reg}, {right_reg}")
        elif func_name == "MAX":
            left_reg = self.generate_expression(expr.arguments[0], "R1")
            right_reg = self.generate_expression(expr.arguments[1], "R2")
            self.output.append(f"MAX {target_reg}, {left_reg}, {right_reg}")
        elif func_name == "ATAN":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"ATAN {target_reg}, {arg_reg}")
        elif func_name == "ASIN":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"ASIN {target_reg}, {arg_reg}")
        elif func_name == "ACOS":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"ACOS {target_reg}, {arg_reg}")
        elif func_name == "DEG":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"DEG {target_reg}, {arg_reg}")
        elif func_name == "RAD":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"RAD {target_reg}, {arg_reg}")
        elif func_name == "FLOOR":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"FLOOR {target_reg}, {arg_reg}")
        elif func_name == "CEIL":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"CEIL {target_reg}, {arg_reg}")
        elif func_name == "ROUND":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"ROUND {target_reg}, {arg_reg}")
        elif func_name == "TRUNC":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"TRUNC {target_reg}, {arg_reg}")
        elif func_name == "FRAC":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"FRAC {target_reg}, {arg_reg}")
        elif func_name == "INTGR":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"INTGR {target_reg}, {arg_reg}")
        elif func_name == "POWR":
            left_reg = self.generate_expression(expr.arguments[0], "R1")
            right_reg = self.generate_expression(expr.arguments[1], "R2")
            self.output.append(f"POWR {target_reg}, {left_reg}, {right_reg}")
        elif func_name == "LOG":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"LOG {target_reg}, {arg_reg}")
        elif func_name == "EXP":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"EXP {target_reg}, {arg_reg}")
        elif func_name == "BTST":
            value_reg = self.generate_expression(expr.arguments[0], "R1")
            bit_reg = self.generate_expression(expr.arguments[1], "R2")
            self.output.append(f"BTST {target_reg}, {value_reg}, {bit_reg}")
        elif func_name == "BSET":
            value_reg = self.generate_expression(expr.arguments[0], "R1")
            bit_reg = self.generate_expression(expr.arguments[1], "R2")
            self.output.append(f"BSET {target_reg}, {value_reg}, {bit_reg}")
        elif func_name == "BCLR":
            value_reg = self.generate_expression(expr.arguments[0], "R1")
            bit_reg = self.generate_expression(expr.arguments[1], "R2")
            self.output.append(f"BCLR {target_reg}, {value_reg}, {bit_reg}")
        elif func_name == "BFLIP":
            value_reg = self.generate_expression(expr.arguments[0], "R1")
            bit_reg = self.generate_expression(expr.arguments[1], "R2")
            self.output.append(f"BFLIP {target_reg}, {value_reg}, {bit_reg}")
        elif func_name == "CLZ":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"CLZ {target_reg}, {arg_reg}")
        elif func_name == "CTZ":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"CTZ {target_reg}, {arg_reg}")
        elif func_name == "POPCNT":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"POPCNT {target_reg}, {arg_reg}")
        elif func_name == "MEMCPY":
            dest_reg = self.generate_expression(expr.arguments[0], "R1")
            src_reg = self.generate_expression(expr.arguments[1], "R2")
            len_reg = self.generate_expression(expr.arguments[2], "R3")
            self.output.append(f"MEMCPY {dest_reg}, {src_reg}, {len_reg}")
            self.output.append(f"MOV {target_reg}, {dest_reg}")  # Return destination
        elif func_name == "MEMSET":
            addr_reg = self.generate_expression(expr.arguments[0], "R1")
            value_reg = self.generate_expression(expr.arguments[1], "R2")
            len_reg = self.generate_expression(expr.arguments[2], "R3")
            self.output.append(f"MEMSET {addr_reg}, {value_reg}, {len_reg}")
            self.output.append(f"MOV {target_reg}, {addr_reg}")  # Return address
        elif func_name == "MEMTEST":
            addr1_reg = self.generate_expression(expr.arguments[0], "R1")
            addr2_reg = self.generate_expression(expr.arguments[1], "R2")
            len_reg = self.generate_expression(expr.arguments[2], "R3")
            self.output.append(f"MEMTEST {target_reg}, {addr1_reg}, {addr2_reg}, {len_reg}")
        elif func_name == "MEMMOVE":
            dest_reg = self.generate_expression(expr.arguments[0], "R1")
            src_reg = self.generate_expression(expr.arguments[1], "R2")
            len_reg = self.generate_expression(expr.arguments[2], "R3")
            self.output.append(f"MEMMOVE {dest_reg}, {src_reg}, {len_reg}")
            self.output.append(f"MOV {target_reg}, {dest_reg}")  # Return destination
        elif func_name == "MEMCMP":
            result_reg = self.generate_expression(expr.arguments[0], "R1")
            addr1_reg = self.generate_expression(expr.arguments[1], "R2")
            addr2_reg = self.generate_expression(expr.arguments[2], "R3")
            len_reg = self.generate_expression(expr.arguments[3], "R4")
            self.output.append(f"MEMCMP {result_reg}, {addr1_reg}, {addr2_reg}, {len_reg}")
            self.output.append(f"MOV {target_reg}, {result_reg}")  # Return result
        elif func_name == "MEMSWAP":
            addr1_reg = self.generate_expression(expr.arguments[0], "R1")
            addr2_reg = self.generate_expression(expr.arguments[1], "R2")
            len_reg = self.generate_expression(expr.arguments[2], "R3")
            self.output.append(f"MEMSWAP {addr1_reg}, {addr2_reg}, {len_reg}")
            self.output.append(f"MOV {target_reg}, {addr1_reg}")  # Return first address
        elif func_name == "ADC":
            result_reg = self.generate_expression(expr.arguments[0], "R1")
            a_reg = self.generate_expression(expr.arguments[1], "R2")
            b_reg = self.generate_expression(expr.arguments[2], "R3")
            self.output.append(f"ADC {result_reg}, {a_reg}, {b_reg}")
            self.output.append(f"MOV {target_reg}, {result_reg}")
        elif func_name == "SBC":
            result_reg = self.generate_expression(expr.arguments[0], "R1")
            a_reg = self.generate_expression(expr.arguments[1], "R2")
            b_reg = self.generate_expression(expr.arguments[2], "R3")
            self.output.append(f"SBC {result_reg}, {a_reg}, {b_reg}")
            self.output.append(f"MOV {target_reg}, {result_reg}")
        elif func_name == "MULH":
            result_reg = self.generate_expression(expr.arguments[0], "R1")
            a_reg = self.generate_expression(expr.arguments[1], "R2")
            b_reg = self.generate_expression(expr.arguments[2], "R3")
            self.output.append(f"MULH {result_reg}, {a_reg}, {b_reg}")
            self.output.append(f"MOV {target_reg}, {result_reg}")
        elif func_name == "DIVH":
            result_reg = self.generate_expression(expr.arguments[0], "R1")
            a_reg = self.generate_expression(expr.arguments[1], "R2")
            b_reg = self.generate_expression(expr.arguments[2], "R3")
            self.output.append(f"DIVH {result_reg}, {a_reg}, {b_reg}")
            self.output.append(f"MOV {target_reg}, {result_reg}")
        elif func_name == "SWAP":
            value_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"SWAP {value_reg}")
            self.output.append(f"MOV {target_reg}, {value_reg}")
        elif func_name == "XCHNG":
            a_reg = self.generate_expression(expr.arguments[0], "R1")
            b_reg = self.generate_expression(expr.arguments[1], "R2")
            self.output.append(f"XCHNG {a_reg}, {b_reg}")
            self.output.append(f"MOV {target_reg}, {a_reg}")
        elif func_name == "MOVZ":
            dest_reg = self.generate_expression(expr.arguments[0], "R1")
            src_reg = self.generate_expression(expr.arguments[1], "R2")
            self.output.append(f"MOVZ {dest_reg}, {src_reg}")
            self.output.append(f"MOV {target_reg}, {dest_reg}")
        elif func_name == "MOVNZ":
            dest_reg = self.generate_expression(expr.arguments[0], "R1")
            src_reg = self.generate_expression(expr.arguments[1], "R2")
            self.output.append(f"MOVNZ {dest_reg}, {src_reg}")
            self.output.append(f"MOV {target_reg}, {dest_reg}")
        elif func_name == "LEA":
            dest_reg = self.generate_expression(expr.arguments[0], "R1")
            src_reg = self.generate_expression(expr.arguments[1], "R2")
            self.output.append(f"LEA {dest_reg}, {src_reg}")
            self.output.append(f"MOV {target_reg}, {dest_reg}")
        elif func_name == "SHL":
            value_reg = self.generate_expression(expr.arguments[0], "R1")
            shift_reg = self.generate_expression(expr.arguments[1], "R2")
            self.output.append(f"SHL {target_reg}, {value_reg}, {shift_reg}")
        elif func_name == "SHR":
            value_reg = self.generate_expression(expr.arguments[0], "R1")
            shift_reg = self.generate_expression(expr.arguments[1], "R2")
            self.output.append(f"SHR {target_reg}, {value_reg}, {shift_reg}")
        elif func_name == "SAL":
            value_reg = self.generate_expression(expr.arguments[0], "R1")
            shift_reg = self.generate_expression(expr.arguments[1], "R2")
            self.output.append(f"SAL {target_reg}, {value_reg}, {shift_reg}")
        elif func_name == "SAR":
            value_reg = self.generate_expression(expr.arguments[0], "R1")
            shift_reg = self.generate_expression(expr.arguments[1], "R2")
            self.output.append(f"SAR {target_reg}, {value_reg}, {shift_reg}")
        elif func_name == "ROL":
            value_reg = self.generate_expression(expr.arguments[0], "R1")
            shift_reg = self.generate_expression(expr.arguments[1], "R2")
            self.output.append(f"ROL {target_reg}, {value_reg}, {shift_reg}")
        elif func_name == "ROR":
            value_reg = self.generate_expression(expr.arguments[0], "R1")
            shift_reg = self.generate_expression(expr.arguments[1], "R2")
            self.output.append(f"ROR {target_reg}, {value_reg}, {shift_reg}")
        elif func_name == "RCL":
            value_reg = self.generate_expression(expr.arguments[0], "R1")
            shift_reg = self.generate_expression(expr.arguments[1], "R2")
            self.output.append(f"RCL {target_reg}, {value_reg}, {shift_reg}")
        elif func_name == "RCR":
            value_reg = self.generate_expression(expr.arguments[0], "R1")
            shift_reg = self.generate_expression(expr.arguments[1], "R2")
            self.output.append(f"RCR {target_reg}, {value_reg}, {shift_reg}")
        elif func_name == "BAND":
            a_reg = self.generate_expression(expr.arguments[0], "R1")
            b_reg = self.generate_expression(expr.arguments[1], "R2")
            self.output.append(f"AND {target_reg}, {a_reg}, {b_reg}")
        elif func_name == "BOR":
            a_reg = self.generate_expression(expr.arguments[0], "R1")
            b_reg = self.generate_expression(expr.arguments[1], "R2")
            self.output.append(f"OR {target_reg}, {a_reg}, {b_reg}")
        elif func_name == "BXOR":
            a_reg = self.generate_expression(expr.arguments[0], "R1")
            b_reg = self.generate_expression(expr.arguments[1], "R2")
            self.output.append(f"XOR {target_reg}, {a_reg}, {b_reg}")
        elif func_name == "BNOT":
            value_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"NOT {target_reg}, {value_reg}")
        elif func_name == "ITOB":
            result_reg = self.generate_expression(expr.arguments[0], "R1")
            value_reg = self.generate_expression(expr.arguments[1], "R2")
            self.output.append(f"ITOB {result_reg}, {value_reg}")
            self.output.append(f"MOV {target_reg}, {result_reg}")
        elif func_name == "BTOI":
            result_reg = self.generate_expression(expr.arguments[0], "R1")
            binary_reg = self.generate_expression(expr.arguments[1], "R2")
            self.output.append(f"BTOI {result_reg}, {binary_reg}")
            self.output.append(f"MOV {target_reg}, {result_reg}")
        elif func_name == "ITOS":
            result_reg = self.generate_expression(expr.arguments[0], "R1")
            value_reg = self.generate_expression(expr.arguments[1], "R2")
            self.output.append(f"ITOS {result_reg}, {value_reg}")
            self.output.append(f"MOV {target_reg}, {result_reg}")
        elif func_name == "STOI":
            result_reg = self.generate_expression(expr.arguments[0], "R1")
            string_reg = self.generate_expression(expr.arguments[1], "R2")
            self.output.append(f"STOI {result_reg}, {string_reg}")
            self.output.append(f"MOV {target_reg}, {result_reg}")
        elif func_name == "SUB":
            string_reg = self.generate_expression(expr.arguments[0], "R1")
            start_reg = self.generate_expression(expr.arguments[1], "R2")
            len_reg = self.generate_expression(expr.arguments[2], "R3")
            self.output.append(f"STREXT {target_reg}, {string_reg}, {start_reg}, {len_reg}")
        elif func_name == "CLRDRAW":
            self.output.append("MOV VM, 0")  # Clear screen mode
            self.output.append("SFILL 0")    # Fill with black
        elif func_name == "SETLAYER":
            layer_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"MOV VL, {layer_reg}")
        elif func_name == "PXLON":
            x_reg = self.generate_expression(expr.arguments[0], "R1")
            y_reg = self.generate_expression(expr.arguments[1], "R2")
            color_reg = self.generate_expression(expr.arguments[2], "R3")
            self.output.append(f"MOV VX, {x_reg}")
            self.output.append(f"MOV VY, {y_reg}")
            self.output.append(f"MOV VC, {color_reg}")
            self.output.append("SWRITE VC")
        elif func_name == "PXLOFF":
            x_reg = self.generate_expression(expr.arguments[0], "R1")
            y_reg = self.generate_expression(expr.arguments[1], "R2")
            self.output.append(f"MOV VX, {x_reg}")
            self.output.append(f"MOV VY, {y_reg}")
            self.output.append("SWRITE 0")
        elif func_name == "LINE":
            x1_reg = self.generate_expression(expr.arguments[0], "R1")
            y1_reg = self.generate_expression(expr.arguments[1], "R2")
            x2_reg = self.generate_expression(expr.arguments[2], "R3")
            y2_reg = self.generate_expression(expr.arguments[3], "R4")
            color_reg = self.generate_expression(expr.arguments[4], "R5")
            self.output.append(f"MOV VX, {x1_reg}")
            self.output.append(f"MOV VY, {y1_reg}")
            self.output.append(f"SLINE {x2_reg}, {y2_reg}, {color_reg}")
        elif func_name == "CIRCLE":
            x_reg = self.generate_expression(expr.arguments[0], "R1")
            y_reg = self.generate_expression(expr.arguments[1], "R2")
            radius_reg = self.generate_expression(expr.arguments[2], "R3")
            color_reg = self.generate_expression(expr.arguments[3], "R4")
            self.output.append(f"MOV VX, {x_reg}")
            self.output.append(f"MOV VY, {y_reg}")
            self.output.append(f"SCIRC {radius_reg}, {color_reg}")
        elif func_name == "TEXT":
            x_reg = self.generate_expression(expr.arguments[0], "R1")
            y_reg = self.generate_expression(expr.arguments[1], "R2")
            text_reg = self.generate_expression(expr.arguments[2], "R3")
            color_reg = self.generate_expression(expr.arguments[3], "R4")
            self.output.append(f"MOV VX, {x_reg}")
            self.output.append(f"MOV VY, {y_reg}")
            self.output.append(f"TEXT {text_reg}, {color_reg}")
        elif func_name == "RECT":
            x1_reg = self.generate_expression(expr.arguments[0], "R1")
            y1_reg = self.generate_expression(expr.arguments[1], "R2")
            x2_reg = self.generate_expression(expr.arguments[2], "R3")
            y2_reg = self.generate_expression(expr.arguments[3], "R4")
            fill_reg = self.generate_expression(expr.arguments[4], "R5")
            self.output.append(f"MOV VX, {x1_reg}")
            self.output.append(f"MOV VY, {y1_reg}")
            self.output.append(f"SRECT {x2_reg}, {y2_reg}, {fill_reg}")
        elif func_name == "SUM":
            # For now, just return 0 - proper list handling needs more work
            self.output.append(f"MOV {target_reg}, 0")
        elif func_name == "MEAN":
            # For now, just return 0 - proper list handling needs more work
            self.output.append(f"MOV {target_reg}, 0")
        elif func_name == "DIM":
            # For now, just return 0 - proper list handling needs more work
            self.output.append(f"MOV {target_reg}, 0")
        elif func_name == "GETKEY":
            self.output.append("KEYIN R0")
            self.output.append(f"MOV {target_reg}, R0")
        elif func_name == "PAUSE":
            # Wait for key press
            self.output.append("KEYSTAT R0")
            label = self.new_label()
            self.output.append(f"JZ {label}")
            self.output.append(f"{label}:")
            self.output.append("KEYIN R0")  # Consume the key

    def load_variable(self, name: str, target_reg: str = "R0") -> str:
        """Load a variable into a register."""
        addr = self.get_variable_address(name)
        self.output.append(f"MOV P0, {addr}")
        self.output.append(f"MOV {target_reg}, [P0]")
        return target_reg

    def get_variable_address(self, variable) -> int:
        """Get the memory address for a variable."""
        # Handle both string names and VariableExpr objects
        if isinstance(variable, str):
            name = variable
        elif hasattr(variable, 'name'):
            name = variable.name
        else:
            raise TypeError(f"Expected string or VariableExpr, got {type(variable)}")

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