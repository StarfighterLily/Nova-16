import sys; sys.path.insert(0,'.')
from NovaDOS.tests.conftest import boot_novados, run_until, in_repl, KBD_DELAY_MS
import time
proc, mem, gfx, kbd = boot_novados()
assert run_until(proc, in_repl, max_cycles=20000)

print('=== Booted ===')
print('cursor y:', mem.read_byte(0x0025))
print('PC:', hex(proc.pc))
print('VL:', proc.gfx.VL)
print('VX:', proc.gfx.VX)
print('VY:', proc.gfx.VY)
print()

# Check what proc.gfx.layers looks like
print('layers shape:', gfx._compositor.layers.shape)
for layer in range(3):
    non_zero = (gfx._compositor.layers[layer] != 0).sum()
    print('layer {} non-zero pixels: {}'.format(layer, non_zero))

print()
print('=== Typing single char on layer 1 ===')
kbd.add_key(ord('A'))
run_until(proc, lambda p: p.flags[7]==1, max_cycles=10000)
print('After A: VL=', proc.gfx.VL, 'VX=', proc.gfx.VX, 'VY=', proc.gfx.VY)
for layer in range(3):
    non_zero = (gfx._compositor.layers[layer] != 0).sum()
    print('layer {} non-zero pixels: {}'.format(layer, non_zero))
    if non_zero > 0:
        for row in range(0, 240, 8):
            has = [col for col in range(256) if gfx._compositor.layers[layer][row,col]!=0]
            if has:
                print('  layer {} row {}: cols {}'.format(layer, row, has[:10]))