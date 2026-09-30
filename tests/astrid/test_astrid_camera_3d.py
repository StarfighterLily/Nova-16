"""Tests for the 3D camera library (astrid/progs/includes/camera.ast).

Two layers of validation:

1. ``test_projtest_*`` compile astrid/progs/projtest.ast, run it headlessly,
   and compare every scratch word it pokes against a Python model that
   re-derives the same integer arithmetic (Q8.8 sine/cosine, the split
   multiply, the Q7 inverse, the clamps). Hand-derived anchors (screen center
   for a dead-ahead point, symmetry, behind-the-camera rejection) are asserted
   separately so a bug in the model cannot hide a bug in the camera.
2. The same run's framebuffer is compared against a replay of the predicted
   screen endpoints through the same Bresenham rasterizer the GPU uses, which
   covers the near-plane clipping path of cam_line.

The ``test_demo_*`` cases compile the shipped demo programs and check that
they assemble, run, and draw on the layer they claim.
"""
import math
import os

import pytest

# Path setup is handled by tests/astrid/conftest.py
from nova_main import initialize_system

pytestmark = pytest.mark.integration

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ASTRID_DIR = os.path.join(_ROOT, 'astrid')
PROGS_DIR = os.path.join(ASTRID_DIR, 'progs')

SCRATCH = 0x9000          # projtest.ast pokes word results here


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------

def compile_program(name):
    """Compile+assemble a program in astrid/progs, returning the .bin path."""
    source_path = os.path.join(PROGS_DIR, name)
    asm_path = source_path[:-4] + '.asm'
    bin_path = source_path[:-4] + '.bin'
    from astrid.compiler_api import compile_astrid
    from nova_assembler import Assembler
    compile_astrid(source_path, asm_path, log=lambda m: None,
                   assemble_callback=lambda p, v, e: bool(
                       Assembler().assemble(str(p))))
    assert os.path.exists(asm_path), 'no assembly generated'
    assert os.path.exists(bin_path), 'no binary generated'
    return bin_path


def run_binary(bin_path, max_cycles):
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    entry = mem.load(bin_path)
    proc.pc = entry
    cycles = 0
    while cycles < max_cycles and not proc.halted:
        cycles += 1
        proc.step()
    return proc, mem, gfx, cycles


def read_slot(mem, slot):
    return mem.read_word(SCRATCH + slot * 2)


# ---------------------------------------------------------------------------
# Integer model of camera.ast (mirrors the emulator's instruction semantics)
# ---------------------------------------------------------------------------

def s16(v):
    """Wrap to signed 16-bit, the width of every CPU register."""
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def asr5(v):
    """cam_asr5: shift the magnitude, then re-apply the sign (toward zero)."""
    return -((-v) >> 5) if v < 0 else v >> 5


def qmul(a, cq):
    """cam_qmul: (a * cq) / 256 through the 128-unit split, sign folded out."""
    sign = 1
    if a < 0:
        sign = -sign
        a = -a
    if cq < 0:
        sign = -sign
        cq = -cq
    hi = (a >> 7) * cq
    lo = (a & 127) * cq
    return sign * ((hi >> 1) + (lo >> 8))


def trig(yaw):
    """cam_calc_trig: renormalize yaw, then raw Q8.8 sine/cosine bits."""
    while yaw > 16080:
        yaw -= 16088
    while yaw < -16080:
        yaw += 16088
    return yaw, int(math.sin(yaw / 256.0) * 256), int(math.cos(yaw / 256.0) * 256)


