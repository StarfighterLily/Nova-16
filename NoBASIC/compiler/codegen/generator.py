"""
NoBASIC Code Generator
Generates Nova-16 assembly code from AST.

Enhanced with fine-grained liveness analysis for optimal register allocation.
Registers are freed immediately after their last use to minimize register pressure.
"""

from typing import List, Dict, Tuple, Set, Optional
from ..parser.ast import (
    Program, Statement, Expression, ClrDrawStmt, PxlOnStmt, PxlOffStmt,
    LineStmt, CircleStmt, TextStmt, SetLayerStmt, SpriteOnStmt, SpriteOffStmt,
    PlayToneStmt, PlayWaveStmt, StopSoundStmt, SetChannelStmt, GetKeyStmt,
    InputStmt, DispStmt, PauseStmt, FunctionCallStmt, AssignmentStmt, IfStmt, ForStmt,
    WhileStmt, RepeatStmt, GotoStmt, LabelStmt, StructDeclarationStmt, LiteralExpr, VariableExpr,
    ListAccessExpr, MatrixAccessExpr, MemberAccessExpr, BinaryExpr, UnaryExpr, FunctionCallExpr,
    GroupingExpr, StructType
)


class LivenessTracker:
    """
    Tracks register liveness at a fine-grained level.
    Determines when each register value is last used and can be freed.
    """
    
    def __init__(self):
        # Maps register to a list of "last use" positions in the expression tree
        self.register_last_use: Dict[str, int] = {}
        self.current_position = 0
        # Track which registers are managed by us (temporary) vs external (variables)
        self.managed_registers: Set[str] = set()
        
    def allocate_temp(self, reg: str):
        """Mark a register as a managed temporary."""
        self.managed_registers.add(reg)
        self.register_last_use[reg] = self.current_position
        
    def use_register(self, reg: str):
        """Update the last use position for a register."""
        self.register_last_use[reg] = self.current_position
        self.current_position += 1
        
    def mark_dead(self, reg: str) -> bool:
        """
        Mark a register as dead (no longer needed).
        Returns True if the register can be freed.
        """
        if reg in self.managed_registers:
            self.managed_registers.discard(reg)
            self.register_last_use.pop(reg, None)
            return True
        return False
        
    def get_dead_registers(self, after_position: int) -> Set[str]:
        """Get all registers that are dead after the given position."""
        dead = set()
        for reg, last_use in self.register_last_use.items():
            if last_use <= after_position and reg in self.managed_registers:
                dead.add(reg)
        return dead
        
    def reset(self):
        """Reset the tracker for a new statement or scope."""
        self.register_last_use.clear()
        self.managed_registers.clear()
        self.current_position = 0


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
        
        # Struct support
        self.struct_types: Dict[str, StructType] = {}  # struct_name -> StructType
        self.struct_bases: Dict[str, int] = {}  # instance_name -> base_address
        self.struct_instances: Dict[str, str] = {}  # var_name -> struct_name
        
        # Liveness analysis for fine-grained register management
        self.liveness = LivenessTracker()
        # Track registers that should be automatically freed after use
        self.auto_free_registers: Set[str] = set()

    def allocate_register(self, preferred_reg: str = None) -> str:
        """Allocate an unused register, preferring the specified register if available."""
        # Try preferred register first
        if preferred_reg and not self.register_usage[preferred_reg]:
            self.register_usage[preferred_reg] = True
            self.liveness.allocate_temp(preferred_reg)
            self.auto_free_registers.add(preferred_reg)
            return preferred_reg
        
        # Try allocation order
        for reg in self.allocation_order:
            if not self.register_usage[reg]:
                self.register_usage[reg] = True
                self.liveness.allocate_temp(reg)
                self.auto_free_registers.add(reg)
                return reg
        
        raise RuntimeError("No available registers for allocation")

    def deallocate_register(self, reg: str):
        """Deallocate a register, marking it as available."""
        if reg in self.register_usage:
            self.register_usage[reg] = False
            self.liveness.mark_dead(reg)
            self.auto_free_registers.discard(reg)
            
    def smart_deallocate(self, reg: str, is_last_use: bool = True):
        """
        Intelligently deallocate a register only if it's truly no longer needed.
        
        Args:
            reg: Register to potentially deallocate
            is_last_use: If True, this is the last use of the register's value
        """
        # Only deallocate if this is truly the last use
        # Check if it's a register that was allocated (not a variable register)
        if is_last_use and reg in self.register_usage and self.register_usage[reg]:
            # Don't free variable registers (they stay allocated throughout)
            if reg not in self.var_reg.values():
                self.deallocate_register(reg)
                self.output.append(f"; Free {reg} (last use)")
            
    def generate_and_free_args(self, arguments: List[Expression], preferred_regs: List[str] = None) -> List[str]:
        """
        Generate code for function arguments and prepare them for auto-freeing.
        Returns a list of registers containing the argument values.
        These registers will be automatically freed when smart_deallocate is called.
        
        Args:
            arguments: List of argument expressions
            preferred_regs: List of preferred registers for each argument
            
        Returns:
            List of registers containing argument values
        """
        if preferred_regs is None:
            preferred_regs = [f"R{i+1}" for i in range(len(arguments))]
            
        arg_regs = []
        for i, arg in enumerate(arguments):
            pref = preferred_regs[i] if i < len(preferred_regs) else None
            arg_reg = self.generate_expression(arg, pref)
            arg_regs.append(arg_reg)
        return arg_regs
        
    def free_args(self, arg_regs: List[str]):
        """Free all argument registers after they've been used."""
        for reg in arg_regs:
            self.smart_deallocate(reg, is_last_use=True)

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
            if isinstance(stmt.variable, VariableExpr):
                var_name = stmt.variable.name
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
            for body_stmt in stmt.then_branch:
                self.collect_lifetimes_stmt(body_stmt)
            if stmt.else_branch:
                for body_stmt in stmt.else_branch:
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
        elif isinstance(expr, ListAccessExpr):
            self.collect_lifetimes_expr(expr.index)
        elif isinstance(expr, MemberAccessExpr):
            self.collect_lifetimes_expr(expr.object)
        elif isinstance(expr, MatrixAccessExpr):
            self.collect_lifetimes_expr(expr.row)
            self.collect_lifetimes_expr(expr.col)
        elif isinstance(expr, BinaryExpr):
            self.collect_lifetimes_expr(expr.left)
            self.collect_lifetimes_expr(expr.right)
        elif isinstance(expr, UnaryExpr):
            self.collect_lifetimes_expr(expr.expression)
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
            self.collect_lifetimes_expr(stmt.text)
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
        elif isinstance(stmt, StructDeclarationStmt):
            self.generate_struct_declaration(stmt)

    def generate_struct_declaration(self, stmt: StructDeclarationStmt):
        """Register struct type (no assembly code generated)."""
        self.struct_types[stmt.name] = StructType(stmt.name, stmt.fields)
        self.output.append(f"; Struct {stmt.name} declared with fields: {', '.join(stmt.fields)}")

    def generate_clr_draw(self):
        """Generate ClrDraw code."""
        self.output.append("; ClrDraw")
        self.output.append("MOV VL, 1")  # Layer 1
        self.output.append("SFILL 0x00")

    def generate_pxl_on(self, stmt: PxlOnStmt):
        """Generate optimized PxlOn(x, y, color) code with direct hardware register assignment."""
        # Generate expressions directly into hardware registers - no intermediate MOVs!
        self.generate_expression_into(stmt.x, 'VX')
        self.generate_expression_into(stmt.y, 'VY')
        self.generate_expression_into(stmt.color, 'VC')
        self.output.append("SWRITE VC")

    def generate_pxl_off(self, stmt: PxlOffStmt):
        """Generate optimized PxlOff(x, y) code with direct hardware register assignment."""
        self.generate_expression_into(stmt.x, 'VX')
        self.generate_expression_into(stmt.y, 'VY')
        self.output.append("MOV VC, 0")
        self.output.append("SWRITE VC")

    def generate_line(self, stmt: LineStmt):
        """Generate optimized Line drawing code using SLINE opcode with direct register assignment."""
        # Generate start coordinates directly into hardware registers
        self.generate_expression_into(stmt.x1, 'VX')
        self.generate_expression_into(stmt.y1, 'VY')
        self.generate_expression_into(stmt.color, 'VC')

        # For end coordinates, we need temp registers for SLINE operands
        x2_reg = self.generate_expression(stmt.x2)
        y2_reg = self.generate_expression(stmt.y2)

        # Use SLINE opcode
        self.output.append(f"SLINE {x2_reg}, {y2_reg}")
        
        # Deallocate temp registers
        self.deallocate_register(x2_reg)
        self.deallocate_register(y2_reg)

    def generate_circle(self, stmt: CircleStmt):
        """Generate optimized Circle drawing code using SCIRC opcode with direct register assignment."""
        # Generate coordinates and color directly into hardware registers
        self.generate_expression_into(stmt.x, 'VX')
        self.generate_expression_into(stmt.y, 'VY')
        self.generate_expression_into(stmt.color, 'VC')

        # Radius needs a temp register for SCIRC operand
        radius_reg = self.generate_expression(stmt.radius)

        # Use SCIRC opcode
        self.output.append(f"SCIRC {radius_reg}, 1")  # 1 for filled
        
        # Deallocate temp register
        self.deallocate_register(radius_reg)

    def generate_text(self, stmt: TextStmt):
        """Generate optimized Text rendering code using TEXT opcode with direct register assignment."""
        # Set graphics registers directly
        self.generate_expression_into(stmt.x, 'VX')
        self.generate_expression_into(stmt.y, 'VY')
        self.generate_expression_into(stmt.color, 'VC')

        # Handle text expression
        if isinstance(stmt.text, LiteralExpr) and stmt.text.data_type.name == "STRING":
            # For string literals, create a label and display directly
            label = self.add_string_literal(stmt.text.value)
            self.output.append(f"TEXT {label}")
        elif isinstance(stmt.text, VariableExpr) and stmt.text.name.upper().startswith("STR"):
            # String variable - load address and display
            text_addr_reg = self.generate_expression(stmt.text)
            self.output.append(f"TEXT {text_addr_reg}")
        elif isinstance(stmt.text, BinaryExpr) and stmt.text.operator == "+":
            # Likely string concatenation - evaluate to get address
            text_addr_reg = self.generate_expression(stmt.text)
            self.output.append(f"TEXT {text_addr_reg}")
        else:
            # For numeric expressions, convert to string first
            text_value_reg = self.generate_expression(stmt.text)
            string_reg = self.allocate_register()  # Use P register for string address
            self.output.append(f"ITOS {string_reg}, {text_value_reg}")  # Convert number to string
            self.output.append(f"TEXT {string_reg}")  # Display the converted string
            self.deallocate_register(string_reg)

    def generate_set_layer(self, stmt: SetLayerStmt):
        """Generate optimized SetLayer(layer) code with direct register assignment."""
        self.output.append("MOV VM, 0")  # Coordinate mode for pixel operations
        self.generate_expression_into(stmt.layer, 'VL')

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
        freq_reg = self.generate_expression(stmt.frequency)
        dur_reg = self.generate_expression(stmt.duration)
        vol_reg = self.generate_expression(stmt.volume)
        
        # Set sound registers
        self.output.append(f"MOV SF, {freq_reg}")
        self.output.append(f"MOV SV, {vol_reg}")
        self.output.append("MOV SW, 0")  # Set waveform to default (0)
        self.output.append("SPLAY")

        # Duration handling could use timer, but simplified for now
        self.output.append("; Duration handling - simplified")

    def generate_play_wave(self, stmt: PlayWaveStmt):
        """Generate optimized PlayWave code."""
        wave_reg = self.generate_expression(stmt.waveform)
        freq_reg = self.generate_expression(stmt.frequency)
        vol_reg = self.generate_expression(stmt.volume)
        
        # Set sound registers
        self.output.append(f"MOV SW, {wave_reg}")
        self.output.append(f"MOV SF, {freq_reg}")
        self.output.append(f"MOV SV, {vol_reg}")
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
            # Handle prompt display
            if isinstance(stmt.prompt, LiteralExpr) and stmt.prompt.data_type.name == "STRING":
                # For string literals, display directly
                prompt_label = self.add_string_literal(stmt.prompt.value)
                self.output.append(f"TEXT {prompt_label}, 15")  # White color
            else:
                # For expressions, evaluate and try to display (simplified for now)
                prompt_reg = self.generate_expression(stmt.prompt, "R1")
                self.output.append(f"TEXT {prompt_reg}, 15")  # This may not work properly for non-strings

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
        # Check if this is a string expression
        if isinstance(stmt.text, LiteralExpr) and stmt.text.data_type.name == "STRING":
            # String literal - create label and display
            label = self.add_string_literal(stmt.text.value)
            self.output.append("MOV VX, 0")  # Set X coordinate
            self.output.append("MOV VY, 0")  # Set Y coordinate  
            self.output.append("MOV VC, 15")  # Set color to white
            self.output.append(f"TEXT {label}")  # Display text
        elif isinstance(stmt.text, VariableExpr) and stmt.text.name.upper().startswith("STR"):
            # String variable - load address and display
            text_addr_reg = self.generate_expression(stmt.text, "P1")
            self.output.append("MOV VX, 0")  # Set X coordinate
            self.output.append("MOV VY, 0")  # Set Y coordinate  
            self.output.append("MOV VC, 15")  # Set color to white
            self.output.append(f"TEXT {text_addr_reg}")  # Display text
        elif isinstance(stmt.text, BinaryExpr) and stmt.text.operator == "+":
            # Likely string concatenation - evaluate to get address
            text_addr_reg = self.generate_expression(stmt.text, "P1")
            self.output.append("MOV VX, 0")  # Set X coordinate
            self.output.append("MOV VY, 0")  # Set Y coordinate  
            self.output.append("MOV VC, 15")  # Set color to white
            self.output.append(f"TEXT {text_addr_reg}")  # Display text
        else:
            # Numeric expression - evaluate and convert to string
            value_reg = self.generate_expression(stmt.text, "R1")
            string_reg = self.allocate_register("P1")  # Use a P register for string address
            self.output.append(f"ITOS {string_reg}, {value_reg}")  # Convert to string
            self.output.append("MOV VX, 0")  # Set X coordinate
            self.output.append("MOV VY, 0")  # Set Y coordinate  
            self.output.append("MOV VC, 15")  # Set color to white
            self.output.append(f"TEXT {string_reg}")  # Display text
            self.deallocate_register(string_reg)

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
        # Check if we're assigning a string - if so, ensure we use P register
        is_string_assignment = False
        if isinstance(stmt.variable, VariableExpr):
            is_string_assignment = stmt.variable.name.upper().startswith("STR")
        
        # Generate the value - prefer P register for strings or 16-bit values
        preferred_reg = "P1" if is_string_assignment else "P1"
        value_reg = self.generate_expression(stmt.expression, preferred_reg)

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
        elif isinstance(stmt.variable, MemberAccessExpr):
            # Struct member assignment
            self.generate_member_store(stmt.variable, value_reg)
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

    def generate_member_access(self, expr: MemberAccessExpr, target_reg: str) -> str:
        """Generate code to load from a struct member."""
        if isinstance(expr.object, VariableExpr):
            var_name = expr.object.name
            
            # Check if this is a struct instance
            if var_name in self.struct_instances:
                struct_name = self.struct_instances[var_name]
                struct_def = self.struct_types[struct_name]
                base_addr = self.struct_bases[var_name]
                
                # Calculate field offset
                field_index = struct_def.fields.index(expr.member)
                field_offset = field_index * 2  # 2 bytes per field
                field_addr = base_addr + field_offset
                
                # CRITICAL: Struct fields are 16-bit unsigned values.
                # ALWAYS load into 16-bit P registers to preserve unsigned values!
                # This fixes signed comparison issues with values > 127.
                self.output.append(f"; Load {var_name}.{expr.member}")
                self.output.append(f"MOV P0, {field_addr}")
                
                # If target_reg is a P register, use it directly
                # If target_reg is an R register, we cannot use it (would lose unsigned value)
                # In that case, just use P1 and return it (caller will handle the mismatch)
                if target_reg.startswith('P'):
                    # Target is already a P register, use it
                    self.output.append(f"MOV {target_reg}, [P0]")
                    return target_reg
                else:
                    # Target is an R register, but we need P for unsigned values
                    # Use P1 as a temporary and return it
                    # The caller's target_reg will be unused but that's OK
                    self.output.append(f"MOV P1, [P0]")
                    return 'P1'
            else:
                # Auto-allocate struct instance on first use
                # Try to infer struct type from context (if only one struct defined)
                if len(self.struct_types) == 1:
                    struct_name = list(self.struct_types.keys())[0]
                    self.allocate_struct_instance(var_name, struct_name)
                    return self.generate_member_access(expr, target_reg)
                else:
                    raise RuntimeError(f"Cannot determine struct type for '{var_name}'")
        else:
            raise RuntimeError(f"Member access only supported on variable expressions")

    def generate_member_store(self, expr: MemberAccessExpr, value_reg: str):
        """Generate code to store to a struct member."""
        if isinstance(expr.object, VariableExpr):
            var_name = expr.object.name
            
            # Check if this is a struct instance
            if var_name in self.struct_instances:
                struct_name = self.struct_instances[var_name]
                struct_def = self.struct_types[struct_name]
                base_addr = self.struct_bases[var_name]
                
                # Calculate field offset
                field_index = struct_def.fields.index(expr.member)
                field_offset = field_index * 2  # 2 bytes per field
                field_addr = base_addr + field_offset
                
                # Store field value
                self.output.append(f"; Store to {var_name}.{expr.member}")
                self.output.append(f"MOV P0, {field_addr}")
                self.output.append(f"MOV [P0], {value_reg}")
            else:
                # Auto-allocate struct instance on first use
                # Try to infer struct type from context (if only one struct defined)
                if len(self.struct_types) == 1:
                    struct_name = list(self.struct_types.keys())[0]
                    self.allocate_struct_instance(var_name, struct_name)
                    self.generate_member_store(expr, value_reg)
                else:
                    raise RuntimeError(f"Cannot determine struct type for '{var_name}'")
        else:
            raise RuntimeError(f"Member access only supported on variable expressions")

    def allocate_struct_instance(self, var_name: str, struct_name: str) -> int:
        """Allocate memory for a struct instance."""
        if var_name in self.struct_bases:
            return self.struct_bases[var_name]
        
        struct_def = self.struct_types[struct_name]
        field_count = len(struct_def.fields)
        
        base_addr = self.next_address
        self.struct_bases[var_name] = base_addr
        self.struct_instances[var_name] = struct_name
        self.next_address += field_count * 2  # 2 bytes per field
        
        self.output.append(f"; Allocate struct {var_name} ({struct_name}) at 0x{base_addr:04X}")
        return base_addr

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
        """Generate optimized For loop code with hoisted end value and efficient comparisons."""
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
            # Register the loop variable so the body knows where it is
            self.var_reg[stmt.variable] = loop_reg

        # Allocate end_reg, avoiding conflicts
        if end_reg == loop_reg or self.register_usage.get(end_reg, False):
            end_reg = self.allocate_register()
        self.register_usage[end_reg] = True

        # Allocate step_reg if needed, avoiding conflicts
        if stmt.step:
            if step_reg == loop_reg or step_reg == end_reg or self.register_usage.get(step_reg, False):
                step_reg = self.allocate_register()
            self.register_usage[step_reg] = True

        # Initialize loop variable
        start_reg = self.generate_expression(stmt.start)
        self.output.append(f"MOV {loop_reg}, {start_reg}")
        self.deallocate_register(start_reg)
        if not is_register_allocated:
            var_addr = self.get_variable_address(stmt.variable)
            self.output.append(f"MOV P0, {var_addr}")
            self.output.append(f"MOV [P0], {loop_reg}")

        # **OPTIMIZATION: Load end value ONCE before loop**
        end_value_reg = self.generate_expression(stmt.end, end_reg)
        if end_value_reg != end_reg:
            self.output.append(f"MOV {end_reg}, {end_value_reg}")
            self.deallocate_register(end_value_reg)
            end_value_reg = end_reg

        # Load step value once if it's a constant expression
        if stmt.step:
            step_value_reg = self.generate_expression(stmt.step, step_reg)
            if step_value_reg != step_reg:
                self.output.append(f"MOV {step_reg}, {step_value_reg}")
                self.deallocate_register(step_value_reg)
                step_value_reg = step_reg

        # Loop start
        self.output.append(f"{loop_label}:")

        # Update memory for loop variable if not register-allocated
        if not is_register_allocated:
            var_addr = self.get_variable_address(stmt.variable)
            self.output.append(f"MOV P0, {var_addr}")
            self.output.append(f"MOV [P0], {loop_reg}")

        # **OPTIMIZATION: Single comparison with proper jump instruction**
        # Compare current to end (end value already in register)
        self.output.append(f"CMP {loop_reg}, {end_value_reg}")
        
        # Use JGT (jump if greater than) for cleaner exit condition
        # Loop continues while loop_reg <= end_value_reg
        self.output.append(f"JGT {end_label}")  # Exit if current > end

        # Loop body
        for s in stmt.body:
            self.generate_statement(s)

        # Increment/step
        if stmt.step:
            # Use pre-loaded step value
            self.output.append(f"ADD {loop_reg}, {step_value_reg}")
        else:
            # **OPTIMIZATION: Use INC for default step=1**
            self.output.append(f"INC {loop_reg}")

        self.output.append(f"JMP {loop_label}")
        self.output.append(f"{end_label}:")

        # Cleanup
        if not is_register_allocated:
            # Remove from var_reg since we allocated it
            if stmt.variable in self.var_reg:
                del self.var_reg[stmt.variable]
            self.deallocate_register(loop_reg)
        self.deallocate_register(end_reg)
        if stmt.step:
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

    def fold_constants(self, operator: str, left_val, right_val):
        """
        Evaluate constant expressions at compile time.
        
        Returns the computed value, or None if the operation cannot be folded.
        """
        try:
            if operator == "+":
                return left_val + right_val
            elif operator == "-":
                return left_val - right_val
            elif operator == "*":
                return left_val * right_val
            elif operator == "/":
                if right_val == 0:
                    return None  # Avoid division by zero at compile time
                return int(left_val / right_val)  # Integer division
            elif operator == "%" or operator == "MOD":
                if right_val == 0:
                    return None
                return left_val % right_val
            elif operator == "&" or operator == "AND":
                return int(left_val) & int(right_val)
            elif operator == "|" or operator == "OR":
                return int(left_val) | int(right_val)
            elif operator == "^" or operator == "XOR":
                return int(left_val) ^ int(right_val)
            elif operator == "<<" or operator == "SHL":
                return int(left_val) << int(right_val)
            elif operator == ">>" or operator == "SHR":
                return int(left_val) >> int(right_val)
            elif operator == "<":
                return 1 if left_val < right_val else 0
            elif operator == ">":
                return 1 if left_val > right_val else 0
            elif operator == "=":
                return 1 if left_val == right_val else 0
            elif operator == "<>":
                return 1 if left_val != right_val else 0
            elif operator == "<=":
                return 1 if left_val <= right_val else 0
            elif operator == ">=":
                return 1 if left_val >= right_val else 0
            else:
                # Unknown operator, cannot fold
                return None
        except (ValueError, TypeError, ZeroDivisionError):
            # Cannot fold this expression
            return None

    def fold_unary_constant(self, operator: str, value):
        """
        Evaluate constant unary expressions at compile time.
        
        Returns the computed value, or None if the operation cannot be folded.
        """
        try:
            if operator == "-":
                return -value
            elif operator == "NOT":
                return ~int(value)  # Bitwise NOT
            elif operator == "ABS":
                return abs(value)
            else:
                return None
        except (ValueError, TypeError):
            return None

    def is_string_expression(self, expr: Expression) -> bool:
        """Check if an expression will produce a string address (16-bit)."""
        if isinstance(expr, LiteralExpr):
            return expr.data_type.name == "STRING"
        elif isinstance(expr, VariableExpr):
            # String variables (Str1, Str2, etc.) hold string addresses
            return expr.name.upper().startswith("STR")
        elif isinstance(expr, BinaryExpr):
            # String concatenation with + operator, or nested string operations
            if expr.operator == "+":
                return self.is_string_expression(expr.left) or self.is_string_expression(expr.right)
        return False

    def generate_expression_into(self, expr: Expression, target_reg: str):
        """
        Generate an expression directly into a target register (hardware or general).
        This avoids the intermediate MOV instruction when the target is known.
        Optimized for hardware registers like VX, VY, VC.
        
        Args:
            expr: The expression to generate
            target_reg: The register to place the result in (e.g., 'VX', 'VY', 'VC', 'R0', 'P1')
        """
        # For simple cases, generate directly
        if isinstance(expr, LiteralExpr):
            if expr.data_type.name == "NUMBER":
                # Generate literal directly into target
                if expr.value == 0:
                    self.output.append(f"XOR {target_reg}, {target_reg}")
                elif expr.value == 1:
                    self.output.append(f"MOV {target_reg}, 1")
                elif expr.value in [2, 4, 8, 16, 32, 64, 128, 256, 512, 1024]:
                    # Use shifts for powers of 2
                    shift_amount = expr.value.bit_length() - 1
                    self.output.append(f"MOV {target_reg}, 1")
                    self.output.append(f"SHL {target_reg}, {shift_amount}")
                else:
                    self.output.append(f"MOV {target_reg}, {expr.value}")
            elif expr.data_type.name == "STRING":
                label = self.add_string_literal(expr.value)
                self.output.append(f"MOV {target_reg}, {label}")
            else:
                self.output.append(f"MOV {target_reg}, 0")
        elif isinstance(expr, VariableExpr):
            # Load variable directly into target
            if expr.name in self.var_reg:
                reg = self.var_reg[expr.name]
                if reg != target_reg:
                    self.output.append(f"MOV {target_reg}, {reg}")
                # If reg == target_reg, no operation needed!
            else:
                # Load from memory directly into target
                addr = self.get_variable_address(expr.name)
                if target_reg.startswith('R') or target_reg in ['VX', 'VY', 'VC', 'VL', 'VM']:
                    # For 8-bit registers, read the low byte
                    self.output.append(f"MOV P0, {addr + 1}")
                    self.output.append(f"MOV {target_reg}, [P0]")
                else:
                    # For 16-bit registers, read the full word
                    self.output.append(f"MOV P0, {addr}")
                    self.output.append(f"MOV {target_reg}, [P0]")
        else:
            # For complex expressions, generate into a temp then move
            temp_reg = self.generate_expression(expr)
            if temp_reg != target_reg:
                self.output.append(f"MOV {target_reg}, {temp_reg}")
            self.deallocate_register(temp_reg)

    def generate_expression(self, expr: Expression, preferred_reg: str = None) -> str:
        """Generate code for an expression and return the register containing the result."""
        # Check if this expression will produce a string address (needs P register)
        needs_p_register = self.is_string_expression(expr)
        
        # If we need a P register but preferred_reg is an R register, ignore the preference
        if needs_p_register and preferred_reg and preferred_reg.startswith('R'):
            preferred_reg = None
        
        # If we need a P register and no preferred_reg, ensure we get a P register
        if needs_p_register and not preferred_reg:
            # Find first available P register
            for reg in ['P0', 'P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7']:
                if not self.register_usage.get(reg, False):
                    preferred_reg = reg
                    break
        
        if preferred_reg and not self.register_usage.get(preferred_reg, False):
            # Preferred register is available, use it
            target_reg = self.allocate_register(preferred_reg)
        else:
            # No preferred register or it's busy
            if needs_p_register:
                # Force allocation from P registers only
                for reg in ['P0', 'P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7']:
                    if not self.register_usage.get(reg, False):
                        target_reg = self.allocate_register(reg)
                        break
                else:
                    raise RuntimeError("No available P registers for string expression")
            else:
                # Allocate any available register
                target_reg = self.allocate_register()
                
        try:
            result_reg = None
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
                    result_reg = target_reg
                elif expr.data_type.name == "STRING":
                    # String literals: create DEFSTR label and load address (16-bit, needs P register)
                    # If we somehow got an R register, we need to fix it
                    if target_reg.startswith('R'):
                        self.deallocate_register(target_reg)
                        target_reg = self.allocate_register('P1')
                    label = self.add_string_literal(expr.value)
                    self.output.append(f"MOV {target_reg}, {label}")
                    result_reg = target_reg
                else:
                    # Other types - default to zero
                    self.output.append(f"MOV {target_reg}, 0")
                    result_reg = target_reg
            elif isinstance(expr, VariableExpr):
                result_reg = self.load_variable(expr.name, target_reg)
            elif isinstance(expr, MemberAccessExpr):
                result_reg = self.generate_member_access(expr, target_reg)
            elif isinstance(expr, ListAccessExpr):
                result_reg = self.generate_list_access(expr, target_reg)
            elif isinstance(expr, MatrixAccessExpr):
                result_reg = self.generate_matrix_access(expr, target_reg)
            elif isinstance(expr, BinaryExpr):
                result_reg = self.generate_binary_expression(expr, target_reg)
            elif isinstance(expr, UnaryExpr):
                result_reg = self.generate_unary_expression(expr, target_reg)
            elif isinstance(expr, FunctionCallExpr):
                result_reg = self.generate_function_call(expr, target_reg)
            else:
                self.output.append(f"MOV {target_reg}, 0")  # Default
                result_reg = target_reg
                
            # Result register is returned to caller - they are responsible for freeing it
            return result_reg
        except Exception as e:
            # If anything goes wrong and we allocated the register here, deallocate it
            if not (preferred_reg and self.register_usage.get(preferred_reg, False)):
                self.deallocate_register(target_reg)
            raise

    def generate_binary_expression(self, expr: BinaryExpr, target_reg: str) -> str:
        """Generate optimized code for binary expressions with immediate register freeing."""
        # **OPTIMIZATION: Constant Folding**
        # If both operands are numeric literals, evaluate at compile time
        if (isinstance(expr.left, LiteralExpr) and isinstance(expr.right, LiteralExpr) and
            expr.left.data_type.name == "NUMBER" and expr.right.data_type.name == "NUMBER"):
            
            folded_value = self.fold_constants(expr.operator, expr.left.value, expr.right.value)
            if folded_value is not None:
                self.output.append(f"; Constant folded: {expr.left.value} {expr.operator} {expr.right.value} = {folded_value}")
                self.output.append(f"MOV {target_reg}, {folded_value}")
                return target_reg
        
        # Check if this is string concatenation using our helper
        is_string_concat = False
        if expr.operator == "+":
            is_string_concat = self.is_string_expression(expr.left) or self.is_string_expression(expr.right)
        
        if is_string_concat:
            # String concatenation: allocate temporary buffer and use STRCAT
            # Ensure target_reg is a P register (string addresses are 16-bit)
            if target_reg.startswith('R'):
                self.deallocate_register(target_reg)
                target_reg = self.allocate_register('P1')
            
            # Generate left operand
            left_result = self.generate_expression(expr.left)
            # Immediately move to a safe temporary if needed
            if left_result != 'P2':
                self.output.append(f"MOV P2, {left_result}")
                # Free the left result register immediately after moving
                self.smart_deallocate(left_result, is_last_use=True)
                left_result = 'P2'
                self.register_usage['P2'] = True
            
            # Generate right operand (left_result is now in P2)
            right_result = self.generate_expression(expr.right)
            # Immediately move to a safe temporary if needed
            if right_result != 'P3':
                self.output.append(f"MOV P3, {right_result}")
                # Free the right result register immediately after moving
                self.smart_deallocate(right_result, is_last_use=True)
                right_result = 'P3'
                self.register_usage['P3'] = True
            
            try:
                # Allocate temporary buffer for result (use next_address space)
                buffer_addr = self.next_address
                self.next_address += 256  # Reserve 256 bytes for concatenated string
                
                # Copy left string to buffer
                self.output.append(f"MOV P0, {buffer_addr}")  # Destination
                self.output.append(f"STRCPY P0, {left_result}")  # Copy left string
                
                # Concatenate right string to buffer
                self.output.append(f"STRCAT P0, {right_result}")  # Append right string
                
                # Return buffer address in target register
                self.output.append(f"MOV {target_reg}, {buffer_addr}")
                
                return target_reg
            finally:
                # Deallocate the temporary registers
                self.deallocate_register('P2')
                self.deallocate_register('P3')
        
        # Numeric operations - allocate registers for operands, avoiding the target register
        available_regs = [r for r in self.allocation_order if r != target_reg]
        
        left_reg = self.allocate_register(available_regs[0] if available_regs else None)
        right_reg = self.allocate_register(available_regs[1] if len(available_regs) > 1 else None)
        
        try:
            # Generate left operand
            left_result = self.generate_expression(expr.left, left_reg)
            
            # Generate right operand
            right_result = self.generate_expression(expr.right, right_reg)

            # Perform the operation
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
                
                # Free registers immediately after comparison
                self.smart_deallocate(left_result, is_last_use=True)
                self.smart_deallocate(right_result, is_last_use=True)
                
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
                
                # Registers already freed above for comparisons
                return target_reg
            else:
                # Fallback
                self.output.append(f"MOV {target_reg}, #0")
                
            # Free operand registers immediately after use (unless they're the target)
            if left_result != target_reg:
                self.smart_deallocate(left_result, is_last_use=True)
            if right_result != target_reg:
                self.smart_deallocate(right_result, is_last_use=True)
                
        finally:
            # Always deallocate the pre-allocated registers if they weren't already freed
            if left_reg in self.auto_free_registers:
                self.deallocate_register(left_reg)
            if right_reg in self.auto_free_registers:
                self.deallocate_register(right_reg)
            
        return target_reg

    def generate_unary_expression(self, expr: UnaryExpr, target_reg: str) -> str:
        """Generate code for unary expressions with immediate register freeing."""
        # **OPTIMIZATION: Constant Folding for Unary Operations**
        # If operand is a numeric literal, evaluate at compile time
        if isinstance(expr.expression, LiteralExpr) and expr.expression.data_type.name == "NUMBER":
            folded_value = self.fold_unary_constant(expr.operator, expr.expression.value)
            if folded_value is not None:
                self.output.append(f"; Constant folded: {expr.operator}({expr.expression.value}) = {folded_value}")
                self.output.append(f"MOV {target_reg}, {folded_value}")
                return target_reg
        
        operand_reg = self.generate_expression(expr.expression, target_reg)

        if expr.operator == "-":
            # NEG modifies in place, so move to target first if needed
            if operand_reg != target_reg:
                self.output.append(f"MOV {target_reg}, {operand_reg}")
                self.smart_deallocate(operand_reg, is_last_use=True)
            self.output.append(f"NEG {target_reg}")
        elif expr.operator == "NOT":
            if operand_reg != target_reg:
                self.output.append(f"MOV {target_reg}, {operand_reg}")
                self.smart_deallocate(operand_reg, is_last_use=True)
            self.output.append(f"NOT {target_reg}")
        elif expr.operator == "ABS":
            if operand_reg != target_reg:
                self.output.append(f"MOV {target_reg}, {operand_reg}")
                self.smart_deallocate(operand_reg, is_last_use=True)
            self.output.append(f"ABS {target_reg}")
        else:
            if operand_reg != target_reg:
                self.output.append(f"MOV {target_reg}, {operand_reg}")
                self.smart_deallocate(operand_reg, is_last_use=True)
        return target_reg

    def generate_function_call(self, expr: FunctionCallExpr, target_reg: str) -> str:
        """Generate optimized code for function calls with immediate register freeing."""
        func_name = expr.name.upper()

        if func_name == "SIN":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"SIN {target_reg}, {arg_reg}")
            self.smart_deallocate(arg_reg, is_last_use=True)
        elif func_name == "COS":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"COS {target_reg}, {arg_reg}")
            self.smart_deallocate(arg_reg, is_last_use=True)
        elif func_name == "TAN":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"TAN {target_reg}, {arg_reg}")
            self.smart_deallocate(arg_reg, is_last_use=True)
        elif func_name == "SQRT":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"SQRT {target_reg}, {arg_reg}")
            self.smart_deallocate(arg_reg, is_last_use=True)
        elif func_name == "ABS":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"ABS {target_reg}, {arg_reg}")
            self.smart_deallocate(arg_reg, is_last_use=True)
        elif func_name == "RND":
            self.output.append(f"RND {target_reg}")
        elif func_name == "LEN" or func_name == "LENGTH" or func_name == "STRLEN":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"STRLEN {target_reg}, {arg_reg}")
            self.smart_deallocate(arg_reg, is_last_use=True)
        elif func_name == "STRCPY":
            dest_reg = self.generate_expression(expr.arguments[0], "R1")
            src_reg = self.generate_expression(expr.arguments[1], "R2")
            self.output.append(f"STRCPY {dest_reg}, {src_reg}")
            self.output.append(f"MOV {target_reg}, {dest_reg}")  # Return destination
            self.smart_deallocate(dest_reg, is_last_use=True)
            self.smart_deallocate(src_reg, is_last_use=True)
        elif func_name == "STRCAT":
            dest_reg = self.generate_expression(expr.arguments[0], "R1")
            src_reg = self.generate_expression(expr.arguments[1], "R2")
            self.output.append(f"STRCAT {dest_reg}, {src_reg}")
            self.output.append(f"MOV {target_reg}, {dest_reg}")  # Return destination
            self.smart_deallocate(dest_reg, is_last_use=True)
            self.smart_deallocate(src_reg, is_last_use=True)
        elif func_name == "STRCMP":
            str1_reg = self.generate_expression(expr.arguments[0], "R1")
            str2_reg = self.generate_expression(expr.arguments[1], "R2")
            len_reg = self.generate_expression(expr.arguments[2], "R3")
            self.output.append(f"STRCMP {target_reg}, {str1_reg}, {str2_reg}, {len_reg}")
            self.smart_deallocate(str1_reg, is_last_use=True)
            self.smart_deallocate(str2_reg, is_last_use=True)
            self.smart_deallocate(len_reg, is_last_use=True)
        elif func_name == "STRUPR":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"STRUPR {target_reg}, {arg_reg}")
            self.smart_deallocate(arg_reg, is_last_use=True)
        elif func_name == "STRLWR":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"STRLWR {target_reg}, {arg_reg}")
            self.smart_deallocate(arg_reg, is_last_use=True)
        elif func_name == "STRREV":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"STRREV {target_reg}, {arg_reg}")
            self.smart_deallocate(arg_reg, is_last_use=True)
        elif func_name == "STRFIND":
            haystack_reg = self.generate_expression(expr.arguments[0], "R1")
            needle_reg = self.generate_expression(expr.arguments[1], "R2")
            self.output.append(f"STRFIND {target_reg}, {haystack_reg}, {needle_reg}")
            self.smart_deallocate(haystack_reg, is_last_use=True)
            self.smart_deallocate(needle_reg, is_last_use=True)
        elif func_name == "STRFINDI":
            haystack_reg = self.generate_expression(expr.arguments[0], "R1")
            needle_reg = self.generate_expression(expr.arguments[1], "R2")
            self.output.append(f"STRFINDI {target_reg}, {haystack_reg}, {needle_reg}")
            self.smart_deallocate(haystack_reg, is_last_use=True)
            self.smart_deallocate(needle_reg, is_last_use=True)
        elif func_name == "STREXT":
            dest_reg = self.generate_expression(expr.arguments[0], "R1")
            haystack_reg = self.generate_expression(expr.arguments[1], "R2")
            needle_reg = self.generate_expression(expr.arguments[2], "R3")
            len_reg = self.generate_expression(expr.arguments[3], "R4")
            self.output.append(f"STREXT {dest_reg}, {haystack_reg}, {needle_reg}, {len_reg}")
            self.output.append(f"MOV {target_reg}, {dest_reg}")  # Return destination
            self.smart_deallocate(dest_reg, is_last_use=True)
            self.smart_deallocate(haystack_reg, is_last_use=True)
            self.smart_deallocate(needle_reg, is_last_use=True)
            self.smart_deallocate(len_reg, is_last_use=True)
        elif func_name == "STREXTI":
            dest_reg = self.generate_expression(expr.arguments[0], "R1")
            haystack_reg = self.generate_expression(expr.arguments[1], "R2")
            needle_reg = self.generate_expression(expr.arguments[2], "R3")
            len_reg = self.generate_expression(expr.arguments[3], "R4")
            self.output.append(f"STREXTI {dest_reg}, {haystack_reg}, {needle_reg}, {len_reg}")
            self.output.append(f"MOV {target_reg}, {dest_reg}")  # Return destination
            self.smart_deallocate(dest_reg, is_last_use=True)
            self.smart_deallocate(haystack_reg, is_last_use=True)
            self.smart_deallocate(needle_reg, is_last_use=True)
            self.smart_deallocate(len_reg, is_last_use=True)
        elif func_name == "MIN":
            left_reg = self.generate_expression(expr.arguments[0], "R1")
            right_reg = self.generate_expression(expr.arguments[1], "R2")
            self.output.append(f"MIN {target_reg}, {left_reg}, {right_reg}")
            # Don't free if it's the target register (needed for nested calls)
            if left_reg != target_reg:
                self.smart_deallocate(left_reg, is_last_use=True)
            if right_reg != target_reg:
                self.smart_deallocate(right_reg, is_last_use=True)
        elif func_name == "MAX":
            left_reg = self.generate_expression(expr.arguments[0], "R1")
            right_reg = self.generate_expression(expr.arguments[1], "R2")
            self.output.append(f"MAX {target_reg}, {left_reg}, {right_reg}")
            # Don't free if it's the target register (needed for nested calls)
            if left_reg != target_reg:
                self.smart_deallocate(left_reg, is_last_use=True)
            if right_reg != target_reg:
                self.smart_deallocate(right_reg, is_last_use=True)
        elif func_name == "ATAN":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"ATAN {target_reg}, {arg_reg}")
            self.smart_deallocate(arg_reg, is_last_use=True)
        elif func_name == "ASIN":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"ASIN {target_reg}, {arg_reg}")
            self.smart_deallocate(arg_reg, is_last_use=True)
        elif func_name == "ACOS":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"ACOS {target_reg}, {arg_reg}")
            self.smart_deallocate(arg_reg, is_last_use=True)
        elif func_name == "DEG":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"DEG {target_reg}, {arg_reg}")
            self.smart_deallocate(arg_reg, is_last_use=True)
        elif func_name == "RAD":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"RAD {target_reg}, {arg_reg}")
            self.smart_deallocate(arg_reg, is_last_use=True)
        elif func_name == "FLOOR":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"FLOOR {target_reg}, {arg_reg}")
            self.smart_deallocate(arg_reg, is_last_use=True)
        elif func_name == "CEIL":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"CEIL {target_reg}, {arg_reg}")
            self.smart_deallocate(arg_reg, is_last_use=True)
        elif func_name == "ROUND":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"ROUND {target_reg}, {arg_reg}")
            self.smart_deallocate(arg_reg, is_last_use=True)
        elif func_name == "TRUNC":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"TRUNC {target_reg}, {arg_reg}")
            self.smart_deallocate(arg_reg, is_last_use=True)
        elif func_name == "FRAC":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"FRAC {target_reg}, {arg_reg}")
            self.smart_deallocate(arg_reg, is_last_use=True)
        elif func_name == "INTGR":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"INTGR {target_reg}, {arg_reg}")
            self.smart_deallocate(arg_reg, is_last_use=True)
        elif func_name == "POWR":
            left_reg = self.generate_expression(expr.arguments[0], "R1")
            right_reg = self.generate_expression(expr.arguments[1], "R2")
            self.output.append(f"POWR {target_reg}, {left_reg}, {right_reg}")
            self.smart_deallocate(left_reg, is_last_use=True)
            self.smart_deallocate(right_reg, is_last_use=True)
        elif func_name == "LOG":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"LOG {target_reg}, {arg_reg}")
            self.smart_deallocate(arg_reg, is_last_use=True)
        elif func_name == "EXP":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.output.append(f"EXP {target_reg}, {arg_reg}")
            self.smart_deallocate(arg_reg, is_last_use=True)
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
            # Sum all elements in the list
            list_expr = expr.arguments[0]
            if isinstance(list_expr, VariableExpr) and list_expr.name.upper().startswith('L'):
                try:
                    list_num = int(list_expr.name[1:])
                    base_addr = 0x1000 + (list_num - 1) * 0x100
                    size = 100
                    # Initialize sum
                    self.output.append(f"MOV {target_reg}, 0")
                    # Use R1 for index, R2 for value, P2 for address
                    index_reg = "R1"
                    value_reg = "R2"
                    addr_reg = "P2"
                    self.output.append(f"MOV {index_reg}, 0")
                    loop_label = self.new_label()
                    end_label = self.new_label()
                    self.output.append(f"{loop_label}:")
                    self.output.append(f"CMP {index_reg}, {size}")
                    self.output.append(f"JGE {end_label}")
                    # Calculate address
                    self.output.append(f"MOV {addr_reg}, {index_reg}")
                    self.output.append(f"SHL {addr_reg}, {addr_reg}, 1")
                    self.output.append(f"ADD {addr_reg}, {addr_reg}, {base_addr}")
                    # Load value
                    self.output.append(f"MOV P0, {addr_reg}")
                    self.output.append(f"MOV {value_reg}, [P0]")
                    # Add to sum
                    self.output.append(f"ADD {target_reg}, {target_reg}, {value_reg}")
                    # Increment index
                    self.output.append(f"INC {index_reg}")
                    self.output.append(f"JMP {loop_label}")
                    self.output.append(f"{end_label}:")
                except ValueError:
                    self.output.append(f"MOV {target_reg}, 0")
            else:
                self.output.append(f"MOV {target_reg}, 0")
        elif func_name == "MEAN":
            # Calculate average of list elements
            list_expr = expr.arguments[0]
            if isinstance(list_expr, VariableExpr) and list_expr.name.upper().startswith('L'):
                try:
                    list_num = int(list_expr.name[1:])
                    base_addr = 0x1000 + (list_num - 1) * 0x100
                    size = 100
                    # Initialize sum
                    self.output.append(f"MOV {target_reg}, 0")
                    # Use R1 for index, R2 for value, P2 for address
                    index_reg = "R1"
                    value_reg = "R2"
                    addr_reg = "P2"
                    self.output.append(f"MOV {index_reg}, 0")
                    loop_label = self.new_label()
                    end_label = self.new_label()
                    self.output.append(f"{loop_label}:")
                    self.output.append(f"CMP {index_reg}, {size}")
                    self.output.append(f"JGE {end_label}")
                    # Calculate address
                    self.output.append(f"MOV {addr_reg}, {index_reg}")
                    self.output.append(f"SHL {addr_reg}, {addr_reg}, 1")
                    self.output.append(f"ADD {addr_reg}, {addr_reg}, {base_addr}")
                    # Load value
                    self.output.append(f"MOV P0, {addr_reg}")
                    self.output.append(f"MOV {value_reg}, [P0]")
                    # Add to sum
                    self.output.append(f"ADD {target_reg}, {target_reg}, {value_reg}")
                    # Increment index
                    self.output.append(f"INC {index_reg}")
                    self.output.append(f"JMP {loop_label}")
                    self.output.append(f"{end_label}:")
                    # Divide by size
                    self.output.append(f"MOV R3, {size}")
                    self.output.append(f"DIV {target_reg}, {target_reg}, R3")
                except ValueError:
                    self.output.append(f"MOV {target_reg}, 0")
            else:
                self.output.append(f"MOV {target_reg}, 0")
        elif func_name == "DIM":
            # Return the size of the list (default 100 elements)
            list_expr = expr.arguments[0]
            if isinstance(list_expr, VariableExpr) and list_expr.name.upper().startswith('L'):
                try:
                    list_num = int(list_expr.name[1:])
                    size = 100  # Default size per list
                    self.output.append(f"MOV {target_reg}, {size}")
                except ValueError:
                    self.output.append(f"MOV {target_reg}, 0")
            else:
                self.output.append(f"MOV {target_reg}, 0")
        elif func_name == "GETKEY":
            self.output.append("KEYIN R0")
            self.output.append(f"MOV {target_reg}, R0")
        elif func_name == "PAUSE":
            # Wait for key press
            label = self.new_label()
            self.output.append(f"{label}:")
            self.output.append("KEYSTAT R0")
            self.output.append("CMP R0, 0")
            self.output.append(f"JZ {label}")  # Loop until key is available
            self.output.append("KEYIN R0")  # Consume the key

    def load_variable(self, name: str, target_reg: str = "R0") -> str:
        """Load a variable into a register. For string variables, ensure we use P registers."""
        # String variables need P registers (16-bit addresses)
        if name.upper().startswith("STR") and target_reg.startswith('R'):
            # Force use of a P register for string variables
            target_reg = 'P1'
            
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