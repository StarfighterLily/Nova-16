# Star System 1

A small operating system for the Nova-16, written in Astrid.

**Document status:** This is a de-facto statement of intent. Every device,
address, and behavior described below refers to a real, verifiable Nova-16
mechanism (see `docs/CPU Specification.md`, `docs/VRAM Specification.md`,
`docs/SPRITE_SYSTEM.md`, `docs/SOUND_SYSTEM.md`, `docs/UART_SYSTEM.md`).
Nothing here requires hardware that does not exist.

Heritage: Plan 9's "everything is a file" namespace discipline, fused with
MS-DOS's raw, single-address-space directness. On the Nova-16 this fusion is
not a metaphor — the machine presents one 64KB address space (expanded by a
bank-switched window, below), has no MMU, and memory-maps its peripherals,
so a file that *is* the hardware is the only honest abstraction available.

---

## Platform Facts This Design Is Built On

| Resource | Nova-16 reality |
|---|---|
| Address space | 64KB unified (Princeton), big-endian |
| Banked window | 0x8000–0xBFFF (16KB), 16 banks selected by the `BANK` register (code 0xC2; `MOV BANK, imm/reg`). Bank 0 is pass-through to base RAM; banks 1–15 are separate 16KB pages — exactly +240KB. Writes to banked pages never touch base memory; word accesses straddling 0xBFFF resolve per-byte. Bank switches clamp out-of-range values and always invalidate the instruction cache. Binary loading (`load`) always targets base RAM regardless of active bank. |
| Zero page | 0x0000–0x00FF, hot-cached |
| Interrupt vectors | 0x0100–0x011F — 8 vectors × 4 bytes; handler read from `0x0100 + vec*4`; priority: timer > keyboard > user |
| Program image | Assembled at `ORG 0x1000+` (Astrid default entry) |
| Globals / data | 0x8000+ (Astrid `gvar_*` symbols) — note this sits *inside* the bank window; see the banking policy in §3 |
| String buffers | ITOS at 0xA000, ITOB at 0xA100 |
| Compiler spill region | 0xC000–0xEFFF (kernel keeps its tables below this) |
| Sprite control blocks | 0xF000–0xF0FF — 16 sprites × 16 bytes; writes publish `memory.scb_written` |
| Stack | Grows down from 0xFFFF (Astrid initializes SP=FP=0xFFFF) |
| Video | 256×256 px, 8 layers; VM(0xE1)=0 coordinate / =1 address mode; VX(0xFD)/VY(0xFE)/VC(0xC8)/VL(0xE2) |
| Sound | 8 channels; SA(0xDD)/SF(0xDE)/SV(0xDF)/SW(0xE0) + SPLAY; channel in SW bits 3–5 |
| Timer | TT(0xE3)/TM(0xE4)/TC(0xE5)/TS(0xE6); fires vector 0 |
| RTC | C0(0xC3)/C1(0xC4), read-only |
| Mouse | MX(0xC5)/MY(0xC6)/MB(0xC7) |
| Keyboard | KEYIN/KEYSTAT/KEYCLEAR — 16-key ring, publishes `keyboard.key_pressed` |
| Serial | UART (`nova_uart.py`) with TCP/terminal host bridge: ser_out / ser_in / ser_stat / ser_ctrl |

## Toolchain

```powershell
py -3.13 astrid/astrid_compiler.py starsystem.ast -o starsystem.asm
py -3.13 nova_assembler.py starsystem.asm
py -3.13 nova_main.py --headless starsystem.bin --cycles 100000
```

## 1. Everything Is a File — Including the Silicon

There is no syscall layer between a program and the machine, so the device
tree is a *naming convention over existing access paths*. Opening a device
means agreeing on which register or memory window a name denotes. Streams are
raw binary bytes — there is no text parsing anywhere in the kernel.