class Model:
    """The camera's state and arithmetic, independent of the assembly."""

    FOCAL = 112
    CX = 128
    CY = 128
    NEAR = 32
    NEAR32 = 1024

    def __init__(self):
        self.xq = self.yq = self.zq = 0
        self.yaw, self.sin, self.cos = trig(0)

    def set8(self, x8, y8, z8, yaw):
        self.xq, self.yq, self.zq = x8, y8, z8
        self.yaw, self.sin, self.cos = trig(yaw)

    def set(self, x, y, z, yaw):
        self.set8(x << 3, y << 3, z << 3, yaw)

    def forward(self, step8):
        self.xq += qmul(step8, self.sin)
        self.zq += qmul(step8, self.cos)

    def transform(self, wx, wy, wz):
        dx = (wx << 5) - (self.xq << 2)
        dy = (wy << 5) - (self.yq << 2)
        dz = (wz << 5) - (self.zq << 2)
        return (qmul(dx, self.cos) - qmul(dz, self.sin),
                dy,
                qmul(dx, self.sin) + qmul(dz, self.cos))

    def offset(self, vxw, vzw):
        if vzw < self.NEAR:
            vzw = self.NEAR
        inv = ((self.FOCAL << 7) + (vzw >> 1)) // vzw
        if inv < 1:
            inv = 1
        limit = 32767 // inv
        neg = vxw < 0
        if neg:
            vxw = -vxw
        if vxw > limit:
            vxw = limit
        t = (vxw * inv) >> 7
        return -t if neg else t

    def project(self, v):
        if v[2] < self.NEAR32:
            return 0, None, None
        z = asr5(v[2])
        return 1, self.CX + self.offset(asr5(v[0]), z), \
            self.CY - self.offset(asr5(v[1]), z)

    def depth(self, wx, wy, wz):
        v = self.transform(wx, wy, wz)
        return 0 if v[2] < self.NEAR32 else asr5(v[2])

    def line(self, x1, y1, z1, x2, y2, z2):
        """cam_line's screen endpoints, or None when the segment is dropped."""
        a = self.transform(x1, y1, z1)
        b = self.transform(x2, y2, z2)
        if a[2] >= self.NEAR32 and b[2] >= self.NEAR32:
            return (self.CX + self.offset(asr5(a[0]), asr5(a[2])),
                    self.CY - self.offset(asr5(a[1]), asr5(a[2])),
                    self.CX + self.offset(asr5(b[0]), asr5(b[2])),
                    self.CY - self.offset(asr5(b[1]), asr5(b[2])))
        if a[2] <= -self.NEAR32 or b[2] <= -self.NEAR32:
            return None
        ax, ay, az = a
        bx, by, bz = b
        if az < self.NEAR32:
            ax, ay, az, bx, by, bz = bx, by, bz, ax, ay, az
        axw, ayw, aw = asr5(ax), asr5(ay), asr5(az)
        den = aw - asr5(bz)
        if den < 1:
            return None
        t6 = ((aw - self.NEAR) << 6) // den
        bx = ax + (qmul(bx - ax, t6) << 2)
        by = ay + (qmul(by - ay, t6) << 2)
        return (self.CX + self.offset(axw, aw),
                self.CY - self.offset(ayw, aw),
                self.CX + self.offset(asr5(bx), self.NEAR),
                self.CY - self.offset(asr5(by), self.NEAR))


def bresenham(x1, y1, x2, y2):
    """Replay of gfx.draw_line's integer DDA, clipped to the 256x256 screen."""
    pixels = set()
    dx, dy = abs(x2 - x1), abs(y2 - y1)
    sx = 1 if x1 < x2 else -1
    sy = 1 if y1 < y2 else -1
    err = dx - dy
    x, y = x1, y1
    while True:
        if 0 <= x < 256 and 0 <= y < 256:
            pixels.add((x, y))
        if x == x2 and y == y2:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy
    return pixels


# The two segments projtest.ast draws (see the program's scratch map):
#   a fully visible diagonal, then one whose first endpoint is inside the
#   near plane and must be clipped forward before it can be drawn.
VISIBLE_SEGMENT = (-50, -50, 100, 50, 50, 100)
CLIPPED_SEGMENT = (0, 0, 10, 80, 0, 200)


def expected_screen():
    """Model-predicted screen endpoints and framebuffer for projtest.ast."""
    cam = Model()
    cam.set(0, 0, 0, 0)
    first = cam.line(*VISIBLE_SEGMENT)
    clipped = cam.line(*CLIPPED_SEGMENT)
    assert first is not None, 'the visible diagonal must project'
    assert clipped is not None, 'the straddling segment must clip, not drop'
    pixels = bresenham(*first) | bresenham(*clipped)
    return cam, first, clipped, pixels


# ---------------------------------------------------------------------------
# Compiler pipeline
# ---------------------------------------------------------------------------

def test_camera_library_compiles():
    """camera.ast is only meaningful inside a program; projtest includes it."""
    bin_path = compile_program('projtest.ast')
    assert os.path.getsize(bin_path) > 1000


