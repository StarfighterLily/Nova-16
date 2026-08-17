# Astrid Language Code Generator
# File: astrid/codegen/codegen.py
# Translates Astrid AST to Nova-16 assembly code with register allocation optimizations

from typing import List, Dict, Optional, Set, Tuple
from collections import Counter
from astrid.parser.parser import (
    Program, FunctionDef, VarDecl, Assignment, Return, If, While, DoWhile, For, FuncCall,
    Switch, Case,
    Expression, Number, StringLiteral, CharLiteral, Identifier, BinaryOp, UnaryOp, PostfixOp,
    Break, Continue
)
from astrid.codegen.optimizations import (
    ExpressionSimplifier,
    FunctionInliner,
    StrengthReducer,
    RegisterColoringPass,
    HotSpillAnalyzer,
    DynamicSpillAllocator,
    get_optimization_config,
)

class CodeGenerator:
    # Generates Nova-16 assembly code from Astrid AST with enhanced register allocation
    DATA_REGION_START = 0x0120
    LIVE_RANGE_SCHEDULER_MAX_LINES = 384
    LIVE_RANGE_SCHEDULER_MAX_WORK = 24576

    def __init__(self, enable_peephole: bool = True, debug_optimizations: bool = False,
                 enable_expr_simplify: bool = True, enable_live_range: bool = True,
                 enable_optimizations: bool = True,
                 enable_live_range_scheduling: Optional[bool] = None):
        self.debug_optimizations = debug_optimizations
        self.opt_config = get_optimization_config()
        self.opt_config['debug_optimizations'] = debug_optimizations

        if enable_live_range_scheduling is not None:
            enable_live_range = enable_live_range_scheduling

        self.enable_optimizations = bool(enable_optimizations)
        if debug_optimizations:
            self.enable_optimizations = True

        self.enable_peephole = bool(enable_peephole)
        self.enable_expr_simplify = bool(enable_expr_simplify) and self.enable_optimizations
        self.enable_live_range = bool(enable_live_range) and self.enable_optimizations
        self.enable_live_range_scheduling = self.enable_live_range
        self.assembly = []
        self.global_vars = {}
        self.local_vars = {}
        self.var_types = {}  # name -> 'int' (16-bit, 2 bytes) or 'char' (8-bit)
        self.functions = {}
        self.strings = {}
        self.string_counter = 0
        self.label_counter = 0
        self.reg_counter = 0 
        self.current_function = None
        self.builtin_functions = self._init_builtins()
        # Stack of (start_label, end_label) for break/continue support
        self.loop_stack = []
        
        # Access count tracking for hot variable optimization
        self.variable_access_counts: Dict[str, int] = Counter()
        # Spill allocations (var -> absolute memory address) determined by
        # the dynamic spill allocator. Populated during function generation.
        self.spill_allocations: Dict[str, int] = {}
        
        # Unified liveness tracking
        self.live_ranges: Dict[str, Tuple[int, int]] = {}  # name -> (start, end)
        self.live_at_point: Dict[int, Set[str]] = {}  # program_point -> set of live variables
        
        # Interference graph (tracks which variables cannot share registers)
        self.interference_graph: Dict[str, Set[str]] = {}  # variable -> set of interfering variables
        
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
        
        # Preferred register order for allocation (P registers first for 16-bit, 
        # then R registers as fallback for 8-bit).
        # P3 is excluded (reserved for DIV remainder storage).
        self.allocation_order = [
            'P0', 'P1', 'P2', 'P4', 'P5', 'P6',
            'R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9',
        ]
        
        # Variable register allocation (maps variable name to register)
        self.var_reg: Dict[str, str] = {}
        
        # Auto-free register set (registers freed after last use)
        self.auto_free_registers: Set[str] = set()
        
        # Register allocation statistics
        self.allocation_stats = {
            'total_allocations': 0,
            'total_deallocations': 0,
            'allocation_failures': 0,
            'max_simultaneous_allocated': 0
        }

    def _init_builtins(self) -> Dict[str, str]:
        # Initialize built-in function to assembly mappings
        return {
            'set_mode': 'builtin_set_vmode', 'set_vmode': 'builtin_set_vmode',
            'set_layer': 'builtin_set_layer', 'set_pos': 'builtin_set_pos',
            'write_screen': 'builtin_write_screen', 'read_screen': 'builtin_read_screen',
            'scroll_x': 'builtin_scroll_x', 'scroll_y': 'builtin_scroll_y',
            'set_pointers': 'builtin_set_pointers', 'write_text': 'builtin_write_text',
            'set_font': 'builtin_set_font', 'sound_play': 'builtin_sound_play',
            'sound_stop': 'builtin_sound_stop', 'set_timer': 'builtin_set_timer',
            'sti': 'builtin_sti', 'cli': 'builtin_cli', 'iret': 'builtin_iret',
            'key_available': 'builtin_key_available', 'key_read': 'builtin_key_read',
            'key_clear': 'builtin_key_clear', 'random': 'builtin_random',
            'random_range': 'builtin_random_range', 'halt': 'builtin_halt',
            'enable_interrupts': 'builtin_sti', 'disable_interrupts': 'builtin_cli'
        }

    def _should_run_live_range_scheduler(self, assembly_lines: List[str]) -> Tuple[bool, str]:
        """Return whether the live-range scheduler is worth the compile-time cost."""
        line_count = len(assembly_lines)
        live_range_count = len(self.live_ranges)
        work_estimate = line_count * max(1, live_range_count)

        if line_count > self.LIVE_RANGE_SCHEDULER_MAX_LINES:
            return (
                False,
                f"line count {line_count} exceeds threshold {self.LIVE_RANGE_SCHEDULER_MAX_LINES}",
            )

        if work_estimate > self.LIVE_RANGE_SCHEDULER_MAX_WORK:
            return (
                False,
                f"work estimate {work_estimate} exceeds threshold {self.LIVE_RANGE_SCHEDULER_MAX_WORK} "
                f"({line_count} lines x {live_range_count} live ranges)",
            )

        return (
            True,
            f"within budget ({line_count} lines, {live_range_count} live ranges, work {work_estimate})",
        )

    def generate(self, ast: Program) -> List[str]:
        self.assembly.append("; Generated by the Astrid Compiler for Nova-16")
        # Run front-end expression simplifier (constant-folding, algebraic
        # simplifications, and CSE) to reduce register pressure and code size.
        if self.enable_optimizations and self.enable_expr_simplify:
            try:
                simplifier = ExpressionSimplifier(debug=self.debug_optimizations)
                for func in ast.functions:
                    self._simplify_function_expressions(func, simplifier)
                if self.debug_optimizations:
                    print("[CODEGEN] Expression simplification applied to AST")
            except Exception:
                if self.debug_optimizations:
                    import traceback; traceback.print_exc()

        # Run function inlining pass (conservative) to eliminate small
        # call/return overhead and enable further optimizations. This must
        # run after expression simplification so constant-folding helps the
        # inliner decide eligibility.
        try:
            if self.enable_optimizations and self.opt_config.get('enable_function_inlining', True):
                inliner = FunctionInliner(
                    max_statements=self.opt_config.get('inlining_max_statements', 8),
                    min_call_sites=self.opt_config.get('inlining_min_call_sites', 2),
                    debug=self.debug_optimizations
                )
                # Analyze and inline; ast.functions is a list of FunctionDef
                try:
                    inlineable = inliner.analyze(ast.functions)
                    if inlineable and self.debug_optimizations:
                        print(f"[CODEGEN] Functions eligible for inlining: {inlineable}")
                except Exception:
                    # Some AST shapes may differ; fallback to conservative behavior
                    if self.debug_optimizations:
                        import traceback; traceback.print_exc()

                try:
                    ast.functions = inliner.inline_functions(ast.functions, inlineable if 'inlineable' in locals() else None)
                    if self.debug_optimizations:
                        print("[CODEGEN] Function inlining applied to AST")
                except Exception:
                    if self.debug_optimizations:
                        import traceback; traceback.print_exc()
        except Exception:
            if self.debug_optimizations:
                import traceback; traceback.print_exc()

        # Run strength reduction pass to convert multiplications by powers of 2
        # to left shifts for better performance. Applied after inlining so that
        # inlined multiply operations can be optimized.
        try:
            if self.enable_optimizations and self.opt_config.get('enable_strength_reduction', True):
                reducer = StrengthReducer(debug=self.debug_optimizations)
                for func in ast.functions:
                    func.body = reducer.reduce(func.body)
                if self.debug_optimizations:
                    print("[CODEGEN] Strength reduction applied to AST")
        except Exception:
            if self.debug_optimizations:
                import traceback; traceback.print_exc()

        # Main entry point MUST be first segment so emulator sets PC correctly
        self.assembly.append("ORG 0x1000")
        self.assembly.append("start:")
        self.assembly.append("    MOV SP, 0xFF00 ; Set stack pointer to high memory")
        self.assembly.append("    MOV FP, 0xFF00 ; Also init frame pointer")
        self.assembly.append("    CALL func_main")
        self.assembly.append("    HLT")
        self.assembly.append("")

        # Emit interrupt vector FIRST at 0x0100 (before functions)
        if any(func.name == 'timer_interrupt' for func in ast.functions):
            self.assembly.append("ORG 0x0100")
            self.assembly.append("    DW func_timer_interrupt")
            # Skip past the interrupt vector table (0x0100-0x011F, 8 vectors x 4 bytes)
            self.assembly.append("ORG 0x0120")
            self.assembly.append("")

        # Generate all functions and data AFTER interrupt vector
        for func_def in ast.functions:
            self.generate_function(func_def)

        self.generate_strings()
        self.generate_builtins()

        assembly_output = "\n".join(self.assembly)
        assembly_lines = assembly_output.splitlines()

        if self.enable_optimizations and self.enable_live_range:
            should_schedule, schedule_reason = self._should_run_live_range_scheduler(assembly_lines)
            if should_schedule:
                try:
                    from astrid.codegen.live_range_scheduler import LiveRangeScheduler
                    scheduler = LiveRangeScheduler(debug=self.debug_optimizations)
                    assembly_lines = scheduler.schedule(assembly_lines, self.live_ranges)
                    if self.debug_optimizations:
                        print("[CODEGEN] Live-range scheduling applied")
                except Exception:
                    if self.debug_optimizations:
                        import traceback; traceback.print_exc()
            elif self.debug_optimizations:
                print(f"[CODEGEN] Skipping live-range scheduling: {schedule_reason}")

        if self.enable_optimizations and self.enable_peephole:
            from astrid.codegen.peephole import PeepholeOptimizer
            peephole_opt = PeepholeOptimizer(debug=self.debug_optimizations)
            assembly_output = peephole_opt.optimize("\n".join(assembly_lines))
            assembly_lines = assembly_output.splitlines()

            if self.debug_optimizations:
                print("[CODEGEN] Peephole optimization applied")
                print(f"[CODEGEN] Original: {len(self.assembly)} lines, Optimized: {len(assembly_lines)} lines")

        return assembly_lines

    def _simplify_function_expressions(self, func: FunctionDef, simplifier: ExpressionSimplifier):
        """Walk a function AST and simplify expression nodes in-place."""
        def simplify_node(node):
            if node is None:
                return None
            if isinstance(node, (Number, Identifier, StringLiteral, CharLiteral, BinaryOp, UnaryOp, PostfixOp, FuncCall)):
                return simplifier.simplify(node)
            if isinstance(node, VarDecl):
                if node.value is not None:
                    node.value = simplify_node(node.value)
                return node
            if isinstance(node, Assignment):
                node.value = simplify_node(node.value)
                return node
            if isinstance(node, Return):
                if node.value is not None:
                    node.value = simplify_node(node.value)
                return node
            if isinstance(node, If):
                node.cond = simplify_node(node.cond)
                node.then_body = [simplify_node(n) or n for n in node.then_body]
                if node.else_body:
                    node.else_body = [simplify_node(n) or n for n in node.else_body]
                return node
            if isinstance(node, While):
                node.cond = simplify_node(node.cond)
                node.body = [simplify_node(n) or n for n in node.body]
                return node
            if isinstance(node, DoWhile):
                node.cond = simplify_node(node.cond)
                node.body = [simplify_node(n) or n for n in node.body]
                return node
            if isinstance(node, For):
                if node.init is not None:
                    if isinstance(node.init, list):
                        node.init = [simplify_node(n) or n for n in node.init]
                    else:
                        node.init = simplify_node(node.init)
                if node.cond is not None:
                    node.cond = simplify_node(node.cond)
                if node.update is not None:
                    node.update = simplify_node(node.update)
                node.body = [simplify_node(n) or n for n in node.body]
                return node
            if isinstance(node, Switch):
                node.expr = simplify_node(node.expr)
                for case in node.cases:
                    case.value = simplify_node(case.value)
                    case.body = [simplify_node(n) or n for n in case.body]
                if node.default_body:
                    node.default_body = [simplify_node(n) or n for n in node.default_body]
                return node
            if isinstance(node, list):
                return [simplify_node(n) or n for n in node]
            return node

        func.body = [simplify_node(n) or n for n in func.body]

    def generate_strings(self):
        if not self.strings:
            return
        self.assembly.append(";")
        self.assembly.append("; Data Section")
        self.assembly.append(";")
        for value, label in self.strings.items():
            self.assembly.append(f"{label}: DEFSTR \"{value}\"")
        self.assembly.append("")

    def find_local_vars(self, statements: List) -> List[VarDecl]:
        # Recursively find all VarDecl nodes in a list of statements.
        decls = []
        for stmt in statements:
            if isinstance(stmt, VarDecl):
                decls.append(stmt)
            elif isinstance(stmt, list):
                decls.extend(self.find_local_vars(stmt))
            elif isinstance(stmt, If):
                decls.extend(self.find_local_vars(stmt.then_body))
                if stmt.else_body:
                    decls.extend(self.find_local_vars(stmt.else_body))
            elif isinstance(stmt, While):
                decls.extend(self.find_local_vars(stmt.body))
            elif isinstance(stmt, DoWhile):
                decls.extend(self.find_local_vars(stmt.body))
            elif isinstance(stmt, For):
                if isinstance(stmt.init, list):
                    decls.extend(stmt.init)
                decls.extend(self.find_local_vars(stmt.body))
            elif isinstance(stmt, Switch):
                for case in stmt.cases:
                    decls.extend(self.find_local_vars(case.body))
                if stmt.default_body:
                    decls.extend(self.find_local_vars(stmt.default_body))
        return decls

    def _var_size(self, name: str) -> int:
        # Return storage size in bytes for a variable (2 for int, 1 for char).
        return 2 if self.var_types.get(name) == 'int' else 1

    def _is_int_var(self, name: str) -> bool:
        return self.var_types.get(name) == 'int'

    def _get_local_offset(self, name: str) -> int:
        offset = self.local_vars[name]['offset']
        return offset

    def _emit_local_load(self, reg: str, name: str):
        offset = self._get_local_offset(name)
        is_int = self._is_int_var(name)
        var_size = 2 if is_int else 1
        # Record access for hot-variable optimization.
        self.variable_access_counts[name] += 1
        # If this local was migrated to a spill allocation, load from that
        # absolute address instead of the frame pointer slot. Do NOT do this
        # for `timer_interrupt` (uses SP-relative locals).
        if name in self.spill_allocations and self.current_function != 'timer_interrupt':
            addr = self.spill_allocations[name]
            self.emit(f"    MOV {reg}, [0x{addr:04X}]")
            return
        if self.current_function == 'timer_interrupt':
            # Interrupt handler uses SP-relative locals (no ENTER/FP).
            # After "SUB SP, N", the first local (offset=-size) is at SP+0,
            # the second (offset=-2*size) is at SP+size, etc.
            # In general the byte offset from SP is: -(offset) - var_size.
            sp_offset = -offset - var_size
            self.emit(f"    MOV {reg}, [SP+{sp_offset}]")
        else:
            # Use [FP+offset] direct indexed addressing. This avoids
            # clobbering P2, which get_register() may have already
            # allocated as an expression temporary.
            self.emit(f"    MOV {reg}, [FP{offset:+d}]")

    def _emit_local_store(self, name: str, src_reg: str):
        offset = self._get_local_offset(name)
        is_int = self._is_int_var(name)
        var_size = 2 if is_int else 1
        # Record access frequency for hot-variable optimization.
        self.variable_access_counts[name] += 1
        # If this local was migrated to a spill allocation, store to that
        # absolute address instead of the frame pointer slot. Do NOT do this
        # for `timer_interrupt` (uses SP-relative locals).
        if name in self.spill_allocations and self.current_function != 'timer_interrupt':
            addr = self.spill_allocations[name]
            self.emit(f"    MOV [0x{addr:04X}], {src_reg}")
            return
        if self.current_function == 'timer_interrupt':
            # Interrupt handler uses SP-relative locals (no ENTER/FP) — see
            # _emit_local_load for the offset formula.
            sp_offset = -offset - var_size
            self.emit(f"    MOV [SP+{sp_offset}], {src_reg}")
        else:
            # Use [FP+offset] direct indexed addressing. This avoids
            # clobbering P2, which get_register() may have already
            # allocated as an expression temporary.
            self.emit(f"    MOV [FP{offset:+d}], {src_reg}")

    def generate_function(self, func_def: FunctionDef):
        self.functions[func_def.name] = {
            'label': f'func_{func_def.name}',
            'params': len(func_def.params),
            'return_type': func_def.return_type
        }

        # Clear spill allocations for this function (per-function scope)
        self.spill_allocations = {}
        
        # Apply register-coloring metadata pass to local variables. This is a
        # lightweight, conservative optimization pass that records likely color
        # assignments without breaking the current expression-temporary allocator.
        if self.local_vars:
            # Reset to safe local variable scope for this function.
            pass
        
        self.current_function = func_def.name
        self.local_vars = {}
        self.var_types = {}
        
        self.assembly.append(f"; Function: {func_def.name}")
        self.assembly.append(f"func_{func_def.name}:")
        
        all_local_decls = self.find_local_vars(func_def.body)
        
        # Compute stack frame size: each int var/param takes 2 bytes, char takes 1
        # Params: int params use 2 bytes each, char params use 1 byte
        param_size = 0
        for param in func_def.params:
            self.var_types[param.name] = param.var_type
            param_size += 2 if param.var_type == 'int' else 1
        
        local_size = 0
        for decl in all_local_decls:
            self.var_types[decl.name] = decl.var_type
            local_size += 2 if decl.var_type == 'int' else 1
        
        if func_def.name == 'timer_interrupt':
            # Interrupt handlers must NOT use ENTER/LEAVE because the CPU
            # already pushed PC and flags on the stack. Use direct SP
            # manipulation instead so IRET can find the saved context.
            if local_size > 0:
                self.assembly.append(f"    SUB SP, {local_size} ; Allocate locals")
        else:
            self.assembly.append(f"    ENTER {local_size}")

        # Param offsets: after ENTER pushes FP (2 bytes) and CALL pushes ret addr (2 bytes),
        # params are at positive offsets from FP starting at +4.
        param_offset = 4
        for param in func_def.params:
            self.local_vars[param.name] = {'offset': param_offset}
            param_offset += 2 if param.var_type == 'int' else 1

        # Local offsets: start at -2 going down (2 bytes per slot for simplicity;
        # char vars also get 2 bytes to keep word access alignment simple)
        local_offset = 0
        for decl in all_local_decls:
            local_offset += 2 if decl.var_type == 'int' else 1
            self.local_vars[decl.name] = {'offset': -local_offset}

        # Store locals_size for iret() cleanup
        self._timer_interrupt_locals_size = local_size if func_def.name == 'timer_interrupt' else 0
        self._emitted_return = False

        # Run a lightweight register-coloring pass to record assignment hints.
        # IMPORTANT: Only process actual local variables (VarDecl), not parameters.
        # Parameters have their own stack offsets and should never be spilled to zero-page.
        if self.local_vars:
            # Separate parameters from local variables
            param_names = {p.name for p in func_def.params}
            actual_local_names = [name for name in self.local_vars if name not in param_names]
            
            if actual_local_names:
                candidate_graph: Dict[str, Set[str]] = {name: set() for name in actual_local_names}
                for i, name in enumerate(actual_local_names):
                    for other in actual_local_names[i + 1:]:
                        candidate_graph[name].add(other)
                        candidate_graph[other].add(name)
                available_regs = ['P0', 'P1', 'P2', 'P4', 'P5', 'P6', 'R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9']
                color_map = RegisterColoringPass(candidate_graph, available_regs, debug=self.debug_optimizations).color_graph()
                if color_map:
                    self.var_reg.update(color_map)
                    if self.debug_optimizations:
                        print(f"[CODEGEN] Register colors assigned in {func_def.name}: {color_map}")

                hot = HotSpillAnalyzer(
                    spill_slots={name: idx for idx, name in enumerate(actual_local_names)},
                    access_counts={name: self.variable_access_counts.get(name, 0) for name in actual_local_names},
                    debug=self.debug_optimizations,
                )
                hot_spills = hot.identify_hot_spills(threshold_percentile=75.0)
                if hot_spills and self.debug_optimizations:
                    print(f"[CODEGEN] Hot spills for {func_def.name}: {hot_spills}")

                # Use DynamicSpillAllocator to assign concrete spill addresses
                # (fallback to a larger spill region) for hot/spilled locals.
                try:
                    allocator = DynamicSpillAllocator(
                        spill_slots={name: idx for idx, name in enumerate(actual_local_names)},
                        access_counts={name: self.variable_access_counts.get(name, 0) for name in actual_local_names},
                        debug=self.debug_optimizations,
                        zero_page_base=self.opt_config.get('zero_page_base', 0x0080),
                        zero_page_size=self.opt_config.get('zero_page_size', 128),
                    )
                    allocs = allocator.allocate()
                    for var, addr in allocs.items():
                        self.spill_allocations[var] = addr
                    if allocs and self.debug_optimizations:
                        print(f"[CODEGEN] Spill allocations for {func_def.name}: {allocs}")
                except Exception:
                    if self.debug_optimizations:
                        import traceback; traceback.print_exc()

        self.generate_block(func_def.body)

        # Only emit implicit return if the function didn't already return (e.g. via iret)
        if func_def.return_type == 'void' and not self._emitted_return:
            self.assembly.append("; Implicit return for void function")
            self.assembly.append("    MOV SP, FP")
            self.assembly.append("    POP FP")
            self.assembly.append("    RET")

        self.assembly.append("")
        self.current_function = None

    def generate_block(self, body: List):
        for statement in body:
            if isinstance(statement, list):
                self.generate_block(statement)
            elif isinstance(statement, VarDecl):
                self.generate_var_decl(statement)
            elif isinstance(statement, Assignment):
                self.generate_assignment(statement)
            elif isinstance(statement, Return):
                self.generate_return(statement)
            elif isinstance(statement, If):
                self.generate_if(statement)
            elif isinstance(statement, While):
                self.generate_while(statement)
            elif isinstance(statement, DoWhile):
                self.generate_do_while(statement)
            elif isinstance(statement, Switch):
                self.generate_switch(statement)
            elif isinstance(statement, For):
                self.generate_for(statement)
            elif isinstance(statement, Break):
                self.generate_break()
            elif isinstance(statement, Continue):
                self.generate_continue()
            elif isinstance(statement, FuncCall):
                if statement.name == 'iret' and self.current_function == 'timer_interrupt':
                    # Special handling for iret: don't emit normal epilogue
                    if hasattr(self, '_timer_interrupt_locals_size') and self._timer_interrupt_locals_size > 0:
                        self.emit(f"    ADD SP, {self._timer_interrupt_locals_size} ; Deallocate locals before IRET")
                    self.emit("    IRET")
                    self._emitted_return = True
                    return  # Exit function after IRET
                else:
                    self.generate_call(statement)
            elif isinstance(statement, Expression):
                self.generate_expression(statement)
            else:
                raise RuntimeError(f"Unknown statement type: {type(statement)}")

    def generate_var_decl(self, var_decl: VarDecl):
        if var_decl.value:
            self.emit_comment(f"var {var_decl.name} = ...")
            reg = self.generate_expression(var_decl.value)
            self._emit_local_store(var_decl.name, reg)
            self.free_register()

    def generate_assignment(self, assignment: Assignment):
        self.emit_comment(f"Assignment to {assignment.name}")
        # Check for compound assignment pattern: x = x <op> rhs
        # The parser decomposes x += y into Assignment('x', BinaryOp(Identifier('x'), '+', y))
        if (isinstance(assignment.value, BinaryOp) and
            isinstance(assignment.value.left, Identifier) and
            assignment.value.left.name == assignment.name):
            op = assignment.value.op
            var_reg = self.get_register()
            self._emit_local_load(var_reg, assignment.name)
            if op in ['<<', '>>']:
                # Shift operations: amount must be a constant (parser requires this)
                if not isinstance(assignment.value.right, Number):
                    raise TypeError("Shift amount must be a constant integer for this compiler version.")
                shift_amount = int(assignment.value.right.value, 0)
                op_mnemonic = "SHR" if op == '>>' else "SHL"
                self.emit_comment(f"Compound shift {op_mnemonic} by {shift_amount}")
                for _ in range(shift_amount):
                    self.emit(f"    {op_mnemonic} {var_reg}")
            else:
                rhs_reg = self.generate_expression(assignment.value.right)
                if op == '+': self.emit(f"    ADD {var_reg}, {rhs_reg}")
                elif op == '-': self.emit(f"    SUB {var_reg}, {rhs_reg}")
                elif op == '*': self.emit(f"    MUL {var_reg}, {rhs_reg}")
                elif op == '/': self.emit(f"    DIV {var_reg}, {rhs_reg}")
                elif op == '&': self.emit(f"    AND {var_reg}, {rhs_reg}")
                elif op == '|': self.emit(f"    OR {var_reg}, {rhs_reg}")
                elif op == '^': self.emit(f"    XOR {var_reg}, {rhs_reg}")
                else: raise SyntaxError(f"Unknown compound operator '{op}'")
                self.free_register()
            self._emit_local_store(assignment.name, var_reg)
            self.free_register()
        else:
            reg = self.generate_expression(assignment.value)
            if assignment.name in self.local_vars:
                self._emit_local_store(assignment.name, reg)
            else:
                raise NameError(f"Undefined variable '{assignment.name}'")
            self.free_register()

    def generate_return(self, return_stmt: Return):
        self.emit_comment("Function return")
        if return_stmt.value:
            reg = self.generate_expression(return_stmt.value)
            self.emit(f"    MOV R0, {reg}")
            self.free_register()
        self.emit("    MOV SP, FP")
        self.emit("    POP FP")
        self.emit("    RET")
        self._emitted_return = True

    def generate_if(self, if_stmt: If):
        self.emit_comment("If statement")
        end_label = self.generate_label("if_end")
        else_label = self.generate_label("if_else")
        reg = self.generate_expression(if_stmt.cond)
        self.emit(f"    CMP {reg}, 0")
        self.free_register()
        self.emit(f"    JZ {else_label if if_stmt.else_body else end_label}")
        self.generate_block(if_stmt.then_body)
        if if_stmt.else_body:
            self.emit(f"    JMP {end_label}")
            self.emit_label(else_label)
            self.generate_block(if_stmt.else_body)
        self.emit_label(end_label)

    def generate_while(self, while_stmt: While):
        self.emit_comment("While loop")
        start_label = self.generate_label("while_start")
        end_label = self.generate_label("while_end")
        # For while loops, continue jumps to the start (condition check)
        self.loop_stack.append((start_label, end_label))
        self.emit_label(start_label)
        reg = self.generate_expression(while_stmt.cond)
        self.emit(f"    CMP {reg}, 0")
        self.free_register()
        self.emit(f"    JZ {end_label}")
        self.generate_block(while_stmt.body)
        self.emit(f"    JMP {start_label}")
        self.emit_label(end_label)
        self.loop_stack.pop()

    def _detect_wrap_prone_var(self, for_stmt: For) -> Optional[str]:
        """Detect if a for-loop has a pattern prone to 16-bit unsigned wrap-around.

        Recognizes patterns where a loop variable is compared in the condition
        and modified by a compound-update in the update expression, such that
        the variable could overflow/underflow the 16-bit range before the
        condition becomes false.

        Recognized condition patterns (var is the loop variable):
        - var < bound   (incrementing var, bound near 0xFFFF)
        - var <= bound
        - var > bound   (decrementing var, bound near 0x0000)
        - var >= bound

        Recognized update patterns:
        - var += expr  (compound: var = var + expr)
        - var -= expr  (compound: var = var - expr)
        - var++        (postfix increment)
        - var--        (postfix decrement)

        The wrap check is suppressed for 'timer_interrupt' because that function
        uses SP-relative locals (no ENTER/FP) and PUSH/POP would shift the SP
        base, corrupting SP-relative addresses for all local variables.

        Args:
            for_stmt: The For AST node.

        Returns:
            The loop variable name if a wrap-prone pattern is detected, else None.
        """
        if not for_stmt.cond or not for_stmt.update:
            return None
        if not isinstance(for_stmt.cond, BinaryOp):
            return None
        if for_stmt.cond.op not in ['<', '<=', '>', '>=', '==', '!=']:
            return None

        # Collect candidate loop-variable names from both sides of the condition.
        # The variable may appear on either side depending on how the AST was
        # constructed (e.g. "p < finish" or "finish > p").
        candidates = []
        if isinstance(for_stmt.cond.left, Identifier):
            candidates.append(for_stmt.cond.left.name)
        if isinstance(for_stmt.cond.right, Identifier):
            candidates.append(for_stmt.cond.right.name)

        if not candidates:
            return None

        update = for_stmt.update
        for var_name in candidates:
            # Case 1: Compound assignment — var = var <op> expr
            # Parser decomposes "var += expr" into Assignment('var', BinaryOp(Identifier('var'), '+', expr))
            if isinstance(update, Assignment):
                if update.name == var_name:
                    value = update.value
                    if isinstance(value, BinaryOp) and isinstance(value.left, Identifier) \
                            and value.left.name == var_name:
                        return var_name

            # Case 2: Postfix operator — var++ or var--
            elif isinstance(update, PostfixOp):
                if isinstance(update.left, Identifier) and update.left.name == var_name:
                    return var_name

        return None

    def generate_for(self, for_stmt: For):
        self.emit_comment("For loop")
        start_label = self.generate_label("for_start")
        end_label = self.generate_label("for_end")
        # For for loops, continue jumps to the update expression
        # We use a separate continue_label that points to the update section
        continue_label = self.generate_label("for_continue")
        self.loop_stack.append((continue_label, end_label))

        # Emit initialization (may be a VarDecl list for "for(int x=...)",
        # or an Assignment/Expression for "for(x=...)")
        if for_stmt.init:
            self.generate_block([for_stmt.init])

        # Condition check: evaluate cond to 0/1, exit if false (zero)
        self.emit_label(start_label)
        if for_stmt.cond:
            reg = self.generate_expression(for_stmt.cond)
            self.emit(f"    CMP {reg}, 0")
            self.free_register()
            self.emit(f"    JZ {end_label}")

        # Loop body
        self.generate_block(for_stmt.body)

        # Continue target: update expression
        self.emit_label(continue_label)

        # Wrap-aware for-loop emission:
        # When a 16-bit loop variable is incremented (e.g., p += 32) and
        # the loop bound is 0xFFFF (or any value near 0xFFFF), the variable
        # can wrap from 0xFFF0 to 0x0010.  The unsigned comparison
        # (p < 0xFFFF) remains true after the wrap, causing an infinite loop.
        #
        # To detect this, we save the variable's value before the update, then
        # compare it with the new value after the update.  If new < old
        # (unsigned borrow / carry), the variable wrapped → exit loop.
        #
        # This check is suppressed in 'timer_interrupt' because that function
        # uses SP-relative locals (no ENTER/FP) and PUSH/POP would shift the
        # SP base, corrupting SP-relative addresses for all local variables.
        loop_var = self._detect_wrap_prone_var(for_stmt)
        need_wrap_check = (
            loop_var is not None
            and self.current_function != 'timer_interrupt'
        )

        if need_wrap_check:
            # Save current value of loop variable on the stack before update.
            # PUSH/POP are safe here because FP-relative addressing is unaffected
            # by SP changes (only SP-relative access in timer_interrupt is affected,
            # which we've already excluded above).
            self.emit_comment(f"Wrap-check: save {loop_var} before update")
            old_reg = self.get_register()
            self._emit_local_load(old_reg, loop_var)
            self.emit(f"    PUSH {old_reg}")
            self.free_register()

        # Emit update expression (e.g., p += step)
        if for_stmt.update:
            self.generate_block([for_stmt.update])

        if need_wrap_check:
            # Restore pre-update value and compare with new value to detect
            # unsigned wrap-around.
            # CMP new, old computes new - old.  If new < old (unsigned),
            # the carry/borrow flag is set, indicating the variable wrapped
            # from a high value back to a low value.
            self.emit_comment(f"Wrap-check: compare {loop_var} new vs old")
            old_reg = self.get_register()
            self.emit(f"    POP {old_reg}")
            new_reg = self.get_register()
            self._emit_local_load(new_reg, loop_var)
            self.emit(f"    CMP {new_reg}, {old_reg}")
            self.free_register()
            # JC = jump if carry (borrow) → new < old → wrapped → exit
            self.emit(f"    JC {end_label}")

        # Jump back to condition check
        self.emit(f"    JMP {start_label}")
        self.emit_label(end_label)
        self.loop_stack.pop()

    def generate_do_while(self, stmt: DoWhile):
        """Generate code for do-while loop: do { body } while (cond);"""
        self.emit_comment("Do-While loop")
        start_label = self.generate_label("dowhile_start")
        end_label = self.generate_label("dowhile_end")
        # For do-while, continue jumps to the start of the loop body
        self.loop_stack.append((start_label, end_label))
        self.emit_label(start_label)
        self.generate_block(stmt.body)
        reg = self.generate_expression(stmt.cond)
        self.emit(f"    CMP {reg}, 0")
        self.free_register()
        self.emit(f"    JNZ {start_label}")  # Loop back if condition is true
        self.emit_label(end_label)
        self.loop_stack.pop()

    def generate_switch(self, stmt: Switch):
        """Generate code for switch/case statement.

        Compiles to a series of comparisons (CMP/JZ) against each case value.
        Supports break and C-style fall-through between cases (no break).
        """
        self.emit_comment("Switch statement")
        end_label = self.generate_label("switch_end")
        # Push loop context so break inside switch exits to end_label.
        # No continue target (None) because continue is not valid in switch.
        self.loop_stack.append((None, end_label))

        reg = self.generate_expression(stmt.expr)

        # Pre-generate labels for each case body
        case_labels = [self.generate_label("case") for _ in stmt.cases]

        # Emit comparisons for each case value
        for i, case in enumerate(stmt.cases):
            case_val_reg = self.generate_expression(case.value)
            self.emit(f"    CMP {reg}, {case_val_reg}")
            self.free_register()  # free case_val_reg
            self.emit(f"    JZ {case_labels[i]}")

        # If no case matched, go to default or end
        if stmt.default_body:
            self.generate_block(stmt.default_body)
            self.emit(f"    JMP {end_label}")
        else:
            self.emit(f"    JMP {end_label}")

        # Emit case bodies (fall-through is natural between consecutive cases)
        for i, case in enumerate(stmt.cases):
            self.emit_label(case_labels[i])
            self.generate_block(case.body)

        self.emit_label(end_label)
        self.loop_stack.pop()

    def generate_break(self):
        # Generate assembly for a break statement - jump to loop end
        if not self.loop_stack:
            raise RuntimeError("break statement outside of loop")
        _, end_label = self.loop_stack[-1]
        self.emit_comment("break")
        self.emit(f"    JMP {end_label}")

    def generate_continue(self):
        # Generate assembly for a continue statement - jump to loop continue target
        if not self.loop_stack:
            raise RuntimeError("continue statement outside of loop")
        continue_label, _ = self.loop_stack[-1]
        if continue_label is None:
            raise RuntimeError("continue statement is not valid inside a switch")
        self.emit_comment("continue")
        self.emit(f"    JMP {continue_label}")

    def generate_expression(self, expr: Expression) -> str:
        if isinstance(expr, Number):
            reg = self.get_register()
            self.emit(f"    MOV {reg}, {expr.value}")
            return reg
        elif isinstance(expr, StringLiteral):
            reg = self.get_register()
            label = self.get_string_label(expr.value)
            self.emit(f"    MOV {reg}, {label}")
            return reg
        elif isinstance(expr, CharLiteral):
            reg = self.get_register()
            self.emit(f"    MOV {reg}, {expr.char_value}")
            return reg
        elif isinstance(expr, Identifier):
            reg = self.get_register()
            if expr.name in self.local_vars:
                self._emit_local_load(reg, expr.name)
                return reg
            else:
                raise NameError(f"Undefined variable '{expr.name}'")
        elif isinstance(expr, BinaryOp):
            # Constant folding: evaluate simple binary ops with two numeric
            # literal operands at compile time (brought over from NoBASIC's
            # ExpressionSimplifier). This avoids emitting MOV/ADD/SUB/etc.
            # instructions for expressions like `2 + 3` or `10 * 5`.
            if isinstance(expr.left, Number) and isinstance(expr.right, Number):
                try:
                    left_val = int(expr.left.value, 0)
                    right_val = int(expr.right.value, 0)
                    op = expr.op
                    if op == '+': folded = left_val + right_val
                    elif op == '-': folded = left_val - right_val
                    elif op == '*': folded = left_val * right_val
                    elif op == '/':
                        if right_val == 0:
                            folded = None
                            raise ArithmeticError("Division by zero")
                        folded = int(left_val / right_val)
                    elif op == '%': folded = left_val % right_val if right_val != 0 else None
                    elif op == '&': folded = left_val & right_val
                    elif op == '|': folded = left_val | right_val
                    elif op == '^': folded = left_val ^ right_val
                    elif op == '<<': folded = left_val << right_val
                    elif op == '>>': folded = left_val >> right_val
                    elif op == '==': folded = 1 if left_val == right_val else 0
                    elif op == '!=': folded = 1 if left_val != right_val else 0
                    elif op == '<': folded = 1 if left_val < right_val else 0
                    elif op == '>': folded = 1 if left_val > right_val else 0
                    elif op == '<=': folded = 1 if left_val <= right_val else 0
                    elif op == '>=': folded = 1 if left_val >= right_val else 0
                    elif op == '&&': folded = 1 if (left_val != 0 and right_val != 0) else 0
                    elif op == '||': folded = 1 if (left_val != 0 or right_val != 0) else 0
                    else: folded = None
                    if folded is not None:
                        self.emit_comment(f"Constant folded: {left_val} {op} {right_val} = {folded}")
                        reg = self.get_register()
                        self.emit(f"    MOV {reg}, {folded}")
                        return reg
                except (ArithmeticError, ValueError):
                    pass

            if (expr.op == '&' and isinstance(expr.right, Number) and expr.right.value in ('0xFF', '255')):
                if (isinstance(expr.left, BinaryOp) and expr.left.op == '>>' and 
                    isinstance(expr.left.right, Number) and expr.left.right.value == '8'):
                    self.emit_comment("Optimized high-byte access: (val >> 8) & 0xFF")
                    val_reg = self.generate_expression(expr.left.left)
                    result_reg = self.get_register()
                    if val_reg.startswith('P'):
                        self.emit(f"    MOV {result_reg}, {val_reg}:")
                    else:
                        self.emit(f"    MOV {result_reg}, {val_reg}")
                    self.free_register()
                    return result_reg
                else:
                    self.emit_comment("Optimized low-byte access: val & 0xFF")
                    val_reg = self.generate_expression(expr.left)
                    result_reg = self.get_register()
                    if val_reg.startswith('P'):
                        self.emit(f"    MOV {result_reg}, :{val_reg}")
                    else:
                        self.emit(f"    MOV {result_reg}, {val_reg}")
                    self.free_register()
                    return result_reg
            
            if expr.op == '>>' or expr.op == '<<':
                if not isinstance(expr.right, Number):
                    raise TypeError("Shift amount must be a constant integer for this compiler version.")
                left_reg = self.generate_expression(expr.left)
                shift_amount = int(expr.right.value, 0)
                op_mnemonic = "SHR" if expr.op == '>>' else "SHL"
                self.emit_comment(f"Unrolled shift {op_mnemonic} by {shift_amount}")
                for _ in range(shift_amount):
                    self.emit(f"    {op_mnemonic} {left_reg}")
                return left_reg

            left_reg = self.generate_expression(expr.left)
            right_reg = self.generate_expression(expr.right)
            op = expr.op
            if op == '+': self.emit(f"    ADD {left_reg}, {right_reg}")
            elif op == '-': self.emit(f"    SUB {left_reg}, {right_reg}")
            elif op == '*': self.emit(f"    MUL {left_reg}, {right_reg}")
            elif op == '/': self.emit(f"    DIV {left_reg}, {right_reg}")
            elif op == '%': self.emit(f"    MOD {left_reg}, {right_reg}")
            elif op in ['==', '!=', '>', '<', '>=', '<=']:
                # Use unsigned comparisons (JC/JNC) based on carry flag for
                # <, >, <=, >=.  After CMP a,b (a-b), carry = 1 (borrow) iff
                # a < b (unsigned).  For > and <= we swap operands so a single
                # conditional jump suffices.
                true_label = self.generate_label("cmp_true")
                end_label = self.generate_label("cmp_end")
                if op == '==':
                    self.emit(f"    CMP {left_reg}, {right_reg}")
                    self.emit(f"    JZ {true_label}")
                elif op == '!=':
                    self.emit(f"    CMP {left_reg}, {right_reg}")
                    self.emit(f"    JNZ {true_label}")
                elif op == '<':
                    self.emit(f"    CMP {left_reg}, {right_reg}")
                    self.emit(f"    JC {true_label}")     # borrow → left < right (unsigned)
                elif op == '>=':
                    self.emit(f"    CMP {left_reg}, {right_reg}")
                    self.emit(f"    JNC {true_label}")   # no borrow → left >= right (unsigned)
                elif op == '>':
                    self.emit(f"    CMP {right_reg}, {left_reg}")
                    self.emit(f"    JC {true_label}")     # borrow of (right-left) → right < left → left > right (unsigned)
                elif op == '<=':
                    self.emit(f"    CMP {right_reg}, {left_reg}")
                    self.emit(f"    JNC {true_label}")   # no borrow → right >= left → left <= right (unsigned)
                self.emit(f"    MOV {left_reg}, 0")
                self.emit(f"    JMP {end_label}")
                self.emit_label(true_label)
                self.emit(f"    MOV {left_reg}, 1")
                self.emit_label(end_label)

            elif op == '&&': self.emit(f"    AND {left_reg}, {right_reg}")
            elif op == '||': self.emit(f"    OR {left_reg}, {right_reg}")
            elif op == '&': self.emit(f"    AND {left_reg}, {right_reg}")
            elif op == '|': self.emit(f"    OR {left_reg}, {right_reg}")
            elif op == '^': self.emit(f"    XOR {left_reg}, {right_reg}")
            else: raise SyntaxError(f"Unknown binary operator '{op}'")
            self.free_register()
            return left_reg
        elif isinstance(expr, UnaryOp):
            reg = self.generate_expression(expr.right)
            op = expr.op
            if op == '-': self.emit(f"    NEG {reg}")
            elif op == '!': self.emit(f"    NOT {reg}")
            elif op == '~': self.emit(f"    INV {reg}")
            else: raise SyntaxError(f"Unknown unary operator '{op}'")
            return reg
        elif isinstance(expr, PostfixOp):
            if not isinstance(expr.left, Identifier):
                raise SyntaxError("Postfix operators can only be applied to identifiers")
            reg = self.get_register()
            self._emit_local_load(reg, expr.left.name)
            result_reg = self.get_register()
            self.emit(f"    MOV {result_reg}, {reg}")
            if expr.op == '++': self.emit(f"    INC {reg}")
            elif expr.op == '--': self.emit(f"    DEC {reg}")
            else: raise SyntaxError(f"Unknown postfix operator '{expr.op}'")
            self._emit_local_store(expr.left.name, reg)
            self.free_register()
            return result_reg
        elif isinstance(expr, FuncCall):
            return self.generate_call(expr)
        else:
            raise RuntimeError(f"Unknown expression type: {type(expr)}")

    def generate_call(self, call: FuncCall) -> str:
        self.emit_comment(f"Call to {call.name}")
        for arg in reversed(call.args):
            arg_reg = self.generate_expression(arg)
            self.emit(f"    PUSH {arg_reg}")
            self.free_register()
        
        label = self.functions.get(call.name, {}).get('label') or self.builtin_functions.get(call.name)
        if not label:
            raise NameError(f"Undefined function '{call.name}'")
        
        self.emit(f"    CALL {label}")
        if call.args:
            self.emit(f"    ; Args consumed by callee")

        result_reg = self.get_register()
        if call.name in ('random', 'random_range'):
            # RND/RNDR writes a 16-bit result to P0; read it back as a 16-bit value.
            self.emit(f"    MOV {result_reg}, P0")
        else:
            self.emit(f"    MOV {result_reg}, R0")
        return result_reg

    def generate_builtins(self):
        self.assembly.append("; Built-in Function Implementations")
        self.emit_label("builtin_set_vmode")
        self.emit("    POP P0"); self.emit("    POP P1"); self.emit("    MOV VM, P1"); self.emit("    PUSH P0"); self.emit("    RET")
        self.emit_label("builtin_set_layer")
        self.emit("    POP P0"); self.emit("    POP P1"); self.emit("    MOV VL, P1"); self.emit("    PUSH P0"); self.emit("    RET")
        self.emit_label("builtin_set_pos")
        self.emit("    POP P0"); self.emit("    POP P1"); self.emit("    POP P2"); self.emit("    MOV VX, P1"); self.emit("    MOV VY, P2"); self.emit("    PUSH P0"); self.emit("    RET")
        self.emit_label("builtin_write_screen")
        self.emit("    POP P0"); self.emit("    POP P1"); self.emit("    SWRITE P1"); self.emit("    PUSH P0"); self.emit("    RET")
        self.emit_label("builtin_read_screen")
        self.emit("    SREAD P0"); self.emit("    RET")
        self.emit_label("builtin_scroll_x")
        self.emit("    POP P0"); self.emit("    POP P1"); self.emit("    SROL 0, 1"); self.emit("    PUSH P0"); self.emit("    RET")
        self.emit_label("builtin_scroll_y")
        self.emit("    POP P0"); self.emit("    POP P1"); self.emit("    SROL 1, 1"); self.emit("    PUSH P0"); self.emit("    RET")
        self.emit_label("builtin_set_pointers")
        # All pushes/pops are P (2 bytes) for 16-bit ABI consistency.
        self.emit("    POP P3"); self.emit("    POP P1"); self.emit("    POP P2")
        self.emit("    MOV P0, P1"); self.emit("    MOV P1, P2"); self.emit("    PUSH P3"); self.emit("    RET")
        self.emit_label("builtin_write_text")
        self.emit("    POP P0"); self.emit("    POP P1"); self.emit("    POP P2")
        self.emit("    MOV VC, P2"); self.emit("    TEXT P1"); self.emit("    PUSH P0"); self.emit("    RET")
        self.emit_label("builtin_set_font")
        self.emit("    POP P0"); self.emit("    POP P1"); self.emit("    PUSH P0"); self.emit("    RET")
        self.emit_label("builtin_sound_play")
        self.emit("    POP P0"); self.emit("    POP P1"); self.emit("    POP P2"); self.emit("    POP P3"); self.emit("    SPLAY P3, P2, P1"); self.emit("    PUSH P0"); self.emit("    RET")
        self.emit_label("builtin_sound_stop")
        self.emit("    POP P0"); self.emit("    POP P1"); self.emit("    SPLAY P1, 0, 0"); self.emit("    PUSH P0"); self.emit("    RET")
        self.emit_label("builtin_set_timer")
        self.emit("    POP P0"); self.emit("    POP P1"); self.emit("    POP P2"); self.emit("    POP P3"); self.emit("    POP P4")
        # Args pushed in reversed source order: stack top->bottom after POP P0 is
        # [arg0=TT, arg1=TM, arg2=TS, arg3=TC]. So POP P1=TT, P2=TM, P3=TS, P4=TC.
        self.emit("    MOV TT, P1"); self.emit("    MOV TM, P2"); self.emit("    MOV TS, P3"); self.emit("    MOV TC, P4"); self.emit("    PUSH P0"); self.emit("    RET")
        self.emit_label("builtin_sti")
        self.emit("    STI"); self.emit("    RET")
        self.emit_label("builtin_cli")
        self.emit("    CLI"); self.emit("    RET")
        self.emit_label("builtin_iret")
        self.emit("    IRET"); self.emit("    RET")
        self.emit_label("builtin_random")
        self.emit("    RND P0"); self.emit("    RET")
        self.emit_label("builtin_random_range")
        # Save return address in P3 (not P0, since RNDR will write its result to P0).
        # Stack: [ret_addr, color_max, color_min] (top = last pushed = color_min)
        # builtins with P0 as destination use P3 for the return address (see
        # builtin_set_pointers for the same pattern).
        self.emit("    POP P3"); self.emit("    POP P1"); self.emit("    POP P2")
        self.emit("    RNDR P0, P1, P2")
        self.emit("    PUSH P3"); self.emit("    RET")
        self.emit_label("builtin_key_available")
        self.emit("    KEYSTAT P0"); self.emit("    RET")
        self.emit_label("builtin_key_read")
        self.emit("    KEYIN P0"); self.emit("    RET")
        self.emit_label("builtin_key_clear")
        self.emit("    KEYCLEAR"); self.emit("    RET")
        self.emit_label("builtin_halt")
        self.emit("    HLT"); self.emit("    RET")

    def get_string_label(self, value: str) -> str:
        if value not in self.strings:
            label = self.generate_label("str")
            self.strings[value] = label
            return label
        return self.strings[value]

    def emit(self, line: str):
        self.assembly.append(f"    {line}")

    def emit_comment(self, comment: str):
        self.assembly.append(f"; {comment}")

    def emit_label(self, label: str):
        self.assembly.append(f"{label}:")

    def generate_label(self, prefix: str) -> str:
        label = f"{prefix}_{self.label_counter}"
        self.label_counter += 1
        return label

    def get_register(self, exclude: set = None, preferred: str = None) -> str:
        # Use P0-P7 as 16-bit expression temporaries. P8 is SP and P9 is FP,
        # so they must never be used for general temporaries or arithmetic
        # results (e.g. MOV P9, 3 would clobber the frame pointer).
        # P3 is reserved for DIV remainder storage (the CPU's DIV instruction
        # unconditionally writes the remainder to P3), so we exclude P3.
        # Preferred register can be specified (e.g., 'P0', 'P1', etc.)
        # P3 is always excluded (reserved for DIV remainder). Use string matching.
        # 
        # Round-robin through P0-P7 (skipping P3 and user-excluded registers).
        # This preserves the original behavior where expression temporaries are
        # reused freely between statements without true liveness-based allocation.
        # The register_usage/var_reg/auto_free infrastructure is retained for
        # future graph-coloring allocation passes but does NOT gate allocation here.
        excluded = {'P3'} | (exclude or set())
        
        # Try preferred register first
        if preferred and preferred not in excluded:
            return preferred
        
        # Round-robin through P registers only (preserves original behavior)
        for _ in range(20):
            idx = self.reg_counter % 8
            self.reg_counter += 1
            reg = f"P{idx}"
            if reg not in excluded:
                return reg
        
        # Fallback (should never happen)
        return "P0"

    def free_register(self):
        # Expression temporaries are reused round-robin; no-op to preserve
        # original behavior where registers are safe to reuse after an
        # expression completes. Advanced liveness-based deallocation is
        # available via deallocate_register()/_clear_temp_registers() for
        # future integration, but is NOT used at expression boundaries here
        # to avoid freeing registers still referenced by outer expressions.
        pass

    def record_live_range(self, name: str, program_point: int):
        # Record that a variable/temporary is live at a program point.
        if name not in self.live_ranges:
            self.live_ranges[name] = (program_point, program_point)
        else:
            start, end = self.live_ranges[name]
            self.live_ranges[name] = (min(start, program_point), max(end, program_point))
        
        if program_point not in self.live_at_point:
            self.live_at_point[program_point] = set()
        self.live_at_point[program_point].add(name)

    def allocate_register(self, preferred_reg: str = None) -> str:
        # Allocate an unused register, preferring the specified register if available.
        self.allocation_stats['total_allocations'] += 1
        
        # Try preferred register first
        if preferred_reg and not self.register_usage.get(preferred_reg, True):
            self.register_usage[preferred_reg] = True
            self.auto_free_registers.add(preferred_reg)
            self.allocation_stats['max_simultaneous_allocated'] = max(
                self.allocation_stats['max_simultaneous_allocated'],
                sum(1 for used in self.register_usage.values() if used)
            )
            return preferred_reg
        
        # Try allocation order
        for reg in self.allocation_order:
            if not self.register_usage[reg]:
                self.register_usage[reg] = True
                self.auto_free_registers.add(reg)
                self.allocation_stats['max_simultaneous_allocated'] = max(
                    self.allocation_stats['max_simultaneous_allocated'],
                    sum(1 for used in self.register_usage.values() if used)
                )
                return reg
        
        # No free registers
        self.allocation_stats['allocation_failures'] += 1
        raise RuntimeError("Register exhaustion: No available registers")

    def deallocate_register(self, reg: str):
        # Deallocate a register, marking it as available.
        if reg in self.register_usage:
            self.register_usage[reg] = False
            self.auto_free_registers.discard(reg)
            self.allocation_stats['total_deallocations'] += 1

    def _clear_temp_registers(self):
        # Clear all temporary registers that aren't variable registers.
        var_regs = set(self.var_reg.values())
        for reg in list(self.auto_free_registers):
            if reg not in var_regs:
                self.deallocate_register(reg)

    def smart_deallocate_regs(self):
        # Intelligently deallocate temporary registers that are likely dead.
        var_regs = set(self.var_reg.values())
        for reg in list(self.auto_free_registers):
            if reg not in var_regs:
                self.deallocate_register(reg)
        
        self.allocation_stats['total_deallocations'] += 1
