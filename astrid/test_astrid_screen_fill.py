"""Tests for the Astrid screen_fill() built-in function."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nova_main import initialize_system


def run_binary(bin_path, max_cycles=2000000):
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    entry_point = mem.load(bin_path)
    proc.pc = entry_point
    cycle = 0
    while cycle < max_cycles and not proc.halted:
        cycle += 1
        proc.step()
    return proc, cycle, gfx


def compile_and_run(source):
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
        proc, cycles, gfx = run_binary(bin_path)
        assert proc.halted, "Program did not halt"
        return proc, cycles, gfx
    finally:
        os.unlink(source_path)
        for ext in ['.asm', '.bin', '.org', '.sym']:
            path = source_path.replace('.ast', ext)
            if os.path.exists(path):
                os.unlink(path)


def test_screen_fill_constant():
    source = """
void main() {
    set_layer(0);
    screen_fill(0x0F);
}
"""
    proc, cycles, gfx = compile_and_run(source)
    screen = gfx.screen
    non_zero_pixels = (screen != 0).sum()
    assert non_zero_pixels > 0, "Screen should have non-zero pixels after fill"
    assert screen[0, 0] == 0x0F, f"Pixel (0,0) = {screen[0, 0]}, expected 0x0F"
    assert screen[128, 128] == 0x0F, f"Pixel (128,128) = {screen[128, 128]}, expected 0x0F"
    assert screen[255, 255] == 0x0F, f"Pixel (255,255) = {screen[255, 255]}, expected 0x0F"
    print(f"PASS test_screen_fill_constant (cycles={cycles}, non_zero_pixels={non_zero_pixels})")


def test_screen_fill_variable():
    source = """
void main() {
    set_layer(0);
    int color = 0x1F;
    screen_fill(color);
}
"""
    proc, cycles, gfx = compile_and_run(source)
    screen = gfx.screen
    assert screen[0, 0] == 0x1F, f"Pixel (0,0) = {screen[0, 0]}, expected 0x1F"
    assert screen[200, 100] == 0x1F, f"Pixel (200,100) = {screen[200, 100]}, expected 0x1F"
    print(f"PASS test_screen_fill_variable (cycles={cycles})")


def test_screen_fill_expression():
    source = """
void main() {
    set_layer(0);
    screen_fill(0x10 + 0x05);
}
"""
    proc, cycles, gfx = compile_and_run(source)
    screen = gfx.screen
    assert screen[64, 64] == 0x15, f"Pixel (64,64) = {screen[64, 64]}, expected 0x15"
    print(f"PASS test_screen_fill_expression (cycles={cycles})")


def test_screen_fill_black():
    source = """
void main() {
    set_layer(0);
    screen_fill(0x0F);
    screen_fill(0x00);
}
"""
    proc, cycles, gfx = compile_and_run(source)
    screen = gfx.screen
    non_zero_pixels = (screen != 0).sum()
    assert non_zero_pixels == 0, f"Screen should be empty after fill(0), got {non_zero_pixels}"
    print(f"PASS test_screen_fill_black (cycles={cycles})")


def test_screen_fill_generated_asm():
    import tempfile
    source = """
void main() {
    set_layer(0);
    screen_fill(0x0F);
}
"""
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
        with open(asm_path, encoding='utf-8') as f:
            asm_content = f.read()
        assert 'builtin_screen_fill' in asm_content, "builtin_screen_fill label not found"
        assert 'SFILL' in asm_content, "SFILL instruction not found in generated assembly"
        print("PASS test_screen_fill_generated_asm")
    finally:
        os.unlink(source_path)
        for ext in ['.asm', '.bin', '.org', '.sym']:
            path = source_path.replace('.ast', ext)
            if os.path.exists(path):
                os.unlink(path)


if __name__ == '__main__':
    test_screen_fill_constant()
    test_screen_fill_variable()
    test_screen_fill_expression()
    test_screen_fill_black()
    test_screen_fill_generated_asm()
    print("All Astrid screen_fill tests passed!")