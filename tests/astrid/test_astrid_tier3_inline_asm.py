"""Tests for Tier 3: inline assembly features.

Covers:
- asm("...") string-form inline asm as a statement
- asm { ... } block-form inline asm as a statement
- asm("...") in expression context (P0 holds result)
- {varname} substitution resolving locals to [FP+n] / registers
- {varname} substitution resolving globals to [0xXXXX]
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


def compile_and_run(source, expected_r0=None, expected_p0=None, max_cycles=2000000):
    """Compile Astrid source, assemble, and run. Returns (proc, cycles, mem)."""
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
        Assembler().assemble(asm_path)
        proc, cycles, mem = run_binary(bin_path, max_cycles=max_cycles)
        assert proc.halted, "Program did not halt"
        if expected_r0 is not None:
            assert proc.r0 == expected_r0, f"Expected R0={expected_r0}, got {proc.r0}"
        if expected_p0 is not None:
            assert proc.p0 == expected_p0, f"Expected P0={expected_p0}, got {proc.p0}"
        return proc, cycles, mem
    finally:
        os.unlink(source_path)
        for ext in ['.asm', '.bin', '.org', '.sym']:
            path = source_path.replace('.ast', ext)
            if os.path.exists(path):
                os.unlink(path)


class TestInlineAsmStatement:
    """Inline asm as a statement (existing behavior, regression check)."""

    def test_asm_string_form_emitted(self):
        """asm("MOV R0, 5") should emit the raw instruction in the assembly."""
        source = """
int main() {
    asm("MOV R0, 42");
    return 0;
}
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
            with open(asm_path, encoding='utf-8') as f:
                text = f.read()
            assert 'MOV R0, 42' in text, "asm instruction not found in output"
        finally:
            os.unlink(source_path)
            for ext in ['.asm', '.bin', '.org', '.sym']:
                p = source_path.replace('.ast', ext)
                if os.path.exists(p):
                    os.unlink(p)

    def test_asm_block_form_emitted(self):
        """asm { MOV R0, 7; } should emit the raw instructions."""
        source = """
int main() {
    asm {
        MOV R0, 7
    }
    return 0;
}
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
            with open(asm_path, encoding='utf-8') as f:
                text = f.read()
            assert 'MOV R0, 7' in text, "asm block instruction not found in output"
        finally:
            os.unlink(source_path)
            for ext in ['.asm', '.bin', '.org', '.sym']:
                p = source_path.replace('.ast', ext)
                if os.path.exists(p):
                    os.unlink(p)


class TestInlineAsmExpression:
    """Inline asm in expression context: P0 holds the result."""

    def test_asm_expression_string_form(self):
        """int x = asm("MOV P0, 99"); should load 99 into x via P0."""
        source = """
int main() {
    int x = asm("MOV P0, 99");
    return x;
}
"""
        proc, cycles, mem = compile_and_run(source, expected_r0=99)

    def test_asm_expression_used_in_arithmetic(self):
        """asm result in P0 should compose with arithmetic."""
        source = """
int main() {
    int x = asm("MOV P0, 50");
    return x + 25;
}
"""
        proc, cycles, mem = compile_and_run(source, expected_r0=75)


class TestInlineAsmVarSubstitution:
    """{varname} substitution in inline asm."""

    def _compile_to_asm_text(self, source):
        """Compile source and return the assembly text."""
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
            with open(asm_path, encoding='utf-8') as f:
                return f.read()
        finally:
            os.unlink(source_path)
            for ext in ['.asm', '.bin', '.org', '.sym']:
                p = source_path.replace('.ast', ext)
                if os.path.exists(p):
                    os.unlink(p)

    def test_asm_substitute_local(self):
        """{x} in asm should resolve to the local's memory address."""
        source = """
int main() {
    int x = 10;
    asm("MOV R0, {x}");
    return 0;
}
"""
        text = self._compile_to_asm_text(source)
        # The substitution should resolve {x} to a memory reference
        # (either [FP+n] for FP-relative or [0xXXXX] for spilled/globals)
        assert '{x}' not in text, "Unresolved {x} found in output"
        # Should contain a memory reference (not the bare {x} token)
        assert 'MOV R0, [' in text, "Expected MOV R0, [mem] after substitution"

    def test_asm_substitute_global(self):
        """{g} in asm should resolve to the global's absolute address."""
        source = """
int g = 55;
int main() {
    asm("MOV R0, {g}");
    return 0;
}
"""
        text = self._compile_to_asm_text(source)
        assert '{g}' not in text, "Unresolved {g} found in output"
        assert 'MOV R0, [' in text, "Expected MOV R0, [mem] after substitution"

    def test_asm_substitute_multiple_vars(self):
        """Multiple {var} substitutions in one asm block."""
        source = """
int main() {
    int a = 20;
    int b = 30;
    asm("MOV R0, {a}; ADD R0, {b}");
    return 0;
}
"""
        text = self._compile_to_asm_text(source)
        assert '{a}' not in text, "Unresolved {a} found in output"
        assert '{b}' not in text, "Unresolved {b} found in output"
        # Both should be resolved to memory references
        # Count memory references in the asm instructions
        lines = text.split('\n')
        mem_refs = 0
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('MOV R0, [') or stripped.startswith('ADD R0, ['):
                mem_refs += 1
        assert mem_refs >= 2, \
            f"Expected at least 2 memory references after substitution, got {mem_refs}"

    def test_asm_substitute_unknown_passes_through(self):
        """Unknown {name} should have braces stripped for label resolution."""
        source = """
int main() {
    asm("JMP {some_label}");
    return 0;
}
"""
        text = self._compile_to_asm_text(source)
        # Unknown names have braces stripped (bare name used as asm label)
        assert 'JMP some_label' in text, "Unknown {name} should resolve to bare label"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
