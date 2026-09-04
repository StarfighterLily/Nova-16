"""Runtime tests for mouse_read() and mouse_pos() builtins.

These tests verify that the new mouse builtins correctly read from the
Nova-16 mouse registers (MX, MY, MB) at runtime.
"""
import os
import sys
import tempfile

import pytest

from nova_main import initialize_system


def run_binary(bin_path, max_cycles=2000000):
    """Run a binary headlessly and return (proc, cycles, mem)."""
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    entry_point = mem.load(bin_path)
    proc.pc = entry_point
    cycle = 0
    while cycle < max_cycles and not proc.halted:
        cycle += 1
        proc.step()
    return proc, cycle, mem


def _compile_and_run(source, mx=0, my=0, mb=0):
    """Compile Astrid source, assemble, run with mouse state preset.

    Returns the processor after execution (asserts the program halted).
    """
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

        proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
        entry_point = mem.load(bin_path)
        proc.pc = entry_point
        proc.mx = mx
        proc.my = my
        proc.mb = mb

        cycle = 0
        while cycle < 100000 and not proc.halted:
            cycle += 1
            proc.step()

        assert proc.halted, "Program did not halt"
        return proc
    finally:
        os.unlink(source_path)
        for ext in ['.asm', '.bin', '.org', '.sym']:
            path = source_path.replace('.ast', ext)
            if os.path.exists(path):
                os.unlink(path)
# SECTION2


class TestMouseReadBuiltin:
    """Tests for mouse_read() builtin - returns mouse button state (MB)."""

    def test_mouse_read_default_state(self):
        """mouse_read() should return 0 when no buttons are pressed."""
        source = """
int main() {
    return mouse_read();
}
"""
        proc = _compile_and_run(source, mb=0x00)
        assert proc.r0 == 0, f"Expected R0=0, got {proc.r0}"

    def test_mouse_read_both_buttons(self):
        """mouse_read() should return 3 when both buttons are pressed."""
        source = """
int main() {
    return mouse_read();
}
"""
        proc = _compile_and_run(source, mb=0x03)
        assert proc.r0 == 3, f"Expected R0=3 (both buttons), got {proc.r0}"

    def test_mouse_read_left_button_only(self):
        """mouse_read() should return 1 when only the left button is pressed."""
        source = """
int main() {
    return mouse_read();
}
"""
        proc = _compile_and_run(source, mb=0x01)
        assert proc.r0 == 1, f"Expected R0=1 (left button), got {proc.r0}"

    def test_mouse_read_right_button_only(self):
        """mouse_read() should return 2 when only the right button is pressed."""
        source = """
int main() {
    return mouse_read();
}
"""
        proc = _compile_and_run(source, mb=0x02)
        assert proc.r0 == 2, f"Expected R0=2 (right button), got {proc.r0}"
# SECTION3


class TestMousePosBuiltin:
    """Tests for mouse_pos(axis) builtin - axis 0 returns X, axis 1 returns Y."""

    def test_mouse_pos_x_default(self):
        """mouse_pos(0) should return 0 when X is at default."""
        source = """
int main() {
    return mouse_pos(0);
}
"""
        proc = _compile_and_run(source, mx=0)
        assert proc.r0 == 0, f"Expected R0=0, got {proc.r0}"

    def test_mouse_pos_y_default(self):
        """mouse_pos(1) should return 0 when Y is at default."""
        source = """
int main() {
    return mouse_pos(1);
}
"""
        proc = _compile_and_run(source, my=0)
        assert proc.r0 == 0, f"Expected R0=0, got {proc.r0}"

    def test_mouse_pos_x_with_position(self):
        """mouse_pos(0) should return the X position from the MX register."""
        source = """
int main() {
    return mouse_pos(0);
}
"""
        proc = _compile_and_run(source, mx=100)
        assert proc.r0 == 100, f"Expected R0=100 (X position), got {proc.r0}"

    def test_mouse_pos_y_with_position(self):
        """mouse_pos(1) should return the Y position from the MY register."""
        source = """
int main() {
    return mouse_pos(1);
}
"""
        proc = _compile_and_run(source, my=50)
        assert proc.r0 == 50, f"Expected R0=50 (Y position), got {proc.r0}"

    def test_mouse_pos_y_ignores_x(self):
        """mouse_pos(1) must not return the X value."""
        source = """
int main() {
    return mouse_pos(1);
}
"""
        proc = _compile_and_run(source, mx=100, my=50)
        assert proc.r0 == 50, f"Expected R0=50 (Y only), got {proc.r0}"
# SECTION4

    def test_mouse_pos_x_ignores_y(self):
        """mouse_pos(0) must not return the Y value."""
        source = """
int main() {
    return mouse_pos(0);
}
"""
        proc = _compile_and_run(source, mx=100, my=50)
        assert proc.r0 == 100, f"Expected R0=100 (X only), got {proc.r0}"

    def test_mouse_pos_different_values(self):
        """mouse_pos(0) and mouse_pos(1) should return their own axes."""
        source = """
int main() {
    int x = mouse_pos(0);
    int y = mouse_pos(1);
    return x + y;
}
"""
        proc = _compile_and_run(source, mx=100, my=50)
        assert proc.r0 == 150, f"Expected R0=150 (X+Y), got {proc.r0}"

    def test_mouse_pos_with_variable_axis(self):
        """mouse_pos() should work with a variable axis argument."""
        source = """
int main() {
    int axis = 0;
    int x = mouse_pos(axis);
    return x;
}
"""
        proc = _compile_and_run(source, mx=75)
        assert proc.r0 == 75, f"Expected R0=75 (X via variable), got {proc.r0}"


class TestMouseBuiltinsIntegration:
    """Integration tests combining mouse_read() and mouse_pos()."""

    def test_mouse_state_and_position(self):
        """Both mouse builtins should work together in one program."""
        source = """
int main() {
    int buttons = mouse_read();
    int x = mouse_pos(0);
    int y = mouse_pos(1);
    return buttons + x + y;
}
"""
        proc = _compile_and_run(source, mx=200, my=150, mb=0x01)
        # P0 holds the full 16-bit return value (1 + 200 + 150 = 351);
        # R0 holds only the low byte (351 & 0xFF = 95).
        assert proc.p0 == 351, f"Expected P0=351 (1+200+150), got {proc.p0}"
        assert proc.r0 == 351 & 0xFF, f"Expected R0 low byte 0x5F, got {proc.r0}"

    def test_mouse_read_in_loop(self):
        """mouse_read() should work inside a loop."""
        source = """
int main() {
    int i = 0;
    int sum = 0;
    while (i < 5) {
        sum = sum + mouse_read();
        i = i + 1;
    }
    return sum;
}
"""
        proc = _compile_and_run(source, mb=0x01)
        # mouse_read() returns 1 each time, 5 iterations = 5
        assert proc.r0 == 5, f"Expected R0=5, got {proc.r0}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])



