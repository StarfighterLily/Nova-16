"""Tests for the 3D camera library (astrid/progs/includes/camera.ast).

Layers of validation:

1. ``test_projtest_*`` compile astrid/progs/projtest.ast, run it headlessly,
   and compare every scratch word it pokes against a Python model that
   re-derives the same integer arithmetic (Q8.8 sine/cosine, the split
   multiply, the rounded reciprocal, the MUL/MULH scale, the near-plane
   interpolation). Hand-derived anchors (exact pixel values such as
   50 * 112 / 100 = 56 px, symmetry, behind-the-camera rejection) are
   asserted separately so a bug in the model cannot hide a bug in the camera.
2. ``test_clipper_*`` drive cam_draw_clipped and cam_line through a program
   built with -DCAM_TRACE, which prints every primitive handed to the GPU
   over the serial port. The clipped endpoints must equal the integer model
   exactly and an ideal floating-point clip to within one pixel -- including
   lines that leave through every edge, both endpoint orders, corner cuts and
   near-plane crossings.
3. ``test_demo_*`` run the shipped demos with -DCAM_TRACE for a few frames:
   every traced primitive must match the model, shared vertices must share
   pixels (connected edges stay connected), solid discs must arrive in
   painter's order, and the visible layer must hold an opaque finished frame.

The traces of all three demos were also diffed line for line between this
Python reference and nova16.exe (the 16 MHz compiled emulator) over every
frame of every demo, with identical results; these tests pin the Python side.
"""
import math
import os
import tempfile

import pytest

# Path setup is handled by tests/astrid/conftest.py
from nova_main import initialize_system

pytestmark = pytest.mark.integration

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ASTRID_DIR = os.path.join(_ROOT, 'astrid')
PROGS_DIR = os.path.join(ASTRID_DIR, 'progs')
CAMERA_INCLUDE = os.path.join(PROGS_DIR, 'includes', 'camera.ast').replace('\\', '/')

SCRATCH = 0x9000          # projtest.ast pokes word results here
CAM_BG = 0x10             # camera.ast's opaque black frame background


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------

def _compile(source_path, defines=None, outdir=None):
    """Compile+assemble an Astrid file, returning the .bin path."""
    from astrid.compiler_api import compile_astrid
    from nova_assembler import Assembler
    if outdir is None:
        outdir = tempfile.mkdtemp(prefix='astrid_cam_')
    base = os.path.splitext(os.path.basename(source_path))[0]
    asm_path = os.path.join(outdir, base + '.asm')
    compile_astrid(source_path, asm_path, log=lambda m: None, defines=defines,
                   assemble_callback=lambda p, v, e: bool(
                       Assembler().assemble(str(p))))
    bin_path = asm_path[:-4] + '.bin'
    assert os.path.exists(bin_path), 'no binary generated'
    return bin_path


def compile_program(name, defines=None):
    """Compile a program in astrid/progs into a temp dir (the checked-in
    binaries are left alone)."""
    return _compile(os.path.join(PROGS_DIR, name), defines)


def compile_source(text, defines=None):
    outdir = tempfile.mkdtemp(prefix='astrid_cam_')
    src = os.path.join(outdir, 'prog.ast')
    with open(src, 'w', encoding='utf-8') as f:
        f.write(text)
    return _compile(src, defines, outdir)


class _Capture:
    """UART host bridge that keeps everything the program transmits."""

    def __init__(self):
        self.data = bytearray()

    def send_bytes(self, data):
        self.data.extend(data)

    def poll_rx(self):
        return b''

    def close(self):
        return None


def run_binary(bin_path, max_cycles, frames=None):
    """Run a binary; with ``frames`` stop after that many traced 'F' lines.

    Returns (proc, mem, gfx, cycles, serial_text)."""
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    cap = _Capture()
    proc.uart.set_host_bridge(cap)
    proc.pc = mem.load(bin_path)
    cycles = 0
    while cycles < max_cycles and not proc.halted:
        cycles += 1
        proc.step()
        # '\nF\n': a bare F record, not the last hex digit of a word ("000F\n").
        if frames is not None and cap.data.count(b'\nF\n') >= frames:
            break
    return proc, mem, gfx, cycles, cap.data.decode('latin1')


