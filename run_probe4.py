import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'astrid')

# Recompile the probes to pick up the latest codegen, then assemble and run.
import importlib
import astrid_compiler
importlib.reload(astrid_compiler)


def compile_one(name):
    old = list(sys.argv)
    sys.argv = ['astrid_compiler.py', name + '.ast']
    try:
        astrid_compiler.main()
    finally:
        sys.argv = old


compile_one('probe_signed')
compile_one('probe_floatcmp')

from nova_assembler import Assembler
from nova_main import initialize_system

Assembler().assemble('probe_signed.asm')
Assembler().assemble('probe_floatcmp.asm')


def run(path):
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    entry = mem.load(path)
    proc.pc = entry
    c = 0
    while c < 2000000 and not proc.halted:
        c += 1
        proc.step()
    return proc, c

for p in ['probe_signed.bin', 'probe_floatcmp.bin']:
    pr, cy = run(p)
    print("%s -> R0=%d P0=%d halted=%s cycles=%d"
          % (p, pr.r0, pr.p0, pr.halted, cy))