| Path | Backing hardware | Semantics |
|---|---|---|
| `/dev/vga/layers/0..8` | VL, VX, VY, VC; SWRITE / SFILL | A byte written is one pixel of that color at (VX,VY) on layer VL. SFILL floods the active layer. |
| `/dev/vga/mode` | VM | 0 = coordinate mode, 1 = address mode (VX/VY index VRAM directly). |
| `/dev/vga/glyphs` | VC, TEXT | Byte streams render as font glyphs at (VX,VY) in color VC. Glyphs are 8×8; only set bits write pixels — erase by rewriting the same glyph in color 0. |
| `/dev/vga/scroll/x`,`y` | SROL | Roll a layer's content along an axis; wraps at screen edges. |
| `/dev/vga/rect` | SRECT | Filled/outline rectangle from (VX,VY), color VC. |
| `/dev/vga/sprites/0..15` | SCB at 0xF000+n*16 | Direct word writes; each write notifies the sprite engine via `memory.scb_written`. |
| `/dev/pic` | IVT 0x0100–0x011F | Handler addresses, 4 bytes per vector, 8 vectors. Vector 0 = timer, 1 = keyboard, 2–7 = user. Mask = STI / CLI. Raise = `INT n`. |
| `/dev/timer` | TT, TM, TC, TS | Counter, modulo threshold, control (bit 0 enable, bit 1 IRQ enable), speed divisor (TS+1 cycles per tick). |
| `/dev/rtc` | C0, C1 | Read-only wall clock. Writes are discarded. |
| `/dev/key` | KEYIN / KEYSTAT | Reads dequeue raw key codes from the ring (0 = empty). KEYSTAT bit 0 = ready, bit 1 = full. |
| `/dev/snd/ch/0..7` | SA, SF, SV, SW, SPLAY | Address, frequency (0–255 ≈ 55–1760 Hz), volume (0–255), waveform/channel/enable word. |
| `/dev/mouse` | MX, MY, MB | Position and buttons, refreshed by the host bridge. |
| `/dev/com` | UART | ser_out / ser_in / ser_stat / ser_ctrl. The transport behind §2. |

Because these are conventions over real opcodes, a device "driver" is just an
Astrid function — often three instructions long:

```c
// /dev/vga/layers/N putc: emit one pixel
void px_putc(int layer, int x, int y, int color) {
    set_layer(layer);
    set_pos(x, y);
    write_screen(color);
}
```

## 2. Network-Transparent Bus

The Nova-16 already has the wire: the UART with its TCP host bridge
(`create_host_bridge`). Star System layers a framed protocol over it:

- **Frame:** `[magic u8][path-len u8][path][op u8][payload...]`. Ops: READ,
  WRITE, STAT. Minimal metadata, fits the serial byte stream.
- **NET USE:** `NET USE B: //wizard-node/dev/vga` opens a session over
  `/dev/com` and binds the remote node's device path to a local drive letter.
  Reads/writes on `B:` are serialized into frames and replayed by the remote
  node's kernel against its own hardware.
- **What this buys:** another Nova-16's screen, sound chip, keyboard, or spare
  RAM becomes locally mountable. A headless rack node can serve its sprite
  engine to a terminal across the room.

**The cost, stated plainly:** both machines are real-mode with a single
address space and no protection. If a remote peer writes past the end of a
mounted window, it corrupts *local* memory and can crash the machine. Sharing
is caring; a bad length field is fatal. The mitigation is bounds checking in
the frame handler — protocol-level, not hardware — so the frame parser is the
security boundary and must be treated like one.

## 3. Drive Letters as Union Mounts

On the Nova-16 there are no disks — storage *is* memory. Drive letters name
stacked search lists over memory regions:

| Letter | Composition (searched in order) |
|---|---|
| `C:` | Resident system segments: code at 0x1000+, data/globals at 0x8000+. Always backed by base RAM (bank 0). |
| `R:` | RAM disk living in **bank pages**: `MOV BANK, n` selects page *n* of the 0x8000–0xBFFF window; banks 1–15 provide exactly 240KB of removable-page storage. |
| `A:`–`E:` | Remote mounts via NET USE (§2). |

**Banking policy (kernel invariant):** the window at 0x8000–0xBFFF overlaps
the resident globals/data region. Therefore banks are only nonzero while the
kernel is explicitly reading or writing an `R:` page, and every such access
is bracketed by save/restore of `BANK`:

```c
// Read one byte from R: page n at window offset off
int r_read(int n, int off) {
    int prev = read_bank();      // MOV R?, BANK
    set_bank(n);                 // MOV BANK, n   (clamped 0-15)
    int v = peek(0x8000 + off);
    set_bank(prev);
    return v;
}
```

With `BANK` restored to 0 before any other operation, globals and program
data are never shadowed. Two hardware behaviors make this cheap and safe:
bank switches invalidate only the instruction cache (no writeback — banked
writes never touch base memory), and binary loads always land in base RAM,
so program images can never end up stranded in a hidden page.

