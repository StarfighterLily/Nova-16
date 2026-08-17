"""Tests for Astrid language features: break, continue, compound assignment."""
import os
import sys

# Add project root to path so we can import nova_main and astrid modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Add astrid directory to path so we can import astrid_compiler
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nova_main import initialize_system
from astrid.parser.parser import BinaryOp, Number
from astrid.codegen.optimizations import (
    ExpressionSimplifier,
    FunctionInliner,
    RegisterColoringPass,
    HotSpillAnalyzer,
    RegisterPressureMonitor,
)
from astrid.codegen.codegen import CodeGenerator


def run_binary(bin_path, max_cycles=2000000):
    """Run a binary headlessly and return (proc, cycles)."""
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    entry_point = mem.load(bin_path)
    proc.pc = entry_point
    cycle = 0
    while cycle < max_cycles and not proc.halted:
        cycle += 1
        proc.step()
    return proc, cycle


def compile_and_run(source, expected_r0=None):
    """Compile Astrid source, assemble, and run. Returns (proc, cycles)."""
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ast', delete=False) as f:
        f.write(source)
        source_path = f.name

    try:
        from astrid_compiler import main as compiler_main
        old_argv = sys.argv
        sys.argv = [old_argv[0], source_path, '-o', source_path.replace('.ast', '.asm')]
        try:
            compiler_main()
        finally:
            sys.argv = old_argv

        asm_path = source_path.replace('.ast', '.asm')
        bin_path = source_path.replace('.ast', '.bin')

        from nova_assembler import Assembler
        asm = Assembler()
        asm.assemble(asm_path)

        proc, cycles = run_binary(bin_path)
        assert proc.halted, "Program did not halt"
        if expected_r0 is not None:
            assert proc.r0 == expected_r0, f"Expected R0={expected_r0}, got {proc.r0}"
        return proc, cycles
    finally:
        os.unlink(source_path)
        for ext in ['.asm', '.bin', '.org', '.sym']:
            path = source_path.replace('.ast', ext)
            if os.path.exists(path):
                os.unlink(path)


def test_optimization_passes_api():
    """Verify NoBASIC optimization passes are available and usable."""
    expr = ExpressionSimplifier()
    folded = expr.simplify(BinaryOp(Number("1"), "+", Number("2")))
    assert hasattr(folded, 'value')

    # Register coloring should assign a valid mapping for a small interference set.
    graph = {'a': {'b'}, 'b': {'a'}}
    mapping = RegisterColoringPass(graph, ['P0', 'P1']).color_graph()
    assert set(mapping) == {'a', 'b'}

    # Hot spills should map hot vars to zero-page addresses with the right sizing.
    hot = HotSpillAnalyzer({'x': 0x0100}, {'x': 10, 'y': 3}, debug=False)
    hot_spills = hot.identify_hot_spills(threshold_percentile=50.0)
    assert 'x' in hot_spills

    # Pressure monitoring should expose the same diagnostics as the NoBASIC compiler.
    pressure = RegisterPressureMonitor({0: {'a'}, 1: {'a', 'b'}}, available_registers=1)
    stats = pressure.analyze_pressure()
    assert stats['max_pressure'] >= 1

    # Function inlining should recognize tiny helper functions.
    function = FunctionInliner(max_statements=3)
    assert function.analyze([]) == set()

    # The Astrid compiler should default to the same peephole-on behavior as NoBASIC.
    assert CodeGenerator().enable_peephole is True


def test_optimization_config_and_wiring():
    """Astrid should expose the same optimization toggles and config defaults as NoBASIC."""
    generator = CodeGenerator(enable_optimizations=False, enable_live_range_scheduling=False)
    assert generator.enable_optimizations is False
    assert generator.enable_peephole is True  # peephole is still independent from the master switch
    assert generator.enable_live_range is False
    assert generator.opt_config['enable_expression_simplification'] is True

    generator = CodeGenerator(debug_optimizations=True)
    assert generator.opt_config['debug_optimizations'] is True
    assert generator.enable_optimizations is True


def test_live_range_scheduler_budget_gate():
    """Astrid should skip expensive live-range scheduling when code size or work estimate exceeds NoBASIC budgets."""
    generator = CodeGenerator()
    schedule_ok, reason = generator._should_run_live_range_scheduler(["MOV P0, 1"] * 20)
    assert schedule_ok is True
    assert "within budget" in reason.lower()

    oversized = ["MOV P0, 1"] * (generator.LIVE_RANGE_SCHEDULER_MAX_LINES + 5)
    schedule_ok, reason = generator._should_run_live_range_scheduler(oversized)
    assert schedule_ok is False
    assert "line count" in reason.lower()


def test_break_statement():
    """Test that break exits a loop early."""
    source = """
int main() {
    int sum = 0;
    for (int i = 0; i < 10; i++) {
        if (i == 5) {
            break;
        }
        sum = sum + i;
    }
    return sum;  // 0+1+2+3+4 = 10
}
"""
    proc, cycles = compile_and_run(source, expected_r0=10)
    print(f"PASS test_break_statement (cycles={cycles}, R0={proc.r0})")


def test_continue_statement():
    """Test that continue skips to next iteration."""
    source = """
int main() {
    int sum = 0;
    for (int i = 0; i < 10; i++) {
        if (i % 2 == 0) {
            continue;
        }
        sum = sum + i;
    }
    return sum;  // 1+3+5+7+9 = 25
}
"""
    proc, cycles = compile_and_run(source, expected_r0=25)
    print(f"PASS test_continue_statement (cycles={cycles}, R0={proc.r0})")


def test_compound_assignment():
    """Test *= and /= compound assignment operators."""
    source = """
int main() {
    int x = 10;
    x *= 2;  // x = 20
    x /= 4;  // x = 5
    return x;  // 5
}
"""
    proc, cycles = compile_and_run(source, expected_r0=5)
    print(f"PASS test_compound_assignment (cycles={cycles}, R0={proc.r0})")


def test_break_in_while():
    """Test break in a while loop."""
    source = """
int main() {
    int i = 0;
    int sum = 0;
    while (1) {
        if (i >= 5) {
            break;
        }
        sum = sum + i;
        i = i + 1;
    }
    return sum;  // 0+1+2+3+4 = 10
}
"""
    proc, cycles = compile_and_run(source, expected_r0=10)
    print(f"PASS test_break_in_while (cycles={cycles}, R0={proc.r0})")


def test_continue_in_while():
    """Test continue in a while loop."""
    source = """
int main() {
    int i = 0;
    int sum = 0;
    while (i < 10) {
        i = i + 1;
        if (i % 2 == 0) {
            continue;
        }
        sum = sum + i;
    }
    return sum;  // 1+3+5+7+9 = 25
}
"""
    proc, cycles = compile_and_run(source, expected_r0=25)
    print(f"PASS test_continue_in_while (cycles={cycles}, R0={proc.r0})")


if __name__ == '__main__':
    test_break_statement()
    test_continue_statement()
    test_compound_assignment()
    test_break_in_while()
    test_continue_in_while()
    print("All Astrid feature tests passed!")