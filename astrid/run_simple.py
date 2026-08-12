import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from nova_main import initialize_system

proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
entry = mem.load('astrid/simple.bin')
proc.pc = entry
cycle = 0
while cycle < 200000 and not proc.halted:
    cycle += 1
    proc.step()
print(f'halted={proc.halted}, cycles={cycle}')
print(f'PC=0x{proc.pc:04X}, SP=0x{proc.sp:04X}, FP=0x{proc.fp:04X}')
print(f'R0-R9: {[f"0x{r:02X}" for r in proc.Rregisters[:10]]}')