def read_slot(mem, slot):
    return mem.read_word(SCRATCH + slot * 2)


def s16(v):
    """Wrap to signed 16-bit, the width of every CPU register."""
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def parse_trace(text):
    """CAM_TRACE output -> list of frames; each frame a list of tuples
    ('L', x1, y1, x2, y2, color) / ('C', x, y, r, color) / ('M', ...)."""
    frames, cur = [], []
    for line in text.splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == 'F':
            frames.append(cur)
            cur = []
        else:
            cur.append((parts[0],) + tuple(s16(int(p, 16)) for p in parts[1:]))
    if cur:
        frames.append(cur)
    return frames


# ---------------------------------------------------------------------------
# Integer model of camera.ast (mirrors the emulator's instruction semantics)
# ---------------------------------------------------------------------------

FOCAL = 112
CX = CY = 128
NEAR32 = 1024


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


def wrap(yaw):
    while yaw > 16085:
        yaw -= 16085
    while yaw < -16085:
        yaw += 16085
    return yaw


def qsin(a):
    return int(math.sin(wrap(a) / 256.0) * 256)


def qcos(a):
    return int(math.cos(wrap(a) / 256.0) * 256)


def muldiv(a, b, c):
    """cam_muldiv: round(a * b / c) via the exact product and remainder."""
    q, r = divmod(a * b, c)
    return q + (1 if 2 * r >= c else 0)


def smuldiv(a, b, c):
    return -muldiv(-a, b, c) if a < 0 else muldiv(a, b, c)


def recip(z):
    """cam_recip: round(FOCAL * 65536 / z)."""
    return muldiv(FOCAL, 65536, z)


def scale(v, inv):
    """cam_scale: round(|v| * inv / 65536) from MUL/MULH, sign re-applied."""
    p = abs(v) * inv
    t = (p >> 16) + (1 if (p & 0xFFFF) >= 0x8000 else 0)
    return -t if v < 0 else t


def proj(x, y, z):
    inv = recip(z)
    return CX + scale(x, inv), CY - scale(y, inv)


def outcode(x, y):
    return (x < 0) | ((x > 255) << 1) | ((y < 0) << 2) | ((y > 255) << 3)


def clip2d(x1, y1, x2, y2):
    """cam_draw_clipped: Cohen-Sutherland, interpolating from the anchor."""
    c1, c2 = outcode(x1, y1), outcode(x2, y2)
    guard = 0
    while c1 | c2:
        if c1 & c2:
            return None
        if c1 == 0:
            px, py, qx, qy, cc = x2, y2, x1, y1, c2
        else:
            px, py, qx, qy, cc = x1, y1, x2, y2, c1
        if cc & 1:
            py, px = qy + smuldiv(py - qy, qx, qx - px), 0
        elif cc & 2:
            py, px = qy + smuldiv(py - qy, 255 - qx, px - qx), 255
        elif cc & 4:
            px, py = qx + smuldiv(px - qx, qy, qy - py), 0
        else:
            px, py = qx + smuldiv(px - qx, 255 - qy, py - qy), 255
        if c1 == 0:
            x2, y2 = px, py
            c2 = outcode(x2, y2)
        else:
            x1, y1 = px, py
            c1 = outcode(x1, y1)
        guard += 1
        if guard > 4:
            return None
    return x1, y1, x2, y2


def line_v(a, b):
    """cam_line_v: near-plane clip in view space, project, clip on screen."""
    ax, ay, az = a
    bx, by, bz = b
    if az < NEAR32:
        if bz < NEAR32:
            return None
        ax, ay, az, bx, by, bz = bx, by, bz, ax, ay, az
    if bz < NEAR32:
        num, den = az - NEAR32, az - bz
        bx = ax + smuldiv(bx - ax, num, den)
        by = ay + smuldiv(by - ay, num, den)
        bz = NEAR32
    return clip2d(*proj(ax, ay, az), *proj(bx, by, bz))


