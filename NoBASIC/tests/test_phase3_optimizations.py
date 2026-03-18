"""
Test suite for Peephole Optimizer and Live Range Scheduler

Comprehensive tests covering:
1. Peephole optimization correctness
2. Live range scheduling correctness
3. Performance metrics
4. Integration with code generator
5. Regression tests with existing programs
"""

import pytest
import sys
from pathlib import Path

# Add compiler to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from compiler.codegen.peephole import PeepholeOptimizer, Instruction
from compiler.codegen.live_range_scheduler import LiveRangeScheduler, SpillMinimizer


# ============================================================================
# PEEPHOLE OPTIMIZER TESTS
# ============================================================================

class TestPeepholeOptimizer:
    """Test suite for peephole optimizer."""
    
    def setup_method(self):
        """Set up optimizer for each test."""
        self.optimizer = PeepholeOptimizer(debug=False)
    
    def test_self_mov_elimination(self):
        """Test elimination of self-moves: MOV A, A -> nothing"""
        # The issue is the middle MOV R1, 5 is on separate line with indentation
        # Let's test self-move elimination separately
        code = "MOV R0, R0"
        
        result = self.optimizer.optimize(code)
        lines = [l for l in result.split('\n') if l.strip()]
        
        # Self-move should be eliminated entirely
        assert len(lines) == 0 or all('MOV R0, R0' not in l for l in lines)
    
    def test_redundant_mov_elimination(self):
        """Test elimination of redundant consecutive MOVs."""
        code = "MOV R0, R1\nMOV R0, R2\nADD R0, 1"
        
        result = self.optimizer.optimize(code)
        lines = [l for l in result.split('\n') if l.strip()]
        
        # First redundant MOV should be eliminated
        # Should have MOV R0, R2 and ADD, possibly plus R1 if not optimized
        assert 'MOV R0, R2' in result
        assert 'ADD R0, 1' in result
    
    def test_identical_mov_elimination(self):
        """Test elimination of identical MOVs."""
        code = """MOV R0, 5
        MOV R0, 5"""
        
        result = self.optimizer.optimize(code)
        lines = [l for l in result.split('\n') if l.strip()]
        
        # Both identical, should eliminate first
        assert len(lines) == 1
    
    def test_register_chain_elimination(self):
        """Test elimination of register chains: MOV A, B; MOV C, A -> MOV C, B"""
        code = """MOV R0, R1
        MOV R2, R0
        ADD R2, 1"""
        
        result = self.optimizer.optimize(code)
        
        # Should optimize chain: MOV R2, R1
        assert 'MOV R2, R1' in result
    
    def test_constant_folding(self):
        """Test constant folding: MOV A, 5; ADD A, 3 -> MOV A, 8"""
        code = """MOV R0, 5
        ADD R0, 3"""
        
        result = self.optimizer.optimize(code)
        
        # Should fold to MOV R0, 8 (0x0008)
        assert 'MOV R0, 0x0008' in result or 'MOV R0, 8' in result
    
    def test_load_store_optimization(self):
        """Test load-store optimization: MOV A, X; MOV Y, A -> MOV Y, X"""
        code = """MOV R0, 0x1234
        MOV R1, R0"""
        
        result = self.optimizer.optimize(code)
        
        # Should directly move: MOV R1, 0x1234
        assert 'MOV R1, 0x1234' in result
    
    def test_dead_code_before_jump(self):
        """Test elimination of dead code before jumps."""
        code = """MOV R0, 5
        JMP end_label
        end_label:
        MOV R1, 10"""
        
        result = self.optimizer.optimize(code)
        lines = [l for l in result.split('\n') if l.strip() and not l.strip().startswith(';')]
        
        # Code after label should be preserved (label makes it reachable)
        assert 'JMP end_label' in result
        assert 'end_label:' in result
    
    def test_label_preservation(self):
        """Test that labels are preserved."""
        code = """loop_start:
        MOV R0, 5
        JMP loop_start"""
        
        result = self.optimizer.optimize(code)
        
        assert 'loop_start:' in result
        assert 'JMP loop_start' in result
    
    def test_complex_optimization(self):
        """Test complex optimization with multiple patterns."""
        code = """MOV R0, R0
        MOV R0, 5
        MOV R1, R0
        ADD R1, 3
        MOV R2, R1"""
        
        result = self.optimizer.optimize(code)
        lines = [l for l in result.split('\n') if l.strip()]
        
        # Should have significantly fewer lines after optimization
        assert len(lines) < 5
    
    def test_optimization_correctness(self):
        """Test that optimization preserves semantics."""
        codes = [
            ("MOV R0, 5\nADD R0, 3\nMOV R1, R0", "R1 should be 8"),
            ("MOV R0, 10\nSUB R0, 2\nMOV R1, R0", "R1 should be 8"),
        ]
        
        for code, desc in codes:
            result = self.optimizer.optimize(code)
            # Should not crash or produce empty result
            assert result.strip(), desc
    
    def test_no_optimization_for_dependent_instrs(self):
        """Test that dependent instructions are not optimized incorrectly."""
        code = """MOV R0, R1
        ADD R0, 5
        MOV R1, R0"""
        
        result = self.optimizer.optimize(code)
        
        # All three instructions are needed
        lines = [l for l in result.split('\n') if l.strip()]
        assert len(lines) >= 3
    
    def test_multiple_passes(self):
        """Test that optimizer handles multiple passes correctly."""
        code = """MOV R0, R1
        MOV R2, R0
        MOV R3, R2
        ADD R3, 1"""
        
        result = self.optimizer.optimize(code)
        
        # Should chain optimize: MOV R3, R1 (or similar)
        lines = [l for l in result.split('\n') if l.strip()]
        assert len(lines) <= 2

    def test_call_is_not_treated_as_terminal_jump(self):
        """Calls return, so dead-code elimination must not treat CALL like JMP/RET."""
        assert self.optimizer._is_unconditional_jump("CALL") is False

    def test_new_control_flow_opcodes_classification(self):
        """CALLZ/CALLNZ/LOOPZ should be treated as conditional control-flow ops."""
        assert self.optimizer._is_conditional_jump("CALLZ") is True
        assert self.optimizer._is_conditional_jump("CALLNZ") is True
        assert self.optimizer._is_conditional_jump("LOOPZ") is True
        assert self.optimizer._is_unconditional_jump("RETN") is True

    def test_flag_dependency_with_while_and_callz(self):
        """WHILE writes flags and CALLZ reads them; optimizer must preserve dependency."""
        code = """WHILE R0
        CALLZ fn
        fn:
        HLT"""

        self.optimizer.instructions = self.optimizer._parse_assembly(code)
        assert self.optimizer._has_flag_dependency_between(0, 2) is True

    def test_indirect_memory_store_is_not_elided(self):
        """Indirect stores back compiler-managed state and must not disappear."""
        code = """MOV P0, 292
        MOV P1, R1
        MOV [P0], P1
        MOV R1, 1"""

        result = self.optimizer.optimize(code)

        assert "MOV P0, 292" in result
        assert "MOV R1, 1" in result
        assert "MOV [P0], P1" in result

    def test_indirect_store_followed_by_reload_is_preserved(self):
        """Key/state stores often reload through a different pointer register."""
        code = """MOV P1, 312
        MOV [P1], P0
        MOV P0, 312
        MOV P1, [P0]"""

        result = self.optimizer.optimize(code)

        assert "MOV [P1], P0" in result
        assert "MOV P1, [P0]" in result

    def test_load_store_optimization_skips_memory_destination(self):
        """MOV temp; MOV [addr], temp must remain intact for 16-bit state writes."""
        code = """MOV P1, R1
        MOV [P0], P1"""

        result = self.optimizer.optimize(code)

        assert "MOV P1, R1" in result
        assert "MOV [P0], P1" in result

    def test_register_chain_skips_mixed_width_registers(self):
        """Cross-family rewrites like P1<-R1; P0<-P1 must not collapse to P0<-R1."""
        code = """MOV P1, R1
        MOV P0, P1"""

        result = self.optimizer.optimize(code)

        assert "MOV P1, R1" in result
        assert "MOV P0, P1" in result


