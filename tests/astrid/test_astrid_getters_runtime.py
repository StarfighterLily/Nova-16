"""Runtime tests for the get_layer() / get_color() / get_rtc() builtins.

These tests verify that the hardware state getter builtins correctly read
back the Nova-16 graphics and real-time-clock state at runtime:

* get_layer() -> the active graphics layer (VL register, set by set_layer())
* get_color() -> the current drawing color (VC register, set by set_color())
* get_rtc(chunk) -> one 16-bit word of the RTC seconds-since-epoch counter:
                 get_rtc(0) = HIGH word (C1), get_rtc(1) = LOW word (C0)
"""
import os
import sys
import tempfile

import pytest

from nova_main import initialize_system

# Path setup handled by tests/astrid/conftest.py


def _compile_and_run(source, rtc_seconds=0):
    """Compile Astrid source, assemble, run with an optional fixed RTC value.

    Returns the processor after execution (asserts the program halted).
    The RTC clock source is pinned so C0/C1 are deterministic regardless of
    wall-clock time (see nova_cpu.CPU.rtc_seconds).
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ast', delete=False,
                                     encoding='utf-8') as f:
        f.write(source)
        source_path = f.name

    try:
        from astrid_compiler import main as compiler_main
        old_argv = sys.argv
        sys.argv = [old_argv[0], source_path,
                    '-o', source_path.replace('.ast', '.asm')]
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
        # Pin the RTC: rtc_seconds is subtracted from the (unix) source, so
        # return EPOCH + the desired value to observe exactly that delta.
        proc.rtc_time_source = (
            lambda: proc.RTC_EPOCH_UNIX + rtc_seconds)

        cycle = 0
        while cycle < 100000 and not proc.halted:
            cycle += 1
            proc.step()

        assert proc.halted, "Program did not halt"
        return proc, gfx
    finally:
        os.unlink(source_path)
        for ext in ['.asm', '.bin', '.org', '.sym']:
            path = source_path.replace('.ast', ext)
            if os.path.exists(path):
                os.unlink(path)


class TestGetLayerBuiltin:
    """Tests for get_layer() - returns the active graphics layer (VL)."""

    def test_get_layer_default_is_zero(self):
        """Freshly initialized graphics default to layer 0 (VL=0)."""
        source = """
int main() {
    return get_layer();
}
"""
        proc, _ = _compile_and_run(source)
        assert proc.p0 == 0, f"Expected P0=0, got {proc.p0}"

    def test_get_layer_reads_back_set_layer(self):
        """set_layer(5) must be visible through get_layer()."""
        source = """
int main() {
    set_layer(5);
    return get_layer();
}
"""
        proc, _ = _compile_and_run(source)
        assert proc.p0 == 5, f"Expected P0=5, got {proc.p0}"
        assert proc.r0 == 5, f"Expected R0=5, got {proc.r0}"

    def test_get_layer_with_variable_layer(self):
        """A variable layer value round-trips through set_layer/get_layer."""
        source = """
int main() {
    int L = 2;
    set_layer(L);
    return get_layer();
}
"""
        proc, _ = _compile_and_run(source)
        assert proc.p0 == 2, f"Expected P0=2, got {proc.p0}"

    def test_get_layer_tracks_successive_changes(self):
        """get_layer() reports the most recent set_layer() call."""
        source = """
int main() {
    set_layer(3);
    set_layer(8);
    set_layer(1);
    return get_layer();
}
"""
        proc, _ = _compile_and_run(source)
        assert proc.p0 == 1, f"Expected P0=1, got {proc.p0}"


class TestGetColorBuiltin:
    """Tests for get_color() - returns the current drawing color (VC)."""

    def test_get_color_reads_back_set_color(self):
        """set_color(0x3C) must be visible through get_color()."""
        source = """
int main() {
    set_color(0x3C);
    return get_color();
}
"""
        proc, _ = _compile_and_run(source)
        assert proc.p0 == 0x3C, f"Expected P0=0x3C, got {proc.p0:#06x}"
        assert proc.r0 == 0x3C, f"Expected R0=0x3C, got {proc.r0:#06x}"

    def test_get_color_tracks_successive_changes(self):
        """get_color() reports the most recent set_color() call."""
        source = """
int main() {
    set_color(0x11);
    set_color(0xAB);
    return get_color();
}
"""
        proc, _ = _compile_and_run(source)
        assert proc.p0 == 0xAB, f"Expected P0=0xAB, got {proc.p0:#06x}"

    def test_get_color_usable_in_expression(self):
        """get_color() composes like any int-valued expression."""
        source = """