class Model:
    """The camera's state and arithmetic, independent of the assembly."""

    def __init__(self):
        self.set8(0, 0, 0, 0)

    def set8(self, x8, y8, z8, yaw):
        self.xq, self.yq, self.zq = x8, y8, z8
        self.yaw = wrap(yaw)
        self.sin, self.cos = qsin(yaw), qcos(yaw)

    def set(self, x, y, z, yaw):
        self.set8(x << 3, y << 3, z << 3, yaw)

    def forward(self, step8):
        self.xq += qmul(step8, self.sin)
        self.zq += qmul(step8, self.cos)

    def strafe(self, step8):
        self.xq += qmul(step8, self.cos)
        self.zq -= qmul(step8, self.sin)

    def transform8(self, x8, y8, z8):
        dx = s16((x8 - self.xq) << 2)
        dy = s16((y8 - self.yq) << 2)
        dz = s16((z8 - self.zq) << 2)
        return (qmul(dx, self.cos) - qmul(dz, self.sin), dy,
                qmul(dx, self.sin) + qmul(dz, self.cos))

    def transform(self, wx, wy, wz):
        return self.transform8(wx << 3, wy << 3, wz << 3)

    def project(self, v):
        if v[2] < NEAR32:
            return 0, None, None
        return (1,) + proj(*v)

    def depth(self, wx, wy, wz):
        v = self.transform(wx, wy, wz)
        return 0 if v[2] < NEAR32 else asr5(v[2])

    def line(self, x1, y1, z1, x2, y2, z2):
        """cam_line's drawn endpoints, or None when nothing reaches the GPU."""
        return line_v(self.transform(x1, y1, z1), self.transform(x2, y2, z2))


# ---------------------------------------------------------------------------
# Floating-point reference (ideal geometry, no integer shortcuts)
# ---------------------------------------------------------------------------

def ideal_clip(x1, y1, x2, y2):
    """Liang-Barsky clip of a real segment to the [0, 255] screen square."""
    t0, t1 = 0.0, 1.0
    dx, dy = x2 - x1, y2 - y1
    for p, q in ((-dx, x1), (dx, 255 - x1), (-dy, y1), (dy, 255 - y1)):
        if p == 0:
            if q < 0:
                return None
        else:
            r = q / p
            if p < 0:
                t0 = max(t0, r)
            else:
                t1 = min(t1, r)
    if t0 > t1:
        return None
    return x1 + t0 * dx, y1 + t0 * dy, x1 + t1 * dx, y1 + t1 * dy


def ideal_line_v(a, b):
    """Exact near clip and projection of view-space points (world * 32)."""
    a = [c / 32.0 for c in a]
    b = [c / 32.0 for c in b]
    if a[2] < 32 and b[2] < 32:
        return None
    if a[2] < 32:
        a, b = b, a
    if b[2] < 32:
        t = (a[2] - 32) / (a[2] - b[2])
        b = [a[i] + (b[i] - a[i]) * t for i in range(3)]
    return ideal_clip(CX + a[0] * FOCAL / a[2], CY - a[1] * FOCAL / a[2],
                      CX + b[0] * FOCAL / b[2], CY - b[1] * FOCAL / b[2])


def line_distance(px, py, seg):
    """Distance from a point to the infinite line through a real segment."""
    x1, y1, x2, y2 = seg
    length = math.hypot(x2 - x1, y2 - y1)
    if length == 0:
        return math.hypot(px - x1, py - y1)
    return abs((x2 - x1) * (y1 - py) - (x1 - px) * (y2 - y1)) / length


# The two segments projtest.ast draws (see the program's scratch map):
#   a fully visible diagonal, then one whose first endpoint is inside the
#   near plane and must be clipped forward before it can be drawn.
VISIBLE_SEGMENT = (-50, -50, 100, 50, 50, 100)
CLIPPED_SEGMENT = (0, 0, 10, 80, 0, 200)


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


