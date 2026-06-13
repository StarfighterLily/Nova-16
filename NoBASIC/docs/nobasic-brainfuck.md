# NoBASIC Brainfuck Interpreter

## Pipeline Summary

The NoBASIC toolchain in this repo is:

1. Preprocess `#include` directives in `NoBASIC/nobasic_compiler.py`.
2. Lex and parse through `NoBASIC/compiler/lexer` and `NoBASIC/compiler/parser`.
3. Run semantic analysis in `NoBASIC/compiler/semantic/analyzer.py`.
4. Generate Nova-16 assembly in `NoBASIC/compiler/codegen/generator.py`.
5. Assemble the generated `.asm` into `.bin` through `nova_assembler.py` or the MCP `nobasic_compile` path.

## Interpreter Location

The Brainfuck interpreter source is at `NoBASIC/progs/brainfuck_interpreter.nobasic`.

The interpreter keeps all Brainfuck state in NoBASIC globals because the current runtime path for general `MEMWRITE`/`MEMREAD` usage in compiled NoBASIC programs is unreliable in this repo.

Implemented Brainfuck commands:

- `>` and `<` move a wrapped tape pointer across 8 cells.
- `+` and `-` update byte cells with 0-255 wrapping.
- `.` writes the current byte into `out0`..`out7`.
- `,` reads from `in0`..`in3`.
- `[` and `]` use forward/backward scans over the built-in program stream.

## Built-in Demo Program

The embedded Brainfuck program is:

```text
+++++++[>++++++++<-]>+.+.
```

Expected output:

```text
AB
```

## Compile Via MCP

Use the MCP `nobasic_compile` tool against:

`c:\Code\projects\Nova\NoBASIC\progs\brainfuck_interpreter.nobasic`

This produces:

- `NoBASIC/progs/brainfuck_interpreter.asm`
- `NoBASIC/progs/brainfuck_interpreter.bin`

## Execution Caveat

The current MCP emulator run helpers in this workspace stop after 10 cycles on NoBASIC-generated binaries even when the normal emulator executes them correctly. Compile/load/disassembly work through MCP, but execution verification currently needs the normal headless emulator path.

Validated command:

```powershell
py -3.13 .\nova.py --headless .\NoBASIC\progs\brainfuck_interpreter.bin --cycles 250000
```

Observed final state after validation:

- `outCount = 2`
- `out0 = 0x41`
- `out1 = 0x42`

So the interpreter emits `AB` as expected.