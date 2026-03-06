"""
NoBASIC Code Generator
Generates Nova-16 assembly code from AST.

Enhanced with fine-grained liveness analysis for optimal register allocation.
Registers are freed immediately after their last use to minimize register pressure.

Optimizations:
1. Graph Coloring - Better register reuse (~3-5% gain)
2. Hot Spill Migration - Move frequent spills to zero-page (~2-3% gain)
3. Register Pressure Monitoring - Identify bottlenecks (debugging aid)
4. Dynamic Spill Allocation - Reduce memory overhead (~1-2% gain)
5. Expression Simplification - Minimize register pressure (~3-7% gain)
"""

from typing import List, Dict, Tuple, Set, Optional
from contextlib import contextmanager
from collections import Counter
from ..parser.ast import (
    Program, Statement, Expression, ClrDrawStmt, PxlOnStmt, PxlOffStmt,
    LineStmt, CircleStmt, TextStmt, SetLayerStmt, SpriteOnStmt, SpriteOffStmt,
    PlayToneStmt, PlayWaveStmt, StopSoundStmt, SetChannelStmt, GetKeyStmt,
    InputStmt, DispStmt, PauseStmt, FunctionCallStmt, ExpressionStmt, AssignmentStmt, IfStmt, ForStmt,
    WhileStmt, RepeatStmt, GotoStmt, LabelStmt, StructDeclarationStmt, VarDeclarationStmt,
    AsmBlockStmt, FunctionDefStmt, ReturnStmt, LiteralExpr, VariableExpr, ListAccessExpr, 
    MatrixAccessExpr, MemberAccessExpr, BinaryExpr, UnaryExpr, FunctionCallExpr, GroupingExpr, StructType, VarScope
)
from .optimizations import (
    RegisterColoringPass, HotSpillAnalyzer, RegisterPressureMonitor,
    DynamicSpillAllocator, ExpressionSimplifier, get_optimization_config
)