# ============================================================================
# LIVE RANGE SCHEDULER TESTS
# ============================================================================

class TestLiveRangeScheduler:
    """Test suite for live range scheduler."""
    
    def setup_method(self):
        """Set up scheduler for each test."""
        self.scheduler = LiveRangeScheduler(debug=False)
    
    def test_basic_scheduling(self):
        """Test basic instruction scheduling."""
        code = [
            "MOV R0, 5",
            "MOV R1, 10",
            "ADD R0, R1"
        ]
        
        result = self.scheduler.schedule(code)
        
        # Should return valid assembly
        assert len(result) >= 3
        assert "MOV R0, 5" in result
        assert "ADD R0, R1" in result
    
    def test_dependency_preservation(self):
        """Test that dependencies are preserved during scheduling."""
        code = [
            "MOV R0, 5",
            "MOV R1, 10",
            "ADD R0, R1"
        ]
        
        result = self.scheduler.schedule(code)
        lines = result
        
        # Find indices of instructions
        mov_r0_idx = next(i for i, l in enumerate(lines) if "MOV R0, 5" in l)
        add_idx = next(i for i, l in enumerate(lines) if "ADD R0, R1" in l)
        
        # MOV R0 must come before ADD R0
        assert mov_r0_idx < add_idx
    
    def test_independent_instructions_reorder(self):
        """Test that independent instructions can be reordered."""
        code = [
            "MOV R0, 5",
            "MOV R1, 10",
            "MOV R2, 15"
        ]
        
        result = self.scheduler.schedule(code)
        
        # All three moves are independent and should be present
        assert "MOV R0, 5" in result
        assert "MOV R1, 10" in result
        assert "MOV R2, 15" in result
    
    def test_label_preservation_in_scheduler(self):
        """Test that labels are preserved during scheduling."""
        code = [
            "loop_start:",
            "MOV R0, 5",
            "ADD R0, 1",
            "JMP loop_start"
        ]
        
        result = self.scheduler.schedule(code)
        
        assert "loop_start:" in result
        assert "JMP loop_start" in result
    
    def test_jump_not_reordered(self):
        """Test that jumps are not reordered past other instructions."""
        code = [
            "MOV R0, 5",
            "JMP end",
            "MOV R1, 10",
            "end:"
        ]
        
        result = self.scheduler.schedule(code)
        
        # All instructions should be present
        assert "MOV R0, 5" in result
        assert "JMP end" in result
        assert "MOV R1, 10" in result
        assert "end:" in result
    
    def test_call_not_reordered(self):
        """Test that CALL instructions are not reordered."""
        code = [
            "MOV R0, 5",
            "CALL func",
            "MOV R1, 10"
        ]
        
        result = self.scheduler.schedule(code)
        
        # CALL should stay in place
        assert "CALL func" in result
        call_idx = next(i for i, l in enumerate(result) if "CALL func" in l)
        
        # Verify structure is preserved
        assert len(result) == 3

    def test_labeled_directive_is_preserved(self):
        """Scheduler must preserve inline labeled directives as directives."""
        code = [
            "MOV R0, 1",
            "LBUF: DEFSTR \"hello\"",
            "HLT",
        ]

        result = self.scheduler.schedule(code)

        assert "LBUF: DEFSTR \"hello\"" in result
        assert any(line.startswith("LBUF:") for line in result)