@pytest.fixture(scope='module')
def projtest_run():
    bin_path = compile_program('projtest.ast')
    proc, mem, gfx, cycles, _ = run_binary(bin_path, 400000)
    assert proc.halted, f'projtest did not halt (PC=0x{proc.pc:04X})'
    return proc, mem, gfx


# ---------------------------------------------------------------------------
# projtest.ast: projection math against the model and hand anchors
# ---------------------------------------------------------------------------

def test_projtest_scratch_matches_model(projtest_run):
    """Every scratch word projtest pokes must equal the Python model exactly."""
    proc, mem, gfx = projtest_run
    cam, first, clipped, pixels = expected_screen()

    # Case 1: origin camera, yaw 0, point straight ahead. The transform is
    # exact (identity) and the projection must land on the screen center.
    assert [read_slot(mem, s) for s in range(3)] == [0, 0, 3200]
    assert [read_slot(mem, s) for s in range(3, 6)] == [1, 128, 128]

    # Case 2: 50 right / 100 ahead lands exactly 50 * 112 / 100 = 56 px right
    # of center at the same height.
    cam2 = Model()
    cam2.set(0, 0, 0, 0)
    expected = cam2.project(cam2.transform(50, 0, 100))
    assert [read_slot(mem, s) for s in range(6, 9)] == list(expected)
    assert read_slot(mem, 7) == 128 + 56 and read_slot(mem, 8) == 128

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

    # Case 7: depth in world units; 0 is the "in front of the near plane"
    # sentinel that cam_line uses as its visibility test.
    assert read_slot(mem, 25) == 100
    assert read_slot(mem, 26) == 0

    # Case 8: the diagonal's projected endpoints, then the model's own.
    assert [read_slot(mem, s) for s in range(27, 31)] == list(first)
    assert read_slot(mem, 31) == 1 and read_slot(mem, 32) == 1
    assert read_slot(mem, 33) == 200

    # Anchors that do not depend on the model: the visible diagonal is
    # symmetric about the screen center and exact (50 * 112 / 100 = 56).
    assert first == (72, 184, 184, 72)
    # The clipped segment runs at eye level (world y = 0) to the right of
    # center. Its far end is 80 * 112 / 200 = 44.8 px right (173); the near
    # end is cut at z = 32 where x = 80 * 22 / 190, i.e. 32.4 px right (160).
    assert clipped == (173, 128, 160, 128)


def test_projtest_framebuffer_matches_rasterized_model(projtest_run):
    """The GPU's pixels must equal a Bresenham replay of the model endpoints."""
    proc, mem, gfx = projtest_run
    _, first, clipped, pixels = expected_screen()

    drawn = {(x, y) for y in range(256) for x in range(256)
             if int(gfx.screen[y, x]) != 0}
    assert drawn == pixels, (
        f'extra={sorted(drawn - pixels)[:8]} missing={sorted(pixels - drawn)[:8]}')
    assert {int(gfx.screen[y, x]) for (x, y) in drawn} == {0x1F}


def test_projtest_center_pixel_anchor(projtest_run):
    """A point dead ahead lands on (128,128) -- independent of the model."""
    proc, mem, gfx = projtest_run
    assert int(gfx.screen[128, 128]) == 0x1F


# ---------------------------------------------------------------------------
# Clipping: 2D screen clip and 3D near-plane clip through the serial trace
# ---------------------------------------------------------------------------

