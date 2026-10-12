import time, sys, os
sys.path.insert(0, os.getcwd())
from nova_main import initialize_system
proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
proc.pc = 0x1000
# busy loop: JMP self at 0x1000
mem.load_bytes(0x1000, bytes([0x00, 0x00])) if hasattr(mem, 'load_bytes') else None
t0 = time.time()
N = 500000
for i in range(N):
    proc.step()
dt = time.time() - t0
print(f'python step loop: {N} cycles in {dt:.2f}s = {N/dt/1e6:.3f} Mc/s')