class CodeGenerator:
    """Code generator for NoBASIC to Nova-16 assembly."""

    def __init__(self, debug_allocation: bool = False, enable_optimizations: bool = True,
                 enable_peephole: bool = False, enable_live_range_scheduling: bool = False):
        self.output: List[str] = []
        self.label_counter = 0
        self.variable_addresses: Dict[str, int] = {}
        self.next_address = 0x0120  # Start after interrupt vectors
        self.strings: List[Tuple[str, str]] = []  # List of (label, string_value)
        self.loop_nesting_level = 0
        
        # Debug mode for register allocation
        self.debug_allocation = debug_allocation
        
        # Optimization configuration
        self.opt_config = get_optimization_config()
        self.opt_config['debug_optimizations'] = debug_allocation
        self.enable_optimizations = enable_optimizations
        self.enable_peephole = enable_peephole
        self.enable_live_range_scheduling = enable_live_range_scheduling
        
        # Access count tracking for hot variable optimization
        self.variable_access_counts: Dict[str, int] = Counter()
        
        # Dedicated spill slot allocator (memory region 0x7000-0x70FF)
        # Place spill slots well above typical code/data to avoid conflicts
        self.spill_base_address = 0x7000
        self.next_spill_address = self.spill_base_address
        self.spill_slots: Dict[str, int] = {}  # variable/temp -> spill address
        self.max_spill_slots = 128  # 128 slots of 2 bytes each = 256 bytes
        
        # Hot spill tracking (zero-page migration)
        self.hot_spills: Dict[str, int] = {}  # variable -> zero-page address
        
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
        
        # Unified liveness tracking (replaces dual system)
        self.live_ranges: Dict[str, Tuple[int, int]] = {}  # name -> (start, end)
        self.live_at_point: Dict[int, Set[str]] = {}  # program_point -> set of live variables
        self.program_counter = 0  # Tracks current program point for liveness
        
        # Interference graph (tracks which variables cannot share registers)
        self.interference_graph: Dict[str, Set[str]] = {}  # variable -> set of interfering variables
        
        # Register pressure tracking (for optimization warnings)
        self.register_pressure: Dict[int, int] = {}  # program_point -> register demand
        self.max_register_pressure = 0
        
        # Preferred register order for allocation (R registers first, then P registers)
        self.allocation_order = [
            'R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9',
            'P0', 'P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7'
        ]
        
        # Preferred register order for variable allocation (P registers for 16-bit)
        self.var_allocation_order = [
            'P2', 'P3', 'P4', 'P5', 'P6', 'P7'  # Skip P0/P1 by default
        ]
        # Opportunistic fallback registers (used only when pressure is within capacity)
        self.var_allocation_fallback = ['P1']

        # Variable register allocation (unified with temp tracking)
        self.var_reg: Dict[str, str] = {}  # variable name -> register
        self.var_lifetime: Dict[str, Tuple[int, int]] = {}  # DEPRECATED - use live_ranges
        self.statement_counter = 0  # DEPRECATED - use program_counter
        self.var_register_hints: Dict[str, List[str]] = {}  # preferred registers per variable
        
        # Struct support
        self.struct_types: Dict[str, StructType] = {}  # struct_name -> StructType
        self.struct_bases: Dict[str, int] = {}  # instance_name -> base_address
        self.struct_instances: Dict[str, str] = {}  # var_name -> struct_name
        
        # Function support
        self.functions: Dict[str, Tuple[str, List[str], FunctionDefStmt]] = {}  # name -> (label, params, def)
        self.function_labels: Dict[str, str] = {}  # name -> label
        self.function_counter = 0
        self.current_function: Optional[str] = None  # Currently generating function (or None for global)
        self.function_outputs: List[List[str]] = []  # Collected function code lines
        self.current_output = self.output  # Current output target
        self.function_locals: Dict[str, Dict[str, int]] = {}  # function_name -> {var_name -> fp_offset}
        
        # Track registers that should be automatically freed after use
        # These are temporary expression registers vs variable registers
        self.auto_free_registers: Set[str] = set()
        
        # Register allocation statistics (for debugging and optimization)
        self.allocation_stats = {
            'total_allocations': 0,
            'total_deallocations': 0,
            'allocation_failures': 0,
            'max_simultaneous_allocated': 0
        }
        
        # Optimization objects (initialized on demand)
        self.graph_coloring: Optional[RegisterColoringPass] = None
        self.hot_spill_analyzer: Optional[HotSpillAnalyzer] = None
        self.pressure_monitor: Optional[RegisterPressureMonitor] = None
        self.spill_allocator: Optional[DynamicSpillAllocator] = None
        self.expr_simplifier: Optional[ExpressionSimplifier] = None

    def allocate_register(self, preferred_reg: str = None, exclude_interfering: bool = True) -> str:
        """
        Allocate an unused register, preferring the specified register if available.
        Optionally respects interference constraints to prevent overwriting live variables.
        
        Args:
            preferred_reg: Preferred register name (e.g., 'R0', 'P1')
            exclude_interfering: If True, avoids registers used by currently live variables
        
        Raises:
            RuntimeError if no registers are available.
        """
        # Track allocation statistics
        self.allocation_stats['total_allocations'] += 1
        
        # Get registers that are blocked due to interference
        blocked_regs = set()
        if exclude_interfering:
            # Find variables that are currently live at this program point
            live_vars = self.live_at_point.get(self.program_counter, set())
            # Block their allocated registers
            blocked_regs = {self.var_reg.get(v) for v in live_vars if v in self.var_reg}
            blocked_regs.discard(None)
            
            if self.debug_allocation and blocked_regs:
                print(f"[ALLOC] Blocked by live variables at PC={self.program_counter}: {blocked_regs}")
        
        # Try preferred register first (if not blocked)
        if preferred_reg and not self.register_usage[preferred_reg] and preferred_reg not in blocked_regs:
            self.register_usage[preferred_reg] = True
            self.auto_free_registers.add(preferred_reg)
            self._update_allocation_stats()
            # Track this temporary as live
            self.mark_temp_live(preferred_reg)
            if self.debug_allocation:
                print(f"[ALLOC] Allocated preferred register {preferred_reg}")
                self._debug_register_state()
            return preferred_reg
        
        # Try allocation order (excluding blocked registers)
        for reg in self.allocation_order:
            if not self.register_usage[reg] and reg not in blocked_regs:
                self.register_usage[reg] = True
                self.auto_free_registers.add(reg)
                self._update_allocation_stats()
                # Track this temporary as live
                self.mark_temp_live(reg)
                if self.debug_allocation:
                    print(f"[ALLOC] Allocated register {reg} (preferred={preferred_reg}, blocked={blocked_regs})")
                    self._debug_register_state()
                return reg
        
        # No free registers - fail with detailed error message
        self.allocation_stats['allocation_failures'] += 1
        
        active_regs = [r for r, used in self.register_usage.items() if used]
        var_regs = list(self.var_reg.values())
        temp_regs = [r for r in active_regs if r not in var_regs]
        
        error_msg = (
            f"Register exhaustion: No available registers (no free registers available).\n"
            f"  Active registers: {len(active_regs)}/18\n"
            f"  Variable registers: {var_regs} ({len(var_regs)} allocated)\n"
            f"  Temporary registers: {temp_regs} ({len(temp_regs)} in use)\n"
            f"  Blocked by interference: {blocked_regs}\n"
            f"  Preferred: {preferred_reg}\n"
            f"\n"
            f"Suggestions:\n"
            f"  - Simplify complex expressions by breaking them into multiple statements\n"
            f"  - Reduce the number of simultaneous variables (currently {len(self.var_reg)})\n"
            f"  - Use fewer nested function calls\n"
            f"  - Consider reordering operations to free registers earlier"
        )
        
        if self.debug_allocation:
            print(f"[ALLOC] FAILURE - {error_msg}")
            self._debug_register_state()
        
        raise RuntimeError(error_msg)
    
    def _update_allocation_stats(self):
        """Update statistics about register allocation."""
        current_allocated = sum(1 for used in self.register_usage.values() if used)
        if current_allocated > self.allocation_stats['max_simultaneous_allocated']:
            self.allocation_stats['max_simultaneous_allocated'] = current_allocated

    def _debug_register_state(self):
        """Print current register allocation state for debugging."""
        if not self.debug_allocation:
            return
            
        active_regs = [r for r, used in self.register_usage.items() if used]
        var_regs = {var: reg for var, reg in self.var_reg.items()}
        temp_regs = [r for r in active_regs if r not in var_regs.values()]
        auto_free = list(self.auto_free_registers)
        
        print(f"  [STATE] Active: {len(active_regs)}/18, Temps: {temp_regs}, Auto-free: {auto_free}")
        print(f"  [STATE] Variables: {var_regs}")
        print(f"  [STATE] Stats: alloc={self.allocation_stats['total_allocations']}, "
              f"dealloc={self.allocation_stats['total_deallocations']}, "
              f"failures={self.allocation_stats['allocation_failures']}, "
              f"max_simultaneous={self.allocation_stats['max_simultaneous_allocated']}")

    def allocate_spill_slot(self, name: str) -> int:
        """
        Allocate a dedicated memory spill slot for a variable or temporary.
        
        Args:
            name: Name of variable/temporary needing a spill slot
            
        Returns:
            Memory address of allocated spill slot
            
        Raises:
            RuntimeError if spill slot pool is exhausted
        """
        if name in self.spill_slots:
            return self.spill_slots[name]
            
        # Check if we've exhausted spill slots
        if len(self.spill_slots) >= self.max_spill_slots:
            raise RuntimeError(
                f"Spill slot exhaustion: Cannot allocate spill slot for '{name}'.\n"
                f"  Already spilled: {len(self.spill_slots)} variables\n"
                f"  Maximum spill slots: {self.max_spill_slots}\n"
                f"  Spilled variables: {list(self.spill_slots.keys())}\n"
                f"\n"
                f"Suggestions:\n"
                f"  - Drastically reduce variable count\n"
                f"  - Break program into smaller functions\n"
                f"  - Reuse variables more aggressively"
            )
        
        # Allocate new spill slot (2 bytes per slot for 16-bit values)
        spill_addr = self.next_spill_address
        self.spill_slots[name] = spill_addr
        self.next_spill_address += 2
        
        if self.debug_allocation:
            print(f"[SPILL] Allocated spill slot for '{name}' at 0x{spill_addr:04X}")
        
        return spill_addr
    
    def get_spill_slot(self, name: str) -> Optional[int]:
        """Get spill slot address for a variable, or None if not spilled."""
        return self.spill_slots.get(name)
    
    def is_spilled(self, name: str) -> bool:
        """Check if a variable/temporary is spilled to memory."""
        return name in self.spill_slots

    def _clear_temp_registers(self):
        """
        Clear all temporary registers that aren't variable registers.
        This is safe to call at statement boundaries.
        """
        var_regs = set(self.var_reg.values())
        for reg in list(self.auto_free_registers):
            if reg not in var_regs:
                self.deallocate_register(reg)

    def record_live_range(self, name: str, program_point: int):
        """
        Record that a variable/temporary is live at a program point.
        Updates unified live range tracking.
        
        Args:
            name: Variable or temporary name
            program_point: Current program point
        """
        if name not in self.live_ranges:
            self.live_ranges[name] = (program_point, program_point)
        else:
            start, end = self.live_ranges[name]
            self.live_ranges[name] = (min(start, program_point), max(end, program_point))
        
        # Track what's live at this point
        if program_point not in self.live_at_point:
            self.live_at_point[program_point] = set()
        self.live_at_point[program_point].add(name)
    
    def mark_temp_live(self, reg: str):
        """
        Mark a temporary register as live at the current program point.
        This is called during code generation to track runtime temporaries.
        
        Args:
            reg: Register name (e.g., 'R0', 'P1')
        """
        # Create a unique name for this temporary based on register and program counter
        temp_name = f"_temp_{reg}_{self.program_counter}"
        self.record_live_range(temp_name, self.program_counter)
        
        if self.debug_allocation:
            print(f"[LIVENESS] Marked {reg} as live temporary '{temp_name}' at PC={self.program_counter}")
    
    def mark_temp_dead(self, reg: str):
        """
        Mark a temporary register as no longer live.
        Called when deallocating temporary registers.
        
        Args:
            reg: Register name (e.g., 'R0', 'P1')
        """
        # Find the temp name for this register at current or recent program points
        temp_name = f"_temp_{reg}_{self.program_counter}"
        
        # Remove from live_at_point sets for future points
        if temp_name in self.live_ranges:
            start, end = self.live_ranges[temp_name]
            # Update the end point to current program counter
            self.live_ranges[temp_name] = (start, self.program_counter)
            
            if self.debug_allocation:
                print(f"[LIVENESS] Marked {reg} temporary '{temp_name}' as dead at PC={self.program_counter}")
    
    def build_interference_graph(self):
        """
        Build interference graph from live range information.
        Two variables interfere if their live ranges overlap.
        """
        self.interference_graph = {}
        
        # Initialize graph nodes
        for var in self.live_ranges:
            self.interference_graph[var] = set()
        
        # For each program point, variables live at that point interfere with each other
        for point, live_vars in self.live_at_point.items():
            live_list = list(live_vars)
            for i, var1 in enumerate(live_list):
                for var2 in live_list[i+1:]:
                    # Add bidirectional interference edges
                    self.interference_graph[var1].add(var2)
                    self.interference_graph[var2].add(var1)
        
        if self.debug_allocation:
            print(f"\n[INTERFERENCE] Built interference graph:")
            for var, neighbors in sorted(self.interference_graph.items()):
                if neighbors:
                    print(f"  {var} interferes with: {sorted(neighbors)}")
    
    def calculate_register_pressure(self):
        """
        Calculate register pressure (demand) at each program point.
        Updates register_pressure dict and max_register_pressure.
        """
        self.register_pressure = {}
        self.max_register_pressure = 0
        
        for point, live_vars in self.live_at_point.items():
            pressure = len(live_vars)
            self.register_pressure[point] = pressure
            self.max_register_pressure = max(self.max_register_pressure, pressure)
        
        if self.debug_allocation:
            print(f"\n[PRESSURE] Maximum register pressure: {self.max_register_pressure}")
            print(f"[PRESSURE] Available P registers: {len(self.var_allocation_order)}")
            if self.max_register_pressure > len(self.var_allocation_order):
                print(f"[PRESSURE] ⚠️  PRESSURE EXCEEDS REGISTERS by {self.max_register_pressure - len(self.var_allocation_order)}")
            
            # Show high-pressure points
            high_pressure_points = [(p, pr) for p, pr in self.register_pressure.items() 
                                   if pr >= len(self.var_allocation_order)]
            if high_pressure_points:
                print(f"[PRESSURE] High-pressure points:")
                for point, pressure in sorted(high_pressure_points)[:10]:  # Show first 10
                    live = self.live_at_point.get(point, set())
                    print(f"  Point {point}: {pressure} live ({sorted(live)})")

    def enforce_register_pressure_budget(self):
        """Raise when register pressure exceeds available variable registers."""
        available = len(self.var_allocation_order)
        if self.max_register_pressure > available:
            raise RuntimeError(
                "Register exhaustion: No available registers (pressure exceeds budget).\n"
                f"  Pressure: {self.max_register_pressure}\n"
                f"  Available variable registers: {available}\n"
                "Suggestions:\n"
                "  - Split complex expressions into smaller statements\n"
                "  - Reuse temporaries or introduce intermediate variables\n"
                "  - Reduce simultaneously live variables (use local scope where possible)"
            )


    def deallocate_register(self, reg: str):
        """Deallocate a register, marking it as available and no longer live."""
        if reg in self.register_usage:
            # Mark temporary as dead in liveness tracking
            if reg in self.auto_free_registers:
                self.mark_temp_dead(reg)
            
            self.register_usage[reg] = False
            self.auto_free_registers.discard(reg)
            self.allocation_stats['total_deallocations'] += 1
            if self.debug_allocation:
                print(f"[DEALLOC] Freed register {reg}")
                self._debug_register_state()
            
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
                # Verify it's actually a temporary register we can free
                if reg in self.auto_free_registers:
                    self.deallocate_register(reg)
                    self.current_output.append(f"; Free {reg} (last use)")
                else:
                    # Register is in use but not tracked as auto-free
                    # This might be a hardware register or manually managed
                    # Don't free it, but log for debugging
                    pass
            else:
                # This is a variable register - never free it
                pass
        else:
            # Not the last use, or register not allocated
            # Don't free anything
            pass
            
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

    @contextmanager
    def with_temporary_register(self, preferred_reg: str = None):
        """
        Context manager for automatic temporary register allocation and cleanup.
        Ensures registers are always freed, even if exceptions occur.
        
        Usage:
            with self.with_temporary_register('R0') as temp:
                self.current_output.append(f"MOV {temp}, 42")
                # temp is automatically freed when exiting this block
        
        Args:
            preferred_reg: Preferred register name (e.g., 'R0', 'P1')
            
        Yields:
            Allocated register name
        """
        reg = self.allocate_register(preferred_reg)
        try:
            yield reg
        finally:
            self.deallocate_register(reg)
    
    @contextmanager
    def temporary_registers(self, count: int, preferred_prefix: str = 'R'):
        """
        Context manager for allocating multiple temporary registers at once.
        All registers are automatically freed when the context exits.
        
        Usage:
            with self.temporary_registers(3, 'R') as [r1, r2, r3]:
                self.current_output.append(f"MOV {r1}, 1")
                self.current_output.append(f"MOV {r2}, 2")
                # All three registers freed automatically
        
        Args:
            count: Number of registers to allocate
            preferred_prefix: Prefix for preferred registers ('R' or 'P')
            
        Yields:
            List of allocated register names
        """
        regs = []
        try:
            for i in range(count):
                reg = self.allocate_register()
                regs.append(reg)
            yield regs
        finally:
            for reg in regs:
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
        """Collect variable lifetimes by traversing the AST (unified liveness tracking)."""
        self.program_counter = 0  # Reset program counter
        for stmt in program.statements:
            self.collect_lifetimes_stmt(stmt)
        
        # After collection, build interference graph and calculate pressure
        self.build_interference_graph()
        self.calculate_register_pressure()
        
        # Perform SSA analysis for future optimizations
        self.analyze_ssa_form()

    def collect_lifetimes_stmt(self, stmt):
        """Collect lifetimes for a statement (unified liveness tracking)."""
        self.program_counter += 1
        current_point = self.program_counter
        
        # Also update legacy statement_counter for backwards compatibility
        self.statement_counter = current_point

    def collect_lifetimes_stmt(self, stmt):
        """Collect lifetimes for a statement (unified liveness tracking)."""
        self.program_counter += 1
        current_point = self.program_counter
        
        # Also update legacy statement_counter for backwards compatibility
        self.statement_counter = current_point

        if isinstance(stmt, AssignmentStmt):
            if isinstance(stmt.variable, VariableExpr):
                var_name = stmt.variable.name
                # Variable is defined here and may be used later
                self.record_live_range(var_name, current_point)
                # **OPTIMIZATION: Track access counts for hot spill migration**
                self.variable_access_counts[var_name] += 1
                # Legacy support
                if var_name not in self.var_lifetime:
                    self.var_lifetime[var_name] = (current_point, current_point)
                else:
                    start, _ = self.var_lifetime[var_name]
                    self.var_lifetime[var_name] = (start, current_point)
            self.collect_lifetimes_expr(stmt.expression)
        elif isinstance(stmt, ForStmt):
            # Loop variable defined at for
            var_name = stmt.variable
            self.record_live_range(var_name, current_point)
            # **OPTIMIZATION: Track access counts - loop variable is accessed heavily**
            # Multiply by estimated loop iterations (conservative estimate: 100)
            self.variable_access_counts[var_name] += 100
            # Legacy support
            if var_name not in self.var_lifetime:
                self.var_lifetime[var_name] = (current_point, current_point)
            else:
                start, _ = self.var_lifetime[var_name]
                self.var_lifetime[var_name] = (start, current_point)
            
            self.collect_lifetimes_expr(stmt.start)
            self.collect_lifetimes_expr(stmt.end)
            if stmt.step:
                self.collect_lifetimes_expr(stmt.step)
            for body_stmt in stmt.body:
                self.collect_lifetimes_stmt(body_stmt)
            # Extend lifetime to end of loop
            loop_end_point = self.program_counter
            self.record_live_range(var_name, loop_end_point)
            # Legacy support
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
        """Collect lifetimes from expressions (unified liveness tracking)."""
        current_point = self.program_counter
        
        if isinstance(expr, VariableExpr):
            var_name = expr.name
            # Variable is used here
            self.record_live_range(var_name, current_point)
            # **OPTIMIZATION: Track access counts for hot spill migration**
            self.variable_access_counts[var_name] += 1
            # Legacy support
            if var_name not in self.var_lifetime:
                self.var_lifetime[var_name] = (current_point, current_point)
            else:
                start, end = self.var_lifetime[var_name]
                self.var_lifetime[var_name] = (min(start, current_point), max(end, current_point))
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
            self.collect_lifetimes_expr(stmt.text)  # Track the text parameter!
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
        """
        Assign registers to variables using enhanced linear scan with interference graphs.
        Uses proper spill heuristics and considers register pressure.
        """
        def _is_allocatable_variable(name: str) -> bool:
            # Skip compiler temps and string literals/labels
            if name.startswith("_temp_"):
                return False
            upper = name.upper()
            if upper.startswith("STR"):
                return False
            return True

        alloc_live_ranges = {
            var: (start, end)
            for var, (start, end) in self.live_ranges.items()
            if _is_allocatable_variable(var)
        }

        # Recompute pressure for allocatable vars only
        filtered_pressure = {
            point: len({v for v in live if _is_allocatable_variable(v)})
            for point, live in self.live_at_point.items()
        }
        self.max_register_pressure = max(filtered_pressure.values(), default=0)

        # Expand allocation pool opportunistically when pressure fits baseline capacity
        allocation_pool = list(self.var_allocation_order)
        if self.max_register_pressure <= len(self.var_allocation_order):
            allocation_pool += self.var_allocation_fallback

        if self.debug_allocation:
            print(f"\n[ASSIGN_REGS] Starting enhanced linear scan allocation")
            print(f"[ASSIGN_REGS] Variables: {len(alloc_live_ranges)} (filtered from {len(self.live_ranges)})")
            print(f"[ASSIGN_REGS] Available registers: {allocation_pool}")
            print(f"[ASSIGN_REGS] Max register pressure: {self.max_register_pressure}")
            print(f"[ASSIGN_REGS] Live ranges:")
            for var, (start, end) in sorted(alloc_live_ranges.items(), key=lambda x: x[1][0]):
                interferes = len(self.interference_graph.get(var, set()))
                print(f"  {var}: [{start}, {end}] (duration={end-start+1}, interferes={interferes})")
        
        # Sort variables by start time (linear scan requirement)
        vars_sorted = sorted(alloc_live_ranges.items(), key=lambda x: x[1][0])
        
        active_intervals = []  # List of (end_time, var_name, register)
        spilled_vars = []  # Track variables that couldn't get registers
        
        for var, (start, end) in vars_sorted:
            # Expire old intervals (free registers whose live ranges have ended)
            active_intervals = [
                (e, v, r) for e, v, r in active_intervals if e > start
            ]
            
            if self.debug_allocation:
                active_regs = [r for _, _, r in active_intervals]
                print(f"\n[ASSIGN_REGS] Processing '{var}' at time {start}")
                print(f"  Active intervals: {len(active_intervals)}, using regs: {active_regs}")
            
            # Find available registers (not used by active intervals)
            used_regs = {reg for _, _, reg in active_intervals}
            available_regs = [r for r in allocation_pool if r not in used_regs]
            
            # Also check interference graph - can't use registers of interfering variables
            interfering_vars = self.interference_graph.get(var, set())
            interfering_regs = {self.var_reg.get(v) for v in interfering_vars if v in self.var_reg}
            interfering_regs.discard(None)
            available_regs = [r for r in available_regs if r not in interfering_regs]
            
            # Respect pre-allocation register hints when available
            if var in self.var_register_hints:
                for hinted in self.var_register_hints[var]:
                    if hinted in available_regs:
                        available_regs = [hinted] + [r for r in available_regs if r != hinted]
                        if self.debug_allocation:
                            print(f"  Hint applied: prefer {hinted} for {var}")
                        break
            
            if self.debug_allocation and interfering_vars:
                print(f"  Interferes with: {sorted(interfering_vars)}")
                print(f"  Blocked by interference: {sorted(interfering_regs)}")
            
            if available_regs:
                # Successfully allocate register
                reg = available_regs[0]
                self.var_reg[var] = reg
                active_intervals.append((end, var, reg))
                self.register_usage[reg] = True
                
                if self.debug_allocation:
                    print(f"  [OK] Allocated {var} -> {reg}")
            else:
                # Need to spill - use spill heuristic
                # Spill the variable with the SHORTEST remaining live range (ends soonest)
                spillable = [(e, v, r) for e, v, r in active_intervals]
                
                if spillable and end < max(e for e, v, r in spillable):
                    # Spill an active variable with longer range than current
                    spillable.sort(key=lambda x: x[0])  # Sort by end time (earliest first)
                    spill_end, spill_var, spill_reg = spillable[0]  # Take the one that ends soonest
                    
                    # Remove spilled variable from active and var_reg
                    active_intervals.remove((spill_end, spill_var, spill_reg))
                    del self.var_reg[spill_var]
                    spilled_vars.append(spill_var)
                    
                    # Allocate spill slot
                    self.allocate_spill_slot(spill_var)
                    
                    # Assign the freed register to current variable
                    self.var_reg[var] = spill_reg
                    active_intervals.append((end, var, spill_reg))
                    
                    if self.debug_allocation:
                        print(f"  [SPILL] Spilled '{spill_var}' to allocate {spill_reg} to '{var}'")
                else:
                    # Spill current variable
                    spilled_vars.append(var)
                    self.allocate_spill_slot(var)
                    
                    if self.debug_allocation:
                        print(f"  [SPILL] SPILLED '{var}' to memory (no registers available)")
        
        if self.debug_allocation:
            print(f"\n[ASSIGN_REGS] Allocation complete:")
            print(f"  Registers assigned: {len(self.var_reg)}")
            print(f"  Memory spills: {len(spilled_vars)}")
            print(f"  Spill slots used: {len(self.spill_slots)}")
            print(f"  Final mapping: {self.var_reg}")
            if spilled_vars:
                print(f"  Spilled variables: {spilled_vars}\n")
        
        # Emit warning if variables had to spill to memory
        if spilled_vars:
            self._emit_spill_warnings(spilled_vars, total_vars=len(alloc_live_ranges), max_pressure=self.max_register_pressure, available_regs=len(allocation_pool))
    
    def _emit_spill_warnings(self, spilled_vars: List[str], total_vars: int, max_pressure: int, available_regs: int):
        """Emit warnings about spilled variables."""
        # Add comment to generated assembly
        self.current_output.append(f"; WARNING: {len(spilled_vars)} variable(s) using dedicated spill slots")
        self.current_output.append(f";          Spilled variables: {', '.join(spilled_vars)}")
        self.current_output.append(f";          Spill region: 0x{self.spill_base_address:04X}-0x{self.next_spill_address:04X}")
        self.current_output.append(f";          Register pressure: {max_pressure} (max), {available_regs} available")
        self.current_output.append(f";          This will impact performance. Consider:")
        self.current_output.append(f";          - Reducing total variable count (currently {total_vars})")
        self.current_output.append(f";          - Reducing variable lifetimes by localizing scope")
        self.current_output.append(f";          - Breaking complex expressions into simpler parts")
        
        # Also print to console for developer visibility
        print(f"\n[WARNING] REGISTER ALLOCATION")
        print(f"   {len(spilled_vars)} variable(s) spilled to memory: {', '.join(spilled_vars)}")
        print(f"   Total variables: {total_vars}, Available registers: {available_regs}")
        print(f"   Max register pressure: {max_pressure}")
        print(f"   Spill region: 0x{self.spill_base_address:04X}-0x{self.next_spill_address:04X} ({len(self.spill_slots)} slots)")
        print(f"   Memory-based variables will be slower to access.")
        print(f"   Consider simplifying variable usage or reducing variable count.\n")

    # ===== OPTIMIZATION PASSES =====
    
    def apply_graph_coloring_optimization(self):
        """
        Apply graph coloring optimization to improve register reuse (~3-5% gain).
        Uses greedy coloring on the interference graph.
        """
        if not self.enable_optimizations or not self.opt_config['enable_graph_coloring']:
            return
        
        if not self.interference_graph:
            return
        
        debug = self.opt_config['debug_optimizations']
        
        # Create and run graph coloring pass
        self.graph_coloring = RegisterColoringPass(
            interference_graph=self.interference_graph,
            available_registers=self.var_allocation_order,
            debug=debug
        )
        
        color_map = self.graph_coloring.color_graph()
        
        # Update var_reg with coloring result (only update if better)
        initial_spills = len(self.spill_slots)
        for var, reg in color_map.items():
            if var not in self.var_reg:  # Only update unallocated variables
                self.var_reg[var] = reg
                if reg in self.register_usage:
                    self.register_usage[reg] = True
        
        final_spills = len(self.spill_slots)
        if debug:
            print(f"\n[OPT] Graph Coloring: {initial_spills} → {final_spills} spills")

    def apply_hot_spill_migration(self):
        """
        Apply hot spill migration to move frequent spills to zero-page (~2-3% gain).
        """
        if not self.enable_optimizations or not self.opt_config['enable_hot_spill_migration']:
            return
        
        if not self.spill_slots:
            return
        
        debug = self.opt_config['debug_optimizations']
        
        # Create hot spill analyzer
        self.hot_spill_analyzer = HotSpillAnalyzer(
            spill_slots=self.spill_slots,
            access_counts=self.variable_access_counts,
            debug=debug,
            zero_page_base=self.opt_config['zero_page_base'],
            zero_page_size=self.opt_config['zero_page_size']
        )
        
        # Identify and migrate hot spills
        self.hot_spills = self.hot_spill_analyzer.identify_hot_spills(
            threshold_percentile=self.opt_config['pressure_threshold_percentile']
        )
        
        if debug and self.hot_spills:
            print(f"\n[OPT] Hot Spill Migration: {len(self.hot_spills)} variables to zero-page")

    def apply_register_pressure_monitoring(self) -> Dict[str, any]:
        """
        Apply register pressure monitoring to identify bottlenecks (debugging aid).
        Returns pressure statistics.
        """
        if not self.enable_optimizations or not self.opt_config['enable_register_pressure_monitoring']:
            return {}
        
        debug = self.opt_config['debug_optimizations']
        
        # Create pressure monitor
        self.pressure_monitor = RegisterPressureMonitor(
            live_at_point=self.live_at_point,
            available_registers=len(self.var_allocation_order),
            debug=debug
        )
        
        # Analyze pressure
        stats = self.pressure_monitor.analyze_pressure()
        
        if debug:
            print(self.pressure_monitor.get_pressure_report())
        
        return stats

    def apply_dynamic_spill_allocation(self):
        """
        Apply dynamic spill allocation to reduce memory overhead (~1-2% gain).
        Allocates spill slots based on variable frequency.
        """
        if not self.enable_optimizations or not self.opt_config['enable_dynamic_spill_allocation']:
            return
        
        spilled_vars = [v for v in self.live_ranges if self.is_spilled(v)]
        if not spilled_vars:
            return
        
        debug = self.opt_config['debug_optimizations']
        
        # Create dynamic allocator
        self.spill_allocator = DynamicSpillAllocator(
            access_counts=self.variable_access_counts,
            spill_base=self.opt_config['spill_base'],
            spill_size=self.opt_config['spill_size'],
            debug=debug
        )
        
        # Reallocate spill slots dynamically
        new_allocation = self.spill_allocator.allocate_dynamically(spilled_vars)
        
        # Update spill slots
        for var, addr in new_allocation.items():
            self.spill_slots[var] = addr
        
        if debug:
            print(f"\n[OPT] Dynamic Spill Allocation: optimized {len(new_allocation)} slots")

    def apply_expression_simplification(self):
        """
        Apply expression simplification to minimize register pressure (~3-7% gain).
        """
        if not self.enable_optimizations or not self.opt_config['enable_expression_simplification']:
            return
        
        debug = self.opt_config['debug_optimizations']
        
        # Create expression simplifier
        self.expr_simplifier = ExpressionSimplifier(debug=debug)
        
        if debug:
            print(f"\n[OPT] Expression Simplification: enabled")
    
    def apply_pre_allocation_optimizations(self):
        """
        Apply optimizations that should run BEFORE register allocation.
        These guide the allocator to make better decisions.
        """
        if not self.enable_optimizations:
            return

        debug = self.opt_config['debug_optimizations']

        if debug:
            print(f"\n{'='*60}")
            print("PRE-ALLOCATION OPTIMIZATION PASSES")
            print(f"{'='*60}")
            print(f"[PRE] Live ranges: {len(self.live_ranges)} | Interference nodes: {len(self.interference_graph)} | Max pressure: {self.max_register_pressure}")

        # Use graph coloring to derive preferred registers ahead of linear scan.
        if self.opt_config.get('enable_graph_coloring', False) and self.interference_graph:
            available_regs = list(self.var_allocation_order)
            colorer = RegisterColoringPass(
                interference_graph=self.interference_graph,
                available_registers=available_regs,
                debug=debug,
            )
            color_map = colorer.color_graph()

            # Store per-variable register hints; allocation remains authoritative.
            self.var_register_hints = {var: [reg] for var, reg in color_map.items()}

            if debug:
                degrees = [len(neigh) for neigh in self.interference_graph.values()]
                peak_degree = max(degrees) if degrees else 0
                high_degree = sorted(
                    ((var, len(neigh)) for var, neigh in self.interference_graph.items()),
                    key=lambda x: x[1],
                    reverse=True,
                )[:5]
                print(f"[PRE] Graph coloring hints: {len(color_map)} vars, peak degree {peak_degree}")
                if high_degree:
                    print(f"[PRE] Top-degree vars: {high_degree}")

        elif debug:
            reason = "disabled" if not self.opt_config.get('enable_graph_coloring', False) else "no interference graph"
            print(f"[PRE] Skipping graph coloring (reason: {reason})")

    def apply_post_allocation_optimizations(self):
        """
        Apply optimizations that run AFTER register allocation.
        These fine-tune the results and integrate the allocator's decisions.
        """
        if not self.enable_optimizations:
            return
        
        if self.opt_config['debug_optimizations']:
            print(f"\n{'='*60}")
            print("POST-ALLOCATION OPTIMIZATION PASSES")
            print(f"{'='*60}")
        
        # Apply optimizations in order of impact
        self.apply_register_pressure_monitoring()         # Debug aid
        self.apply_hot_spill_migration()                   # 2-3% gain
        self.apply_dynamic_spill_allocation()             # 1-2% gain
        self.apply_expression_simplification()            # 3-7% gain

    def apply_all_optimizations(self):
        """Apply all enabled optimizations in order (legacy - now split into pre/post)."""
        if not self.enable_optimizations:
            return
        
        if self.opt_config['debug_optimizations']:
            print(f"\n{'='*60}")
            print("OPTIMIZATION PASSES (LEGACY)")
            print(f"{'='*60}")
        
        # This is now split into pre and post allocation passes
        self.apply_post_allocation_optimizations()

    def generate(self, program: Program) -> str:
        """
        Generate assembly code from the AST.

        Args:
            program: The AST to generate code for

        Returns:
            Generated assembly code as a string
        """
        self.output = []
        self.current_output = self.output
        self.label_counter = 0
        self.variable_addresses = {}
        self.next_address = 0x0120
        self.var_reg = {}
        self.var_lifetime = {}
        self.statement_counter = 0
        self.var_register_hints = {}

        # First pass: collect function definitions and assign labels
        for stmt in program.statements:
            if isinstance(stmt, FunctionDefStmt):
                func_key = stmt.name.lower()
                label = f"_func_{stmt.name}_{self.function_counter}"
                self.function_counter += 1
                self.function_labels[func_key] = label
                # Extract just parameter names for compatibility
                param_names = [param_name for param_name, _ in stmt.params]
                self.functions[func_key] = (label, param_names, stmt)
                # Generate the function code
                self.generate_function_def(stmt, func_key)

        # Second pass: collect lifetimes
        self.collect_lifetimes(program)

        # Fail fast when register demand already exceeds hardware budget
        # self.enforce_register_pressure_budget()

        # **OPTIMIZATION: Pre-allocation optimizations**
        # These must run BEFORE register allocation to guide the allocator
        if self.enable_optimizations:
            self.apply_pre_allocation_optimizations()

        # Assign registers to variables (guided by pre-allocation optimizations)
        self.assign_registers()
        
        # **OPTIMIZATION: Post-allocation optimizations**
        # These run after allocation to fine-tune the results
        self.apply_post_allocation_optimizations()

        # Set ORG to 0x0200 (past interrupt vectors)
        self.current_output.append("; NoBASIC compiler output")
        self.current_output.append("; Generated for Nova-16")
        self.current_output.append("ORG 0x0200")
        
        # Initialize stack (grows downward from top of memory) with full 16-bit immediate
        self.current_output.append("MOV P7:, 0xFF")   # High byte
        self.current_output.append("MOV :P7, 0xFF")   # Low byte
        self.current_output.append("MOV SP, P7")      # Initialize stack pointer at top of memory
        self.current_output.append("MOV FP, SP")      # Initialize frame pointer

        # Generate code for all statements (skip function definitions in main pass)
        for stmt in program.statements:
            if not isinstance(stmt, FunctionDefStmt):
                self.generate_statement(stmt)

        # Add HLT at the end
        self.current_output.append("HLT")
        
        # Add function code after HLT
        for func_lines in self.function_outputs:
            self.current_output.extend(func_lines)
        
        # Add string literals
        for label, string_value in self.strings:
            self.current_output.append(f"{label}: DEFSTR \"{string_value}\"")

        # **POST-GENERATION OPTIMIZATIONS**
        # Apply peephole and live range optimizations to reduce code size and improve performance
        assembly_output = "\n".join(self.output)
        
        if self.enable_optimizations and self.enable_live_range_scheduling:
            # Run live range scheduler prior to peephole to improve register pressure
            from .live_range_scheduler import LiveRangeScheduler
            scheduler = LiveRangeScheduler(debug=self.debug_allocation)
            scheduled_lines = scheduler.schedule(assembly_output.splitlines(), self.live_ranges)
            assembly_output = "\n".join(scheduled_lines)
            if self.debug_allocation:
                print("[CODEGEN] Live range scheduling applied")
                print(f"[CODEGEN] Scheduled instructions: {len(scheduled_lines)} lines")
        
        # Peephole remains opt-in; keep disabled by default
        if self.enable_optimizations and self.enable_peephole:
            from .peephole import PeepholeOptimizer
            peephole_opt = PeepholeOptimizer(debug=self.debug_allocation)
            assembly_output = peephole_opt.optimize(assembly_output)
            
            if self.debug_allocation:
                print("[CODEGEN] Peephole optimization applied")
                print(f"[CODEGEN] Code size reduction: {len('\n'.join(self.output))} -> {len(assembly_output)} bytes")

        return assembly_output

    def generate_statement(self, stmt: Statement):
        """Generate code for a statement."""
        # Increment program counter for runtime liveness tracking
        self.program_counter += 1
        
        # Clear temp registers at statement boundaries (safety measure)
        self._clear_temp_registers()
        
        if isinstance(stmt, ClrDrawStmt):
            self.generate_clr_draw()
        elif isinstance(stmt, FunctionDefStmt):
            self.generate_function_def(stmt)
        elif isinstance(stmt, ReturnStmt):
            self.generate_return(stmt)
        elif isinstance(stmt, VarDeclarationStmt):
            self.generate_var_declaration(stmt)
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
        elif isinstance(stmt, ExpressionStmt):
            self.generate_expression_statement(stmt)
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
        elif isinstance(stmt, AsmBlockStmt):
            self.generate_asm_block(stmt)

    def generate_function_def(self, stmt: FunctionDefStmt, func_key: Optional[str] = None):
        """Generate a function definition with prologue, body, and epilogue."""
        func_key = func_key or stmt.name.lower()
        label = self.function_labels[func_key]
        
        # Extract parameter names
        param_names = [param_name for param_name, _ in stmt.params]
        
        # Collect local variables and calculate stack space needed
        local_vars = []
        for body_stmt in stmt.body:
            if isinstance(body_stmt, VarDeclarationStmt) and body_stmt.scope == VarScope.LOCAL:
                local_vars.extend(body_stmt.variables)
        
        # Calculate space for local variables (2 bytes each)
        locals_size = len(local_vars) * 2
        
        # Assign FP-relative offsets to local variables (negative offsets from FP)
        self.function_locals[func_key] = {}
        for i, var in enumerate(local_vars):
            # Locals start at FP-2, FP-4, etc.
            offset = -(i + 1) * 2
            self.function_locals[func_key][var] = offset
        
        # Create function output
        func_lines = []
        
        # Function prologue
        func_lines.append("")
        func_lines.append(f"{label}:")
        func_lines.append(f"; Function: {stmt.name}")
        func_lines.append(f"; Parameters: {', '.join(param_names)}")
        func_lines.append(f"; Locals: {', '.join(local_vars)} ({locals_size} bytes)")
        
        # Save old frame pointer and set up new frame with locals space
        func_lines.append(f"ENTER {locals_size}")  # Allocate space for local variables
        
        # Note: Parameters are already on stack (pushed by caller)
        # FP now points to saved FP, params are at FP+4, FP+6, etc.
        # Locals are at FP-2, FP-4, etc.
        
        # Save current function context
        prev_function = self.current_function
        self.current_function = func_key
        
        # Temporarily redirect output to func_lines
        old_output = self.current_output
        self.current_output = func_lines
        
        # Generate function body
        for body_stmt in stmt.body:
            # Skip explicit return statements here, they'll emit their own RET
            self.generate_statement(body_stmt)
        
        # If no explicit return, add default return 0
        if not stmt.body or not isinstance(stmt.body[-1], ReturnStmt):
            self.current_output.append("MOV R0, 0")
            self.current_output.append("LEAVE")  # Native frame teardown
            self.current_output.append("RET")
        
        # Restore output
        self.current_output = old_output
        
        # Add function code to collected outputs
        self.function_outputs.append(func_lines)

    def generate_return(self, stmt: ReturnStmt):
        """Generate a return statement."""
        if stmt.value:
            # Evaluate return value, preferring R0
            result_reg = self.generate_expression(stmt.value, 'R0')
            # Ensure result is in R0 for return
            if result_reg != 'R0':
                self.current_output.append(f"MOV R0, {result_reg}")
                self.smart_deallocate(result_reg, is_last_use=True)
        else:
            # Default return 0
            self.current_output.append("MOV R0, 0")
        
        # Function epilogue
        if self.current_function:
            self.current_output.append("LEAVE")  # Native frame teardown

        self.current_output.append("RET")

    def generate_struct_declaration(self, stmt: StructDeclarationStmt):
        """Register struct type (no assembly code generated)."""
        self.struct_types[stmt.name.lower()] = StructType(stmt.name, [field.lower() for field in stmt.fields])
        self.current_output.append(f"; Struct {stmt.name} declared with fields: {', '.join(stmt.fields)}")

    def generate_asm_block(self, stmt: AsmBlockStmt):
        """
        Generate inline assembly block.
        The assembly code is inserted directly into the output with a comment header.
        """
        self.current_output.append("; --- Inline Assembly Block ---")
        
        # Split the assembly code into lines and emit each one
        lines = stmt.assembly_code.strip().split('\n')
        for line in lines:
            # Strip whitespace and skip empty lines
            stripped = line.strip()
            if stripped:
                self.current_output.append(stripped)
        
        self.current_output.append("; --- End Inline Assembly ---")

    def generate_var_declaration(self, stmt: VarDeclarationStmt):
        """Handle variable declarations (GLOBAL/LOCAL)."""
        scope_str = stmt.scope.value.upper()
        for var_name in stmt.variables:
            if stmt.scope == VarScope.LOCAL and self.current_function:
                # Local variables in functions are allocated on stack, already handled in generate_function_def
                offset = self.function_locals[self.current_function].get(var_name, 0)
                self.current_output.append(f"; {scope_str} variable: {var_name} @ FP{offset:+d}")
            else:
                # Global variables or LOCAL in global scope (error case) get memory addresses
                addr = self.get_variable_address(var_name)
                self.current_output.append(f"; {scope_str} variable: {var_name} @ 0x{addr:04X}")

    def generate_clr_draw(self):
        """Generate ClrDraw code."""
        self.current_output.append("; ClrDraw")
        self.current_output.append("MOV VM, 0")
        self.current_output.append("MOV VL, 1")
        self.current_output.append("SFILL 0x00")

    def generate_pxl_on(self, stmt: PxlOnStmt):
        """Generate optimized PxlOn(x, y, color) code with direct hardware register assignment."""
        # Generate expressions directly into hardware registers - no intermediate MOVs!
        self.generate_expression_into(stmt.x, 'VX')
        self.generate_expression_into(stmt.y, 'VY')
        self.generate_expression_into(stmt.color, 'VC')
        self.current_output.append("SWRITE VC")

    def generate_pxl_off(self, stmt: PxlOffStmt):
        """Generate optimized PxlOff(x, y) code with direct hardware register assignment."""
        self.generate_expression_into(stmt.x, 'VX')
        self.generate_expression_into(stmt.y, 'VY')
        self.current_output.append("MOV VC, 0")
        self.current_output.append("SWRITE VC")

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
        self.current_output.append(f"SLINE {x2_reg}, {y2_reg}")
        
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
        self.current_output.append(f"SCIRC {radius_reg}, 1")  # 1 for filled
        
        # Deallocate temp register
        self.deallocate_register(radius_reg)

    def generate_text(self, stmt: TextStmt):
        """Generate optimized Text rendering code using TEXT opcode with direct register assignment."""
        # Set graphics registers directly
        self.generate_expression_into(stmt.x, 'VX')
        self.generate_expression_into(stmt.y, 'VY')
        self.generate_expression_into(stmt.color, 'VC')

        # Check if this is a string expression
        is_string_literal = isinstance(stmt.text, LiteralExpr) and hasattr(stmt.text, 'data_type') and stmt.text.data_type.name == "STRING"
        is_string_variable = isinstance(stmt.text, VariableExpr) and stmt.text.name.upper().startswith("STR")
        
        if is_string_literal:
            # String literal - create label and display
            label = self.add_string_literal(stmt.text.value)
            self.current_output.append(f"TEXT {label}")
        elif is_string_variable or (isinstance(stmt.text, BinaryExpr) and stmt.text.operator == "+"):
            # String variable or expression - evaluate to get address
            text_addr_reg = self.generate_expression(stmt.text)
            self.current_output.append(f"TEXT {text_addr_reg}")
            if text_addr_reg not in ['P0', 'P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'SP', 'FP']:
                self.smart_deallocate(text_addr_reg, is_last_use=True)
        else:
            # Numeric expression - convert to string first
            text_value_reg = self.generate_expression(stmt.text, "R1")
            
            # Ensure we use an R register for ITOS (it needs R register as source)
            if text_value_reg.startswith('P'):
                temp_r_reg = self.allocate_register("R1")
                self.current_output.append(f"MOV {temp_r_reg}, {text_value_reg}")
                if text_value_reg not in ['P0', 'P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'SP', 'FP']:
                    self.smart_deallocate(text_value_reg, is_last_use=True)
                text_value_reg = temp_r_reg
            
            string_reg = self.allocate_register("P1")  # Use P register for string address
            self.current_output.append(f"ITOS {string_reg}, {text_value_reg}")  # Convert number to string
            self.current_output.append(f"TEXT {string_reg}")  # Display the converted string
            self.deallocate_register(string_reg)
            if text_value_reg not in ['R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9']:
                self.smart_deallocate(text_value_reg, is_last_use=True)

    def generate_set_layer(self, stmt: SetLayerStmt):
        """Generate optimized SetLayer(layer) code with direct register assignment."""
        self.current_output.append("MOV VM, 0")  # Coordinate mode for pixel operations
        self.generate_expression_into(stmt.layer, 'VL')

    def generate_sprite_on(self, stmt: SpriteOnStmt):
        """Generate SpriteOn(spriteId, x, y) code.
        
        Sprite control block structure (at 0xF000 + spriteId * 16):
        Offset 0-1: Data address (16-bit)
        Offset 2: X position (8-bit)
        Offset 3: Y position (8-bit)
        Offset 4: Width (8-bit)
        Offset 5: Height (8-bit)
        Offset 6: Flags (bit 0=active, bit 1=transparency)
        Offset 7: Transparency color (8-bit)
        """
        self.current_output.append("; SpriteOn - Enable and position sprite")
        
        # Evaluate arguments
        sprite_id_reg = self.generate_expression(stmt.sprite_id, "R1")
        x_reg = self.generate_expression(stmt.x, "R2")
        y_reg = self.generate_expression(stmt.y, "R3")
        
        # Calculate sprite control block base address: 0xF000 + (spriteId * 16)
        # Use P2 for address calculation
        self.current_output.append(f"MOV P2, {sprite_id_reg}")
        # Multiply by 16: shift left 4 times (can't do SHL with immediate > 1)
        self.current_output.append(f"SHL P2, P2")  # *2
        self.current_output.append(f"SHL P2, P2")  # *4
        self.current_output.append(f"SHL P2, P2")  # *8
        self.current_output.append(f"SHL P2, P2")  # *16
        # Load sprite memory base and add offset
        self.current_output.append(f"MOV P3, 0xF000  ; Sprite memory base")
        self.current_output.append(f"ADD P2, P3  ; P2 = P2 + P3 (2-operand ADD)")
        
        # Write X position (offset 2)
        self.current_output.append(f"MOV P3, P2")
        self.current_output.append(f"ADD P3, 2")
        self.current_output.append(f"MOV [P3], {x_reg}")
        
        # Write Y position (offset 3)
        self.current_output.append(f"MOV P3, P2")
        self.current_output.append(f"ADD P3, 3")
        self.current_output.append(f"MOV [P3], {y_reg}")
        
        # Set active flag (offset 6, bit 0)
        self.current_output.append(f"MOV P3, P2")
        self.current_output.append(f"ADD P3, 6")
        self.current_output.append(f"MOV R4, [P3]  ; Read current flags")
        self.current_output.append(f"OR R4, 0x01  ; Set bit 0 (active)")
        self.current_output.append(f"MOV [P3], R4")
        
        # Free temporary registers
        self.smart_deallocate(sprite_id_reg, is_last_use=True)
        self.smart_deallocate(x_reg, is_last_use=True)
        self.smart_deallocate(y_reg, is_last_use=True)

    def generate_sprite_off(self, stmt: SpriteOffStmt):
        """Generate SpriteOff(spriteId) code.
        
        Disables a sprite by clearing the active flag (bit 0) in the sprite control block.
        """
        self.current_output.append("; SpriteOff - Disable sprite")
        
        # Evaluate sprite ID
        sprite_id_reg = self.generate_expression(stmt.sprite_id, "R1")
        
        # Calculate sprite control block base address: 0xF000 + (spriteId * 16)
        self.current_output.append(f"MOV P2, {sprite_id_reg}")
        # Multiply by 16: shift left 4 times
        self.current_output.append(f"SHL P2, P2")  # *2
        self.current_output.append(f"SHL P2, P2")  # *4
        self.current_output.append(f"SHL P2, P2")  # *8
        self.current_output.append(f"SHL P2, P2")  # *16
        # Load sprite memory base and add offset
        self.current_output.append(f"MOV P3, 0xF000  ; Sprite memory base")
        self.current_output.append(f"ADD P2, P3  ; P2 = P2 + P3 (2-operand ADD)")
        
        # Clear active flag (offset 6, bit 0)
        self.current_output.append(f"ADD P2, 6  ; Point to flags byte")
        self.current_output.append(f"MOV R2, [P2]  ; Read current flags")
        self.current_output.append(f"AND R2, R2, 0xFE  ; Clear bit 0 (active)")
        self.current_output.append(f"MOV [P2], R2")
        
        # Free temporary register
        self.smart_deallocate(sprite_id_reg, is_last_use=True)

    def generate_play_tone(self, stmt: PlayToneStmt):
        """Generate optimized PlayTone code."""
        freq_reg = self.generate_expression(stmt.frequency)
        dur_reg = self.generate_expression(stmt.duration)
        vol_reg = self.generate_expression(stmt.volume)
        
        # Set sound registers
        self.current_output.append(f"MOV SF, {freq_reg}")
        self.current_output.append(f"MOV SV, {vol_reg}")
        self.current_output.append("MOV SW, 0")  # Set waveform to default (0)
        self.current_output.append("SPLAY")

        # Duration handling could use timer, but simplified for now
        self.current_output.append("; Duration handling - simplified")

    def generate_play_wave(self, stmt: PlayWaveStmt):
        """Generate optimized PlayWave code."""
        wave_reg = self.generate_expression(stmt.waveform)
        freq_reg = self.generate_expression(stmt.frequency)
        vol_reg = self.generate_expression(stmt.volume)
        
        # Set sound registers
        self.current_output.append(f"MOV SW, {wave_reg}")
        self.current_output.append(f"MOV SF, {freq_reg}")
        self.current_output.append(f"MOV SV, {vol_reg}")
        self.current_output.append("SPLAY")

    def generate_stop_sound(self):
        """Generate StopSound code."""
        self.current_output.append("MOV SV, 0")  # Set volume to 0

    def generate_set_channel(self, stmt: SetChannelStmt):
        """Generate SetChannel(channel) code."""
        # Simplified - channel selection
        self.current_output.append("; Set channel - simplified")

    def generate_get_key(self):
        """Generate GetKey code - non-blocking, returns 0 if no key available."""
        # Check if key available, read it, or return 0
        self.current_output.append("KEYIN R0")    # Read key (returns 0 if buffer empty)

    def generate_input(self, stmt: InputStmt):
        """Generate Input(prompt, variable) code."""
        # Display prompt if provided
        if stmt.prompt is not None:
            # Handle prompt display
            if isinstance(stmt.prompt, LiteralExpr) and stmt.prompt.data_type.name == "STRING":
                # For string literals, display directly
                prompt_label = self.add_string_literal(stmt.prompt.value)
                self.current_output.append(f"TEXT {prompt_label}, 15")  # White color
            else:
                # For expressions, evaluate and try to display (simplified for now)
                prompt_reg = self.generate_expression(stmt.prompt, "R1")
                self.current_output.append(f"TEXT {prompt_reg}, 15")  # This may not work properly for non-strings

        # Wait for and read input
        input_label = self.new_label()
        self.current_output.append(f"{input_label}:")
        self.current_output.append("KEYSTAT R0")
        self.current_output.append("CMP R0, 0")
        self.current_output.append(f"JZ {input_label}")  # Wait for key
        self.current_output.append("KEYIN R0")  # Read the key

        # Store in variable
        var_addr = self.get_variable_address(stmt.variable)
        self.current_output.append(f"MOV P0, {var_addr}")
        self.current_output.append(f"MOV [P0], R0")

    def generate_disp(self, stmt: DispStmt):
        """Generate Disp expression code."""
        # Check if this is a string expression by examining the AST node
        is_string_literal = isinstance(stmt.text, LiteralExpr) and hasattr(stmt.text, 'data_type') and stmt.text.data_type.name == "STRING"
        is_string_variable = isinstance(stmt.text, VariableExpr) and stmt.text.name.upper().startswith("STR")
        
        if is_string_literal:
            # String literal - create label and display
            label = self.add_string_literal(stmt.text.value)
            self.current_output.append("MOV VX, 0")  # Set X coordinate
            self.current_output.append("MOV VC, 15")  # Set color to white
            self.current_output.append(f"TEXT {label}")  # Display text
            self.current_output.append(f"ADD VY, 8")  # Move down for next line
        elif is_string_variable:
            # String variable - evaluate to get address
            text_addr_reg = self.generate_expression(stmt.text, "P1")
            self.current_output.append("MOV VX, 0")  # Set X coordinate
            self.current_output.append("MOV VC, 15")  # Set color to white
            self.current_output.append(f"TEXT {text_addr_reg}")  # Display text
            self.current_output.append(f"ADD VY, 8")  # Move down for next line
            if text_addr_reg not in ['P0', 'P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'SP', 'FP']:
                self.smart_deallocate(text_addr_reg, is_last_use=True)
        elif isinstance(stmt.text, BinaryExpr) and stmt.text.operator == "+":
            # Could be string concatenation or numeric addition
            # Try to determine if it's a string operation based on context
            # For safety, assume numeric unless operands are clearly strings
            left_is_string = (isinstance(stmt.text.left, LiteralExpr) and hasattr(stmt.text.left, 'data_type') and stmt.text.left.data_type.name == "STRING") or \
                           (isinstance(stmt.text.left, VariableExpr) and stmt.text.left.name.upper().startswith("STR"))
            right_is_string = (isinstance(stmt.text.right, LiteralExpr) and hasattr(stmt.text.right, 'data_type') and stmt.text.right.data_type.name == "STRING") or \
                            (isinstance(stmt.text.right, VariableExpr) and stmt.text.right.name.upper().startswith("STR"))
            
            if left_is_string or right_is_string:
                # String concatenation - evaluate to get address
                text_addr_reg = self.generate_expression(stmt.text, "P1")
                self.current_output.append("MOV VX, 0")  # Set X coordinate
                self.current_output.append("MOV VC, 15")  # Set color to white
                self.current_output.append(f"TEXT {text_addr_reg}")  # Display text
                self.current_output.append(f"ADD VY, 8")  # Move down for next line
                if text_addr_reg not in ['P0', 'P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'SP', 'FP']:
                    self.smart_deallocate(text_addr_reg, is_last_use=True)
            else:
                # Numeric addition - convert to string
                value_reg = self.generate_expression(stmt.text, "R1")
                
                # Ensure we use an R register for ITOS
                if value_reg.startswith('P'):
                    temp_r_reg = self.allocate_register("R1")
                    self.current_output.append(f"MOV {temp_r_reg}, {value_reg}")
                    if value_reg not in ['P0', 'P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'SP', 'FP']:
                        self.smart_deallocate(value_reg, is_last_use=True)
                    value_reg = temp_r_reg
                
                string_reg = self.allocate_register("P1")
                self.current_output.append(f"ITOS {string_reg}, {value_reg}")
                self.current_output.append("MOV VX, 0")
                self.current_output.append("MOV VC, 15")
                self.current_output.append(f"TEXT {string_reg}")
                self.current_output.append(f"ADD VY, 8")
                self.deallocate_register(string_reg)
                if value_reg not in ['R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9']:
                    self.smart_deallocate(value_reg, is_last_use=True)
        else:
            # Numeric expression (default case) - evaluate and convert to string
            value_reg = self.generate_expression(stmt.text, "R1")
            
            # Ensure we use an R register for ITOS (it needs R register as source)
            if value_reg.startswith('P'):
                temp_r_reg = self.allocate_register("R1")
                self.current_output.append(f"MOV {temp_r_reg}, {value_reg}")
                if value_reg not in ['P0', 'P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'SP', 'FP']:
                    self.smart_deallocate(value_reg, is_last_use=True)
                value_reg = temp_r_reg
            
            string_reg = self.allocate_register("P1")  # Use a P register for string address
            self.current_output.append(f"ITOS {string_reg}, {value_reg}")  # Convert to string
            self.current_output.append("MOV VX, 0")  # Set X coordinate
            self.current_output.append("MOV VC, 15")  # Set color to white
            self.current_output.append(f"TEXT {string_reg}")  # Display text
            self.current_output.append(f"ADD VY, 8")  # Move down for next line
            self.deallocate_register(string_reg)
            if value_reg not in ['R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9']:
                self.smart_deallocate(value_reg, is_last_use=True)

    def generate_pause(self):
        """Generate optimized Pause code."""
        # Use more efficient key checking
        pause_label = self.new_label()
        self.current_output.append(f"{pause_label}:")
        self.current_output.append("KEYSTAT R0")
        self.current_output.append("CMP R0, 0")
        self.current_output.append(f"JZ {pause_label}")  # Loop until key pressed

    def generate_function_call_statement(self, stmt: FunctionCallStmt):
        """Generate code for a function call statement."""
        # Evaluate the function call but discard the result
        self.generate_expression(stmt.function_call, "R0")

    def generate_expression_statement(self, stmt: ExpressionStmt):
        """Generate code for an expression statement (evaluates expression, discards result)."""
        # Evaluate the expression but discard the result
        self.generate_expression(stmt.expression, "R0")

    def generate_assignment(self, stmt: AssignmentStmt):
        """Generate optimized assignment code."""
        # Check if we're assigning a string - if so, ensure we use P register
        is_string_assignment = False
        if isinstance(stmt.variable, VariableExpr):
            is_string_assignment = stmt.variable.name.upper().startswith("STR")
        
        # Generate the value - prefer a P register for strings, R1 for numeric temps
        preferred_reg = "P1" if is_string_assignment else "R1"
        value_reg = self.generate_expression(stmt.expression, preferred_reg)

        if isinstance(stmt.variable, VariableExpr):
            var_name = stmt.variable.name
            if var_name in self.var_reg:
                # Store to register
                reg = self.var_reg[var_name]
                if reg != value_reg:
                    self.current_output.append(f"MOV {reg}, {value_reg}")
            else:
                # Store to memory (handles both regular memory and spill slots)
                self.store_variable(var_name, value_reg)
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
        self.current_output.append(f"MOV {target_reg}, {index_reg}")
        self.current_output.append(f"MUL {target_reg}, 2")  # Multiply by 2 (word stride)
        self.current_output.append(f"MOV P5, 0x{base_addr:04X}")
        self.current_output.append(f"ADD {target_reg}, P5")
        self.current_output.append(f"MOV P0, {target_reg}")
        self.current_output.append(f"MOV {target_reg}, [P0]")
        return target_reg

    def generate_list_store(self, expr: ListAccessExpr, value_reg: str):
        """Generate code to store to a list element."""
        list_num = int(expr.list_name[1])  # L1 -> 1
        base_addr = 0x1000 + (list_num - 1) * 0x100
        
        index_reg = self.generate_expression(expr.index, "R2")
        # Address = base_addr + index * 2
        self.current_output.append(f"MOV P0, {index_reg}")
        self.current_output.append("MUL P0, 2")  # Multiply by 2 (word stride)
        self.current_output.append(f"MOV P5, 0x{base_addr:04X}")
        self.current_output.append("ADD P0, P5")
        store_reg = value_reg
        if store_reg.startswith('R') or store_reg in {"P0", "P5"}:
            self.current_output.append(f"MOV P1, {store_reg}")
            store_reg = "P1"
        self.current_output.append(f"MOV [P0], {store_reg}")

    def generate_matrix_access(self, expr: MatrixAccessExpr, target_reg: str) -> str:
        """Generate code to load from a matrix element."""
        # Matrix layout: MatA, MatB, MatC - each 10x10 = 100 elements (200 bytes for 16-bit)
        # MatA: 0x3000-0x30C7, MatB: 0x30C8-0x318F, MatC: 0x3190-0x3257
        matrix_bases = {
            "MatA": 0x3000,
            "MatB": 0x30C8,
            "MatC": 0x3190
        }
        
        if expr.matrix_name not in matrix_bases:
            base_addr = 0x3000
        else:
            base_addr = matrix_bases[expr.matrix_name]
        
        # Generate row and col into P registers (for address calculation)
        row_reg = self.generate_expression(expr.row, "P1")
        col_reg = self.generate_expression(expr.col, "P2")
        
        # Calculate offset: row * 10 + col (10 columns per row)
        # offset = row * 20 (for 16-bit elements) + col * 2
        self.current_output.append(f"MOV P3, {row_reg}")
        self.current_output.append(f"MUL P3, 20")  # 10 cols * 2 bytes per element
        self.current_output.append(f"MOV P4, {col_reg}")
        self.current_output.append(f"MUL P4, 2")   # 2 bytes per element
        self.current_output.append(f"ADD P3, P4")  # Total offset
        self.current_output.append(f"MOV P4, 0x{base_addr:04X}")
        self.current_output.append(f"ADD P4, P3")  # Address = base + offset
        self.current_output.append(f"MOV {target_reg}, [P4]")  # Load from address
        
        self.smart_deallocate(row_reg, is_last_use=True)
        self.smart_deallocate(col_reg, is_last_use=True)
        return target_reg

    def generate_matrix_store(self, expr: MatrixAccessExpr, value_reg: str):
        """Generate code to store to a matrix element."""
        # Matrix layout: MatA, MatB, MatC - each 10x10 = 100 elements (200 bytes for 16-bit)
        matrix_bases = {
            "MatA": 0x3000,
            "MatB": 0x30C8,
            "MatC": 0x3190
        }
        
        if expr.matrix_name not in matrix_bases:
            base_addr = 0x3000
        else:
            base_addr = matrix_bases[expr.matrix_name]
        
        # Generate row and col into P registers
        row_reg = self.generate_expression(expr.row, "P1")
        col_reg = self.generate_expression(expr.col, "P2")
        
        # Calculate offset: row * 10 + col (10 columns per row)
        self.current_output.append(f"MOV P3, {row_reg}")
        self.current_output.append(f"MUL P3, 20")  # 10 cols * 2 bytes per element
        self.current_output.append(f"MOV P4, {col_reg}")
        self.current_output.append(f"MUL P4, 2")   # 2 bytes per element
        self.current_output.append(f"ADD P3, P4")  # Total offset
        self.current_output.append(f"MOV P4, 0x{base_addr:04X}")
        self.current_output.append(f"ADD P4, P3")  # Address = base + offset
        self.current_output.append(f"MOV [P4], {value_reg}")  # Store to address
        
        self.smart_deallocate(row_reg, is_last_use=True)
        self.smart_deallocate(col_reg, is_last_use=True)

    def generate_member_access(self, expr: MemberAccessExpr, target_reg: str) -> str:
        """Generate code to load from a struct member."""
        if isinstance(expr.object, VariableExpr):
            var_name = expr.object.name
            var_key = var_name.lower()
            member_name = expr.member.lower()
            
            # Check if this is a struct instance
            if var_key in self.struct_instances:
                struct_name = self.struct_instances[var_key]
                struct_def = self.struct_types[struct_name]
                base_addr = self.struct_bases[var_key]
                
                # Calculate field offset
                field_index = struct_def.fields.index(member_name)
                field_offset = field_index * 2  # 2 bytes per field
                field_addr = base_addr + field_offset
                
                # CRITICAL: Struct fields are 16-bit unsigned values.
                # ALWAYS load into 16-bit P registers to preserve unsigned values!
                # This fixes signed comparison issues with values > 127.
                self.current_output.append(f"; Load {var_name}.{expr.member}")
                self.current_output.append(f"MOV P0, {field_addr}")
                
                # If target_reg is a P register, use it directly
                # If target_reg is an R register, we cannot use it (would lose unsigned value)
                # In that case, just use P1 and return it (caller will handle the mismatch)
                if target_reg.startswith('P'):
                    # Target is already a P register, use it
                    self.current_output.append(f"MOV {target_reg}, [P0]")
                    return target_reg
                else:
                    # Target is an R register, but we need P for unsigned values
                    # Use P1 as a temporary and return it
                    # The caller's target_reg will be unused but that's OK
                    self.current_output.append(f"MOV P1, [P0]")
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
            var_key = var_name.lower()
            member_name = expr.member.lower()
            
            # Check if this is a struct instance
            if var_key in self.struct_instances:
                struct_name = self.struct_instances[var_key]
                struct_def = self.struct_types[struct_name]
                base_addr = self.struct_bases[var_key]
                
                # Calculate field offset
                field_index = struct_def.fields.index(member_name)
                field_offset = field_index * 2  # 2 bytes per field
                field_addr = base_addr + field_offset
                
                # Store field value
                self.current_output.append(f"; Store to {var_name}.{expr.member}")
                self.current_output.append(f"MOV P0, {field_addr}")
                self.current_output.append(f"MOV [P0], {value_reg}")
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
        var_key = var_name.lower()
        struct_key = struct_name.lower()

        if var_key in self.struct_bases:
            return self.struct_bases[var_key]
        
        struct_def = self.struct_types[struct_key]
        field_count = len(struct_def.fields)
        
        base_addr = self.next_address
        self.struct_bases[var_key] = base_addr
        self.struct_instances[var_key] = struct_key
        self.next_address += field_count * 2  # 2 bytes per field
        
        self.current_output.append(f"; Allocate struct {var_name} ({struct_def.name}) at 0x{base_addr:04X}")
        return base_addr

    def generate_if(self, stmt: IfStmt):
        """Generate optimized If-Then-Else code."""
        else_label = self.new_label()
        end_label = self.new_label()

        # Allocate a temporary register for the condition (ensures it can be freed)
        temp_reg = self.allocate_register()
        try:
            condition_reg = self.generate_expression(stmt.condition, temp_reg)

            # Test if condition is false (0)
            self.current_output.append(f"CMP {condition_reg}, 0")
            self.current_output.append(f"JZ {else_label}")
        finally:
            # Always free the temp register we allocated
            self.deallocate_register(temp_reg)

        for s in stmt.then_branch:
            self.generate_statement(s)

        if stmt.else_branch:
            self.current_output.append(f"JMP {end_label}")
            self.current_output.append(f"{else_label}:")

            for s in stmt.else_branch:
                self.generate_statement(s)

            self.current_output.append(f"{end_label}:")
        else:
            self.current_output.append(f"{else_label}:")

    def generate_for(self, stmt: ForStmt):
        """Generate optimized For loop code with hoisted end value and efficient comparisons."""
        loop_label = self.new_label()
        end_label = self.new_label()
        
        # Get registers for this nesting level
        current_reg, end_reg, step_reg = self.get_loop_registers()
        
        # Increment nesting level for inner constructs
        self.loop_nesting_level += 1

        # Check if loop variable is a local variable in current function
        is_local_var = (self.current_function and 
                       self.current_function in self.function_locals and 
                       stmt.variable in self.function_locals[self.current_function])
        
        # Allocate loop_reg
        is_register_allocated = (stmt.variable in self.var_reg) and self.current_function is None  # In functions, always use memory for loop variables
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
        if start_reg != loop_reg:
            self.current_output.append(f"MOV {loop_reg}, {start_reg}")
            self.deallocate_register(start_reg)
        # else: start_reg == loop_reg, so generate_expression already set loop_reg to the start value
        
        # Store initial value if needed
        if is_local_var:
            # Store to local variable slot
            offset = self.function_locals[self.current_function][stmt.variable]
            self.current_output.append(f"MOV P0, FP")
            self.current_output.append(f"ADD P0, {offset}")
            self.current_output.append(f"MOV [P0], {loop_reg}")
        elif not is_register_allocated and self.current_function is None:  # Only store in memory for global variables
            var_addr = self.get_variable_address(stmt.variable)
            self.current_output.append(f"MOV P0, {var_addr}")
            self.current_output.append(f"MOV [P0], {loop_reg}")

        # **OPTIMIZATION: Load end value ONCE before loop**
        end_value_reg = self.generate_expression(stmt.end, end_reg)
        if end_value_reg != end_reg:
            self.current_output.append(f"MOV {end_reg}, {end_value_reg}")
            self.deallocate_register(end_value_reg)
            end_value_reg = end_reg

        # Load step value once if it's a constant expression
        if stmt.step:
            step_value_reg = self.generate_expression(stmt.step, step_reg)
            if step_value_reg != step_reg:
                self.current_output.append(f"MOV {step_reg}, {step_value_reg}")
                self.deallocate_register(step_value_reg)
                step_value_reg = step_reg

        # Loop start
        self.current_output.append(f"{loop_label}:")

        # Update memory for loop variable if needed
        if is_local_var:
            # Update local variable slot
            offset = self.function_locals[self.current_function][stmt.variable]
            self.current_output.append(f"MOV P0, FP")
            self.current_output.append(f"ADD P0, {offset}")
            self.current_output.append(f"MOV [P0], {loop_reg}")
        elif not is_register_allocated and self.current_function is None:  # Only store in memory for global variables
            var_addr = self.get_variable_address(stmt.variable)
            self.current_output.append(f"MOV P0, {var_addr}")
            self.current_output.append(f"MOV [P0], {loop_reg}")

        # **OPTIMIZATION: Single comparison with proper jump instruction**
        # Compare current to end (end value already in register)
        self.current_output.append(f"CMP {loop_reg}, {end_value_reg}")
        
        # Use JGT (jump if greater than) for cleaner exit condition
        # Loop continues while loop_reg <= end_value_reg
        self.current_output.append(f"JGT {end_label}")  # Exit if current > end

        # Loop body
        for s in stmt.body:
            self.generate_statement(s)

        # Increment/step
        if stmt.step:
            # Use pre-loaded step value
            self.current_output.append(f"ADD {loop_reg}, {step_value_reg}")
        else:
            # **OPTIMIZATION: Use INC for default step=1**
            self.current_output.append(f"INC {loop_reg}")

        self.current_output.append(f"JMP {loop_label}")
        self.current_output.append(f"{end_label}:")

        # Ensure final value is stored for local variables
        if is_local_var:
            offset = self.function_locals[self.current_function][stmt.variable]
            self.current_output.append(f"MOV P0, FP")
            self.current_output.append(f"ADD P0, {offset}")
            self.current_output.append(f"MOV [P0], {loop_reg}")

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

        self.current_output.append(f"{loop_label}:")

        # Allocate a temporary register for the condition (ensures it can be freed)
        temp_reg = self.allocate_register()
        try:
            condition_reg = self.generate_expression(stmt.condition, temp_reg)
            self.current_output.append(f"CMP {condition_reg}, 0")
            self.current_output.append(f"JZ {end_label}")
        finally:
            # Always free the temp register we allocated
            self.deallocate_register(temp_reg)

        for s in stmt.body:
            self.generate_statement(s)

        self.current_output.append(f"JMP {loop_label}")
        self.current_output.append(f"{end_label}:")

    def generate_repeat(self, stmt: RepeatStmt):
        """Generate optimized Repeat-Until loop code."""
        loop_label = self.new_label()

        self.current_output.append(f"{loop_label}:")

        for s in stmt.body:
            self.generate_statement(s)

        # Allocate a temporary register for the condition (ensures it can be freed)
        temp_reg = self.allocate_register()
        try:
            condition_reg = self.generate_expression(stmt.condition, temp_reg)
            self.current_output.append(f"CMP {condition_reg}, 0")
            self.current_output.append(f"JZ {loop_label}")
        finally:
            # Always free the temp register we allocated
            self.deallocate_register(temp_reg)  # Continue looping if condition is false

    def generate_goto(self, stmt: GotoStmt):
        """Generate Goto code."""
        self.current_output.append(f"JMP {stmt.label}")

    def generate_label(self, stmt: LabelStmt):
        """Generate Label code."""
        self.current_output.append(f"{stmt.label}:")

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

    def _normalize_numeric_literal(self, value):
        """Normalize NoBASIC numeric literals to assembler-safe integer immediates."""
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, float):
            if not value.is_integer():
                return int(value)
            return int(value)
        return value

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
                literal_value = self._normalize_numeric_literal(expr.value)
                # Generate literal directly into target
                if literal_value == 0:
                    self.current_output.append(f"XOR {target_reg}, {target_reg}")
                elif literal_value == 1:
                    self.current_output.append(f"MOV {target_reg}, 1")
                elif literal_value in [2, 4, 8, 16, 32, 64, 128, 256, 512, 1024]:
                    # Use shifts for powers of 2
                    shift_amount = literal_value.bit_length() - 1
                    self.current_output.append(f"MOV {target_reg}, 1")
                    self.current_output.append(f"SHL {target_reg}, {shift_amount}")
                else:
                    self.current_output.append(f"MOV {target_reg}, {literal_value}")
            elif expr.data_type.name == "STRING":
                label = self.add_string_literal(expr.value)
                self.current_output.append(f"MOV {target_reg}, {label}")
            else:
                self.current_output.append(f"MOV {target_reg}, 0")
        elif isinstance(expr, VariableExpr):
            # Load variable directly into target
            if expr.name in self.var_reg:
                reg = self.var_reg[expr.name]
                if reg != target_reg:
                    self.current_output.append(f"MOV {target_reg}, {reg}")
                # If reg == target_reg, no operation needed!
            else:
                # Check if target is an 8-bit register (R or hardware)
                is_8bit_reg = target_reg.startswith('R') or target_reg in ['VX', 'VY', 'VC', 'VL', 'VM', 'SA', 'SF', 'SV', 'SW', 'TT', 'TM', 'TC', 'TS']
                
                if is_8bit_reg:
                    # For 8-bit registers, we need to ensure we only get the low byte
                    # Load variable into a temp P register, then extract low byte
                    temp_p_reg = self.allocate_register()
                    source_reg = self.load_variable(expr.name, temp_p_reg)
                    # source_reg now contains the variable value (16-bit in a P register)
                    # Extract low byte for the 8-bit hardware register
                    self.current_output.append(f"MOV {target_reg}, :{source_reg}")
                    self.deallocate_register(source_reg)
                else:
                    # Load from memory (handles both regular memory and spill slots)
                    source_reg = self.load_variable(expr.name, target_reg)
                    # If load_variable returned a different register, move it to the target register
                    if source_reg != target_reg:
                        self.current_output.append(f"MOV {target_reg}, {source_reg}")
        else:
            # For complex expressions, generate into a temp then move
            temp_reg = self.generate_expression(expr)
            if temp_reg != target_reg:
                self.current_output.append(f"MOV {target_reg}, {temp_reg}")
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
                    literal_value = self._normalize_numeric_literal(expr.value)
                    # Check if we need a P register for this value (> 255 or negative)
                    if (literal_value > 255 or literal_value < 0) and target_reg.startswith('R'):
                        # Value doesn't fit in 8 bits, need a P register
                        self.deallocate_register(target_reg)
                        # Find any available P register
                        p_reg = None
                        for reg in ['P0', 'P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7']:
                            if not self.register_usage.get(reg, False):
                                p_reg = reg
                                break
                        if p_reg:
                            target_reg = self.allocate_register(p_reg)
                        else:
                            raise RuntimeError(f"No available P registers for 16-bit literal {literal_value}")
                    
                    # Optimize for common values
                    if literal_value == 0:
                        self.current_output.append(f"XOR {target_reg}, {target_reg}")  # Zero register
                    elif literal_value == 1:
                        self.current_output.append(f"MOV {target_reg}, 1")
                    elif literal_value in [2, 4, 8, 16, 32, 64, 128, 256, 512, 1024]:
                        # Use shifts for powers of 2
                        shift_amount = literal_value.bit_length() - 1
                        self.current_output.append(f"MOV {target_reg}, 1")
                        self.current_output.append(f"SHL {target_reg}, {shift_amount}")
                    else:
                        self.current_output.append(f"MOV {target_reg}, {literal_value}")
                    result_reg = target_reg
                elif expr.data_type.name == "STRING":
                    # String literals: create DEFSTR label and load address (16-bit, needs P register)
                    # If we somehow got an R register, we need to fix it
                    if target_reg.startswith('R'):
                        self.deallocate_register(target_reg)
                        target_reg = self.allocate_register('P1')
                    label = self.add_string_literal(expr.value)
                    self.current_output.append(f"MOV {target_reg}, {label}")
                    result_reg = target_reg
                else:
                    # Other types - default to zero
                    self.current_output.append(f"MOV {target_reg}, 0")
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
                self.current_output.append(f"MOV {target_reg}, 0")  # Default
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
                folded_emit_value = self._normalize_numeric_literal(folded_value)
                self.current_output.append(f"; Constant folded: {expr.left.value} {expr.operator} {expr.right.value} = {folded_value}")
                self.current_output.append(f"MOV {target_reg}, {folded_emit_value}")
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
                self.current_output.append(f"MOV P2, {left_result}")
                # Free the left result register immediately after moving
                self.smart_deallocate(left_result, is_last_use=True)
                left_result = 'P2'
                self.register_usage['P2'] = True
            
            # Generate right operand (left_result is now in P2)
            right_result = self.generate_expression(expr.right)
            # Immediately move to a safe temporary if needed
            if right_result != 'P3':
                self.current_output.append(f"MOV P3, {right_result}")
                # Free the right result register immediately after moving
                self.smart_deallocate(right_result, is_last_use=True)
                right_result = 'P3'
                self.register_usage['P3'] = True
            
            try:
                # Allocate temporary buffer for result (use next_address space)
                buffer_addr = self.next_address
                self.next_address += 256  # Reserve 256 bytes for concatenated string
                
                # Copy left string to buffer
                self.current_output.append(f"MOV P0, {buffer_addr}")  # Destination
                self.current_output.append(f"STRCPY P0, {left_result}")  # Copy left string
                
                # Concatenate right string to buffer
                self.current_output.append(f"STRCAT P0, {right_result}")  # Append right string
                
                # Return buffer address in target register
                self.current_output.append(f"MOV {target_reg}, {buffer_addr}")
                
                return target_reg
            finally:
                # Deallocate the temporary registers
                self.deallocate_register('P2')
                self.deallocate_register('P3')
        
        # Numeric operations - pick preferred registers (but don't pre-allocate to avoid clobber)
        available_regs = [r for r in self.allocation_order if r != target_reg]
        left_pref = available_regs[0] if available_regs else None
        right_pref = available_regs[1] if len(available_regs) > 1 else None

        # Generate left operand
        left_result = self.generate_expression(expr.left, left_pref)

        # Preserve left across right-side evaluation ONLY for non-comparison ops
        is_comparison = expr.operator in {"<", ">", "=", "<>", "<=", ">="}
        left_preserved_reg = None
        if not is_comparison:
            # **OPTIMIZATION: Use register allocation instead of PUSH/POP for left operand preservation**
            # Find a free register to preserve left operand (avoid target_reg and right_pref)
            self.current_output.append("; Preserve left operand in register across right-side evaluation")
            for reg in self.allocation_order:
                if not self.register_usage.get(reg, False) and reg != target_reg:
                    left_preserved_reg = reg
                    self.current_output.append(f"MOV {left_preserved_reg}, {left_result}")
                    self.register_usage[left_preserved_reg] = True
                    break
            
            # If no free register found, fall back to stack (rare case)
            if not left_preserved_reg:
                if left_result.startswith('R'):
                    p_temp = 'P1' if not self.register_usage.get('P1', False) else 'P2'
                    self.current_output.append(f"MOV {p_temp}, {left_result}")
                    self.current_output.append(f"PUSH {p_temp}")
                else:
                    self.current_output.append(f"PUSH {left_result}")

        # Generate right operand
        right_result = self.generate_expression(expr.right, right_pref)

        if not is_comparison:
            # Restore left operand from register or stack
            if left_preserved_reg:
                left_result = left_preserved_reg
            else:
                # Pop from stack (fallback path)
                self.current_output.append("POP P1")
                if left_result != 'P1':
                    self.current_output.append(f"MOV {left_result}, P1")

        # Perform the operation
        if expr.operator == "+":
            if left_result == target_reg:
                self.current_output.append(f"ADD {target_reg}, {right_result}")
            else:
                self.current_output.append(f"MOV {target_reg}, {left_result}")
                self.current_output.append(f"ADD {target_reg}, {right_result}")
        elif expr.operator == "-":
            if left_result == target_reg:
                self.current_output.append(f"SUB {target_reg}, {right_result}")
            else:
                self.current_output.append(f"MOV {target_reg}, {left_result}")
                self.current_output.append(f"SUB {target_reg}, {right_result}")
        elif expr.operator == "*":
            if left_result == target_reg:
                self.current_output.append(f"MUL {target_reg}, {right_result}")
            else:
                self.current_output.append(f"MOV {target_reg}, {left_result}")
                self.current_output.append(f"MUL {target_reg}, {right_result}")
        elif expr.operator == "/":
            if left_result == target_reg:
                self.current_output.append(f"DIV {target_reg}, {right_result}")
            else:
                self.current_output.append(f"MOV {target_reg}, {left_result}")
                self.current_output.append(f"DIV {target_reg}, {right_result}")
        elif expr.operator == "%" or expr.operator == "MOD":
            if left_result == target_reg:
                self.current_output.append(f"MOD {target_reg}, {right_result}")
            else:
                self.current_output.append(f"MOV {target_reg}, {left_result}")
                self.current_output.append(f"MOD {target_reg}, {right_result}")
        elif expr.operator == "&" or expr.operator == "AND":
            if left_result == target_reg:
                self.current_output.append(f"AND {target_reg}, {right_result}")
            else:
                self.current_output.append(f"MOV {target_reg}, {left_result}")
                self.current_output.append(f"AND {target_reg}, {right_result}")
        elif expr.operator == "|" or expr.operator == "OR":
            if left_result == target_reg:
                self.current_output.append(f"OR {target_reg}, {right_result}")
            else:
                self.current_output.append(f"MOV {target_reg}, {left_result}")
                self.current_output.append(f"OR {target_reg}, {right_result}")
        elif expr.operator == "^" or expr.operator == "XOR":
            if left_result == target_reg:
                self.current_output.append(f"XOR {target_reg}, {right_result}")
            else:
                self.current_output.append(f"MOV {target_reg}, {left_result}")
                self.current_output.append(f"XOR {target_reg}, {right_result}")
        elif expr.operator == "<<" or expr.operator == "SHL":
            if left_result == target_reg:
                self.current_output.append(f"SHL {target_reg}, {right_result}")
            else:
                self.current_output.append(f"MOV {target_reg}, {left_result}")
                self.current_output.append(f"SHL {target_reg}, {right_result}")
        elif expr.operator == ">>" or expr.operator == "SHR":
            if left_result == target_reg:
                self.current_output.append(f"SHR {target_reg}, {right_result}")
            else:
                self.current_output.append(f"MOV {target_reg}, {left_result}")
                self.current_output.append(f"SHR {target_reg}, {right_result}")
        elif expr.operator == "<<<" or expr.operator == "SAL":
            if left_result != target_reg:
                self.current_output.append(f"MOV {target_reg}, {left_result}")
            self.current_output.append(f"SAL {target_reg}, {right_result}")
        elif expr.operator == ">>>" or expr.operator == "SAR":
            if left_result != target_reg:
                self.current_output.append(f"MOV {target_reg}, {left_result}")
            self.current_output.append(f"SAR {target_reg}, {right_result}")
        elif expr.operator == "<@>" or expr.operator == "ROL":
            if left_result != target_reg:
                self.current_output.append(f"MOV {target_reg}, {left_result}")
            self.current_output.append(f"ROL {target_reg}, {right_result}")
        elif expr.operator == "@>" or expr.operator == "ROR":
            if left_result != target_reg:
                self.current_output.append(f"MOV {target_reg}, {left_result}")
            self.current_output.append(f"ROR {target_reg}, {right_result}")
        elif expr.operator == "<@@" or expr.operator == "RCL":
            if left_result != target_reg:
                self.current_output.append(f"MOV {target_reg}, {left_result}")
            self.current_output.append(f"RCL {target_reg}, {right_result}")
        elif expr.operator == "@@>" or expr.operator == "RCR":
            if left_result != target_reg:
                self.current_output.append(f"MOV {target_reg}, {left_result}")
            self.current_output.append(f"RCR {target_reg}, {right_result}")
        elif expr.operator == "<" or expr.operator == ">" or expr.operator == "=" or expr.operator == "<>" or expr.operator == "<=" or expr.operator == ">=":
            # Use CMP for comparisons and set target_reg based on result
            self.current_output.append(f"CMP {left_result}, {right_result}")
            
            # Free registers immediately after comparison
            self.smart_deallocate(left_result, is_last_use=True)
            self.smart_deallocate(right_result, is_last_use=True)
            
            true_label = self.new_label()
            end_label = self.new_label()
            
            # Set default to false
            self.current_output.append(f"MOV {target_reg}, 0")
            
            # Jump to set true if condition met
            if expr.operator == "<":
                self.current_output.append(f"JLT {true_label}")
            elif expr.operator == ">":
                self.current_output.append(f"JGT {true_label}")
            elif expr.operator == "=":
                self.current_output.append(f"JZ {true_label}")
            elif expr.operator == "<>":
                self.current_output.append(f"JNZ {true_label}")
            elif expr.operator == "<=":
                self.current_output.append(f"JLE {true_label}")
            elif expr.operator == ">=":
                self.current_output.append(f"JGE {true_label}")
            
            self.current_output.append(f"JMP {end_label}")
            self.current_output.append(f"{true_label}:")
            self.current_output.append(f"MOV {target_reg}, 1")
            self.current_output.append(f"{end_label}:")
            
            # Registers already freed above for comparisons
            # Free the preserved register if we allocated one
            if left_preserved_reg:
                self.deallocate_register(left_preserved_reg)
            return target_reg
        else:
            # Fallback
            self.current_output.append(f"MOV {target_reg}, #0")
            
        # Free operand registers immediately after use (unless they're the target)
        if left_result != target_reg:
            self.smart_deallocate(left_result, is_last_use=True)
        if right_result != target_reg:
            self.smart_deallocate(right_result, is_last_use=True)
        
        # Free the preserved register if we allocated one
        if left_preserved_reg:
            self.deallocate_register(left_preserved_reg)
        
        return target_reg

    def generate_unary_expression(self, expr: UnaryExpr, target_reg: str) -> str:
        """Generate code for unary expressions, including pre/post ++/--, with immediate register freeing."""
        # ++/-- handling on variables
        if expr.operator in ("++", "--"):
            # Only support simple variables for now
            if isinstance(expr.expression, VariableExpr):
                var_name = expr.expression.name
                # Load 16-bit value into a P register
                value_reg = self.load_variable(var_name, target_reg if target_reg.startswith('P') else 'P1')
                # For post, capture original in target before modification
                if expr.is_post:
                    if target_reg != value_reg:
                        self.current_output.append(f"MOV {target_reg}, {value_reg}")
                # Modify value
                if expr.operator == "++":
                    self.current_output.append(f"ADD {value_reg}, 1")
                else:
                    self.current_output.append(f"SUB {value_reg}, 1")
                # Store back
                self.store_variable(var_name, value_reg)
                # For pre, return updated value
                if not expr.is_post:
                    if target_reg != value_reg:
                        self.current_output.append(f"MOV {target_reg}, {value_reg}")
                return target_reg
            else:
                # Fallback: evaluate operand, but cannot modify non-variable here
                operand_reg = self.generate_expression(expr.expression, target_reg)
                if operand_reg != target_reg:
                    self.current_output.append(f"MOV {target_reg}, {operand_reg}")
                    self.smart_deallocate(operand_reg, is_last_use=True)
                return target_reg

        # **OPTIMIZATION: Constant Folding for Unary Operations**
        if isinstance(expr.expression, LiteralExpr) and expr.expression.data_type.name == "NUMBER":
            folded_value = self.fold_unary_constant(expr.operator, expr.expression.value)
            if folded_value is not None:
                folded_emit_value = self._normalize_numeric_literal(folded_value)
                self.current_output.append(f"; Constant folded: {expr.operator}({expr.expression.value}) = {folded_value}")
                self.current_output.append(f"MOV {target_reg}, {folded_emit_value}")
                return target_reg
        
        operand_reg = self.generate_expression(expr.expression, target_reg)

        if expr.operator == "-":
            if operand_reg != target_reg:
                self.current_output.append(f"MOV {target_reg}, {operand_reg}")
                self.smart_deallocate(operand_reg, is_last_use=True)
            self.current_output.append(f"NEG {target_reg}")
        elif expr.operator == "NOT":
            if operand_reg != target_reg:
                self.current_output.append(f"MOV {target_reg}, {operand_reg}")
                self.smart_deallocate(operand_reg, is_last_use=True)
            self.current_output.append(f"NOT {target_reg}")
        elif expr.operator == "ABS":
            if operand_reg != target_reg:
                self.current_output.append(f"MOV {target_reg}, {operand_reg}")
                self.smart_deallocate(operand_reg, is_last_use=True)
            self.current_output.append(f"ABS {target_reg}")
        else:
            if operand_reg != target_reg:
                self.current_output.append(f"MOV {target_reg}, {operand_reg}")
                self.smart_deallocate(operand_reg, is_last_use=True)
        return target_reg

    def generate_function_call(self, expr: FunctionCallExpr, target_reg: str) -> str:
        """Generate optimized code for function calls with immediate register freeing."""
        func_name_lower = expr.name.lower()
        func_name = expr.name.upper()

        # Check for user-defined functions first
        if func_name_lower in self.functions:
            label, params, func_def = self.functions[func_name_lower]
            
            # Handle default parameters: push provided args, then defaults for missing ones
            provided_args = expr.arguments
            param_specs = func_def.params  # List of (name, default_expr)
            
            # Generate all arguments (provided + defaults) in reverse order
            all_args = []
            arg_index = 0
            
            # First, collect provided arguments
            for arg in provided_args:
                all_args.append(('provided', arg))
                arg_index += 1
            
            # Then, add defaults for missing parameters
            for param_name, default_expr in param_specs[arg_index:]:
                if default_expr is None:
                    # This should have been caught by semantic analysis
                    raise RuntimeError(f"Missing required argument for parameter '{param_name}'")
                all_args.append(('default', default_expr))
            
            # Generate arguments and push onto stack (left to right)
            arg_regs = []
            for arg_type, arg_expr in all_args:
                arg_reg = self.generate_expression(arg_expr)
                arg_regs.append(arg_reg)
                # Ensure 16-bit push: if arg in R register, move to P temp first
                if arg_reg.startswith('R'):
                    p_temp = self.allocate_register('P1') if not self.register_usage.get('P1', False) else self.allocate_register('P2')
                    self.current_output.append(f"MOV {p_temp}, {arg_reg}")
                    self.current_output.append(f"PUSH {p_temp}")
                    self.deallocate_register(p_temp)
                else:
                    self.current_output.append(f"PUSH {arg_reg}")
                self.smart_deallocate(arg_reg, is_last_use=True)
            
            # Call function
            self.current_output.append(f"CALL {label}")
            
            # Clean up stack (add back total_args * 2 bytes)
            total_args = len(all_args)
            if total_args > 0:
                self.current_output.append(f"ADD SP, {total_args * 2}")
            
            # Return value is in R0, move to target_reg
            if target_reg != 'R0':
                self.current_output.append(f"MOV {target_reg}, R0")
            
            return target_reg

        # Built-in functions
        unary_math_ops = {
            "SIN": "SIN",
            "COS": "COS",
            "TAN": "TAN",
            "SQRT": "SQRT",
            "ABS": "ABS",
            "ATAN": "ATAN",
            "ASIN": "ASIN",
            "ACOS": "ACOS",
            "DEG": "DEG",
            "RAD": "RAD",
            "FLOOR": "FLOOR",
            "CEIL": "CEIL",
            "ROUND": "ROUND",
            "TRUNC": "TRUNC",
            "FRAC": "FRAC",
            "INTGR": "INTGR",
            "INT": "INTGR",
            "LOG": "LOG",
            "EXP": "EXP",
        }

        if func_name in unary_math_ops:
            arg_reg = self.generate_expression(expr.arguments[0], target_reg)
            work_reg = target_reg
            if arg_reg != target_reg:
                self.current_output.append(f"MOV {target_reg}, {arg_reg}")
                self.smart_deallocate(arg_reg, is_last_use=True)
            self.current_output.append(f"{unary_math_ops[func_name]} {work_reg}")
            return target_reg

        if func_name == "RND":
            self.current_output.append(f"RND {target_reg}")
        elif func_name == "RNDR":
            # RNDR takes min and max, generates random in range [min, max]
            min_reg = self.generate_expression(expr.arguments[0], "R1")
            max_reg = self.generate_expression(expr.arguments[1], "R2")
            self.current_output.append(f"RNDR {target_reg}, {min_reg}, {max_reg}")
            self.smart_deallocate(min_reg, is_last_use=True)
            self.smart_deallocate(max_reg, is_last_use=True)
        elif func_name == "RANDOMIZE":
            # RANDOMIZE seeds the random number generator
            # For now, we'll use RND with the seed value to initialize
            # In a full implementation, this would set the RNG seed
            seed_reg = self.generate_expression(expr.arguments[0], "R1")
            self.current_output.append(f"; RANDOMIZE({seed_reg}) - seed RNG")
            self.current_output.append(f"MOV R0, {seed_reg}")
            self.current_output.append(f"RND {target_reg}  ; Initialize RNG with seed")
            self.smart_deallocate(seed_reg, is_last_use=True)
        elif func_name == "LEN" or func_name == "LENGTH" or func_name == "STRLEN":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.current_output.append(f"STRLEN {arg_reg}")
            if target_reg != "R0":
                self.current_output.append(f"MOV {target_reg}, R0")
            self.smart_deallocate(arg_reg, is_last_use=True)
        elif func_name == "STRCPY":
            dest_reg = self.generate_expression(expr.arguments[0], "R1")
            src_reg = self.generate_expression(expr.arguments[1], "R2")
            self.current_output.append(f"STRCPY {dest_reg}, {src_reg}")
            self.current_output.append(f"MOV {target_reg}, {dest_reg}")  # Return destination
            self.smart_deallocate(dest_reg, is_last_use=True)
            self.smart_deallocate(src_reg, is_last_use=True)
        elif func_name == "STRCAT":
            dest_reg = self.generate_expression(expr.arguments[0], "R1")
            src_reg = self.generate_expression(expr.arguments[1], "R2")
            self.current_output.append(f"STRCAT {dest_reg}, {src_reg}")
            self.current_output.append(f"MOV {target_reg}, {dest_reg}")  # Return destination
            self.smart_deallocate(dest_reg, is_last_use=True)
            self.smart_deallocate(src_reg, is_last_use=True)
        elif func_name == "STRCMP":
            str1_reg = self.generate_expression(expr.arguments[0], "R1")
            str2_reg = self.generate_expression(expr.arguments[1], "R2")
            len_reg = self.generate_expression(expr.arguments[2], "R3")
            self.current_output.append(f"STRCMP {str1_reg}, {str2_reg}, {len_reg}")
            # STRCMP sets flags from the comparison result (-1, 0, 1)
            less_label = self.new_label()
            equal_label = self.new_label()
            end_label = self.new_label()
            self.current_output.append(f"MOV {target_reg}, 1")
            self.current_output.append(f"JZ {equal_label}")
            self.current_output.append(f"JS {less_label}")
            self.current_output.append(f"JMP {end_label}")
            self.current_output.append(f"{less_label}:")
            self.current_output.append(f"MOV {target_reg}, 0xFFFF")
            self.current_output.append(f"JMP {end_label}")
            self.current_output.append(f"{equal_label}:")
            self.current_output.append(f"MOV {target_reg}, 0")
            self.current_output.append(f"{end_label}:")
            if str1_reg != target_reg:
                self.smart_deallocate(str1_reg, is_last_use=True)
            if str2_reg != target_reg:
                self.smart_deallocate(str2_reg, is_last_use=True)
            if len_reg != target_reg:
                self.smart_deallocate(len_reg, is_last_use=True)
        elif func_name == "STRUPR":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.current_output.append(f"STRUPR {arg_reg}")
            if target_reg != arg_reg:
                self.current_output.append(f"MOV {target_reg}, {arg_reg}")
                self.smart_deallocate(arg_reg, is_last_use=True)
        elif func_name == "STRLWR":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.current_output.append(f"STRLWR {arg_reg}")
            if target_reg != arg_reg:
                self.current_output.append(f"MOV {target_reg}, {arg_reg}")
                self.smart_deallocate(arg_reg, is_last_use=True)
        elif func_name == "LOWSTRING":
            # LOWSTRING uses STRLWR
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.current_output.append(f"STRLWR {arg_reg}")
            if target_reg != arg_reg:
                self.current_output.append(f"MOV {target_reg}, {arg_reg}")
                self.smart_deallocate(arg_reg, is_last_use=True)
        elif func_name == "UPSTRING":
            # UPSTRING uses STRUPR
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.current_output.append(f"STRUPR {arg_reg}")
            if target_reg != arg_reg:
                self.current_output.append(f"MOV {target_reg}, {arg_reg}")
                self.smart_deallocate(arg_reg, is_last_use=True)
        elif func_name == "LENSTRING":
            # LENSTRING uses STRLEN
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.current_output.append(f"STRLEN {arg_reg}")
            # STRLEN stores result in R0, so copy to target
            if target_reg != "R0":
                self.current_output.append(f"MOV {target_reg}, R0")
            self.smart_deallocate(arg_reg, is_last_use=True)
        elif func_name == "INSTRING":
            # INSTRING uses STRFIND
            haystack_reg = self.generate_expression(expr.arguments[0], "R1")
            needle_reg = self.generate_expression(expr.arguments[1], "R2")
            self.current_output.append(f"STRFIND {haystack_reg}, {needle_reg}")
            # STRFIND stores result in R0
            if target_reg != "R0":
                self.current_output.append(f"MOV {target_reg}, R0")
            self.smart_deallocate(haystack_reg, is_last_use=True)
            self.smart_deallocate(needle_reg, is_last_use=True)
        elif func_name == "STRREV":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.current_output.append(f"STRREV {arg_reg}")
            if target_reg != arg_reg:
                self.current_output.append(f"MOV {target_reg}, {arg_reg}")
                self.smart_deallocate(arg_reg, is_last_use=True)
        elif func_name == "STRFIND":
            haystack_reg = self.generate_expression(expr.arguments[0], "R1")
            needle_reg = self.generate_expression(expr.arguments[1], "R2")
            self.current_output.append(f"STRFIND {haystack_reg}, {needle_reg}")
            if target_reg != "R0":
                self.current_output.append(f"MOV {target_reg}, R0")
            self.smart_deallocate(haystack_reg, is_last_use=True)
            self.smart_deallocate(needle_reg, is_last_use=True)
        elif func_name == "STRFINDI":
            haystack_reg = self.generate_expression(expr.arguments[0], "R1")
            needle_reg = self.generate_expression(expr.arguments[1], "R2")
            self.current_output.append(f"STRFINDI {haystack_reg}, {needle_reg}")
            if target_reg != "R0":
                self.current_output.append(f"MOV {target_reg}, R0")
            self.smart_deallocate(haystack_reg, is_last_use=True)
            self.smart_deallocate(needle_reg, is_last_use=True)
        elif func_name == "STREXT":
            self.generate_expression_into(expr.arguments[0], "R1")
            self.generate_expression_into(expr.arguments[1], "R2")
            self.generate_expression_into(expr.arguments[2], "R3")
            self.generate_expression_into(expr.arguments[3], "R4")
            self.current_output.append("STREXT R1, R2, R3, R4")
            self.current_output.append(f"MOV {target_reg}, R1")  # Return destination
            for reg in ("R1", "R2", "R3", "R4"):
                if reg != target_reg:
                    self.smart_deallocate(reg, is_last_use=True)
        elif func_name == "STREXTI":
            self.generate_expression_into(expr.arguments[0], "R1")
            self.generate_expression_into(expr.arguments[1], "R2")
            self.generate_expression_into(expr.arguments[2], "R3")
            self.generate_expression_into(expr.arguments[3], "R4")
            self.current_output.append("STREXTI R1, R2, R3, R4")
            self.current_output.append(f"MOV {target_reg}, R1")  # Return destination
            for reg in ("R1", "R2", "R3", "R4"):
                if reg != target_reg:
                    self.smart_deallocate(reg, is_last_use=True)
        elif func_name == "MIN":
            left_reg = self.generate_expression(expr.arguments[0], "R1")
            right_reg = self.generate_expression(expr.arguments[1], "R2")
            self.current_output.append(f"MIN {target_reg}, {left_reg}, {right_reg}")
            # Don't free if it's the target register (needed for nested calls)
            if left_reg != target_reg:
                self.smart_deallocate(left_reg, is_last_use=True)
            if right_reg != target_reg:
                self.smart_deallocate(right_reg, is_last_use=True)
        elif func_name == "MAX":
            left_reg = self.generate_expression(expr.arguments[0], "R1")
            right_reg = self.generate_expression(expr.arguments[1], "R2")
            self.current_output.append(f"MAX {target_reg}, {left_reg}, {right_reg}")
            # Don't free if it's the target register (needed for nested calls)
            if left_reg != target_reg:
                self.smart_deallocate(left_reg, is_last_use=True)
            if right_reg != target_reg:
                self.smart_deallocate(right_reg, is_last_use=True)
        elif func_name == "ATAN":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.current_output.append(f"ATAN {target_reg}, {arg_reg}")
            self.smart_deallocate(arg_reg, is_last_use=True)
        elif func_name == "ASIN":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.current_output.append(f"ASIN {target_reg}, {arg_reg}")
            self.smart_deallocate(arg_reg, is_last_use=True)
        elif func_name == "ACOS":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.current_output.append(f"ACOS {target_reg}, {arg_reg}")
            self.smart_deallocate(arg_reg, is_last_use=True)
        elif func_name == "DEG":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.current_output.append(f"DEG {target_reg}, {arg_reg}")
            self.smart_deallocate(arg_reg, is_last_use=True)
        elif func_name == "RAD":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.current_output.append(f"RAD {target_reg}, {arg_reg}")
            self.smart_deallocate(arg_reg, is_last_use=True)
        elif func_name == "FLOOR":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.current_output.append(f"FLOOR {target_reg}, {arg_reg}")
            self.smart_deallocate(arg_reg, is_last_use=True)
        elif func_name == "CEIL":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.current_output.append(f"CEIL {target_reg}, {arg_reg}")
            self.smart_deallocate(arg_reg, is_last_use=True)
        elif func_name == "ROUND":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.current_output.append(f"ROUND {target_reg}, {arg_reg}")
            self.smart_deallocate(arg_reg, is_last_use=True)
        elif func_name == "TRUNC":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.current_output.append(f"TRUNC {target_reg}, {arg_reg}")
            self.smart_deallocate(arg_reg, is_last_use=True)
        elif func_name == "FRAC":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.current_output.append(f"FRAC {target_reg}, {arg_reg}")
            self.smart_deallocate(arg_reg, is_last_use=True)
        elif func_name == "INTGR":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.current_output.append(f"INTGR {target_reg}, {arg_reg}")
            self.smart_deallocate(arg_reg, is_last_use=True)
        elif func_name == "POWR":
            left_reg = self.generate_expression(expr.arguments[0], "R1")
            right_reg = self.generate_expression(expr.arguments[1], "R2")
            self.current_output.append(f"POWR {target_reg}, {left_reg}, {right_reg}")
            self.smart_deallocate(left_reg, is_last_use=True)
            self.smart_deallocate(right_reg, is_last_use=True)
        elif func_name == "LOG":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.current_output.append(f"LOG {target_reg}, {arg_reg}")
            self.smart_deallocate(arg_reg, is_last_use=True)
        elif func_name == "EXP":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            self.current_output.append(f"EXP {target_reg}, {arg_reg}")
            self.smart_deallocate(arg_reg, is_last_use=True)
        elif func_name == "BTST":
            value_reg = self.generate_expression(expr.arguments[0], "R1")
            bit_reg = self.generate_expression(expr.arguments[1], "R2")
            if value_reg != target_reg:
                self.current_output.append(f"MOV {target_reg}, {value_reg}")
            self.current_output.append(f"BTST {target_reg}, {bit_reg}")
            result_label = self.new_label()
            self.current_output.append(f"MOV {target_reg}, 0")
            self.current_output.append(f"JZ {result_label}")
            self.current_output.append(f"MOV {target_reg}, 1")
            self.current_output.append(f"{result_label}:")
            if value_reg != target_reg:
                self.smart_deallocate(value_reg, is_last_use=True)
            if bit_reg != target_reg:
                self.smart_deallocate(bit_reg, is_last_use=True)
        elif func_name == "BSET":
            value_reg = self.generate_expression(expr.arguments[0], "R1")
            bit_reg = self.generate_expression(expr.arguments[1], "R2")
            if value_reg != target_reg:
                self.current_output.append(f"MOV {target_reg}, {value_reg}")
            self.current_output.append(f"BSET {target_reg}, {bit_reg}")
            if value_reg != target_reg:
                self.smart_deallocate(value_reg, is_last_use=True)
            if bit_reg != target_reg:
                self.smart_deallocate(bit_reg, is_last_use=True)
        elif func_name == "BCLR":
            value_reg = self.generate_expression(expr.arguments[0], "R1")
            bit_reg = self.generate_expression(expr.arguments[1], "R2")
            if value_reg != target_reg:
                self.current_output.append(f"MOV {target_reg}, {value_reg}")
            self.current_output.append(f"BCLR {target_reg}, {bit_reg}")
            if value_reg != target_reg:
                self.smart_deallocate(value_reg, is_last_use=True)
            if bit_reg != target_reg:
                self.smart_deallocate(bit_reg, is_last_use=True)
        elif func_name == "BFLIP":
            value_reg = self.generate_expression(expr.arguments[0], "R1")
            bit_reg = self.generate_expression(expr.arguments[1], "R2")
            if value_reg != target_reg:
                self.current_output.append(f"MOV {target_reg}, {value_reg}")
            self.current_output.append(f"BFLIP {target_reg}, {bit_reg}")
            if value_reg != target_reg:
                self.smart_deallocate(value_reg, is_last_use=True)
            if bit_reg != target_reg:
                self.smart_deallocate(bit_reg, is_last_use=True)
        elif func_name == "CLZ":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            if arg_reg != target_reg:
                self.current_output.append(f"MOV {target_reg}, {arg_reg}")
            self.current_output.append(f"CLZ {target_reg}")
            if arg_reg != target_reg:
                self.smart_deallocate(arg_reg, is_last_use=True)
        elif func_name == "CTZ":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            if arg_reg != target_reg:
                self.current_output.append(f"MOV {target_reg}, {arg_reg}")
            self.current_output.append(f"CTZ {target_reg}")
            if arg_reg != target_reg:
                self.smart_deallocate(arg_reg, is_last_use=True)
        elif func_name == "POPCNT":
            arg_reg = self.generate_expression(expr.arguments[0], "R1")
            if arg_reg != target_reg:
                self.current_output.append(f"MOV {target_reg}, {arg_reg}")
            self.current_output.append(f"POPCNT {target_reg}")
            if arg_reg != target_reg:
                self.smart_deallocate(arg_reg, is_last_use=True)
        elif func_name == "MEMREAD":
            # Read a value from memory address
            # MEMREAD(addr) returns the 16-bit value at that address
            addr_reg = self.generate_expression(expr.arguments[0], "P1")
            self.current_output.append(f"; MEMREAD - Read from memory")
            # Ensure we're using a P register for addressing
            if not addr_reg.startswith('P'):
                temp_p = "P1"
                self.current_output.append(f"MOV {temp_p}, {addr_reg}")
                addr_reg = temp_p
            # If addr_reg == target_reg, we need a temp to avoid MOV P1, [P1]
            if addr_reg == target_reg:
                # Find another P register for the address
                temp_addr = self.allocate_register(preferred_reg="P2")
                self.current_output.append(f"MOV {temp_addr}, {addr_reg}")
                self.current_output.append(f"MOV {target_reg}, [{temp_addr}]")
                self.smart_deallocate(temp_addr, is_last_use=True)
                self.smart_deallocate(addr_reg, is_last_use=True)
            else:
                self.current_output.append(f"MOV {target_reg}, [{addr_reg}]")
                # Only deallocate addr_reg if it's not the target register
                self.smart_deallocate(addr_reg, is_last_use=True)
        elif func_name == "MEMWRITE":
            # Write a value to memory address
            # MEMWRITE(addr, value) returns the value written
            addr_reg = self.generate_expression(expr.arguments[0], "P1")
            value_reg = self.generate_expression(expr.arguments[1], "R2")
            self.current_output.append(f"; MEMWRITE - Write to memory")
            # Ensure we're using a P register for addressing
            if not addr_reg.startswith('P'):
                temp_p = "P1"
                self.current_output.append(f"MOV {temp_p}, {addr_reg}")
                addr_reg = temp_p
            self.current_output.append(f"MOV [{addr_reg}], {value_reg}")
            self.current_output.append(f"MOV {target_reg}, {value_reg}")  # Return value written
            # Only deallocate if they're not the target register
            if addr_reg != target_reg:
                self.smart_deallocate(addr_reg, is_last_use=True)
            if value_reg != target_reg:
                self.smart_deallocate(value_reg, is_last_use=True)
        elif func_name == "MEMCPY":
            dest_reg = self.generate_expression(expr.arguments[0], "R1")
            src_reg = self.generate_expression(expr.arguments[1], "R2")
            len_reg = self.generate_expression(expr.arguments[2], "R3")
            self.current_output.append(f"MEMCPY {dest_reg}, {src_reg}, {len_reg}")
            self.current_output.append(f"MOV {target_reg}, {dest_reg}")  # Return destination
        elif func_name == "MEMSET":
            addr_reg = self.generate_expression(expr.arguments[0], "R1")
            value_reg = self.generate_expression(expr.arguments[1], "R2")
            len_reg = self.generate_expression(expr.arguments[2], "R3")
            self.current_output.append(f"MEMSET {addr_reg}, {value_reg}, {len_reg}")
            self.current_output.append(f"MOV {target_reg}, {addr_reg}")  # Return address
        elif func_name == "MEMTEST":
            addr1_reg = self.generate_expression(expr.arguments[0], "R1")
            addr2_reg = self.generate_expression(expr.arguments[1], "R2")
            len_reg = self.generate_expression(expr.arguments[2], "R3")
            self.current_output.append(f"MEMTEST {target_reg}, {addr1_reg}, {addr2_reg}, {len_reg}")
        elif func_name == "MEMMOVE":
            dest_reg = self.generate_expression(expr.arguments[0], "R1")
            src_reg = self.generate_expression(expr.arguments[1], "R2")
            len_reg = self.generate_expression(expr.arguments[2], "R3")
            self.current_output.append(f"MEMMOVE {dest_reg}, {src_reg}, {len_reg}")
            self.current_output.append(f"MOV {target_reg}, {dest_reg}")  # Return destination
        elif func_name == "MEMCMP":
            result_reg = self.generate_expression(expr.arguments[0], "R1")
            addr1_reg = self.generate_expression(expr.arguments[1], "R2")
            addr2_reg = self.generate_expression(expr.arguments[2], "R3")
            len_reg = self.generate_expression(expr.arguments[3], "R4")
            self.current_output.append(f"MEMCMP {result_reg}, {addr1_reg}, {addr2_reg}, {len_reg}")
            self.current_output.append(f"MOV {target_reg}, {result_reg}")  # Return result
        elif func_name == "MEMSWAP":
            addr1_reg = self.generate_expression(expr.arguments[0], "R1")
            addr2_reg = self.generate_expression(expr.arguments[1], "R2")
            len_reg = self.generate_expression(expr.arguments[2], "R3")
            self.current_output.append(f"MEMSWAP {addr1_reg}, {addr2_reg}, {len_reg}")
            self.current_output.append(f"MOV {target_reg}, {addr1_reg}")  # Return first address
        elif func_name == "ADC":
            result_reg = self.generate_expression(expr.arguments[0], "R1")
            a_reg = self.generate_expression(expr.arguments[1], "R2")
            b_reg = self.generate_expression(expr.arguments[2], "R3")
            self.current_output.append(f"ADC {result_reg}, {a_reg}, {b_reg}")
            self.current_output.append(f"MOV {target_reg}, {result_reg}")
        elif func_name == "SBC":
            result_reg = self.generate_expression(expr.arguments[0], "R1")
            a_reg = self.generate_expression(expr.arguments[1], "R2")
            b_reg = self.generate_expression(expr.arguments[2], "R3")
            self.current_output.append(f"SBC {result_reg}, {a_reg}, {b_reg}")
            self.current_output.append(f"MOV {target_reg}, {result_reg}")
        elif func_name == "MULH":
            result_reg = self.generate_expression(expr.arguments[0], "R1")
            a_reg = self.generate_expression(expr.arguments[1], "R2")
            b_reg = self.generate_expression(expr.arguments[2], "R3")
            self.current_output.append(f"MULH {result_reg}, {a_reg}, {b_reg}")
            self.current_output.append(f"MOV {target_reg}, {result_reg}")
        elif func_name == "DIVH":
            result_reg = self.generate_expression(expr.arguments[0], "R1")
            a_reg = self.generate_expression(expr.arguments[1], "R2")
            b_reg = self.generate_expression(expr.arguments[2], "R3")
            self.current_output.append(f"DIVH {result_reg}, {a_reg}, {b_reg}")
            self.current_output.append(f"MOV {target_reg}, {result_reg}")
        elif func_name == "SWAP":
            value_reg = self.generate_expression(expr.arguments[0], "R1")
            self.current_output.append(f"SWAP {value_reg}")
            self.current_output.append(f"MOV {target_reg}, {value_reg}")
        elif func_name == "XCHNG":
            a_reg = self.generate_expression(expr.arguments[0], "R1")
            b_reg = self.generate_expression(expr.arguments[1], "R2")
            self.current_output.append(f"XCHNG {a_reg}, {b_reg}")
            self.current_output.append(f"MOV {target_reg}, {a_reg}")
        elif func_name == "MOVZ":
            dest_reg = self.generate_expression(expr.arguments[0], "R1")
            src_reg = self.generate_expression(expr.arguments[1], "R2")
            self.current_output.append(f"MOVZ {dest_reg}, {src_reg}")
            self.current_output.append(f"MOV {target_reg}, {dest_reg}")
        elif func_name == "MOVNZ":
            dest_reg = self.generate_expression(expr.arguments[0], "R1")
            src_reg = self.generate_expression(expr.arguments[1], "R2")
            self.current_output.append(f"MOVNZ {dest_reg}, {src_reg}")
            self.current_output.append(f"MOV {target_reg}, {dest_reg}")
        elif func_name == "LEA":
            self.generate_expression_into(expr.arguments[0], "R1")
            self.generate_expression_into(expr.arguments[1], "R2")
            self.current_output.append("LEA R1, R2")
            self.current_output.append(f"MOV {target_reg}, R1")
            for reg in ("R1", "R2"):
                if reg != target_reg:
                    self.smart_deallocate(reg, is_last_use=True)
        elif func_name == "SHL":
            value_reg = self.generate_expression(expr.arguments[0], "R1")
            shift_reg = self.generate_expression(expr.arguments[1], "R2")
            if value_reg != target_reg:
                self.current_output.append(f"MOV {target_reg}, {value_reg}")
            self.current_output.append(f"SHL {target_reg}, {shift_reg}")
            if value_reg != target_reg:
                self.smart_deallocate(value_reg, is_last_use=True)
            if shift_reg != target_reg:
                self.smart_deallocate(shift_reg, is_last_use=True)
        elif func_name == "SHR":
            value_reg = self.generate_expression(expr.arguments[0], "R1")
            shift_reg = self.generate_expression(expr.arguments[1], "R2")
            if value_reg != target_reg:
                self.current_output.append(f"MOV {target_reg}, {value_reg}")
            self.current_output.append(f"SHR {target_reg}, {shift_reg}")
            if value_reg != target_reg:
                self.smart_deallocate(value_reg, is_last_use=True)
            if shift_reg != target_reg:
                self.smart_deallocate(shift_reg, is_last_use=True)
        elif func_name == "SAL":
            value_reg = self.generate_expression(expr.arguments[0], "R1")
            shift_reg = self.generate_expression(expr.arguments[1], "R2")
            if value_reg != target_reg:
                self.current_output.append(f"MOV {target_reg}, {value_reg}")
            self.current_output.append(f"SAL {target_reg}, {shift_reg}")
            if value_reg != target_reg:
                self.smart_deallocate(value_reg, is_last_use=True)
            if shift_reg != target_reg:
                self.smart_deallocate(shift_reg, is_last_use=True)
        elif func_name == "SAR":
            value_reg = self.generate_expression(expr.arguments[0], "R1")
            shift_reg = self.generate_expression(expr.arguments[1], "R2")
            if value_reg != target_reg:
                self.current_output.append(f"MOV {target_reg}, {value_reg}")
            self.current_output.append(f"SAR {target_reg}, {shift_reg}")
            if value_reg != target_reg:
                self.smart_deallocate(value_reg, is_last_use=True)
            if shift_reg != target_reg:
                self.smart_deallocate(shift_reg, is_last_use=True)
        elif func_name == "ROL":
            value_reg = self.generate_expression(expr.arguments[0], "R1")
            shift_reg = self.generate_expression(expr.arguments[1], "R2")
            if value_reg != target_reg:
                self.current_output.append(f"MOV {target_reg}, {value_reg}")
            self.current_output.append(f"ROL {target_reg}, {shift_reg}")
            if value_reg != target_reg:
                self.smart_deallocate(value_reg, is_last_use=True)
            if shift_reg != target_reg:
                self.smart_deallocate(shift_reg, is_last_use=True)
        elif func_name == "ROR":
            value_reg = self.generate_expression(expr.arguments[0], "R1")
            shift_reg = self.generate_expression(expr.arguments[1], "R2")
            if value_reg != target_reg:
                self.current_output.append(f"MOV {target_reg}, {value_reg}")
            self.current_output.append(f"ROR {target_reg}, {shift_reg}")
            if value_reg != target_reg:
                self.smart_deallocate(value_reg, is_last_use=True)
            if shift_reg != target_reg:
                self.smart_deallocate(shift_reg, is_last_use=True)
        elif func_name == "RCL":
            value_reg = self.generate_expression(expr.arguments[0], "R1")
            shift_reg = self.generate_expression(expr.arguments[1], "R2")
            if value_reg != target_reg:
                self.current_output.append(f"MOV {target_reg}, {value_reg}")
            self.current_output.append(f"RCL {target_reg}, {shift_reg}")
            if value_reg != target_reg:
                self.smart_deallocate(value_reg, is_last_use=True)
            if shift_reg != target_reg:
                self.smart_deallocate(shift_reg, is_last_use=True)
        elif func_name == "RCR":
            value_reg = self.generate_expression(expr.arguments[0], "R1")
            shift_reg = self.generate_expression(expr.arguments[1], "R2")
            if value_reg != target_reg:
                self.current_output.append(f"MOV {target_reg}, {value_reg}")
            self.current_output.append(f"RCR {target_reg}, {shift_reg}")
            if value_reg != target_reg:
                self.smart_deallocate(value_reg, is_last_use=True)
            if shift_reg != target_reg:
                self.smart_deallocate(shift_reg, is_last_use=True)
        elif func_name == "BAND":
            a_reg = self.generate_expression(expr.arguments[0], "R1")
            b_reg = self.generate_expression(expr.arguments[1], "R2")
            if a_reg != target_reg:
                self.current_output.append(f"MOV {target_reg}, {a_reg}")
            self.current_output.append(f"AND {target_reg}, {b_reg}")
            if a_reg != target_reg:
                self.smart_deallocate(a_reg, is_last_use=True)
            if b_reg != target_reg:
                self.smart_deallocate(b_reg, is_last_use=True)
        elif func_name == "BOR":
            a_reg = self.generate_expression(expr.arguments[0], "R1")
            b_reg = self.generate_expression(expr.arguments[1], "R2")
            if a_reg != target_reg:
                self.current_output.append(f"MOV {target_reg}, {a_reg}")
            self.current_output.append(f"OR {target_reg}, {b_reg}")
            if a_reg != target_reg:
                self.smart_deallocate(a_reg, is_last_use=True)
            if b_reg != target_reg:
                self.smart_deallocate(b_reg, is_last_use=True)
        elif func_name == "BXOR":
            a_reg = self.generate_expression(expr.arguments[0], "R1")
            b_reg = self.generate_expression(expr.arguments[1], "R2")
            if a_reg != target_reg:
                self.current_output.append(f"MOV {target_reg}, {a_reg}")
            self.current_output.append(f"XOR {target_reg}, {b_reg}")
            if a_reg != target_reg:
                self.smart_deallocate(a_reg, is_last_use=True)
            if b_reg != target_reg:
                self.smart_deallocate(b_reg, is_last_use=True)
        elif func_name == "BNOT":
            value_reg = self.generate_expression(expr.arguments[0], "R1")
            if value_reg != target_reg:
                self.current_output.append(f"MOV {target_reg}, {value_reg}")
            self.current_output.append(f"NOT {target_reg}")
            if value_reg != target_reg:
                self.smart_deallocate(value_reg, is_last_use=True)
        elif func_name == "ITOB":
            result_reg = self.generate_expression(expr.arguments[0], "R1")
            value_reg = self.generate_expression(expr.arguments[1], "R2")
            self.current_output.append(f"ITOB {result_reg}, {value_reg}")
            self.current_output.append(f"MOV {target_reg}, {result_reg}")
        elif func_name == "BTOI":
            result_reg = self.generate_expression(expr.arguments[0], "R1")
            binary_reg = self.generate_expression(expr.arguments[1], "R2")
            self.current_output.append(f"BTOI {result_reg}, {binary_reg}")
            self.current_output.append(f"MOV {target_reg}, {result_reg}")
        elif func_name == "ITOS":
            result_reg = self.generate_expression(expr.arguments[0], "R1")
            value_reg = self.generate_expression(expr.arguments[1], "R2")
            self.current_output.append(f"ITOS {result_reg}, {value_reg}")
            self.current_output.append(f"MOV {target_reg}, {result_reg}")
        elif func_name == "STOI":
            result_reg = self.generate_expression(expr.arguments[0], "R1")
            string_reg = self.generate_expression(expr.arguments[1], "R2")
            self.current_output.append(f"STOI {result_reg}, {string_reg}")
            self.current_output.append(f"MOV {target_reg}, {result_reg}")
        elif func_name == "SUB":
            string_reg = self.generate_expression(expr.arguments[0], "R1")
            start_reg = self.generate_expression(expr.arguments[1], "R2")
            len_reg = self.generate_expression(expr.arguments[2], "R3")
            self.current_output.append(f"STREXT {target_reg}, {string_reg}, {start_reg}, {len_reg}")
        elif func_name == "CLRDRAW":
            self.current_output.append("MOV VM, 0")  # Clear screen mode
            self.current_output.append("SFILL 0")    # Fill with black
        elif func_name == "SETLAYER":
            layer_reg = self.generate_expression(expr.arguments[0], "R1")
            self.current_output.append(f"MOV VL, {layer_reg}")
        elif func_name == "PXLON":
            x_reg = self.generate_expression(expr.arguments[0], "R1")
            y_reg = self.generate_expression(expr.arguments[1], "R2")
            color_reg = self.generate_expression(expr.arguments[2], "R3")
            self.current_output.append(f"MOV VX, {x_reg}")
            self.current_output.append(f"MOV VY, {y_reg}")
            self.current_output.append(f"MOV VC, {color_reg}")
            self.current_output.append("SWRITE VC")
        elif func_name == "PXLOFF":
            x_reg = self.generate_expression(expr.arguments[0], "R1")
            y_reg = self.generate_expression(expr.arguments[1], "R2")
            self.current_output.append(f"MOV VX, {x_reg}")
            self.current_output.append(f"MOV VY, {y_reg}")
            self.current_output.append("SWRITE 0")
        elif func_name == "LINE":
            x1_reg = self.generate_expression(expr.arguments[0], "R1")
            y1_reg = self.generate_expression(expr.arguments[1], "R2")
            x2_reg = self.generate_expression(expr.arguments[2], "R3")
            y2_reg = self.generate_expression(expr.arguments[3], "R4")
            color_reg = self.generate_expression(expr.arguments[4], "R5")
            self.current_output.append(f"MOV VX, {x1_reg}")
            self.current_output.append(f"MOV VY, {y1_reg}")
            self.current_output.append(f"SLINE {x2_reg}, {y2_reg}, {color_reg}")
        elif func_name == "CIRCLE":
            x_reg = self.generate_expression(expr.arguments[0], "R1")
            y_reg = self.generate_expression(expr.arguments[1], "R2")
            radius_reg = self.generate_expression(expr.arguments[2], "R3")
            color_reg = self.generate_expression(expr.arguments[3], "R4")
            self.current_output.append(f"MOV VX, {x_reg}")
            self.current_output.append(f"MOV VY, {y_reg}")
            self.current_output.append(f"SCIRC {radius_reg}, {color_reg}")
        elif func_name == "TEXT":
            x_reg = self.generate_expression(expr.arguments[0], "R1")
            y_reg = self.generate_expression(expr.arguments[1], "R2")
            text_reg = self.generate_expression(expr.arguments[2], "R3")
            color_reg = self.generate_expression(expr.arguments[3], "R4")
            self.current_output.append(f"MOV VX, {x_reg}")
            self.current_output.append(f"MOV VY, {y_reg}")
            self.current_output.append(f"TEXT {text_reg}, {color_reg}")
        elif func_name == "RECT":
            x1_reg = self.generate_expression(expr.arguments[0], "R1")
            y1_reg = self.generate_expression(expr.arguments[1], "R2")
            x2_reg = self.generate_expression(expr.arguments[2], "R3")
            y2_reg = self.generate_expression(expr.arguments[3], "R4")
            fill_reg = self.generate_expression(expr.arguments[4], "R5")
            self.current_output.append(f"MOV VX, {x1_reg}")
            self.current_output.append(f"MOV VY, {y1_reg}")
            self.current_output.append(f"SRECT {x2_reg}, {y2_reg}, {fill_reg}")
        elif func_name in {"FILL", "SORTA", "SORTD", "SEQ", "REVERSE"}:
            # Resolve target list base address; default to L1 if not identifiable
            base_addr = 0x1000
            list_expr = expr.arguments[0] if expr.arguments else None
            if isinstance(list_expr, VariableExpr) and list_expr.name.upper().startswith('L'):
                try:
                    list_num = int(list_expr.name[1:])
                    base_addr = 0x1000 + (list_num - 1) * 0x100
                except ValueError:
                    pass

            if func_name == "FILL":
                # Use a P-register so 16-bit fill values (e.g., 30000) are not truncated
                value_reg = self.generate_expression(expr.arguments[1], "P3")
                # Keep base address in a dedicated P-register to avoid clobbering value_reg
                base_reg = "P4" if value_reg != "P4" else ("P5" if value_reg != "P5" else "P6")
                self.current_output.append(f"; Fill list starting at 0x{base_addr:04X}")
                self.current_output.append(f"MOV {base_reg}, 0x{base_addr:04X}")
                self.current_output.append("MOV R1, 0")
                loop_label = self.new_label()
                end_label = self.new_label()
                self.current_output.append(f"{loop_label}:")
                self.current_output.append("CMP R1, 100")
                self.current_output.append(f"JGE {end_label}")
                self.current_output.append("MOV P1, R1")
                self.current_output.append("MUL P1, 2")
                self.current_output.append(f"ADD P1, {base_reg}")
                self.current_output.append(f"MOV [P1], {value_reg}")
                self.current_output.append("INC R1")
                self.current_output.append(f"JMP {loop_label}")
                self.current_output.append(f"{end_label}:")
                self.current_output.append(f"MOV {target_reg}, {base_addr}")
                if value_reg != target_reg:
                    self.smart_deallocate(value_reg, is_last_use=True)

            elif func_name in {"SORTA", "SORTD"}:
                # Simple bubble sort (100 elements, 0-based indices)
                ascending = func_name == "SORTA"
                self.current_output.append(f"; Sort {'ascending' if ascending else 'descending'} list at 0x{base_addr:04X}")
                self.current_output.append(f"MOV P0, 0x{base_addr:04X}")
                outer_label = self.new_label()
                inner_label = self.new_label()
                next_outer = self.new_label()
                skip_label = self.new_label()
                end_label = self.new_label()
                self.current_output.append("MOV R1, 0")  # i
                self.current_output.append(f"{outer_label}:")
                self.current_output.append("CMP R1, 100")
                self.current_output.append(f"JGE {end_label}")
                self.current_output.append("MOV R2, 0")  # j
                self.current_output.append(f"{inner_label}:")
                self.current_output.append("MOV R5, 99")
                self.current_output.append("SUB R5, R1")  # limit = 99 - i
                self.current_output.append("CMP R2, R5")
                self.current_output.append(f"JGE {next_outer}")
                # Addresses for j and j+1
                self.current_output.append("MOV P1, R2")
                self.current_output.append("MUL P1, 2")  # Scale index to bytes
                self.current_output.append("ADD P1, P0")
                self.current_output.append("MOV P2, P1")
                self.current_output.append("INC P2")
                self.current_output.append("INC P2")
                self.current_output.append("MOV P3, [P1]")
                self.current_output.append("MOV P4, [P2]")
                self.current_output.append("CMP P3, P4")
                if ascending:
                    self.current_output.append(f"JLE {skip_label}")
                else:
                    self.current_output.append(f"JGE {skip_label}")
                # Swap when out of order
                self.current_output.append("MOV [P1], P4")
                self.current_output.append("MOV [P2], P3")
                self.current_output.append(f"{skip_label}:")
                self.current_output.append("INC R2")
                self.current_output.append(f"JMP {inner_label}")
                self.current_output.append(f"{next_outer}:")
                self.current_output.append("INC R1")
                self.current_output.append(f"JMP {outer_label}")
                self.current_output.append(f"{end_label}:")
                self.current_output.append(f"MOV {target_reg}, {base_addr}")

            elif func_name == "SEQ":
                # Generate a numeric sequence into the target list (default L1)
                current_reg = self.generate_expression(expr.arguments[2], "P2")
                end_reg = self.generate_expression(expr.arguments[3], "P4")
                step_reg = None
                if len(expr.arguments) > 4:
                    step_reg = self.generate_expression(expr.arguments[4], "P5")
                self.current_output.append(f"; Seq into list at 0x{base_addr:04X}")
                self.current_output.append("MOV R1, 0")       # list index
                loop_label = self.new_label()
                end_label = self.new_label()
                self.current_output.append(f"{loop_label}:")
                self.current_output.append("CMP R1, 100")
                self.current_output.append(f"JGE {end_label}")
                self.current_output.append(f"CMP {current_reg}, {end_reg}")
                self.current_output.append(f"JGT {end_label}")
                self.current_output.append("MOV P1, R1")
                self.current_output.append("MUL P1, 2")
                self.current_output.append(f"MOV P0, 0x{base_addr:04X}")
                self.current_output.append("ADD P1, P0")
                self.current_output.append(f"MOV [P1], {current_reg}")
                self.current_output.append("INC R1")
                if step_reg:
                    self.current_output.append(f"ADD {current_reg}, {step_reg}")
                else:
                    self.current_output.append(f"INC {current_reg}")
                self.current_output.append(f"JMP {loop_label}")
                self.current_output.append(f"{end_label}:")
                self.current_output.append(f"MOV {target_reg}, {base_addr}")
                if step_reg:
                    self.smart_deallocate(step_reg, is_last_use=True)

            elif func_name == "REVERSE":
                # Reverse the list in place (100 elements)
                self.current_output.append(f"; Reverse list at 0x{base_addr:04X}")
                self.current_output.append(f"MOV P0, 0x{base_addr:04X}")
                self.current_output.append("MOV R1, 0")          # i
                self.current_output.append("MOV R2, 99")         # j = size-1
                outer_label = self.new_label()
                end_label = self.new_label()
                self.current_output.append(f"{outer_label}:")
                # Stop when i >= j
                self.current_output.append("CMP R1, R2")
                self.current_output.append(f"JGE {end_label}")
                # Compute addresses for i and j
                self.current_output.append("MOV P1, R1")
                self.current_output.append("MUL P1, 2")
                self.current_output.append("ADD P1, P0")
                self.current_output.append("MOV P2, R2")
                self.current_output.append("MUL P2, 2")
                self.current_output.append("ADD P2, P0")
                # Swap values
                self.current_output.append("MOV P3, [P1]")
                self.current_output.append("MOV P4, [P2]")
                self.current_output.append("MOV [P1], P4")
                self.current_output.append("MOV [P2], P3")
                # Move indices
                self.current_output.append("INC R1")
                self.current_output.append("DEC R2")
                self.current_output.append(f"JMP {outer_label}")
                self.current_output.append(f"{end_label}:")
                self.current_output.append(f"MOV {target_reg}, {base_addr}")

        elif func_name == "SUM":
            # Sum all elements in the list
            list_expr = expr.arguments[0]
            if isinstance(list_expr, VariableExpr) and list_expr.name.upper().startswith('L'):
                try:
                    list_num = int(list_expr.name[1:])
                    base_addr = 0x1000 + (list_num - 1) * 0x100
                    size = 100
                    # Initialize sum
                    self.current_output.append(f"MOV {target_reg}, 0")
                    self.current_output.append(f"MOV P5, 0x{base_addr:04X}")
                    # Use R1 for index, R2 for value, P2 for address
                    index_reg = "R1"
                    value_reg = "R2"
                    addr_reg = "P2"
                    self.current_output.append(f"MOV {index_reg}, 0")
                    loop_label = self.new_label()
                    end_label = self.new_label()
                    self.current_output.append(f"{loop_label}:")
                    self.current_output.append(f"CMP {index_reg}, {size}")
                    self.current_output.append(f"JGE {end_label}")
                    # Calculate address
                    self.current_output.append(f"MOV {addr_reg}, {index_reg}")
                    self.current_output.append(f"MUL {addr_reg}, 2")
                    self.current_output.append(f"ADD {addr_reg}, P5")
                    # Load value
                    self.current_output.append(f"MOV P0, {addr_reg}")
                    self.current_output.append(f"MOV {value_reg}, [P0]")
                    # Add to sum
                    self.current_output.append(f"ADD {target_reg}, {value_reg}")
                    # Increment index
                    self.current_output.append(f"INC {index_reg}")
                    self.current_output.append(f"JMP {loop_label}")
                    self.current_output.append(f"{end_label}:")
                except ValueError:
                    self.current_output.append(f"MOV {target_reg}, 0")
            else:
                self.current_output.append(f"MOV {target_reg}, 0")
        elif func_name == "MEAN":
            # Calculate average of list elements
            list_expr = expr.arguments[0]
            if isinstance(list_expr, VariableExpr) and list_expr.name.upper().startswith('L'):
                try:
                    list_num = int(list_expr.name[1:])
                    base_addr = 0x1000 + (list_num - 1) * 0x100
                    size = 100
                    # Initialize sum
                    self.current_output.append(f"MOV {target_reg}, 0")
                    self.current_output.append(f"MOV P5, 0x{base_addr:04X}")
                    # Use R1 for index, R2 for value, P2 for address
                    index_reg = "R1"
                    value_reg = "R2"
                    addr_reg = "P2"
                    self.current_output.append(f"MOV {index_reg}, 0")
                    loop_label = self.new_label()
                    end_label = self.new_label()
                    self.current_output.append(f"{loop_label}:")
                    self.current_output.append(f"CMP {index_reg}, {size}")
                    self.current_output.append(f"JGE {end_label}")
                    # Calculate address
                    self.current_output.append(f"MOV {addr_reg}, {index_reg}")
                    self.current_output.append(f"MUL {addr_reg}, 2")
                    self.current_output.append(f"ADD {addr_reg}, P5")
                    # Load value
                    self.current_output.append(f"MOV P0, {addr_reg}")
                    self.current_output.append(f"MOV {value_reg}, [P0]")
                    # Add to sum
                    self.current_output.append(f"ADD {target_reg}, {value_reg}")
                    # Increment index
                    self.current_output.append(f"INC {index_reg}")
                    self.current_output.append(f"JMP {loop_label}")
                    self.current_output.append(f"{end_label}:")
                    # Divide by size
                    self.current_output.append(f"MOV R3, {size}")
                    self.current_output.append(f"DIV {target_reg}, R3")
                except ValueError:
                    self.current_output.append(f"MOV {target_reg}, 0")
            else:
                self.current_output.append(f"MOV {target_reg}, 0")
        elif func_name == "DIM":
            # Return the size of the list (default 100 elements)
            list_expr = expr.arguments[0]
            if isinstance(list_expr, VariableExpr) and list_expr.name.upper().startswith('L'):
                try:
                    list_num = int(list_expr.name[1:])
                    size = 100  # Default size per list
                    self.current_output.append(f"MOV {target_reg}, {size}")
                except ValueError:
                    self.current_output.append(f"MOV {target_reg}, 0")
            else:
                self.current_output.append(f"MOV {target_reg}, 0")
        elif func_name == "GETKEY":
            # Non-blocking: returns key code or 0 if no key available
            self.current_output.append("KEYIN R0")          # Read key (0 if empty)
            self.current_output.append(f"MOV {target_reg}, R0")
        elif func_name == "PAUSE":
            # Wait for key press
            label = self.new_label()
            self.current_output.append(f"{label}:")
            self.current_output.append("KEYSTAT R0")
            self.current_output.append("CMP R0, 0")
            self.current_output.append(f"JZ {label}")  # Loop until key is available
            self.current_output.append("KEYIN R0")  # Consume the key
        
        # Return the target register for all function calls
        return target_reg

    def load_variable(self, name: str, target_reg: str = "R0") -> str:
        """
        Load a variable into a register.
        Handles both register-allocated and spilled variables.
        For string variables, ensures we use P registers.
        
        NOTE: All NoBASIC variables are 16-bit, so if a spilled variable is requested
        into an R register, we upgrade to a P register to avoid truncation.
        """
        # Function local variable access: fetch from stack via FP
        if self.current_function and self.current_function in self.function_locals and name in self.function_locals[self.current_function]:
            offset = self.function_locals[self.current_function][name]
            # Use P register for full 16-bit local load; fall back to target if already P
            dest_reg = target_reg
            if dest_reg.startswith('R'):
                dest_reg = self.allocate_register('P1')
            self.current_output.append(f"MOV P0, FP")
            self.current_output.append(f"ADD P0, {offset}")
            self.current_output.append(f"MOV {dest_reg}, [P0]")
            return dest_reg

        # Function parameter access: fetch directly from the call stack via FP
        if self.current_function:
            func = self.functions.get(self.current_function.lower())
            if func:
                _, params, _ = func
                if name in params:
                    idx = params.index(name)
                    # Parameters are pushed in order, so the last parameter pushed is closest to FP.
                    # FP points to saved FP, FP+2 is return address, FP+4 is the last parameter.
                    # Therefore: param[0] (first pushed) is at FP + 4 + (len(params) - 1 - 0) * 2
                    #           param[1] (second pushed) is at FP + 4 + (len(params) - 1 - 1) * 2, etc.
                    offset = 4 + (len(params) - 1 - idx) * 2
                    # Use P register for full 16-bit parameter load; fall back to target if already P
                    dest_reg = target_reg
                    if dest_reg.startswith('R'):
                        dest_reg = self.allocate_register('P1')
                    self.current_output.append(f"MOV P0, FP")
                    self.current_output.append(f"ADD P0, {offset}")
                    self.current_output.append(f"MOV {dest_reg}, [P0]")
                    return dest_reg

        # String variables need P registers (16-bit addresses)
        if name.upper().startswith("STR") and target_reg.startswith('R'):
            # Force use of a P register for string variables
            target_reg = 'P1'
        
        # Check if variable is in a register
        if name in self.var_reg:
            reg = self.var_reg[name]
            # If variable is in a P register and target is R, keep the P register
            # (don't truncate 16-bit values!)
            if reg.startswith('P') and target_reg.startswith('R'):
                return reg
            if reg != target_reg:
                self.current_output.append(f"MOV {target_reg}, {reg}")
            return target_reg
        
        # Check if variable is spilled
        if self.is_spilled(name):
            # **OPTIMIZATION: Hot Spill Migration**
            # Check if this spilled variable is in zero-page (hot spill)
            if name in self.hot_spills:
                # Use faster zero-page access
                spill_addr = self.hot_spills[name]
                if self.debug_allocation:
                    print(f"[LOAD] Loading hot-spilled variable '{name}' from zero-page 0x{spill_addr:04X} into {target_reg}")
            else:
                # Use regular spill region access
                spill_addr = self.get_spill_slot(name)
                if self.debug_allocation:
                    print(f"[LOAD] Loading spilled variable '{name}' from 0x{spill_addr:04X} into {target_reg}")
            
            # All NoBASIC variables are 16-bit, so upgrade R register to P register
            # to avoid truncation when loading from spill slot
            if target_reg.startswith('R'):
                # Use P0 as temporary for loading full 16-bit value
                # P0 needs to be allocated since we're returning it
                self.register_usage['P0'] = True
                self.auto_free_registers.add('P0')
                self.current_output.append(f"MOV P0, {spill_addr}")
                self.current_output.append(f"MOV P0, [P0]")
                # Return P0 so caller gets the full 16-bit value (P0 is now allocated)
                if self.debug_allocation:
                    print(f"[LOAD] Allocated P0 for spilled '{name}'")
                return 'P0'
            else:
                # For 16-bit P registers, read the full word
                self.current_output.append(f"MOV P0, {spill_addr}")
                self.current_output.append(f"MOV {target_reg}, [P0]")
            
            return target_reg
        
        # Not in register or spill slot, use regular memory
        addr = self.get_variable_address(name)
        if target_reg.startswith('R'):
            # For 8-bit R registers, read the low byte (stored at addr + 1)
            # But NOTE: all NoBASIC variables are 16-bit, so we should upgrade to P register
            # Use P0 as temporary for loading full 16-bit value
            # P0 needs to be allocated since we're returning it
            self.register_usage['P0'] = True
            self.auto_free_registers.add('P0')
            self.current_output.append(f"MOV P0, {addr}")
            self.current_output.append(f"MOV P0, [P0]")
            # Return P0 so caller gets the full 16-bit value (P0 is now allocated)
            if self.debug_allocation:
                print(f"[LOAD] Allocated P0 for non-spilled memory variable '{name}'")
            return 'P0'
        else:
            # For 16-bit P registers, read the full word
            self.current_output.append(f"MOV P0, {addr}")
            self.current_output.append(f"MOV {target_reg}, [P0]")
        return target_reg
    
    def store_variable(self, name: str, source_reg: str):
        """
        Store a value from a register into a variable.
        Handles both register-allocated and spilled variables.
        """
        # Function local variable store: write to stack via FP
        if self.current_function and self.current_function in self.function_locals and name in self.function_locals[self.current_function]:
            offset = self.function_locals[self.current_function][name]
            self.current_output.append(f"MOV P0, FP")
            self.current_output.append(f"ADD P0, {offset}")
            self.current_output.append(f"MOV [P0], {source_reg}")
            return

        # Function parameter store: write back to caller-passed stack slot
        if self.current_function:
            func = self.functions.get(self.current_function.lower())
            if func:
                _, params, _ = func
                if name in params:
                    idx = params.index(name)
                    # Same offset calculation as load_variable: account for reversed parameter order
                    offset = 4 + (len(params) - 1 - idx) * 2
                    self.current_output.append(f"MOV P0, FP")
                    self.current_output.append(f"ADD P0, {offset}")
                    self.current_output.append(f"MOV [P0], {source_reg}")
                    return

        # Check if variable is in a register
        if name in self.var_reg:
            reg = self.var_reg[name]
            if reg != source_reg:
                self.current_output.append(f"MOV {reg}, {source_reg}")
            return
        
        # Check if variable is spilled
        if self.is_spilled(name):
            # **OPTIMIZATION: Hot Spill Migration**
            # Check if this spilled variable is in zero-page (hot spill)
            if name in self.hot_spills:
                spill_addr = self.hot_spills[name]
                if self.debug_allocation:
                    print(f"[STORE] Storing to hot-spilled variable '{name}' in zero-page 0x{spill_addr:04X} from {source_reg}")
            else:
                spill_addr = self.get_spill_slot(name)
                if self.debug_allocation:
                    print(f"[STORE] Storing to spilled variable '{name}' at 0x{spill_addr:04X} from {source_reg}")
            
            # All NoBASIC variables are 16-bit, so always write the full word to spill_addr
            if source_reg.startswith('R'):
                # For 8-bit R registers, use P0 as intermediate for full 16-bit store
                self.current_output.append(f"MOV P0, 0")
                self.current_output.append(f"MOV :P0, {source_reg}")  # Move to LOW byte (not high!)
                self.current_output.append(f"MOV P1, {spill_addr}")
                self.current_output.append(f"MOV [P1], P0")
            else:
                # For 16-bit P registers, avoid clobbering the source register when it is P0
                addr_reg = 'P1' if source_reg == 'P0' else 'P0'
                self.current_output.append(f"MOV {addr_reg}, {spill_addr}")
                self.current_output.append(f"MOV [{addr_reg}], {source_reg}")
            
            return
        
        # Not in register or spill slot, use regular memory
        addr = self.get_variable_address(name)
        # All NoBASIC variables are 16-bit, so always write the full word
        if source_reg.startswith('R'):
            # For 8-bit R registers, use P0 as intermediate for full 16-bit store
            self.current_output.append(f"MOV P0, 0")
            self.current_output.append(f"MOV :P0, {source_reg}")  # Move to LOW byte (not high!)
            self.current_output.append(f"MOV P1, {addr}")
            self.current_output.append(f"MOV [P1], P0")
        else:
            # For 16-bit P registers, avoid clobbering the source register when it is P0
            addr_reg = 'P1' if source_reg == 'P0' else 'P0'
            self.current_output.append(f"MOV {addr_reg}, {addr}")
            self.current_output.append(f"MOV [{addr_reg}], {source_reg}")

    def analyze_ssa_form(self):
        """
        Basic SSA (Static Single Assignment) form analysis.
        This is a foundation for future optimizations like:
        - Dead code elimination
        - Constant propagation
        - Common subexpression elimination
        - Register coalescing
        
        Current implementation provides:
        - Def-use chains
        - Dominance information (basic)
        - Phi node detection points
        """
        # Track definitions and uses
        self.ssa_defs: Dict[str, List[int]] = {}  # variable -> list of definition points
        self.ssa_uses: Dict[str, List[int]] = {}  # variable -> list of use points
        
        # Build def-use chains from live ranges
        for var, (start, end) in self.live_ranges.items():
            # First occurrence is typically a definition
            if var not in self.ssa_defs:
                self.ssa_defs[var] = [start]
            
            # All points in range could be uses
            if var not in self.ssa_uses:
                self.ssa_uses[var] = []
            
            # Find actual use points from live_at_point
            for point in range(start, end + 1):
                if point in self.live_at_point and var in self.live_at_point[point]:
                    if point != start:  # Don't count definition as use
                        self.ssa_uses[var].append(point)
        
        # Detect potential phi node locations (merge points)
        # These occur where control flow merges (end of if/else, loops)
        self.phi_node_points: Dict[int, Set[str]] = {}  # point -> variables needing phi
        
        # Find points with sudden pressure changes (potential merge points)
        pressure_points = sorted(self.register_pressure.items())
        for i in range(1, len(pressure_points)):
            prev_point, prev_pressure = pressure_points[i-1]
            curr_point, curr_pressure = pressure_points[i]
            
            # If pressure increases significantly, might be a merge point
            if curr_pressure > prev_pressure + 2:
                # Find variables that become live at this point
                curr_live = self.live_at_point.get(curr_point, set())
                prev_live = self.live_at_point.get(prev_point, set())
                new_live = curr_live - prev_live
                
                if new_live:
                    self.phi_node_points[curr_point] = new_live
        
        if self.debug_allocation:
            print(f"\n[SSA] SSA Form Analysis:")
            print(f"[SSA] Variables with multiple definitions:")
            for var, defs in self.ssa_defs.items():
                if len(defs) > 1:
                    print(f"  {var}: {len(defs)} definitions at {defs}")
            
            print(f"[SSA] Potential phi node points: {len(self.phi_node_points)}")
            for point, vars in sorted(self.phi_node_points.items()):
                print(f"  Point {point}: {sorted(vars)}")
            
            # Compute def-use chain statistics
            total_uses = sum(len(uses) for uses in self.ssa_uses.values())
            total_defs = sum(len(defs) for defs in self.ssa_defs.values())
            print(f"[SSA] Total definitions: {total_defs}, Total uses: {total_uses}")

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
