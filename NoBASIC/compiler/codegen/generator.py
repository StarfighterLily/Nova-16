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
        self.loop_nesting_level = 0
        
        # Register allocation tracking
        self.register_usage: Dict[str, bool] = {
            'R0': False, 'R1': False, 'R2': False, 'R3': False, 'R4': False,
            'R5': False, 'R6': False, 'R7': False, 'R8': False, 'R9': False,
            'P0': False, 'P1': False, 'P2': False, 'P3': False, 'P4': False,
            'P5': False, 'P6': False, 'P7': False, 'SP': False, 'FP': False,
            'VX': False, 'VY': False, 'VM': False, 'VL': False, 'VC': False,
            'SA': False, 'SF': False, 'SV': False, 'SW': False,
            'TT': False, 'TM': False, 'TC': False, 'TS': False
        }
        
        # Preferred register order for allocation (R registers first, then P registers)
        self.allocation_order = [
            'R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9',
            'P0', 'P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7'
        ]
        
        # Preferred register order for variable allocation (P registers for 16-bit)
        self.var_allocation_order = [
            'P2', 'P3', 'P4', 'P5', 'P6', 'P7'  # Skip P0, P1 for temps
        ]

        # Variable register allocation
        self.var_reg: Dict[str, str] = {}  # variable name -> register
        self.var_lifetime: Dict[str, Tuple[int, int]] = {}  # var -> (start, end)
        self.statement_counter = 0

    def allocate_register(self, preferred_reg: str = None) -> str:
        """Allocate an unused register, preferring the specified register if available."""
        # Try preferred register first
        if preferred_reg and not self.register_usage[preferred_reg]:
            self.register_usage[preferred_reg] = True
            return preferred_reg
        
        # Try allocation order
        for reg in self.allocation_order:
            if not self.register_usage[reg]:
                self.register_usage[reg] = True
                return reg
        
        raise RuntimeError("No available registers for allocation")

    def deallocate_register(self, reg: str):
        """Deallocate a register, marking it as available."""
        if reg in self.register_usage:
            self.register_usage[reg] = False

    def with_temporary_register(self, preferred_reg: str = None):
        """Context manager for temporary register allocation."""
        reg = self.allocate_register(preferred_reg)
        try:
            yield reg
        finally:
            self.deallocate_register(reg)

    def get_loop_registers(self) -> Tuple[str, str, str]:
        """Get the appropriate registers for the current loop nesting level.
        
        Returns:
            Tuple of (current_reg, end_reg, step_reg) for the current nesting level.
        """
        # Use different register sets for different nesting levels
        # Level 0: P1, P2, P3
        # Level 1: P4, P5, P6  
        # Level 2: P7, P8, P9
        base_reg_num = 1 + (self.loop_nesting_level * 3)
        return (f"P{base_reg_num}", f"P{base_reg_num + 1}", f"P{base_reg_num + 2}")

    def collect_lifetimes(self, program: Program):
        """Collect variable lifetimes by traversing the AST."""
        for stmt in program.statements:
            self.collect_lifetimes_stmt(stmt)

    def collect_lifetimes_stmt(self, stmt):
        """Collect lifetimes for a statement."""
        self.statement_counter += 1
        current_counter = self.statement_counter

        if isinstance(stmt, AssignmentStmt):
            if hasattr(stmt.variable, 'name'):
                var_name = stmt.variable.name
            else:
                var_name = stmt.variable
            current_counter = self.statement_counter
            if var_name not in self.var_lifetime:
                self.var_lifetime[var_name] = (current_counter, current_counter)
            else:
                start, _ = self.var_lifetime[var_name]
                self.var_lifetime[var_name] = (start, current_counter)
            self.collect_lifetimes_expr(stmt.expression)
        elif isinstance(stmt, ForStmt):
            # Loop variable defined at for
            var_name = stmt.variable
            if var_name not in self.var_lifetime:
                self.var_lifetime[var_name] = (current_counter, current_counter)
            else:
                start, _ = self.var_lifetime[var_name]
                self.var_lifetime[var_name] = (start, current_counter)
            self.collect_lifetimes_expr(stmt.start)
            self.collect_lifetimes_expr(stmt.end)
            if stmt.step:
                self.collect_lifetimes_expr(stmt.step)
            for body_stmt in stmt.body:
                self.collect_lifetimes_stmt(body_stmt)
            # Extend lifetime to end of loop
            if var_name in self.var_lifetime:
                start, _ = self.var_lifetime[var_name]
                self.var_lifetime[var_name] = (start, self.statement_counter)
        elif isinstance(stmt, IfStmt):
            self.collect_lifetimes_expr(stmt.condition)
            for body_stmt in stmt.then_body:
                self.collect_lifetimes_stmt(body_stmt)
            for body_stmt in stmt.else_body:
                self.collect_lifetimes_stmt(body_stmt)
        elif isinstance(stmt, WhileStmt):
            self.collect_lifetimes_expr(stmt.condition)
            for body_stmt in stmt.body:
                self.collect_lifetimes_stmt(body_stmt)
        elif isinstance(stmt, RepeatStmt):
            for body_stmt in stmt.body:
                self.collect_lifetimes_stmt(body_stmt)
            self.collect_lifetimes_expr(stmt.condition)
        else:
            # For other statements, collect from expressions
            self.collect_lifetimes_expr_from_stmt(stmt)

    def collect_lifetimes_expr(self, expr):
        """Collect lifetimes from expressions."""
        if isinstance(expr, VariableExpr):
            var_name = expr.name
            current_counter = self.statement_counter
            if var_name not in self.var_lifetime:
                self.var_lifetime[var_name] = (current_counter, current_counter)
            else:
                start, end = self.var_lifetime[var_name]
                self.var_lifetime[var_name] = (min(start, current_counter), max(end, current_counter))
        elif isinstance(expr, BinaryExpr):
            self.collect_lifetimes_expr(expr.left)
            self.collect_lifetimes_expr(expr.right)
        elif isinstance(expr, UnaryExpr):
            self.collect_lifetimes_expr(expr.operand)
        elif isinstance(expr, FunctionCallExpr):
            for arg in expr.arguments:
                self.collect_lifetimes_expr(arg)
        elif isinstance(expr, GroupingExpr):
            self.collect_lifetimes_expr(expr.expression)
        # Literals don't have variables

    def collect_lifetimes_expr_from_stmt(self, stmt):
        """Collect lifetimes from statements that have expressions."""
        if isinstance(stmt, PxlOnStmt):
            self.collect_lifetimes_expr(stmt.x)
            self.collect_lifetimes_expr(stmt.y)
            self.collect_lifetimes_expr(stmt.color)
        elif isinstance(stmt, PxlOffStmt):
            self.collect_lifetimes_expr(stmt.x)
            self.collect_lifetimes_expr(stmt.y)
        elif isinstance(stmt, LineStmt):
            self.collect_lifetimes_expr(stmt.x1)
            self.collect_lifetimes_expr(stmt.y1)
            self.collect_lifetimes_expr(stmt.x2)
            self.collect_lifetimes_expr(stmt.y2)
            self.collect_lifetimes_expr(stmt.color)
        elif isinstance(stmt, CircleStmt):
            self.collect_lifetimes_expr(stmt.x)
            self.collect_lifetimes_expr(stmt.y)
            self.collect_lifetimes_expr(stmt.radius)
            self.collect_lifetimes_expr(stmt.color)
        elif isinstance(stmt, TextStmt):
            self.collect_lifetimes_expr(stmt.x)
            self.collect_lifetimes_expr(stmt.y)
            self.collect_lifetimes_expr(stmt.color)
        elif isinstance(stmt, SetLayerStmt):
            self.collect_lifetimes_expr(stmt.layer)
        elif isinstance(stmt, PlayToneStmt):
            self.collect_lifetimes_expr(stmt.frequency)
            self.collect_lifetimes_expr(stmt.duration)
            self.collect_lifetimes_expr(stmt.volume)
        elif isinstance(stmt, PlayWaveStmt):
            self.collect_lifetimes_expr(stmt.frequency)
            self.collect_lifetimes_expr(stmt.volume)
        elif isinstance(stmt, SetChannelStmt):
            self.collect_lifetimes_expr(stmt.channel)
        elif isinstance(stmt, DispStmt):
            self.collect_lifetimes_expr(stmt.expression)
        # Others don't have expressions

    def assign_registers(self):
        """Assign registers to variables using linear scan register allocation."""
        # Sort variables by start time
        vars_sorted = sorted(self.var_lifetime.items(), key=lambda x: x[1][0])
        
        active = []  # List of (end_time, reg)
        
        for var, (start, end) in vars_sorted:
            # Expire old intervals
            active = [(e, r) for e, r in active if e > start]
            
            # Try to allocate a register
            available_regs = [r for r in self.var_allocation_order if not any(r == ar for _, ar in active)]
            if available_regs:
                reg = available_regs[0]
                self.var_reg[var] = reg
                active.append((end, reg))
                # Mark as used
                self.register_usage[reg] = True
            # If no register, leave in memory

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
        self.var_reg = {}
        self.var_lifetime = {}
        self.statement_counter = 0

        # First pass: collect lifetimes
        self.collect_lifetimes(program)

        # Assign registers to variables
        self.assign_registers()

        # Set ORG to 0x0200 (past interrupt vectors)
        self.output.append("ORG 0x0200")
        
        # Initialize stack
        self.output.append("MOV SP, 0xF000")  # Initialize stack pointer
        self.output.append("MOV FP, SP")      # Initialize frame pointer

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
        self.output.append("; ClrDraw")
        self.output.append("MOV VL, 1")  # Layer 1
        self.output.append("SFILL 0x00")

    def generate_pxl_on(self, stmt: PxlOnStmt):
        """Generate PxlOn(x, y, color) code."""
        # Use coordinate mode addressing
        x_reg = self.generate_expression(stmt.x)  # Allocate register automatically
        y_reg = self.generate_expression(stmt.y)  # Allocate register automatically
        self.output.append(f"MOV VX, {x_reg}")  # VX = x coordinate
        self.output.append(f"MOV VY, {y_reg}")  # VY = y coordinate
        color_reg = self.generate_expression(stmt.color)  # Allocate register automatically
        self.output.append(f"MOV VC, {color_reg}")  # Use the allocated color register
        self.output.append("SWRITE VC")
        
        # Deallocate registers
        self.deallocate_register(x_reg)
        self.deallocate_register(y_reg)
        self.deallocate_register(color_reg)

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
        x1_reg = self.generate_expression(stmt.x1)
        y1_reg = self.generate_expression(stmt.y1)
        x2_reg = self.generate_expression(stmt.x2)
        y2_reg = self.generate_expression(stmt.y2)

        # Set up coordinates
        self.output.append(f"MOV VX, {x1_reg}")
        self.output.append(f"MOV VY, {y1_reg}")
        color_reg = self.generate_expression(stmt.color)
        self.output.append(f"MOV VC, {color_reg}")

        # Use SLINE opcode
        self.output.append(f"SLINE {x2_reg}, {y2_reg}")
        
        # Deallocate registers
        self.deallocate_register(x1_reg)
        self.deallocate_register(y1_reg)
        self.deallocate_register(x2_reg)
        self.deallocate_register(y2_reg)
        self.deallocate_register(color_reg)

    def generate_circle(self, stmt: CircleStmt):
        """Generate Circle drawing code using SCIRC opcode."""
        x_reg = self.generate_expression(stmt.x)
        y_reg = self.generate_expression(stmt.y)
        radius_reg = self.generate_expression(stmt.radius)
        color_reg = self.generate_expression(stmt.color)

        # Set coordinates and color
        self.output.append(f"MOV VX, {x_reg}")
        self.output.append(f"MOV VY, {y_reg}")
        self.output.append(f"MOV VC, {color_reg}")

        # Use SCIRC opcode
        self.output.append(f"SCIRC {radius_reg}, 1")  # 1 for filled
        
        # Deallocate registers
        self.deallocate_register(x_reg)
        self.deallocate_register(y_reg)
        self.deallocate_register(radius_reg)
        self.deallocate_register(color_reg)

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
        self.output.append("MOV VM, 0")  # Coordinate mode for pixel operations
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
        value_reg = self.generate_expression(stmt.expression, "P1")  # Prefer P register for 16-bit storage

        if isinstance(stmt.variable, VariableExpr):
            var_name = stmt.variable.name
            if var_name in self.var_reg:
                # Store to register
                reg = self.var_reg[var_name]
                if reg != value_reg:
                    self.output.append(f"MOV {reg}, {value_reg}")
            else:
                # Store to memory
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
        
        # Get registers for this nesting level
        current_reg, end_reg, step_reg = self.get_loop_registers()
        
        # Increment nesting level for inner constructs
        self.loop_nesting_level += 1

        # Allocate loop_reg
        is_register_allocated = stmt.variable in self.var_reg
        if is_register_allocated:
            loop_reg = self.var_reg[stmt.variable]
            self.register_usage[loop_reg] = True
        else:
            # Allocate loop_reg, preferring current_reg
            preferred = [current_reg] + ['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7']
            loop_reg = None
            for reg in preferred:
                if not self.register_usage.get(reg, False):
                    loop_reg = reg
                    break
            if not loop_reg:
                loop_reg = self.allocate_register()
            self.register_usage[loop_reg] = True

        # Allocate end_reg, avoiding conflicts
        if end_reg == loop_reg or self.register_usage.get(end_reg, False):
            end_reg = self.allocate_register()
        self.register_usage[end_reg] = True

        # Allocate step_reg, avoiding conflicts
        if step_reg == loop_reg or step_reg == end_reg or self.register_usage.get(step_reg, False):
            step_reg = self.allocate_register()
        self.register_usage[step_reg] = True

        # Initialize variable
        start_reg = self.generate_expression(stmt.start)
        self.output.append(f"MOV {loop_reg}, {start_reg}")
        if not is_register_allocated:
            var_addr = self.get_variable_address(stmt.variable)
            self.output.append(f"MOV P0, {var_addr}")
            self.output.append(f"MOV [P0], {loop_reg}")

        self.output.append(f"{loop_label}:")

        # Update memory for expressions if not register allocated
        if not is_register_allocated:
            var_addr = self.get_variable_address(stmt.variable)
            self.output.append(f"MOV P0, {var_addr}")
            self.output.append(f"MOV [P0], {loop_reg}")

        # Check condition
        end_reg_loaded = self.generate_expression(stmt.end, end_reg)
        self.output.append(f"CMP {loop_reg}, {end_reg_loaded}")

        # For ascending loops, exit when current > end (unsigned comparison)
        body_label = self.new_label()
        self.output.append(f"JC {body_label}")  # current < end
        self.output.append(f"JZ {body_label}")  # current == end
        self.output.append(f"JMP {end_label}")  # current > end
        self.output.append(f"{body_label}:")

        # Loop body
        for s in stmt.body:
            self.generate_statement(s)

        # Increment
        if stmt.step:
            step_reg_loaded = self.generate_expression(stmt.step, step_reg)
            self.output.append(f"ADD {loop_reg}, {step_reg_loaded}")
        else:
            # Optimize: use INC for step=1
            self.output.append(f"INC {loop_reg}")

        self.output.append(f"JMP {loop_label}")
        self.output.append(f"{end_label}:")

        if not is_register_allocated:
            self.deallocate_register(loop_reg)
        self.deallocate_register(end_reg)
        self.deallocate_register(step_reg)
        
        # Decrement nesting level
        self.loop_nesting_level -= 1

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

    def generate_expression(self, expr: Expression, preferred_reg: str = None) -> str:
        """Generate code for an expression and return the register containing the result."""
        if preferred_reg and self.register_usage.get(preferred_reg, False):
            # preferred_reg is already allocated, use it
            target_reg = preferred_reg
        else:
            # Allocate a new register
            target_reg = self.allocate_register(preferred_reg)
        
        try:
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
                        self.output.append(f"SHL {target_reg}, {shift_amount}")
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
        except Exception as e:
            # If anything goes wrong and we allocated the register here, deallocate it
            if not (preferred_reg and self.register_usage.get(preferred_reg, False)):
                self.deallocate_register(target_reg)
            raise

    def generate_binary_expression(self, expr: BinaryExpr, target_reg: str) -> str:
        """Generate optimized code for binary expressions."""
        # Allocate registers for operands, avoiding the target register
        available_regs = [r for r in self.allocation_order if r != target_reg]
        
        left_reg = self.allocate_register(available_regs[0] if available_regs else None)
        right_reg = self.allocate_register(available_regs[1] if len(available_regs) > 1 else None)
        
        try:
            left_result = self.generate_expression(expr.left, left_reg)
            right_result = self.generate_expression(expr.right, right_reg)

            if expr.operator == "+":
                if left_result == target_reg:
                    self.output.append(f"ADD {target_reg}, {right_result}")
                else:
                    self.output.append(f"MOV {target_reg}, {left_result}")
                    self.output.append(f"ADD {target_reg}, {right_result}")
            elif expr.operator == "-":
                if left_result == target_reg:
                    self.output.append(f"SUB {target_reg}, {right_result}")
                else:
                    self.output.append(f"MOV {target_reg}, {left_result}")
                    self.output.append(f"SUB {target_reg}, {right_result}")
            elif expr.operator == "*":
                if left_result == target_reg:
                    self.output.append(f"MUL {target_reg}, {right_result}")
                else:
                    self.output.append(f"MOV {target_reg}, {left_result}")
                    self.output.append(f"MUL {target_reg}, {right_result}")
            elif expr.operator == "/":
                if left_result == target_reg:
                    self.output.append(f"DIV {target_reg}, {right_result}")
                else:
                    self.output.append(f"MOV {target_reg}, {left_result}")
                    self.output.append(f"DIV {target_reg}, {right_result}")
            elif expr.operator == "%" or expr.operator == "MOD":
                if left_result == target_reg:
                    self.output.append(f"MOD {target_reg}, {right_result}")
                else:
                    self.output.append(f"MOV {target_reg}, {left_result}")
                    self.output.append(f"MOD {target_reg}, {right_result}")
            elif expr.operator == "&" or expr.operator == "AND":
                if left_result == target_reg:
                    self.output.append(f"AND {target_reg}, {right_result}")
                else:
                    self.output.append(f"MOV {target_reg}, {left_result}")
                    self.output.append(f"AND {target_reg}, {right_result}")
            elif expr.operator == "|" or expr.operator == "OR":
                if left_result == target_reg:
                    self.output.append(f"OR {target_reg}, {right_result}")
                else:
                    self.output.append(f"MOV {target_reg}, {left_result}")
                    self.output.append(f"OR {target_reg}, {right_result}")
            elif expr.operator == "^" or expr.operator == "XOR":
                if left_result == target_reg:
                    self.output.append(f"XOR {target_reg}, {right_result}")
                else:
                    self.output.append(f"MOV {target_reg}, {left_result}")
                    self.output.append(f"XOR {target_reg}, {right_result}")
            elif expr.operator == "<<" or expr.operator == "SHL":
                if left_result == target_reg:
                    self.output.append(f"SHL {target_reg}, {right_result}")
                else:
                    self.output.append(f"MOV {target_reg}, {left_result}")
                    self.output.append(f"SHL {target_reg}, {right_result}")
            elif expr.operator == ">>" or expr.operator == "SHR":
                if left_result == target_reg:
                    self.output.append(f"SHR {target_reg}, {right_result}")
                else:
                    self.output.append(f"MOV {target_reg}, {left_result}")
                    self.output.append(f"SHR {target_reg}, {right_result}")
            elif expr.operator == "<<<" or expr.operator == "SAL":
                if left_result == target_reg:
                    self.output.append(f"SAL {target_reg}, {target_reg}, {right_result}")
                else:
                    self.output.append(f"MOV {target_reg}, {left_result}")
                    self.output.append(f"SAL {target_reg}, {target_reg}, {right_result}")
            elif expr.operator == ">>>" or expr.operator == "SAR":
                if left_result == target_reg:
                    self.output.append(f"SAR {target_reg}, {target_reg}, {right_result}")
                else:
                    self.output.append(f"MOV {target_reg}, {left_result}")
                    self.output.append(f"SAR {target_reg}, {target_reg}, {right_result}")
            elif expr.operator == "<@>" or expr.operator == "ROL":
                if left_result == target_reg:
                    self.output.append(f"ROL {target_reg}, {target_reg}, {right_result}")
                else:
                    self.output.append(f"MOV {target_reg}, {left_result}")
                    self.output.append(f"ROL {target_reg}, {target_reg}, {right_result}")
            elif expr.operator == "@>" or expr.operator == "ROR":
                if left_result == target_reg:
                    self.output.append(f"ROR {target_reg}, {target_reg}, {right_result}")
                else:
                    self.output.append(f"MOV {target_reg}, {left_result}")
                    self.output.append(f"ROR {target_reg}, {target_reg}, {right_result}")
            elif expr.operator == "<@@" or expr.operator == "RCL":
                self.output.append(f"RCL {target_reg}, {left_result}, {right_result}")
            elif expr.operator == "@@>" or expr.operator == "RCR":
                self.output.append(f"RCR {target_reg}, {left_result}, {right_result}")
            elif expr.operator == "<" or expr.operator == ">" or expr.operator == "=" or expr.operator == "<>" or expr.operator == "<=" or expr.operator == ">=":
                # Use CMP for comparisons and set target_reg based on result
                self.output.append(f"CMP {left_result}, {right_result}")
                
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
                
        finally:
            # Always deallocate the operand registers
            self.deallocate_register(left_reg)
            self.deallocate_register(right_reg)
            
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
        if name in self.var_reg:
            reg = self.var_reg[name]
            if reg != target_reg:
                self.output.append(f"MOV {target_reg}, {reg}")
            return target_reg
        # Not in register, load from memory
        addr = self.get_variable_address(name)
        if target_reg.startswith('R'):
            # For 8-bit R registers, read the low byte (stored at addr + 1)
            self.output.append(f"MOV P0, {addr + 1}")
            self.output.append(f"MOV {target_reg}, [P0]")
        else:
            # For 16-bit P registers, read the full word
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