def test_projtest_scratch_matches_model():
    """Every scratch word projtest pokes must equal the Python model exactly."""
    bin_path = compile_program('projtest.ast')
    proc, mem, gfx, cycles = run_binary(bin_path, 200000)
    assert proc.halted, f'projtest did not halt (PC=0x{proc.pc:04X})'
    cam, first, clipped, pixels = expected_screen()

    # Case 1: origin camera, yaw 0, point straight ahead. The transform is
    # exact (identity) and the projection must land on the screen center.
    assert [read_slot(mem, s) for s in range(3)] == [0, 0, 3200]
    assert [read_slot(mem, s) for s in range(3, 6)] == [1, 128, 128]

    # Case 2: 50 right / 100 ahead projects right of center at the same height.
    cam2 = Model()
    cam2.set(0, 0, 0, 0)
    v = cam2.transform(50, 0, 100)
    expected = cam2.project(v)
    assert [read_slot(mem, s) for s in range(6, 9)] == list(expected)
    assert read_slot(mem, 7) > 128 and read_slot(mem, 8) == 128

    # Case 3: a point 50 behind the eye is rejected, and its raw view z is
    # negative (proving signed int survived the transform).
    assert read_slot(mem, 9) == 0
    assert s16(read_slot(mem, 24)) == -1600

    # Case 4: yaw 402 is ~90 degrees, so world +x becomes straight ahead.
    cam90 = Model()
    cam90.set(0, 0, 0, 402)
    assert cam90.sin == 255 and cam90.cos == 0     # 1.0 truncates to 255
    expected = cam90.project(cam90.transform(100, 0, 0))
    assert [read_slot(mem, s) for s in range(10, 13)] == list(expected)
    assert read_slot(mem, 11) == 128 and read_slot(mem, 12) == 128

    # Case 5: moving the camera to (30,0,20) puts a point at (30,0,120) dead
    # ahead -- the camera position must subtract out exactly.
    cam5 = Model()
    cam5.set(30, 0, 20, 0)
    expected = cam5.project(cam5.transform(30, 0, 120))
    assert [read_slot(mem, s) for s in range(13, 16)] == list(expected)
    assert read_slot(mem, 14) == 128 and read_slot(mem, 15) == 128

    # Case 6: walking forward while facing +x moves +x only, in 1/8 units.
    assert read_slot(mem, 16) == qmul(48, 255)     # 47: sin is 255, not 256
    assert read_slot(mem, 17) == 0
    assert read_slot(mem, 18) == 0
    assert read_slot(mem, 19) == 255
    assert read_slot(mem, 20) == 0
    assert read_slot(mem, 21) == 402

    # Case 7: depth in world units; 0 is the "at or behind the near plane"
    # sentinel that cam_line uses as its visibility test.
    assert read_slot(mem, 25) == 100
    assert read_slot(mem, 26) == 0

    # Case 8: the two cam_line endpoints, then the model's own endpoints.
    assert [read_slot(mem, s) for s in range(27, 31)] == list(first)
    assert read_slot(mem, 31) == 1 and read_slot(mem, 32) == 1
    assert read_slot(mem, 33) == 200

    # Anchors that do not depend on the model: the visible diagonal is
    # symmetric about the screen center.
    assert first[0] - 128 == -(first[2] - 128)
    assert first[1] - 128 == -(first[3] - 128)
    assert first[0] < 128 < first[2] and first[1] > 128 > first[3]
    # The clipped segment runs at eye level (world y = 0) to the right of
    # center, and the clip point projects nearer the center than the far end.
    assert clipped[1] == 128 and clipped[3] == 128
    assert clipped[0] > 128 and clipped[2] > 128 and clipped[2] < clipped[0]


def test_projtest_framebuffer_matches_rasterized_model():
    """The GPU's pixels must equal a Bresenham replay of the model endpoints."""
    bin_path = compile_program('projtest.ast')
    proc, mem, gfx, cycles = run_binary(bin_path, 200000)
    assert proc.halted
    _, first, clipped, pixels = expected_screen()

    drawn = {(x, y) for y in range(256) for x in range(256)
             if int(gfx.screen[y, x]) != 0}
    assert drawn == pixels, (
        f'extra={sorted(drawn - pixels)[:8]} missing={sorted(pixels - drawn)[:8]}')

    # Both calls used color 0x1F on the layer the program selected.
    assert {int(gfx.screen[y, x]) for (x, y) in drawn} == {0x1F}
    assert first[0] == 73 and first[1] == 183 and first[2] == 183


def test_projtest_center_pixel_anchor():
    """A point dead ahead lands on (128,128) -- independent of the model."""
    bin_path = compile_program('projtest.ast')
    proc, mem, gfx, cycles = run_binary(bin_path, 200000)
    assert int(gfx.screen[128, 128]) == 0x1F


