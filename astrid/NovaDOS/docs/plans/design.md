# NovaDOS — A TI-OS / DOS / Plan-9 Hybrid for the Nova-16

This is the Astrid implementation of NovaDOS. The parent project planned the
kernel in assembly; here the whole OS is written in Astrid, which has enough
systems features (inline asm, interrupt handlers, task switching, absolute
placement, function pointers) to do it in a higher-level language.

The parent design document was removed from the tree in commit `ba75aad`.
Read it with:

```powershell
git show ba75aad^:NovaDOS/docs/plans/design.md
git show ba75aad^:NovaDOS/docs/plans/memory-map.md
```

Where this port differs from the parent design, this directory wins:

* Memory map: the Astrid `bank-safe` layout decides where code, globals and
  scratch live; see `programs-and-syscalls.md` §1.
* Programs load at `0x5800`, not `0x1800`.
* The NDF directory entry has an 8-byte name (parent: 10) followed by
  type, flags, size and data offset; see `programs-and-syscalls.md` §4.

## Phase status

| Phase (parent design §10) | State in the Astrid port |
|---|---|
| 0 Scaffold, banner, boot stub, vectors, HELP | done |
| 1 Console I/O, REPL, NDF loader, A-Z variables, SYS mailbox, LOAD/RUN sample | done, except Str0-9 string variables |
| 2 Device drivers (Plan-9 files), timer heartbeat, batch runner | timer heartbeat done; devices and batch files not started |
| 3 GUI launcher, editor, settings, network console | not started |
| 4 Cooperative multitasking, FAT upgrade, TCP/IP, IDE | two-task kernel (shell + background); full scheduler opt-in and untested beyond boot |

Next steps, in the order they unblock each other:

1. String variables `Str0`-`Str9` (closes Phase 1).
2. `DEL` and file growth in NDF (needs a free-space scheme instead of the
   bump allocator).
3. A batch runner: `RUN` of a text file feeds its lines to `shell_execute`.
4. Device files over the SYS mailbox (`/con` first: SYS_READ/SYS_WRITE with
   a device id).
