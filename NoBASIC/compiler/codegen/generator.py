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
    LineStmt, CircleStmt, TextStmt, SetLayerStmt, SRolStmt, SRotStmt, SShftStmt, SFlipStmt,
    SpriteOnStmt, SpriteOffStmt,
    PlayToneStmt, PlayWaveStmt, StopSoundStmt, SetChannelStmt, GetKeyStmt,
    SerOutStmt, SerInStmt, SerStatStmt, SerCtrlStmt,
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
            'P0', 'P1', 'P2', 'P3', 'P4', 'P5', 'P6'
        ]
        
        # Preferred register order for variable allocation (P registers for 16-bit)
        self.var_allocation_order = [
            'P2', 'P3', 'P4', 'P5', 'P6'  # Skip P0/P1 and reserve P7 for call linkage
        ]
        # Opportunistic fallback registers (used only when pressure is within capacity).
        # Keep empty: P1 is used as a legacy scratch register in multiple codegen paths.
        self.var_allocation_fallback = []

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
        self.expr_constant_values: Dict[str, int] = {}

        # Dynamic list runtime state
        self.list_descriptors: Dict[str, int] = {}  # list name -> descriptor address (base, capacity)
        self.list_heap_next_addr: Optional[int] = None  # Address storing next free list heap byte
        self.list_heap_start = 0x7200
        self.list_heap_end = 0xEFFF
        self.list_runtime_required = False

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

    def allocate_p_register(self, preferred_regs: Optional[List[str]] = None) -> str:
        """Allocate a 16-bit P register only (never falls back to R registers)."""
        if preferred_regs is None:
            preferred_regs = ['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P0']

        self.allocation_stats['total_allocations'] += 1

        for reg in preferred_regs:
            if reg not in self.register_usage:
                continue
            if self.register_usage[reg]:
                continue

            self.register_usage[reg] = True
            self.auto_free_registers.add(reg)
            self._update_allocation_stats()
            self.mark_temp_live(reg)
            if self.debug_allocation:
                print(f"[ALLOC] Allocated P register {reg}")
                self._debug_register_state()
            return reg

        self.allocation_stats['allocation_failures'] += 1
        raise RuntimeError("Register exhaustion: No available P registers for 16-bit operation")
    
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
        elif isinstance(stmt, SerOutStmt):
            self.collect_lifetimes_expr(stmt.value)
        elif isinstance(stmt, SerCtrlStmt):
            self.collect_lifetimes_expr(stmt.value)
        elif isinstance(stmt, DispStmt):
            self.collect_lifetimes_expr(stmt.text)
        # Others (SerInStmt, SerStatStmt, GetKeyStmt, etc.) have no sub-expressions

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
            
            # Find available registers.
            # Block registers held by active intervals plus interfering variables.
            used_regs = {reg for _, _, reg in active_intervals}
            interfering_vars = self.interference_graph.get(var, set())
            interfering_regs = {self.var_reg.get(v) for v in interfering_vars if v in self.var_reg}
            interfering_regs.discard(None)
            blocked_regs = used_regs | interfering_regs
            available_regs = [r for r in allocation_pool if r not in blocked_regs]
            
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
        self.functions = {}
        self.function_labels = {}
        self.function_counter = 0
        self.current_function = None
        self.function_outputs = []
        self.function_locals = {}
        self.expr_constant_values = {}
        self.list_descriptors = {}
        self.list_heap_next_addr = None
        self.list_runtime_required = False

        # Pre-pass: register struct declarations so function code generation
        # can resolve member access on global struct instances.
        for stmt in program.statements:
            if isinstance(stmt, StructDeclarationStmt):
                self.struct_types[stmt.name.lower()] = StructType(
                    stmt.name,
                    [field.lower() for field in stmt.fields],
                )

        # Reserve dynamic list descriptors up-front so initialization code can
        # set deterministic base/capacity state before user code runs.
        self._collect_dynamic_list_descriptors(program)

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

        # Initialize dynamic list runtime state.
        self._emit_list_runtime_init()

        # Generate code for all statements (skip function definitions in main pass)
        for stmt in program.statements:
            if not isinstance(stmt, FunctionDefStmt):
                self.generate_statement(stmt)

        # Add HLT at the end
        self.current_output.append("HLT")
        
        # Add function code after HLT
        for func_lines in self.function_outputs:
            self.current_output.extend(func_lines)

        # Emit list allocator helper when at least one list is used.
        self._emit_list_runtime_helper()
        
        # Add string literals
        for label, string_value in self.strings:
            if string_value.startswith("__BUFFER__"):
                # Special buffer allocation
                size = int(string_value.split("__")[2])
                self.current_output.append(f"{label}: DB " + ", ".join(["0"] * size))
            else:
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
                original_size = len('\n'.join(self.output))
                optimized_size = len(assembly_output)
                print(f"[CODEGEN] Code size reduction: {original_size} -> {optimized_size} bytes")

        return assembly_output

    def generate_statement(self, stmt: Statement):
        """Generate code for a statement."""
        # Increment program counter for runtime liveness tracking
        self.program_counter += 1

        # Keep constant propagation conservative across control-flow boundaries.
        if not isinstance(stmt, AssignmentStmt):
            self.expr_constant_values.clear()
        
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
        elif isinstance(stmt, SRolStmt):
            self.generate_srol(stmt)
        elif isinstance(stmt, SRotStmt):
            self.generate_srot(stmt)
        elif isinstance(stmt, SShftStmt):
            self.generate_sshft(stmt)
        elif isinstance(stmt, SFlipStmt):
            self.generate_sflip(stmt)
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
        elif isinstance(stmt, SerOutStmt):
            self.generate_ser_out(stmt)
        elif isinstance(stmt, SerInStmt):
            self.generate_ser_in(stmt)
        elif isinstance(stmt, SerStatStmt):
            self.generate_ser_stat(stmt)
        elif isinstance(stmt, SerCtrlStmt):
            self.generate_ser_ctrl(stmt)
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

    def _collect_function_local_variables(self, statements: List[Statement]) -> List[str]:
        """Collect LOCAL declarations from a function body, including nested blocks."""
        local_vars: List[str] = []

        for statement in statements:
            if isinstance(statement, VarDeclarationStmt) and statement.scope == VarScope.LOCAL:
                local_vars.extend(statement.variables)
                continue

            if isinstance(statement, IfStmt):
                local_vars.extend(self._collect_function_local_variables(statement.then_branch))
                if statement.else_branch:
                    local_vars.extend(self._collect_function_local_variables(statement.else_branch))
                continue

            if isinstance(statement, (ForStmt, WhileStmt, RepeatStmt)):
                local_vars.extend(self._collect_function_local_variables(statement.body))

        return local_vars

    def generate_function_def(self, stmt: FunctionDefStmt, func_key: Optional[str] = None):
        """Generate a function definition with prologue, body, and epilogue."""
        func_key = func_key or stmt.name.lower()
        label = self.function_labels[func_key]
        
        # Extract parameter names
        param_names = [param_name for param_name, _ in stmt.params]
        
        # Collect local variables and calculate stack space needed.
        # This must include declarations nested inside If/For/While/Repeat blocks.
        local_vars = self._collect_function_local_variables(stmt.body)
        
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

        # Use explicit frame teardown in epilogues instead of LEAVE because
        # LEAVE encoding/decoding currently risks consuming the next opcode.
        
        # Note: Parameters are already on stack (pushed by caller)
        # FP now points to saved FP, params are at FP+4, FP+6, etc.
        # Locals are at FP-2, FP-4, etc.
        
        # Save current function context
        prev_function = self.current_function
        self.current_function = func_key
        
        # Temporarily redirect output to func_lines
        old_output = self.current_output
        self.current_output = func_lines

        try:
            # Generate function body
            for body_stmt in stmt.body:
                # Skip explicit return statements here, they'll emit their own RET
                self.generate_statement(body_stmt)

            # If no explicit return, add default return 0
            if not stmt.body or not isinstance(stmt.body[-1], ReturnStmt):
                self.current_output.append("MOV SP, FP")
                self.current_output.append("POP FP")
                self.current_output.append("RETN 0")
        finally:
            # Always restore generator context after emitting a function body.
            self.current_output = old_output
            self.current_function = prev_function
        
        # Add function code to collected outputs
        self.function_outputs.append(func_lines)

    def generate_return(self, stmt: ReturnStmt):
        """Generate a return statement."""
        return_value = "0"
        if stmt.value:
            # Evaluate return value, preferring R0
            result_reg = self.generate_expression(stmt.value, 'R0')
            return_value = result_reg
        else:
            return_value = "0"
        
        # Function epilogue
        if self.current_function:
            self.current_output.append("MOV SP, FP")
            self.current_output.append("POP FP")

        self.current_output.append(f"RETN {return_value}")

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
            
            string_reg = self.allocate_p_register(["P1", "P2", "P3"])  # Use P register for string address
            self.current_output.append(f"ITOS {string_reg}, {text_value_reg}")  # Convert number to string
            self.current_output.append(f"TEXT {string_reg}")  # Display the converted string
            self.deallocate_register(string_reg)
            if text_value_reg not in ['R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9']:
                self.smart_deallocate(text_value_reg, is_last_use=True)

    def generate_set_layer(self, stmt: SetLayerStmt):
        """Generate optimized SetLayer(layer) code with direct register assignment."""
        self.current_output.append("MOV VM, 0")  # Coordinate mode for pixel operations
        self.generate_expression_into(stmt.layer, 'VL')

    def generate_srol(self, stmt: SRolStmt):
        """Generate ScrRoll(axis, amount) code."""
        axis_reg = self.generate_expression(stmt.axis)
        amount_reg = self.generate_expression(stmt.amount)
        self.current_output.append(f"SROL {axis_reg}, {amount_reg}")
        self.smart_deallocate(axis_reg, is_last_use=True)
        self.smart_deallocate(amount_reg, is_last_use=True)

    def generate_srot(self, stmt: SRotStmt):
        """Generate ScrRotate(direction, amount) code."""
        direction_reg = self.generate_expression(stmt.direction)
        amount_reg = self.generate_expression(stmt.amount)
        self.current_output.append(f"SROT {direction_reg}, {amount_reg}")
        self.smart_deallocate(direction_reg, is_last_use=True)
        self.smart_deallocate(amount_reg, is_last_use=True)

    def generate_sshft(self, stmt: SShftStmt):
        """Generate ScrShift(axis, amount) code."""
        axis_reg = self.generate_expression(stmt.axis)
        amount_reg = self.generate_expression(stmt.amount)
        self.current_output.append(f"SSHFT {axis_reg}, {amount_reg}")
        self.smart_deallocate(axis_reg, is_last_use=True)
        self.smart_deallocate(amount_reg, is_last_use=True)

    def generate_sflip(self, stmt: SFlipStmt):
        """Generate ScrFlip(axis) code."""
        axis_reg = self.generate_expression(stmt.axis)
        self.current_output.append(f"SFLIP {axis_reg}")
        self.smart_deallocate(axis_reg, is_last_use=True)

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

    def generate_ser_out(self, stmt: SerOutStmt):
        """Generate SerOut(value) - transmit a byte over the serial port (SEROUT)."""
        val_reg = self.generate_expression(stmt.value)
        self.current_output.append(f"SEROUT {val_reg}")
        self.smart_deallocate(val_reg, is_last_use=True)

    def generate_ser_in(self, stmt: SerInStmt):
        """Generate SerIn(variable) - read a byte from the serial port (SERIN)."""
        self.current_output.append(f"SERIN R0")
        self.store_variable(stmt.variable, "R0")

    def generate_ser_stat(self, stmt: SerStatStmt):
        """Generate SerStat(variable) - read serial status bits (SERSTAT)."""
        self.current_output.append(f"SERSTAT R0")
        self.store_variable(stmt.variable, "R0")

    def generate_ser_ctrl(self, stmt: SerCtrlStmt):
        """Generate SerCtrl(value) - set serial control bits (SERCTRL)."""
        val_reg = self.generate_expression(stmt.value)
        self.current_output.append(f"SERCTRL {val_reg}")
        self.smart_deallocate(val_reg, is_last_use=True)

    def generate_input(self, stmt: InputStmt):
        """Generate Input(prompt, variable) code."""
        # Left-justify prompt on the current row after prior Disp calls.
        self.current_output.append("MOV VX, 0")

        # Display prompt if provided
        if stmt.prompt is not None:
            # Handle prompt display
            if isinstance(stmt.prompt, LiteralExpr) and stmt.prompt.data_type.name == "STRING":
                # For string literals, display directly
                prompt_label = self.add_string_literal(stmt.prompt.value)
                self.current_output.append("MOV VC, 15")  # Set color to white
                self.current_output.append(f"TEXT {prompt_label}")  # Display prompt
            else:
                # For expressions, evaluate and try to display
                prompt_reg = self.generate_expression(stmt.prompt, "P1")
                self.current_output.append("MOV VC, 15")  # Set color to white
                self.current_output.append(f"TEXT {prompt_reg}")  # Display prompt
                if prompt_reg not in ['P0', 'P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'SP', 'FP']:
                    self.smart_deallocate(prompt_reg, is_last_use=True)

        # Allocate buffer for input string (64 bytes)
        # Create a unique buffer label for this input statement
        input_buffer_label = self.new_label()
        # We need a writable buffer, so we'll add it as raw bytes after the code
        # Reserve 64 bytes (63 chars + null terminator) initialized to zero
        # We'll add this to the output directly rather than using the strings list
        buffer_init = f"{input_buffer_label}: DB " + ", ".join(["0"] * 64)
        # Add to strings list but mark it specially (we'll handle it differently)
        self.strings.append((input_buffer_label, "__BUFFER__64__"))
        
        # Save current VX, VY for cursor position
        self.current_output.append("; Input: Read string from keyboard")
        self.current_output.append(f"MOV P1, {input_buffer_label}")  # Buffer pointer
        self.current_output.append("MOV R1, 0")  # Character count
        self.current_output.append("MOV R2, VX")  # Save starting X position
        self.current_output.append("MOV R3, VY")  # Save starting Y position
        self.current_output.append("MOV R4, 0")  # Shift-pending flag for uppercase input
        self.current_output.append("MOV R6, R3")  # Input row bottom Y for rectangle clears
        self.current_output.append("ADD R6, 7")
        
        # Input loop
        input_loop_label = self.new_label()
        input_done_label = self.new_label()
        
        self.current_output.append(f"{input_loop_label}:")
        self.current_output.append("KEYSTAT R0")  # Check if key available
        self.current_output.append("CMP R0, 0")
        self.current_output.append(f"JZ {input_loop_label}")  # Wait for key
        
        self.current_output.append("KEYIN R0")  # Read the key

        # Treat Shift (0x97 / 151) as a one-shot modifier for the next letter.
        shift_pressed_label = self.new_label()
        after_shift_check_label = self.new_label()
        self.current_output.append("CMP R0, 151")
        self.current_output.append(f"JZ {shift_pressed_label}")
        self.current_output.append(f"JMP {after_shift_check_label}")
        self.current_output.append(f"{shift_pressed_label}:")
        self.current_output.append("MOV R4, 1")
        self.current_output.append(f"JMP {input_loop_label}")
        self.current_output.append(f"{after_shift_check_label}:")
        
        # Check for Enter key (ASCII 13 or key code 10)
        self.current_output.append("CMP R0, 13")  # Enter key
        self.current_output.append(f"JZ {input_done_label}")
        self.current_output.append("CMP R0, 10")  # Alternate Enter
        self.current_output.append(f"JZ {input_done_label}")
        
        # Check for backspace (ASCII 8 or 127)
        backspace_label = self.new_label()
        after_backspace_label = self.new_label()
        self.current_output.append("CMP R0, 8")  # Backspace
        self.current_output.append(f"JZ {backspace_label}")
        self.current_output.append("CMP R0, 127")  # Delete
        self.current_output.append(f"JZ {backspace_label}")
        self.current_output.append(f"JMP {after_backspace_label}")
        
        # Handle backspace
        self.current_output.append(f"{backspace_label}:")
        self.current_output.append("CMP R1, 0")  # Check if buffer empty
        self.current_output.append(f"JZ {input_loop_label}")  # Nothing to delete
        self.current_output.append("DEC R1")  # Decrease count
        # Calculate address: P4 = P1 + R1
        self.current_output.append("MOV P4, P1")
        self.current_output.append("ADD P4, R1")
        self.current_output.append("MOV [P4], 0")  # Clear character in buffer
        # Redraw input area (clear and redisplay)
        self.current_output.append("MOV VX, R2")  # Reset to start X
        self.current_output.append("MOV VY, R3")  # Reset to start Y
        self.current_output.append("MOV VC, 0")  # Black to clear
        self.current_output.append("SRECT 255, R6, 1")  # Clear row segment so deleted glyph pixels are erased
        self.current_output.append("MOV VX, R2")  # Reset to start X
        self.current_output.append("MOV VY, R3")  # Reset to start Y
        self.current_output.append("MOV VC, 15")  # White
        self.current_output.append(f"TEXT {input_buffer_label}")  # Redraw
        self.current_output.append(f"JMP {input_loop_label}")
        
        # Store character in buffer
        self.current_output.append(f"{after_backspace_label}:")

        # Apply one-shot shift to lowercase ASCII letters (a-z -> A-Z).
        apply_shift_label = self.new_label()
        skip_shift_label = self.new_label()
        clear_shift_only_label = self.new_label()
        shift_done_label = self.new_label()
        self.current_output.append("CMP R4, 0")
        self.current_output.append(f"JZ {skip_shift_label}")
        self.current_output.append(f"{apply_shift_label}:")
        self.current_output.append("CMP R0, 97")
        self.current_output.append(f"JLT {clear_shift_only_label}")
        self.current_output.append("CMP R0, 122")
        self.current_output.append(f"JGT {clear_shift_only_label}")
        self.current_output.append("SUB R0, 32")
        self.current_output.append(f"JMP {shift_done_label}")
        self.current_output.append(f"{clear_shift_only_label}:")
        self.current_output.append(f"{shift_done_label}:")
        self.current_output.append("MOV R4, 0")
        self.current_output.append(f"{skip_shift_label}:")

        self.current_output.append("CMP R1, 63")  # Max 63 characters
        self.current_output.append(f"JGE {input_loop_label}")  # Buffer full
        # Calculate address: P4 = P1 + R1
        self.current_output.append("MOV P4, P1")
        self.current_output.append("ADD P4, R1")
        self.current_output.append("MOV [P4], R0")  # Store character
        self.current_output.append("INC R1")  # Increment count
        # Calculate address for null terminator: P4 = P1 + R1
        self.current_output.append("MOV P4, P1")
        self.current_output.append("ADD P4, R1")
        self.current_output.append("MOV [P4], 0")  # Null terminate
        
        # Echo character to screen
        self.current_output.append("MOV VX, R2")  # Reset to start X
        self.current_output.append("MOV VY, R3")  # Reset to start Y
        self.current_output.append("MOV VC, 0")  # Clear row before redraw to avoid overdraw artifacts
        self.current_output.append("SRECT 255, R6, 1")
        self.current_output.append("MOV VX, R2")  # Reset to start X
        self.current_output.append("MOV VY, R3")  # Reset to start Y
        self.current_output.append("MOV VC, 15")  # White color
        self.current_output.append(f"TEXT {input_buffer_label}")  # Display updated string
        
        self.current_output.append(f"JMP {input_loop_label}")
        
        # Input complete
        self.current_output.append(f"{input_done_label}:")
        # Calculate address for final null terminator: P4 = P1 + R1
        self.current_output.append("MOV P4, P1")
        self.current_output.append("ADD P4, R1")
        self.current_output.append("MOV [P4], 0")  # Ensure null termination
        
        # Move cursor to next line
        self.current_output.append("MOV VX, 0")
        self.current_output.append("ADD VY, 8")
        
        # Store buffer address in target variable using normal variable storage rules.
        # This keeps register-allocated variables in sync with Input results.
        self.current_output.append(f"MOV P2, {input_buffer_label}")  # Load buffer address into P2
        self.store_variable(stmt.variable, "P2")

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
                
                string_reg = self.allocate_p_register(["P1", "P2", "P3"])
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
            
            string_reg = self.allocate_p_register(["P1", "P2", "P3"])  # Use a P register for string address
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

        expr_to_generate = stmt.expression
        if self.expr_simplifier is not None:
            expr_to_generate, _ = self.expr_simplifier.simplify_expression(
                stmt.expression,
                context={"constants": self.expr_constant_values},
            )
        
        # Generate the value - prefer a P register for strings, R1 for numeric temps
        preferred_reg = "P1" if is_string_assignment else "R1"
        value_reg = self.generate_expression(expr_to_generate, preferred_reg)

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

            if (
                isinstance(expr_to_generate, LiteralExpr)
                and expr_to_generate.data_type.name == "NUMBER"
            ):
                self.expr_constant_values[var_name] = self._normalize_numeric_literal(expr_to_generate.value)
            else:
                self.expr_constant_values.pop(var_name, None)
        elif isinstance(stmt.variable, MemberAccessExpr):
            # Struct member assignment
            self.generate_member_store(stmt.variable, value_reg)
            self.expr_constant_values.clear()
        elif isinstance(stmt.variable, ListAccessExpr):
            # Array element assignment
            self.generate_list_store(stmt.variable, value_reg)
            self.expr_constant_values.clear()
        elif isinstance(stmt.variable, MatrixAccessExpr):
            # Matrix element assignment
            self.generate_matrix_store(stmt.variable, value_reg)
            self.expr_constant_values.clear()
        else:
            raise TypeError(f"Unsupported assignment target: {type(stmt.variable)}")

    def generate_list_access(self, expr: ListAccessExpr, target_reg: str) -> str:
        """Generate code to load from a list element."""
        desc_addr = self._get_or_create_list_descriptor(expr.list_name)
        index_reg = self.generate_expression(expr.index, "P2")
        self.current_output.append("PUSH P1")
        self.current_output.append("PUSH P2")
        self.current_output.append("PUSH P3")
        self.current_output.append("PUSH P4")
        self.current_output.append("PUSH P5")
        self.current_output.append("PUSH P6")
        self.current_output.append(f"MOV P1, 0x{desc_addr:04X}")
        if index_reg != "P2":
            self.current_output.append(f"MOV P2, {index_reg}")
        self.current_output.append("CALL _nb_list_elem_addr")
        self.current_output.append("POP P6")
        self.current_output.append("POP P5")
        self.current_output.append("POP P4")
        self.current_output.append("POP P3")
        self.current_output.append("POP P2")
        self.current_output.append("POP P1")
        load_ok = self.new_label()
        load_done = self.new_label()
        self.current_output.append("CMP P0, 0")
        self.current_output.append(f"JNZ {load_ok}")
        self.current_output.append(f"MOV {target_reg}, 0")
        self.current_output.append(f"JMP {load_done}")
        self.current_output.append(f"{load_ok}:")
        if target_reg.startswith("R"):
            self.current_output.append("PUSH P1")
            self.current_output.append("MOV P1, [P0]")
            self.current_output.append(f"MOV {target_reg}, :P1")
            self.current_output.append("POP P1")
        else:
            self.current_output.append(f"MOV {target_reg}, [P0]")
        self.current_output.append(f"{load_done}:")
        return target_reg

    def generate_list_store(self, expr: ListAccessExpr, value_reg: str):
        """Generate code to store to a list element."""
        desc_addr = self._get_or_create_list_descriptor(expr.list_name)
        index_reg = self.generate_expression(expr.index, "P2")
        self.current_output.append("PUSH P1")
        self.current_output.append("PUSH P2")
        self.current_output.append("PUSH P3")
        self.current_output.append("PUSH P4")
        self.current_output.append("PUSH P5")
        self.current_output.append("PUSH P6")
        self.current_output.append(f"MOV P1, 0x{desc_addr:04X}")
        if index_reg != "P2":
            self.current_output.append(f"MOV P2, {index_reg}")
        self.current_output.append("CALL _nb_list_elem_addr")
        self.current_output.append("POP P6")
        self.current_output.append("POP P5")
        self.current_output.append("POP P4")
        self.current_output.append("POP P3")
        self.current_output.append("POP P2")
        self.current_output.append("POP P1")
        store_ok = self.new_label()
        store_done = self.new_label()
        self.current_output.append("CMP P0, 0")
        self.current_output.append(f"JNZ {store_ok}")
        self.current_output.append(f"JMP {store_done}")
        self.current_output.append(f"{store_ok}:")
        store_reg = value_reg
        if store_reg.startswith('R'):
            self.current_output.append("MOV P1, 0")
            self.current_output.append(f"MOV :P1, {store_reg}")
            store_reg = "P1"
        elif store_reg in {"P0", "P5"}:
            self.current_output.append(f"MOV P1, {store_reg}")
            store_reg = "P1"
        self.current_output.append(f"MOV [P0], {store_reg}")
        self.current_output.append(f"{store_done}:")

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
                self.current_output.append(f"; Load {var_name}.{expr.member}")
                self.current_output.append(f"MOV P0, {field_addr}")
                
                # CRITICAL FIX: Use target_reg if it's a P register (and not P0 which we just used)
                # This ensures different registers are used for left/right operands in comparisons
                if target_reg and target_reg.startswith('P') and target_reg != 'P0':
                    self.current_output.append(f"MOV {target_reg}, [P0]")
                    return target_reg
                else:
                    # Target is not suitable, find a free P register
                    for reg in ['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7']:
                        if not self.register_usage.get(reg, False):
                            self.current_output.append(f"MOV {reg}, [P0]")
                            # Don't mark as in-use here - let the caller manage it
                            return reg
                    
                    # No free register, use P1 as fallback
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
                
                # CRITICAL FIX: Struct fields are 16-bit, so if value is in R register,
                # we need to move it to a P register first to ensure 16-bit write
                if value_reg.startswith('R'):
                    # Move 8-bit R register to 16-bit P register for proper storage
                    self.current_output.append(f"MOV P1, {value_reg}")
                    self.current_output.append(f"MOV [P0], P1")
                else:
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

        self.emit_condition_false_jump(stmt.condition, else_label)

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

    def _expr_has_unsafe_loop_addr_hoist_nodes(self, expr: Expression) -> bool:
        """Return True when expression shape risks clobbering conservative hoist registers."""
        if isinstance(expr, (FunctionCallExpr, ListAccessExpr, MatrixAccessExpr, MemberAccessExpr)):
            return True
        if isinstance(expr, BinaryExpr):
            return (
                self._expr_has_unsafe_loop_addr_hoist_nodes(expr.left)
                or self._expr_has_unsafe_loop_addr_hoist_nodes(expr.right)
            )
        if isinstance(expr, UnaryExpr):
            return self._expr_has_unsafe_loop_addr_hoist_nodes(expr.expression)
        if isinstance(expr, GroupingExpr):
            return self._expr_has_unsafe_loop_addr_hoist_nodes(expr.expression)
        return False

    def _stmt_allows_loop_addr_hoist(self, stmt: Statement) -> bool:
        """Conservative statement-level check for loop address-hoist safety."""
        if isinstance(stmt, AssignmentStmt):
            target_unsafe = False
            if isinstance(stmt.variable, (ListAccessExpr, MatrixAccessExpr, MemberAccessExpr)):
                target_unsafe = True
            elif isinstance(stmt.variable, Expression):
                target_unsafe = self._expr_has_unsafe_loop_addr_hoist_nodes(stmt.variable)
            return (not target_unsafe) and (not self._expr_has_unsafe_loop_addr_hoist_nodes(stmt.expression))

        if isinstance(stmt, ExpressionStmt):
            return not self._expr_has_unsafe_loop_addr_hoist_nodes(stmt.expression)

        if isinstance(stmt, IfStmt):
            if self._expr_has_unsafe_loop_addr_hoist_nodes(stmt.condition):
                return False
            return all(self._stmt_allows_loop_addr_hoist(s) for s in stmt.then_branch) and (
                stmt.else_branch is None or all(self._stmt_allows_loop_addr_hoist(s) for s in stmt.else_branch)
            )

        # Graphics statements are safe when their arguments do not use complex memory helpers.
        if isinstance(stmt, (PxlOnStmt, PxlOffStmt, LineStmt, CircleStmt, TextStmt, SetLayerStmt)):
            exprs = []
            if isinstance(stmt, PxlOnStmt):
                exprs = [stmt.x, stmt.y, stmt.color]
            elif isinstance(stmt, PxlOffStmt):
                exprs = [stmt.x, stmt.y]
            elif isinstance(stmt, LineStmt):
                exprs = [stmt.x1, stmt.y1, stmt.x2, stmt.y2, stmt.color]
            elif isinstance(stmt, CircleStmt):
                exprs = [stmt.x, stmt.y, stmt.radius, stmt.color]
            elif isinstance(stmt, TextStmt):
                exprs = [stmt.x, stmt.y, stmt.text, stmt.color]
            elif isinstance(stmt, SetLayerStmt):
                exprs = [stmt.layer]
            return all(not self._expr_has_unsafe_loop_addr_hoist_nodes(e) for e in exprs)

        return False

    def _loop_body_allows_address_hoist(self, body: List[Statement]) -> bool:
        """Check whether a loop body is simple enough for conservative address-hoisting."""
        return all(self._stmt_allows_loop_addr_hoist(stmt) for stmt in body)

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

        # Hoist global loop-variable memory address when loop body is simple/safe.
        loop_var_addr_reg: Optional[str] = None
        loop_var_addr: Optional[int] = None
        if not is_local_var and not is_register_allocated and self.current_function is None:
            loop_var_addr = self.get_variable_address(stmt.variable)
            if self._loop_body_allows_address_hoist(stmt.body):
                for candidate in ['P6', 'P5', 'P4']:
                    if candidate in {loop_reg, end_reg, step_reg if stmt.step else ''}:
                        continue
                    if not self.register_usage.get(candidate, False):
                        loop_var_addr_reg = candidate
                        self.register_usage[loop_var_addr_reg] = True
                        self.current_output.append(f"MOV {loop_var_addr_reg}, {loop_var_addr}")
                        break
        
        # Store initial value if needed
        if is_local_var:
            # Store to local variable slot
            offset = self.function_locals[self.current_function][stmt.variable]
            self.current_output.append(f"MOV P0, FP")
            self.current_output.append(f"ADD P0, {offset}")
            self.current_output.append(f"MOV [P0], {loop_reg}")
        elif not is_register_allocated and self.current_function is None:  # Only store in memory for global variables
            if loop_var_addr_reg is not None:
                self.current_output.append(f"MOV [{loop_var_addr_reg}], {loop_reg}")
            else:
                self.current_output.append(f"MOV P0, {loop_var_addr}")
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
            if loop_var_addr_reg is not None:
                self.current_output.append(f"MOV [{loop_var_addr_reg}], {loop_reg}")
            else:
                self.current_output.append(f"MOV P0, {loop_var_addr}")
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
        if loop_var_addr_reg is not None:
            self.deallocate_register(loop_var_addr_reg)
        
        # Decrement nesting level
        self.loop_nesting_level -= 1

    def generate_while(self, stmt: WhileStmt):
        """Generate optimized While loop code."""
        loop_label = self.new_label()
        end_label = self.new_label()

        self.current_output.append(f"{loop_label}:")

        self.emit_condition_false_jump(stmt.condition, end_label)

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

        self.emit_condition_false_jump(stmt.condition, loop_label)

    def emit_condition_false_jump(self, condition: Expression, false_label: str):
        """Emit a jump to ``false_label`` when ``condition`` evaluates to false."""
        if isinstance(condition, BinaryExpr):
            false_jump_map = {
                "<": "JGE",
                ">": "JLE",
                "=": "JNZ",
                "<>": "JZ",
                "<=": "JGT",
                ">=": "JLT",
            }
            jump_opcode = false_jump_map.get(condition.operator)
            if jump_opcode:
                # Direct branch lowering avoids materializing booleans for control flow.
                left_result = self.generate_expression(condition.left, 'P1')
                right_result = self.generate_expression(condition.right, 'P2')
                self.current_output.append(f"CMP {left_result}, {right_result}")
                self.smart_deallocate(left_result, is_last_use=True)
                self.smart_deallocate(right_result, is_last_use=True)
                self.current_output.append(f"{jump_opcode} {false_label}")
                return

        # Fallback path for non-comparison conditions.
        temp_reg = self.allocate_register()
        try:
            condition_reg = self.generate_expression(condition, temp_reg)
            self.current_output.append(f"WHILE {condition_reg}")
            self.current_output.append(f"JZ {false_label}")
        finally:
            self.deallocate_register(temp_reg)

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
        if self.expr_simplifier is not None:
            expr, _ = self.expr_simplifier.simplify_expression(
                expr,
                context={"constants": self.expr_constant_values},
            )

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
                        target_reg = self.allocate_p_register(['P1', 'P2', 'P3'])
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
                target_reg = self.allocate_p_register(['P1', 'P2', 'P3'])
            
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
        # For comparisons, prefer P registers since struct members are 16-bit
        is_comparison = expr.operator in {"<", ">", "=", "<>", "<=", ">="}
        if is_comparison:
            # Use P registers for comparisons to handle struct members properly
            available_regs = ['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7']
        else:
            available_regs = [r for r in self.allocation_order if r != target_reg]
        
        left_pref = available_regs[0] if available_regs else None
        right_pref = available_regs[1] if len(available_regs) > 1 else None

        # Generate left operand
        left_result = self.generate_expression(expr.left, left_pref)

        # Preserve left across right-side evaluation ONLY for non-comparison ops
        left_preserved_reg = None
        
        # CRITICAL FIX: For comparisons, mark left_result as in-use to prevent right operand from using it
        if is_comparison:
            self.register_usage[left_result] = True
        
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
        
        # CRITICAL FIX: If right_result is the same register as left_result (for comparisons),
        # we need to move one of them to a different register
        if is_comparison and right_result == left_result:
            # Find a different register for right operand
            for reg in ['P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P1']:
                if reg != left_result and not self.register_usage.get(reg, False):
                    self.current_output.append(f"MOV {reg}, {right_result}")
                    right_result = reg
                    self.register_usage[reg] = True
                    break

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
        # ++/-- handling on assignable targets
        if expr.operator in ("++", "--"):
            value_reg = None

            if isinstance(expr.expression, VariableExpr):
                var_name = expr.expression.name
                # Load 16-bit value into a P register
                value_reg = self.load_variable(var_name, target_reg if target_reg.startswith('P') else 'P1')
            elif isinstance(expr.expression, MemberAccessExpr):
                # Struct members are 16-bit; prefer P register path used by member access helpers
                value_reg = self.generate_member_access(expr.expression, target_reg if target_reg.startswith('P') else 'P1')

            if value_reg is not None:
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
                if isinstance(expr.expression, VariableExpr):
                    self.store_variable(var_name, value_reg)
                else:
                    self.generate_member_store(expr.expression, value_reg)

                # For pre, return updated value
                if not expr.is_post:
                    if target_reg != value_reg:
                        self.current_output.append(f"MOV {target_reg}, {value_reg}")
                return target_reg

            # Fallback: evaluate operand, but cannot modify non-assignable target here
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

            # Preserve variable-backed registers across calls.
            # User-defined callees freely use P-registers for locals/temps.
            saved_var_regs = [
                reg for reg in sorted(set(self.var_reg.values()))
                if reg not in {'SP', 'FP'} and reg.startswith('P')
            ]
            for reg in saved_var_regs:
                self.current_output.append(f"PUSH {reg}")
            
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
                    p_temp = self.allocate_p_register(['P1', 'P2', 'P3'])
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

            # Restore preserved variable registers (reverse stack order).
            for reg in reversed(saved_var_regs):
                self.current_output.append(f"POP {reg}")
            
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
        elif func_name in {"FILL", "SORTA", "SORTD", "SEQ", "REVERSE", "SUM", "MEAN", "DIM"}:
            list_expr = expr.arguments[0] if expr.arguments else None
            list_name = list_expr.name if isinstance(list_expr, VariableExpr) else "L1"
            desc_addr = self._get_or_create_list_descriptor(list_name)

            self.current_output.append(f"MOV P6, 0x{desc_addr:04X}")
            self.current_output.append("MOV P5, [P6]")  # base
            self.current_output.append("MOV P0, P6")
            self.current_output.append("INC P0")
            self.current_output.append("INC P0")
            self.current_output.append("MOV P4, [P0]")  # capacity

            if func_name == "DIM":
                self.current_output.append(f"MOV {target_reg}, P4")

            elif func_name == "SUM":
                self.current_output.append(f"MOV {target_reg}, 0")
                self.current_output.append("MOV P2, 0")
                loop_label = self.new_label()
                end_label = self.new_label()
                self.current_output.append(f"{loop_label}:")
                self.current_output.append("CMP P2, P4")
                self.current_output.append(f"JGE {end_label}")
                self.current_output.append("MOV P1, P2")
                self.current_output.append("MUL P1, 2")
                self.current_output.append("ADD P1, P5")
                self.current_output.append("MOV P3, [P1]")
                self.current_output.append(f"ADD {target_reg}, P3")
                self.current_output.append("INC P2")
                self.current_output.append(f"JMP {loop_label}")
                self.current_output.append(f"{end_label}:")

            elif func_name == "MEAN":
                self.current_output.append(f"MOV {target_reg}, 0")
                mean_done = self.new_label()
                self.current_output.append("CMP P4, 0")
                self.current_output.append(f"JLE {mean_done}")
                self.current_output.append("MOV P2, 0")
                loop_label = self.new_label()
                end_label = self.new_label()
                self.current_output.append(f"{loop_label}:")
                self.current_output.append("CMP P2, P4")
                self.current_output.append(f"JGE {end_label}")
                self.current_output.append("MOV P1, P2")
                self.current_output.append("MUL P1, 2")
                self.current_output.append("ADD P1, P5")
                self.current_output.append("MOV P3, [P1]")
                self.current_output.append(f"ADD {target_reg}, P3")
                self.current_output.append("INC P2")
                self.current_output.append(f"JMP {loop_label}")
                self.current_output.append(f"{end_label}:")
                self.current_output.append(f"DIV {target_reg}, P4")
                self.current_output.append(f"{mean_done}:")

            elif func_name == "FILL":
                value_reg = self.generate_expression(expr.arguments[1], "P3")
                if value_reg.startswith("R"):
                    self.current_output.append("MOV P3, 0")
                    self.current_output.append(f"MOV :P3, {value_reg}")
                    value_reg = "P3"
                self.current_output.append("MOV P2, 0")
                loop_label = self.new_label()
                end_label = self.new_label()
                self.current_output.append(f"{loop_label}:")
                self.current_output.append("CMP P2, P4")
                self.current_output.append(f"JGE {end_label}")
                self.current_output.append("MOV P1, P2")
                self.current_output.append("MUL P1, 2")
                self.current_output.append("ADD P1, P5")
                self.current_output.append(f"MOV [P1], {value_reg}")
                self.current_output.append("INC P2")
                self.current_output.append(f"JMP {loop_label}")
                self.current_output.append(f"{end_label}:")
                if value_reg != target_reg:
                    self.smart_deallocate(value_reg, is_last_use=True)
                self.current_output.append(f"MOV {target_reg}, P4")

            elif func_name == "SEQ":
                current_reg = self.generate_expression(expr.arguments[2], "P2")
                end_reg = self.generate_expression(expr.arguments[3], "P3")
                step_reg = self.generate_expression(expr.arguments[4], "P7") if len(expr.arguments) > 4 else None
                if step_reg is None:
                    self.current_output.append("MOV P7, 1")
                    step_reg = "P7"
                self.current_output.append("MOV P1, 0")  # list index
                loop_label = self.new_label()
                end_label = self.new_label()
                pos_step = self.new_label()
                do_write = self.new_label()
                self.current_output.append(f"{loop_label}:")
                self.current_output.append("CMP P1, P4")
                self.current_output.append(f"JGE {end_label}")
                self.current_output.append(f"CMP {step_reg}, 0")
                self.current_output.append(f"JGT {pos_step}")
                self.current_output.append(f"CMP {step_reg}, 0")
                self.current_output.append(f"JLT {do_write}")
                self.current_output.append(f"JMP {end_label}")
                self.current_output.append(f"{pos_step}:")
                self.current_output.append(f"CMP {current_reg}, {end_reg}")
                self.current_output.append(f"JGT {end_label}")
                self.current_output.append(f"{do_write}:")
                self.current_output.append("MOV P0, P1")
                self.current_output.append("MUL P0, 2")
                self.current_output.append("ADD P0, P5")
                self.current_output.append(f"MOV [P0], {current_reg}")
                self.current_output.append("INC P1")
                self.current_output.append(f"ADD {current_reg}, {step_reg}")
                self.current_output.append(f"JMP {loop_label}")
                self.current_output.append(f"{end_label}:")
                self.current_output.append(f"MOV {target_reg}, P4")
                if step_reg != "P7":
                    self.smart_deallocate(step_reg, is_last_use=True)

            elif func_name in {"SORTA", "SORTD"}:
                ascending = func_name == "SORTA"
                self.current_output.append("MOV P1, 0")  # i
                outer_label = self.new_label()
                inner_label = self.new_label()
                next_outer = self.new_label()
                skip_swap = self.new_label()
                done_label = self.new_label()
                self.current_output.append(f"{outer_label}:")
                self.current_output.append("CMP P1, P4")
                self.current_output.append(f"JGE {done_label}")
                self.current_output.append("MOV P2, 0")  # j
                self.current_output.append(f"{inner_label}:")
                self.current_output.append("MOV P3, P4")
                self.current_output.append("DEC P3")
                self.current_output.append("SUB P3, P1")
                self.current_output.append("CMP P2, P3")
                self.current_output.append(f"JGE {next_outer}")
                self.current_output.append("MOV P0, P2")
                self.current_output.append("MUL P0, 2")
                self.current_output.append("ADD P0, P5")
                self.current_output.append("MOV P6, [P0]")
                self.current_output.append("MOV P7, P0")
                self.current_output.append("INC P7")
                self.current_output.append("INC P7")
                self.current_output.append("MOV P3, [P7]")
                self.current_output.append("CMP P6, P3")
                if ascending:
                    self.current_output.append(f"JLE {skip_swap}")
                else:
                    self.current_output.append(f"JGE {skip_swap}")
                self.current_output.append("MOV [P0], P3")
                self.current_output.append("MOV [P7], P6")
                self.current_output.append(f"{skip_swap}:")
                self.current_output.append("INC P2")
                self.current_output.append(f"JMP {inner_label}")
                self.current_output.append(f"{next_outer}:")
                self.current_output.append("INC P1")
                self.current_output.append(f"JMP {outer_label}")
                self.current_output.append(f"{done_label}:")
                self.current_output.append(f"MOV {target_reg}, P4")

            elif func_name == "REVERSE":
                self.current_output.append("MOV P1, 0")
                self.current_output.append("MOV P2, P4")
                self.current_output.append("DEC P2")
                loop_label = self.new_label()
                done_label = self.new_label()
                self.current_output.append(f"{loop_label}:")
                self.current_output.append("CMP P1, P2")
                self.current_output.append(f"JGE {done_label}")
                self.current_output.append("MOV P0, P1")
                self.current_output.append("MUL P0, 2")
                self.current_output.append("ADD P0, P5")
                self.current_output.append("MOV P6, [P0]")
                self.current_output.append("MOV P3, P2")
                self.current_output.append("MUL P3, 2")
                self.current_output.append("ADD P3, P5")
                self.current_output.append("MOV P7, [P3]")
                self.current_output.append("MOV [P0], P7")
                self.current_output.append("MOV [P3], P6")
                self.current_output.append("INC P1")
                self.current_output.append("DEC P2")
                self.current_output.append(f"JMP {loop_label}")
                self.current_output.append(f"{done_label}:")
                self.current_output.append(f"MOV {target_reg}, P4")
        elif func_name == "GETKEY":
            # Non-blocking: returns key code or 0 if no key available
            self.current_output.append("KEYIN R0")          # Read key (0 if empty)
            self.current_output.append(f"MOV {target_reg}, R0")
        elif func_name == "SERIN":
            # Read one byte from the serial RX FIFO (0 if empty)
            self.current_output.append("SERIN R0")
            self.current_output.append(f"MOV {target_reg}, R0")
        elif func_name == "SERSTAT":
            # Read serial status flags (0x01=RX available, 0x02=TX complete)
            self.current_output.append("SERSTAT R0")
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
                dest_reg = self.allocate_p_register(['P1', 'P2', 'P3'])
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
                        dest_reg = self.allocate_p_register(['P1', 'P2', 'P3'])
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
                addr_reg = self._select_address_scratch_reg(exclude={'P0', source_reg})
                self.current_output.append(f"MOV {addr_reg}, {spill_addr}")
                self.current_output.append(f"MOV [{addr_reg}], P0")
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
            addr_reg = self._select_address_scratch_reg(exclude={'P0', source_reg})
            self.current_output.append(f"MOV {addr_reg}, {addr}")
            self.current_output.append(f"MOV [{addr_reg}], P0")
        else:
            # For 16-bit P registers, avoid clobbering the source register when it is P0
            addr_reg = 'P1' if source_reg == 'P0' else 'P0'
            self.current_output.append(f"MOV {addr_reg}, {addr}")
            self.current_output.append(f"MOV [{addr_reg}], {source_reg}")

    def _select_address_scratch_reg(self, exclude: Optional[Set[str]] = None) -> str:
        """Pick a P-register scratch for address operands without clobbering live variable registers."""
        excluded = set(exclude or set())

        # Prefer classic scratch registers first, but keep P7 reserved for call linkage.
        candidates = ['P1', 'P2', 'P3', 'P4', 'P5', 'P6']

        live_vars = self.live_at_point.get(self.program_counter, set())
        blocked = {self.var_reg.get(v) for v in live_vars if v in self.var_reg}
        blocked.discard(None)

        for reg in candidates:
            if reg in excluded:
                continue
            if self.register_usage.get(reg, False):
                continue
            if reg in blocked:
                continue
            return reg

        for reg in candidates:
            if reg in excluded:
                continue
            if reg in blocked:
                continue
            return reg

        return 'P1' if 'P1' not in excluded else 'P2'

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

    def _is_list_identifier(self, name: str) -> bool:
        """Return True for TI-style list identifiers like L1, L2, ..."""
        if not isinstance(name, str):
            return False
        if not name.startswith("L"):
            return False
        suffix = name[1:]
        return suffix.isdigit() and len(suffix) > 0

    def _get_or_create_list_descriptor(self, list_name: str) -> int:
        """Allocate (or return) a descriptor storing list base/capacity words."""
        if list_name not in self.list_descriptors:
            desc_addr = self.next_address
            self.list_descriptors[list_name] = desc_addr
            self.next_address += 4  # base pointer + capacity (16-bit each)
            self.list_runtime_required = True
        return self.list_descriptors[list_name]

    def _collect_dynamic_list_descriptors(self, program: Program):
        """Scan AST for list usage so descriptors are allocated before code emission."""

        list_builtins = {"FILL", "SORTA", "SORTD", "SEQ", "REVERSE", "SUM", "MEAN", "DIM"}

        def walk_expression(expr: Expression):
            if expr is None:
                return

            if isinstance(expr, ListAccessExpr):
                self._get_or_create_list_descriptor(expr.list_name)
                walk_expression(expr.index)
                return

            if isinstance(expr, MatrixAccessExpr):
                walk_expression(expr.row)
                walk_expression(expr.col)
                return

            if isinstance(expr, MemberAccessExpr):
                walk_expression(expr.object)
                return

            if isinstance(expr, BinaryExpr):
                walk_expression(expr.left)
                walk_expression(expr.right)
                return

            if isinstance(expr, UnaryExpr):
                walk_expression(expr.expression)
                return

            if isinstance(expr, GroupingExpr):
                walk_expression(expr.expression)
                return

            if isinstance(expr, FunctionCallExpr):
                func_name = expr.name.upper()
                if func_name in list_builtins and expr.arguments:
                    first_arg = expr.arguments[0]
                    if isinstance(first_arg, VariableExpr):
                        # Keep compatibility with TI-style list names and also
                        # support bracket-created list variables.
                        self._get_or_create_list_descriptor(first_arg.name)
                for arg in expr.arguments:
                    walk_expression(arg)

        def walk_statement(stmt: Statement):
            if stmt is None:
                return

            if isinstance(stmt, AssignmentStmt):
                walk_expression(stmt.variable)
                walk_expression(stmt.expression)
                return

            if isinstance(stmt, ExpressionStmt):
                walk_expression(stmt.expression)
                return

            if isinstance(stmt, FunctionCallStmt):
                walk_expression(stmt.function_call)
                return

            if isinstance(stmt, IfStmt):
                walk_expression(stmt.condition)
                for branch_stmt in stmt.then_branch:
                    walk_statement(branch_stmt)
                if stmt.else_branch:
                    for branch_stmt in stmt.else_branch:
                        walk_statement(branch_stmt)
                return

            if isinstance(stmt, (ForStmt, WhileStmt, RepeatStmt)):
                if isinstance(stmt, ForStmt):
                    walk_expression(stmt.start)
                    walk_expression(stmt.end)
                    if stmt.step is not None:
                        walk_expression(stmt.step)
                elif isinstance(stmt, WhileStmt):
                    walk_expression(stmt.condition)
                else:
                    walk_expression(stmt.condition)

                for body_stmt in stmt.body:
                    walk_statement(body_stmt)
                return

            if isinstance(stmt, InputStmt):
                walk_expression(stmt.prompt)
                return

            if isinstance(stmt, DispStmt):
                walk_expression(stmt.text)
                return

            if isinstance(stmt, ReturnStmt):
                if stmt.value is not None:
                    walk_expression(stmt.value)
                return

            if isinstance(stmt, FunctionDefStmt):
                for _, default_expr in stmt.params:
                    if default_expr is not None:
                        walk_expression(default_expr)
                for body_stmt in stmt.body:
                    walk_statement(body_stmt)
                return

        for statement in program.statements:
            walk_statement(statement)

    def _emit_list_runtime_init(self):
        """Emit startup initialization for dynamic list descriptors and heap pointer."""
        if not self.list_descriptors:
            return

        # Shared allocator pointer cell.
        self.list_heap_next_addr = self.get_variable_address("__NB_LIST_HEAP_NEXT")
        self.current_output.append(f"MOV P0, 0x{self.list_heap_next_addr:04X}")
        self.current_output.append(f"MOV P1, 0x{self.list_heap_start:04X}")
        self.current_output.append("MOV [P0], P1")

        # Zero each descriptor (base=0, capacity=0).
        for desc_addr in self.list_descriptors.values():
            self.current_output.append(f"MOV P0, 0x{desc_addr:04X}")
            self.current_output.append("MOV P1, 0")
            self.current_output.append("MOV [P0], P1")
            self.current_output.append("INC P0")
            self.current_output.append("INC P0")
            self.current_output.append("MOV [P0], P1")

    def _emit_list_runtime_helper(self):
        """Emit dynamic list element-address helper used by list load/store/builtins."""
        if not self.list_runtime_required or self.list_heap_next_addr is None:
            return

        self.current_output.append("")
        self.current_output.append("_nb_list_elem_addr:")
        self.current_output.append("; In:  P1=descriptor address, P2=1-based index")
        self.current_output.append("; Out: P0=element address (or 0 on invalid index/OOM)")
        self.current_output.append("PUSH P2")
        self.current_output.append("CMP P2, 1")
        self.current_output.append("JLT _nb_list_elem_addr_fail")
        self.current_output.append("MOV P3, [P1]")
        self.current_output.append("MOV P0, P1")
        self.current_output.append("INC P0")
        self.current_output.append("INC P0")
        self.current_output.append("MOV P4, [P0]")
        self.current_output.append("CMP P2, P4")
        self.current_output.append("JLE _nb_list_have_capacity")
        self.current_output.append(f"MOV P5, 0x{self.list_heap_next_addr:04X}")
        self.current_output.append("MOV P6, [P5]")
        self.current_output.append("MOV P0, P2")
        self.current_output.append("MOV P2, P4")
        self.current_output.append("CMP P2, 0")
        self.current_output.append("JGT _nb_list_cap_from_existing")
        self.current_output.append("MOV P2, 8")
        self.current_output.append("JMP _nb_list_cap_ready_base")
        self.current_output.append("_nb_list_cap_from_existing:")
        self.current_output.append("MUL P2, 2")
        self.current_output.append("_nb_list_cap_ready_base:")
        self.current_output.append("CMP P2, P0")
        self.current_output.append("JGE _nb_list_cap_ready")
        self.current_output.append("MOV P2, P0")
        self.current_output.append("_nb_list_cap_ready:")
        self.current_output.append("MOV P0, P2")
        self.current_output.append("MUL P0, 2")
        self.current_output.append("MOV P5, P6")
        self.current_output.append("ADD P5, P0")
        self.current_output.append("DEC P5")
        self.current_output.append(f"MOV P0, 0x{self.list_heap_end:04X}")
        self.current_output.append("CMP P0, P5")
        self.current_output.append("JC _nb_list_elem_addr_fail")
        self.current_output.append("MOV P5, 0")
        self.current_output.append("_nb_list_zero_loop:")
        self.current_output.append("CMP P5, P2")
        self.current_output.append("JGE _nb_list_zero_done")
        self.current_output.append("MOV P0, P5")
        self.current_output.append("MUL P0, 2")
        self.current_output.append("ADD P0, P6")
        self.current_output.append("MOV [P0], 0")
        self.current_output.append("INC P5")
        self.current_output.append("JMP _nb_list_zero_loop")
        self.current_output.append("_nb_list_zero_done:")
        self.current_output.append("PUSH P1")
        self.current_output.append("CMP P4, 0")
        self.current_output.append("JLE _nb_list_copy_done")
        self.current_output.append("MOV P5, 0")
        self.current_output.append("_nb_list_copy_loop:")
        self.current_output.append("CMP P5, P4")
        self.current_output.append("JGE _nb_list_copy_done")
        self.current_output.append("MOV P0, P5")
        self.current_output.append("MUL P0, 2")
        self.current_output.append("ADD P0, P3")
        self.current_output.append("MOV P1, [P0]")
        self.current_output.append("MOV P0, P5")
        self.current_output.append("MUL P0, 2")
        self.current_output.append("ADD P0, P6")
        self.current_output.append("MOV [P0], P1")
        self.current_output.append("INC P5")
        self.current_output.append("JMP _nb_list_copy_loop")
        self.current_output.append("_nb_list_copy_done:")
        self.current_output.append("POP P1")
        self.current_output.append("MOV [P1], P6")
        self.current_output.append("MOV P0, P1")
        self.current_output.append("INC P0")
        self.current_output.append("INC P0")
        self.current_output.append("MOV [P0], P2")
        self.current_output.append("MOV P0, P2")
        self.current_output.append("MUL P0, 2")
        self.current_output.append("ADD P0, P6")
        self.current_output.append(f"MOV P5, 0x{self.list_heap_next_addr:04X}")
        self.current_output.append("MOV [P5], P0")
        self.current_output.append("MOV P3, P6")
        self.current_output.append("MOV P4, P2")
        self.current_output.append("_nb_list_have_capacity:")
        self.current_output.append("POP P2")
        self.current_output.append("MOV P0, P2")
        self.current_output.append("DEC P0")
        self.current_output.append("MUL P0, 2")
        self.current_output.append("ADD P0, P3")
        self.current_output.append("RET")
        self.current_output.append("_nb_list_elem_addr_fail:")
        self.current_output.append("POP P2")
        self.current_output.append("XOR P0, P0")
        self.current_output.append("RET")

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