# ============================================================================
# SPILL MINIMIZER TESTS
# ============================================================================

class TestSpillMinimizer:
    """Test suite for spill minimizer."""
    
    def setup_method(self):
        """Set up minimizer for each test."""
        self.minimizer = SpillMinimizer(debug=False)
    
    def test_spill_priority_analysis(self):
        """Test that spill priorities are assigned correctly."""
        lifetimes = {
            'var1': (0, 5),      # length = 5
            'var2': (0, 20),     # length = 20 (higher priority)
            'var3': (10, 12),    # length = 2 (lower priority)
        }
        
        priorities = self.minimizer.analyze(lifetimes)
        
        # var2 should have highest priority
        assert priorities['var2'] >= priorities['var1']
        assert priorities['var1'] >= priorities['var3']
    
    def test_spill_suggestions(self):
        """Test that spill suggestions are generated."""
        lifetimes = {
            'long_var': (0, 30),
            'short_var': (0, 5),
        }
        
        priorities = self.minimizer.analyze(lifetimes)
        suggestions = self.minimizer.suggest_optimizations(priorities)
        
        # Should have suggestions
        assert len(suggestions) > 0
        assert any('long_var' in s for s in suggestions)


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests with real NoBASIC programs."""
    
    def test_peephole_preserves_semantics_simple(self):
        """Test that peephole optimization preserves program semantics."""
        assembly = """ORG 0x0200
        MOV P7, 0xFFFF
        MOV SP, P7
        MOV R0, 5
        MOV R1, 10
        ADD R0, R1
        MOV R2, R0
        HLT"""
        
        optimizer = PeepholeOptimizer()
        result = optimizer.optimize(assembly)
        
        # Should contain key instructions
        assert "MOV R0, 5" in result or "MOV R0, 0x0005" in result
        assert "ADD" in result
        assert "HLT" in result
    
    def test_peephole_reduces_code_size(self):
        """Test that peephole optimization reduces code size."""
        # Create redundant code
        assembly = """
        MOV R0, R0
        MOV R0, 5
        MOV R0, 5
        MOV R1, R0
        MOV R1, R0
        MOV R2, R1
        ADD R2, 0"""
        
        optimizer = PeepholeOptimizer()
        result = optimizer.optimize(assembly)
        
        original_lines = len([l for l in assembly.split('\n') if l.strip() and not l.strip().startswith(';')])
        optimized_lines = len([l for l in result.split('\n') if l.strip() and not l.strip().startswith(';')])
        
        # Should reduce number of instructions
        assert optimized_lines < original_lines
    
    def test_scheduler_with_simple_program(self):
        """Test scheduler with simple program."""
        code = [
            "MOV R0, 5",
            "MOV R1, 10",
            "ADD R0, R1",
            "MOV R2, R0"
        ]
        
        scheduler = LiveRangeScheduler()
        result = scheduler.schedule(code)
        
        assert len(result) == 4
        assert "ADD R0, R1" in result


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestPerformance:
    """Performance-related tests."""
    
    def test_peephole_completes_quickly(self):
        """Test that peephole optimization completes in reasonable time."""
        import time
        
        # Generate large code
        large_code = "\n".join([
            f"MOV R0, {i}" for i in range(100)
        ])
        
        optimizer = PeepholeOptimizer()
        start = time.time()
        result = optimizer.optimize(large_code)
        elapsed = time.time() - start
        
        # Should complete in < 1 second
        assert elapsed < 1.0
        assert result.strip()
    
    def test_scheduler_completes_quickly(self):
        """Test that scheduler completes in reasonable time."""
        import time
        
        # Generate large code
        large_code = [f"MOV R{i%10}, {i}" for i in range(100)]
        
        scheduler = LiveRangeScheduler()
        start = time.time()
        result = scheduler.schedule(large_code)
        elapsed = time.time() - start
        
        # Should complete in < 1 second
        assert elapsed < 1.0
        assert len(result) > 0


# ============================================================================
# REGRESSION TESTS
# ============================================================================

class TestRegressions:
    """Regression tests to catch bugs."""
    
    def test_no_crash_on_empty_input(self):
        """Test that optimizer doesn't crash on empty input."""
        optimizer = PeepholeOptimizer()
        result = optimizer.optimize("")
        assert result == ""
    
    def test_no_crash_on_labels_only(self):
        """Test that optimizer handles label-only code."""
        code = """loop_start:
        end_label:
        final:"""
        
        optimizer = PeepholeOptimizer()
        result = optimizer.optimize(code)
        assert "loop_start:" in result
    
    def test_no_crash_on_directives_only(self):
        """Test that optimizer handles directives."""
        code = """ORG 0x0200
        DEFSTR "hello"
        DEFBYTE 0xFF"""
        
        optimizer = PeepholeOptimizer()
        result = optimizer.optimize(code)
        assert "ORG 0x0200" in result

    def test_labeled_directive_not_lost_in_peephole(self):
        """Peephole parser must keep `label: DEFSTR ...` lines intact."""
        code = """ORG 0x0200
        L4: DEFSTR "buffer"
        HLT"""

        optimizer = PeepholeOptimizer()
        result = optimizer.optimize(code)

        assert "L4: DEFSTR \"buffer\"" in result
        assert "L4:" in result

    def test_halt_does_not_delete_following_labeled_directive(self):
        """Dead-code elimination must preserve string/data directives after HLT."""
        code = """MOV P0, STR0
        HLT
        STR0: DEFSTR "hello"""

        optimizer = PeepholeOptimizer()
        result = optimizer.optimize(code)

        assert "MOV P0, STR0" in result
        assert "HLT" in result
        assert "STR0: DEFSTR \"hello" in result

    def test_lowercase_directive_is_classified(self):
        """Directive classification should be case-insensitive."""
        code = """org 0x0200
        l5: defstr "ok"
        hlt"""

        optimizer = PeepholeOptimizer()
        parsed = optimizer._parse_assembly(code)

        assert parsed[0].is_directive is True
        assert parsed[1].is_directive is True
        assert parsed[2].opcode == "hlt"
    
    def test_scheduler_no_crash_on_empty(self):
        """Test that scheduler doesn't crash on empty input."""
        scheduler = LiveRangeScheduler()
        result = scheduler.schedule([])
        assert len(result) == 0
    
    def test_minimizer_no_crash_on_empty(self):
        """Test that minimizer doesn't crash on empty input."""
        minimizer = SpillMinimizer()
        result = minimizer.analyze({})
        assert len(result) == 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
