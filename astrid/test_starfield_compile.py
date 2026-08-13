"""Verify the starfield.ast example compiles, assembles, and runs with the updated codegen."""
import os
import sys

# Add project root to path so we can import nova_main and astrid modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Add astrid directory to path so we can import astrid_compiler
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nova_main import initialize_system


def test_starfield_compiles_and_assembles():
    """Compile starfield.ast -> .asm, assemble -> .bin, and run headlessly."""
    astrid_dir = os.path.dirname(os.path.abspath(__file__))
    source_path = os.path.join(astrid_dir, 'starfield.ast')
    asm_path = os.path.join(astrid_dir, 'starfield_test_regen.asm')
    bin_path = os.path.join(astrid_dir, 'starfield_test_regen.bin')

    try:
        # Compile
        from astrid_compiler import main as compiler_main
        old_argv = sys.argv
        sys.argv = [old_argv[0], source_path, '-o', asm_path]
        try:
            compiler_main()
        finally:
            sys.argv = old_argv

        assert os.path.exists(asm_path), "Assembly file not generated"

        # Assemble
        from nova_assembler import Assembler
        asm = Assembler()
        asm.assemble(asm_path)
        assert os.path.exists(bin_path), "Binary file not generated"

        # Run headlessly. starfield has an infinite while(1) loop, so we
        # just verify it starts executing without crashing.
        proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
        entry_point = mem.load(bin_path)
        proc.pc = entry_point
        cycle = 0
        max_cycles = 10000
        while cycle < max_cycles and not proc.halted:
            cycle += 1
            proc.step()
        # Not halted because of the infinite while(1) loop, but should still
        # be executing valid code (PC should be well-formed)
        print(f"PASS test_starfield_compiles_and_assembles (cycles={cycle}, PC=0x{proc.pc:04X})")
    finally:
        # Clean up generated files
        for ext in ['.asm', '.bin', '.org', '.sym']:
            path = asm_path.replace('.asm', ext)
            if os.path.exists(path):
                os.unlink(path)


if __name__ == '__main__':
    test_starfield_compiles_and_assembles()
    print("Starfield compile test passed!")