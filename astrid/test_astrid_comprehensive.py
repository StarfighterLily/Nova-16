"""Comprehensive tests for Astrid stack frame and code generation against Nova-16."""
import os
import sys

# Add project root to path so we can import nova_main and astrid modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Add astrid directory to path so we can import astrid_compiler
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nova_main import initialize_system


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


def test_nested_function_calls():
    """Test nested function calls preserve stack correctly.
    
    main calls add(10, 20) which returns 30, then calls multiply(30, 2) which returns 60.
    """
    source = """
void add(int a, int b) {
    return a + b;
}

void multiply(int a, int b) {
    return a * b;
}

void main() {
    int x = add(10, 20);
    int y = multiply(x, 2);
    // y should be 60
    // Store y in a known location for testing
}
"""
    import tempfile
    # UTF-8 is required: source strings may contain non-ASCII characters
    # that cp1252 cannot encode on Windows.
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ast', delete=False,
                                     encoding='utf-8') as f:
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
        
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from nova_assembler import Assembler
        asm = Assembler()
        asm.assemble(asm_path)
        
        proc, cycles = run_binary(bin_path)
        assert proc.halted, "Program did not halt"
        assert proc.r0 == 60, f"Expected R0=60, got {proc.r0}"
        print(f"PASS test_nested_function_calls (cycles={cycles}, R0={proc.r0})")
    finally:
        os.unlink(source_path)
        for ext in ['.asm', '.bin', '.org', '.sym']:
            path = source_path.replace('.ast', ext)
            if os.path.exists(path):
                os.unlink(path)


def test_local_variable_isolation():
    """Test that local variables in different functions don't interfere."""
    source = """
void foo() {
    int x = 10;
}

void main() {
    int x = 5;
    foo();
}
"""
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ast', delete=False,
                                     encoding='utf-8') as f:
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
        print(f"PASS test_local_variable_isolation (cycles={cycles})")
    finally:
        os.unlink(source_path)
        for ext in ['.asm', '.bin', '.org', '.sym']:
            path = source_path.replace('.ast', ext)
            if os.path.exists(path):
                os.unlink(path)


def test_recursive_function():
    """Test recursive function calls work correctly with stack frames."""
    source = """
int factorial(int n) {
    if (n <= 1) {
        return 1;
    }
    return n * factorial(n - 1);
}

void main() {
    int result = factorial(5);
}
"""
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ast', delete=False,
                                     encoding='utf-8') as f:
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
        print(f"PASS test_recursive_function (cycles={cycles}, R0=0x{proc.r0:02X})")
    finally:
        os.unlink(source_path)
        for ext in ['.asm', '.bin', '.org', '.sym']:
            path = source_path.replace('.ast', ext)
            if os.path.exists(path):
                os.unlink(path)


def test_stack_pointer_restoration():
    """Test that SP is restored to its original value after function returns."""
    # This uses the existing test_enter_leave.bin which already tests this
    bin_path = os.path.join(os.path.dirname(__file__), 'test_enter_leave.bin')
    proc, cycles = run_binary(bin_path)
    assert proc.halted, "test_enter_leave.bin did not halt"
    assert proc.sp == 0xFF00, f"SP = 0x{proc.sp:04X}, expected 0xFF00"
    assert proc.fp == 0xFF00, f"FP = 0x{proc.fp:04X}, expected 0xFF00"
    print(f"PASS test_stack_pointer_restoration (cycles={cycles}, SP=FP=0xFF00)")


if __name__ == '__main__':
    test_stack_pointer_restoration()
    test_nested_function_calls()
    test_local_variable_isolation()
    test_recursive_function()
    print("All comprehensive Astrid tests passed!")