Mounting is pure bookkeeping: push a region descriptor onto a drive's union
stack. Installing a program means appending its `.bin` segments (with the
assembler's `.org` segment info) to a stack entry — no partitioning, no
formatting. Binary lookup walks the stack top-down and executes the first
hit, DOS-style.

The union tables live in zero page and low general memory — the hot-cached
regions the CPU favors — because path resolution happens on every open.

## 4. The Plumbing Vector Table

The interrupt vector table at 0x0100–0x011F is eight 32-bit slots. That is
the whole extension mechanism, and Star System treats it as such:

- **Vectors 0–1** belong to the hardware (timer, keyboard).
- **Vector 7** is the **plumb vector**: the kernel installs one dispatcher
  there at boot. User "TSRs" never patch vectors directly; they *register*
  with the dispatcher, which multiplexes typed message packets to them.
- **Registration** is a table entry `{ hotkey, handler-address }` in the
  kernel registry region. A popup calculator, a screen saver, a network
  responder — all are ordinary Astrid functions that stay resident in high
  memory and wait for their packet.
- **Message routing** follows the plumber model: events carry types, and a
  filter chain decides who receives them. A hotkey plumbs a "show calculator"
  packet; the handler draws onto a sprite layer (§5), waits for dismissal,
  and restores the previous layer contents.

Interrupt safety is guaranteed by compiler contract, not hope: the Astrid
code generator emits full register save/restore around every ISR body
(hardware entry pushes only PC + flags). Any function named
`timer_interrupt()` is auto-wired at `ORG 0x0100` at link time.

## 5. Windows Are Files

The window system is text-mode rendering plus layer discipline — rio's sweep
gesture wearing a COMMAND.COM suit:

- **A window is a device file**: `/dev/win/1` … backed by a dedicated
  compositor layer (background layers 1–4 for static content, sprite layers
  5+ for popups/overlays) plus a clip rectangle.
- **Drawing is piping**: writing a byte stream to a window file renders it
  through the glyph device at the window cursor. Shell redirection into a
  window file *is* how UI widgets get drawn — no drawing API above TEXT.
- **Sweep-to-create:** hold the right mouse button (MB), track MX/MY, release
  → the swept rectangle becomes `/dev/win/N` on the next free sprite layer,
  containing a bare prompt running the shell. Every window is equally close
  to the metal.
- **Compositing is free:** the GPU's 8-layer compositor handles z-ordering;
  windows never read each other's buffers, so overlap costs nothing.

---

## Summary of Fusions

| Pillar | Plan 9 half | DOS half | Nova-16 realization |
|---|---|---|---|
| Resource abstraction | Synthetic filesystems | Memory-mapped I/O | Device names bound directly to registers (VX/VY/VL/VC, TT/TM/TC/TS, …) and opcodes (SWRITE, TEXT, SPLAY) |
| Storage | Central file servers | Drive letters | Drive letters as union stacks over memory regions + `.org` segment images |
| Execution | Per-process namespaces | Real-mode binaries | One address space; isolation only via layer/region discipline |
| Networking | Transparent 9P mounting | NET USE / NetBIOS | Framed device protocol over the UART/TCP bridge |
| Shell/UI | rc + rio plumbing | TSR hotkeys, TUI | Plumb-vector multiplexer + glyph-pipe windows on compositor layers |

## Non-Goals

- No virtual memory, no user/kernel split, no per-process address spaces.
  The 64KB view (plus explicit bank pages behind 0x8000–0xBFFF) is a feature:
  every "file" is genuinely the hardware, and banking is a kernel policy, not
  a protection mechanism.
- No C runtime, no dynamic linking. Programs are position-segmented `.bin`
  images produced by the standard pipeline.
- No graphics API above the glyph and pixel devices. If it can't be expressed
  as bytes written to a file, it isn't in the kernel.

## Boot Order (Intent)

1. Loader places kernel image at 0x1000; SP=FP=0xFFFF; `BANK`=0 (pass-through).
2. Kernel clears layers 0–8, programs the plumb dispatcher into vector 7,
   installs default `C:`/`R:` unions in the zero-page tables.
3. Timer programmed (`TM`, `TC=0x03`, `TS`) as the scheduler heartbeat;
   then STI.
4. Sweep the mouse or type at the console: either opens your first window.



