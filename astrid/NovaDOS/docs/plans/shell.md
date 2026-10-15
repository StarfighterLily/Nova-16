# NovaDOS (Astrid) — Shell Commands

Status: implemented 2026-10-15 (`src/kernel/shell.ast`). Tests:
`astrid/NovaDOS/tests/test_shell.py`, `test_programs.py`.

Type a line (up to 27 characters) and press Enter. Words are separated by
spaces; command names are case-insensitive, and so are file names, which are
stored in upper case. Numbers are decimal (`-12`) or hex with a `0x` or `$`
prefix (`0x1F`, `$1F`). Backspace edits the line; Esc shuts down like `BYE`.

| Command | Effect |
|---|---|
| `HELP` | list the commands compiled into this build |
| `CLS` | clear the console |
| `PEEK [addr] [count]` | hex bytes at addr (count 1-8, default 1). No arguments: the OS signature, `4E 44` |
| `POKE addr byte...` | write bytes from addr upward |
| `MEM` | free kmalloc heap and program-area size, hex |
| `TIME` | timer ticks since boot, hex |
| `ECHO words...` | print the words, one space apart |
| `X = expr` | set variable X (A-Z). `expr` is terms joined by `+` / `-`; a term is a number or a variable |
| `PRINT expr` | print an expression as signed decimal |
| `LIST` | print every non-zero variable |
| `DIR` | list the current volume: name, type (TXT/PRG), size, free space |
| `TYPE name` | print a file |
| `BANK [n]` | show or select the volume bank (1-15) used by the file commands |
| `FORMAT` | create an empty volume in the current bank |
| `LOAD name` | copy a file to the program area (`0x5800`) |
| `SAVE name [addr len]` | store memory as a program file; without addr/len, the program last loaded |
| `RUN` | call the loaded program |
| `CALL addr` | call any address (the code must `RET`) |
| `NEW` | clear the program area |
| `BYE` | shut down; the machine halts after "System halted." |

`DIR`, `TYPE`, `BANK`, `FORMAT`, `LOAD` and `SAVE` are absent from a
diskless build (`-DNOVADOS_ENABLE_NDF=0`), and `HELP` does not list them.

Errors print one line: `bad command`, `usage: ...`, or a file error
(`file not found`, `directory full`, `disk full`, `file exists`, `bad name`).

## Adding a command

1. Write `void cmd_name()` in `shell.ast`. Arguments are in `argc`/`argv[]`
   (word addresses); read numbers with `arg_num(i, fallback)` and check
   `bad_args`, file names with `arg_name(i)`.
2. Add an id to `enum ShellCmd` (ids are stable; tests observe them through
   `shell_cmd`).
3. Add one row to `commands[]`. `HELP` picks it up automatically.

Keep output lines within 30 characters: the console starts at column 2, and
the emulator's TEXT wraps to column 0 at the screen edge.