int main() {
    set_color(0x0F);
    return get_color() + 1;
}
"""
        proc, _ = _compile_and_run(source)
        assert proc.p0 == 0x10, f"Expected P0=0x10, got {proc.p0:#06x}"
class TestGetRTCBuiltin:
    """Tests for get_rtc(chunk) - returns one 16-bit word of the RTC.

    The Nova-16 RTC keeps a 32-bit seconds-since-epoch counter split across
    two read-only 16-bit registers: C0 holds the LOW word and C1 the HIGH
    word.  get_rtc(chunk) selects either word:
        get_rtc(0) -> HIGH word (C1)
        get_rtc(1) -> LOW word  (C0)
    """

    def test_get_rtc_zero_returns_high_word(self):
        """rtc_seconds=0x12345678 -> get_rtc(0) = 0x1234 (C1)."""
        source = """
int main() {
    return get_rtc(0);
}
"""
        proc, _ = _compile_and_run(source, rtc_seconds=0x12345678)
        assert proc.p0 == 0x1234, f"Expected P0=0x1234, got {proc.p0:#06x}"
        assert proc.r0 == 0x34, f"Expected R0=0x34, got {proc.r0:#06x}"

    def test_get_rtc_one_returns_low_word(self):
        """rtc_seconds=0x12345678 -> get_rtc(1) = 0x5678 (C0)."""
        source = """
int main() {
    return get_rtc(1);
}
"""
        proc, _ = _compile_and_run(source, rtc_seconds=0x12345678)
        assert proc.p0 == 0x5678, f"Expected P0=0x5678, got {proc.p0:#06x}"
        assert proc.r0 == 0x78, f"Expected R0=0x78, got {proc.r0:#06x}"

    def test_get_rtc_zero_high_word_small_value(self):
        """Small epoch deltas keep the high word (get_rtc(0)) at zero."""
        source = """
int main() {
    return get_rtc(0);
}
"""
        proc, _ = _compile_and_run(source, rtc_seconds=0x0000ABCD)
        assert proc.p0 == 0, f"Expected P0=0, got {proc.p0:#06x}"

    def test_get_rtc_one_low_word_small_value(self):
        """Small epoch deltas keep the low word (get_rtc(1)) exact."""
        source = """
int main() {
    return get_rtc(1);
}
"""
        proc, _ = _compile_and_run(source, rtc_seconds=0x0000ABCD)
        assert proc.p0 == 0xABCD, f"Expected P0=0xABCD, got {proc.p0:#06x}"

    def test_get_rtc_with_variable_chunk(self):
        """A variable chunk argument selects the right word."""
        source = """
int main() {
    int c = 0;
    return get_rtc(c);
}
"""
        proc, _ = _compile_and_run(source, rtc_seconds=0x12345678)
        assert proc.p0 == 0x1234, f"Expected P0=0x1234, got {proc.p0:#06x}"

    def test_get_rtc_in_expression(self):
        """get_rtc(1) composes like any int-valued expression."""
        source = """
int main() {
    return get_rtc(1) + 1;
}
"""
        proc, _ = _compile_and_run(source, rtc_seconds=0x0000ABCD)
        assert proc.p0 == 0xABCE, f"Expected P0=0xABCE, got {proc.p0:#06x}"

    def test_get_rtc_full_32bit_via_two_reads(self):
        """Both chunks together reconstruct the full 32-bit value."""
        source = """
int main() {
    int hi = get_rtc(0);
    int lo = get_rtc(1);
    return hi + lo;
}
"""
        proc, _ = _compile_and_run(source, rtc_seconds=0x12345678)
        # hi=0x1234, lo=0x5678 -> 0x1234 + 0x5678 = 0x68AC
        assert proc.p0 == 0x68AC, f"Expected P0=0x68AC, got {proc.p0:#06x}"


if __name__ == "__main__":
    # Manual runner for non-pytest invocation
    failures = 0
    for test in (
        TestGetLayerBuiltin.test_get_layer_default_is_zero,
        TestGetLayerBuiltin.test_get_layer_reads_back_set_layer,
        TestGetLayerBuiltin.test_get_layer_with_variable_layer,
        TestGetLayerBuiltin.test_get_layer_tracks_successive_changes,
        TestGetColorBuiltin.test_get_color_reads_back_set_color,
        TestGetColorBuiltin.test_get_color_tracks_successive_changes,
        TestGetColorBuiltin.test_get_color_usable_in_expression,
        TestGetRTCBuiltin.test_get_rtc_zero_returns_high_word,
        TestGetRTCBuiltin.test_get_rtc_one_returns_low_word,
        TestGetRTCBuiltin.test_get_rtc_zero_high_word_small_value,
        TestGetRTCBuiltin.test_get_rtc_one_low_word_small_value,
        TestGetRTCBuiltin.test_get_rtc_with_variable_chunk,
        TestGetRTCBuiltin.test_get_rtc_in_expression,
        TestGetRTCBuiltin.test_get_rtc_full_32bit_via_two_reads,
    ):
        try:
            test(None)
            print(f"PASS {test.__name__}")
        except AssertionError as e:
            print(f"FAIL {test.__name__}: {e}")
            failures += 1
    if failures:
        print(f"{failures} test(s) failed!")
        sys.exit(1)
    print("All Astrid getter builtin tests passed!")