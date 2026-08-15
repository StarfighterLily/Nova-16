"""Diagnostic: compile starfield.ast, assemble, run headlessly, and inspect state."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nova_main import initialize_system

def main():
    astrid_dir = os.path.dirname(os.path.abspath(__file__))
    source_path = os.path.join(astrid_dir, 'starfield.ast')
    asm_path = os.path.join(astrid_dir, 'starfield_diag.asm')
    bin_path = os.path.join(astrid_dir, 'starfield_diag.bin')

    # Compile
    from astrid_compiler import main as compiler_main
    old_argv = sys.argv
    sys.argv = [old_argv[0], source_path, '-o', asm_path]
    try:
        compiler_main()
    finally:
        sys.argv = old_argv

    # Assemble
    from nova_assembler import Assembler
    asm = Assembler()
    asm.assemble(asm_path)

    # Run headlessly
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    entry_point = mem.load(bin_path)
    proc.pc = entry_point
    print(f"Entry point: 0x{entry_point:04X}")

    # Run in chunks and inspect
    for chunk in range(20):
        cycle = 0
        while cycle < 5000 and not proc.halted:
            cycle += 1
            proc.step()
        screen = gfx.screen
        non_zero = (screen != 0).sum()
        print(f"Chunk {chunk}: cycles={cycle}, PC=0x{proc.pc:04X}, halted={proc.halted}, "
              f"non_zero_pixels={non_zero}, R0=0x{proc.r0:02X}, SP=0x{proc.sp:04X}, FP=0x{proc.fp:04X}")
        if proc.halted:
            break

    # Check layer 1 specifically
    layer1 = gfx.layers[1] if hasattr(gfx, 'layers') else None
    if layer1 is not None:
        nz = (layer1 != 0).sum()
        print(f"Layer 1 non-zero pixels: {nz}")
    else:
        print("No layers attribute on gfx")

if __name__ == '__main__':
    main()