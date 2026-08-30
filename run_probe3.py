import sys
sys.path.insert(0, '.')
from nova_main import initialize_system

def run(path):
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    entry = mem.load(path)
    proc.pc = entry
    c = 0
    while c < 2000000 and not proc.halted:
        c += 1
        proc.step()
    return proc, c

for p in sys.argv[1:]:
    pr, cy = run(p)
    print("%s -> R0=%d P0=%d halted=%s cycles=%d" % (p, pr.r0, pr.p0, pr.halted, cy))