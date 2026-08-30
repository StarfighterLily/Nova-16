import sys
sys.path.insert(0, '.')
from nova_main import initialize_system
def run(path):
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    entry = mem.load(path); proc.pc = entry; c = 0
    while c < 2000000 and not proc.halted:
        c += 1; proc.step()
    return proc, c
proc, c = run('probe_rec.bin')
print('fact(5): R0=%d P0=%d halted=%s cycles=%d' % (proc.r0, proc.p0, proc.halted, c))
proc, c = run('probe_cstr.bin')
print('cstr: R0=%d P0=%d halted=%s cycles=%d' % (proc.r0, proc.p0, proc.halted, c))