# 2D segments for cam_draw_clipped: inside, every exit edge in both endpoint
# orders, both endpoints outside, corner cut, corner miss, steep and shallow.
CLIP2D_CASES = [
    (10, 10, 200, 100),          # wholly inside: untouched
    (231, 149, 383, 268),        # exits right (the old clipper drew y = 149)
    (383, 268, 231, 149),        # same segment, outside endpoint first
    (25, 149, -127, 268),        # exits left
    (-127, 268, 25, 149),
    (128, 128, 300, -900),       # exits top
    (128, 128, -40, 1900),       # exits bottom
    (-100, 128, 400, 128),       # crosses the whole screen horizontally
    (-10, 20, 20, -10),          # cuts the top-left corner
    (-20, 5, 5, -20),            # misses the top-left corner
    (-50, -50, -10, 300),        # wholly left
    (128, -2000, 130, 2600),     # steep, both ends far outside
    (-2000, 40, 2400, 41),       # shallow, both ends far outside
    (255, 0, 0, 255),            # exactly corner to corner
]

# 3D segments (view space is world space: camera at the origin, yaw 0).
CLIP3D_CASES = [
    (0, 0, 10, 80, 0, 200),          # near end inside the near plane
    (-192, -80, -192, -192, -80, 192),  # floor edge passing beside the eye
    (192, 112, -50, 192, 112, 300),  # ceiling edge passing above
    (-60, -40, 20, 90, 30, 25),      # wholly behind the near plane
    (-400, -80, 100, 400, -80, 100), # wide edge, both ends off screen
    (0, -80, -192, 0, -80, 192),     # floor line straight under the eye
]


def _clip_program():
    calls = []
    for i, (x1, y1, x2, y2) in enumerate(CLIP2D_CASES):
        calls.append(f'    r = cam_draw_clipped({x1}, {y1}, {x2}, {y2}, 15);\n'
                     f'    cam_trace(77, {i}, r, 0, 0, 0);')
    for i, seg in enumerate(CLIP3D_CASES):
        calls.append(f'    cam_line({", ".join(map(str, seg))}, 15);\n'
                     f'    cam_trace(78, {i}, 0, 0, 0, 0);')
    return ('include "%s";\n\nvoid main() {\n    ser_ctrl(1);\n'
            '    cam_set(0, 0, 0, 0);\n    signed int r = 0;\n%s\n    halt();\n}\n'
            % (CAMERA_INCLUDE, '\n'.join(calls)))


@pytest.fixture(scope='module')
def clip_trace():
    bin_path = compile_source(_clip_program(), defines={'CAM_TRACE': None})
    proc, mem, gfx, cycles, text = run_binary(bin_path, 2000000)
    assert proc.halted
    records = parse_trace(text)[0]
    # Split into per-call results: each call's 'L' (if any) precedes its marker.
    out2d, out3d, pending = {}, {}, None
    for rec in records:
        if rec[0] == 'L':
            pending = rec[1:5]
        elif rec[0] == 'M':
            out2d[rec[1]] = (pending, rec[2])
            pending = None
        elif rec[0] == 'N':
            out3d[rec[1]] = pending
            pending = None
    return out2d, out3d


def test_clipper_2d_matches_model(clip_trace):
    out2d, _ = clip_trace
    assert len(out2d) == len(CLIP2D_CASES)
    for i, seg in enumerate(CLIP2D_CASES):
        drawn, ret = out2d[i]
        expected = clip2d(*seg)
        assert drawn == expected, (i, seg, drawn, expected)
        assert ret == (0 if expected is None else 1)


def test_clipper_2d_matches_ideal_geometry(clip_trace):
    """Clipped endpoints lie on the screen and within a pixel of the true line."""
    out2d, _ = clip_trace
    for i, seg in enumerate(CLIP2D_CASES):
        drawn, _ = out2d[i]
        ideal = ideal_clip(*map(float, seg))
        if ideal is None:
            assert drawn is None, (i, seg, drawn)
            continue
        assert drawn is not None, (i, seg)
        assert all(0 <= c <= 255 for c in drawn), (i, drawn)
        for px, py in ((drawn[0], drawn[1]), (drawn[2], drawn[3])):
            assert line_distance(px, py, ideal) <= 1.0, (i, seg, drawn, ideal)
    # Symmetry: the same segment clips to the same pixels in either order.
    assert out2d[1][0] == (231, 149, 255, 168)
    assert out2d[2][0] == (255, 168, 231, 149)
    assert out2d[0][0] == CLIP2D_CASES[0]       # an inside segment is untouched


def test_clipper_3d_matches_model_and_ideal(clip_trace):
    _, out3d = clip_trace
    cam = Model()
    for i, seg in enumerate(CLIP3D_CASES):
        expected = cam.line(*seg)
        assert out3d[i] == expected, (i, seg, out3d[i], expected)
        ideal = ideal_line_v(cam.transform(*seg[:3]), cam.transform(*seg[3:]))
        if expected is None:
            assert ideal is None, (i, ideal)
            continue
        for px, py in ((expected[0], expected[1]), (expected[2], expected[3])):
            assert line_distance(px, py, ideal) <= 1.0, (i, expected, ideal)


# ---------------------------------------------------------------------------
# The shipped demos
# ---------------------------------------------------------------------------

def _demo_trace(name, frames, max_cycles):
    bin_path = compile_program(name, defines={'CAM_TRACE': None})
    proc, mem, gfx, cycles, text = run_binary(bin_path, max_cycles, frames=frames)
    traced = parse_trace(text)
    assert len(traced) >= frames, f'{name}: only {len(traced)} frames traced'
    return proc, gfx, traced[:frames]


CUBE_X = [-60, 60, -60, 60, -60, 60, -60, 60]
CUBE_Y = [-60, -60, 60, 60, -60, -60, 60, 60]
CUBE_Z = [-60, -60, -60, -60, 60, 60, 60, 60]
CUBE_A = [0, 1, 3, 2, 4, 5, 7, 6, 0, 1, 2, 3]
CUBE_B = [1, 3, 2, 0, 5, 7, 6, 4, 4, 5, 6, 7]


def _cube_model_frame(f):
    cam = Model()
    a = (f * 67) // 6
    cam.set8(qmul(1920, qsin(a)), -320, qmul(1920, qcos(a)), a + 804)
    lines = []
    for k in range(-2, 3):
        lines.append(cam.line(k * 100, -60, -200, k * 100, -60, 200))
        lines.append(cam.line(-200, -60, k * 100, 200, -60, k * 100))
    view = [cam.transform(CUBE_X[i], CUBE_Y[i], CUBE_Z[i]) for i in range(8)]
    edges = [line_v(view[CUBE_A[e]], view[CUBE_B[e]]) for e in range(12)]
    return [l for l in lines if l], edges, view


def test_demo_cube3d_matches_model_and_stays_connected():
    proc, gfx, traced = _demo_trace('cube3d.ast', 4, 1500000)
    for f, frame in enumerate(traced):
        grid, edges, view = _cube_model_frame(f)
        got = [rec[1:5] for rec in frame if rec[0] == 'L']
        expected = grid + [e for e in edges if e]
        assert sorted(got) == sorted(expected), f'frame {f}'
        # All ten grid lines reach the screen on these frames (the signed
        # for-loop used to stop the grid after k = -1).
        assert len(grid) == 10
        # Connected edges stay connected: every on-screen cube corner is one
        # pixel shared by all three of its edges.
        corner_px = {i: proj(*view[i]) for i in range(8) if view[i][2] >= NEAR32}
        for e in edges:
            assert e is not None
        for e in range(12):
            for end, corner in ((edges[e][:2], CUBE_A[e]), (edges[e][2:], CUBE_B[e])):
                px = corner_px[corner]
                if 0 <= px[0] <= 255 and 0 <= px[1] <= 255:
                    assert end == px, (f, e, end, px)
        # Painter's order: cube edges arrive far to near.
        keys = []
        for rec in frame[len(grid):]:
            idx = edges.index(rec[1:5])
            keys.append(view[CUBE_A[idx]][2] + view[CUBE_B[idx]][2])
        assert keys == sorted(keys, reverse=True), f'frame {f}'


def test_demo_depth3d_draws_sorted_discs_on_a_closed_ring():
    proc, gfx, traced = _demo_trace('depth3d.ast', 3, 1500000)
    for f, frame in enumerate(traced):
        ring = [rec[1:5] for rec in frame if rec[0] == 'L']
        discs = [rec[1:5] for rec in frame if rec[0] == 'C']
        # Every light is visible (the old demo fed 1/8-unit positions in as
        # whole world units and drew nothing).
        assert len(discs) == 16, f'frame {f}: {len(discs)} discs'
        for x, y, r, color in discs:
            assert 0 <= x <= 255 and 0 <= y <= 255 and 1 <= r <= 8
        # Painter's order: radius grows with nearness, so it never shrinks.
        radii = [d[2] for d in discs]
        assert radii == sorted(radii), f'frame {f}: {radii}'
        assert radii[0] < radii[-1]
        # The floor ring is one closed loop: 16 segments, each starting where
        # the previous one ended.
        assert len(ring) == 16
        for i in range(16):
            assert ring[i][2:] == ring[(i + 1) % 16][:2], (f, i)


def test_demo_room3d_matches_model():
    """The first walking frames of room3d against the model's scene and script."""
    W, FL, CE, D = 192, -80, 112, 48
    segs = []
    for h in (FL, 16, CE):
        segs.append((-W, h, -W, W, h, -W))
    segs += [(-W, FL, W, -D, FL, W), (D, FL, W, W, FL, W), (-W, 16, W, -D, 16, W),
             (D, 16, W, W, 16, W), (-D, 64, W, D, 64, W), (-W, CE, W, W, CE, W),
             (-D, FL, W, -D, 64, W), (D, FL, W, D, 64, W)]
    for h in (FL, 16, CE):
        segs += [(-W, h, -W, -W, h, W), (W, h, -W, W, h, W)]
    for x, z in ((-W, -W), (W, -W), (-W, W), (W, W)):
        segs.append((x, FL, z, x, CE, z))
    for k in (-1, 0, 1):
        segs += [(k * 96, FL, -W, k * 96, FL, W), (k * 96, CE, -W, k * 96, CE, W)]
    lo, hi = 72, 120
    for (x1, y1, z1, x2, y2, z2) in [
            (lo, -24, lo, hi, -24, lo), (lo, 24, lo, hi, 24, lo), (lo, -24, hi, hi, -24, hi),
            (lo, 24, hi, hi, 24, hi), (lo, -24, lo, lo, -24, hi), (hi, -24, lo, hi, -24, hi),
            (lo, 24, lo, lo, 24, hi), (hi, 24, lo, hi, 24, hi), (lo, -24, lo, lo, 24, lo),
            (hi, -24, lo, hi, 24, lo), (lo, -24, hi, lo, 24, hi), (hi, -24, hi, hi, 24, hi)]:
        segs.append((x1, y1, z1, x2, y2, z2))

    frames = 6
    proc, gfx, traced = _demo_trace('room3d.ast', frames, 1500000)
    cam = Model()
    cam.set(0, -40, -96, 0)
    for f in range(frames):
        cam.forward(32)                  # script: walk toward the door
        expected = [l for l in (cam.line(*s) for s in segs) if l]
        got = [rec[1:5] for rec in traced[f] if rec[0] == 'L']
        assert sorted(got) == sorted(expected), f'frame {f}'
        # The center floor and ceiling beams (x = 0) are drawn: vertical
        # lines through the screen center column.
        assert any(l[0] == 128 and l[2] == 128 for l in got)


def test_demo_frames_are_double_buffered():
    """The visible layer holds an opaque finished frame; the work layer is
    hidden underneath it."""
    bin_path = compile_program('cube3d.ast', defines={'CAM_NOPACE': None})
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    proc.pc = mem.load(bin_path)
    for _ in range(120000):              # a little over two frames
        proc.step()
    show = gfx.background_layers[0]      # layer 1 (CAM_SHOW)
    assert int((show == 0).sum()) == 0, 'visible frame has transparent holes'
    assert int((show == CAM_BG).sum()) < 65536, 'visible frame is empty'
    assert int(gfx.VL) == 0              # still drawing on the work layer
