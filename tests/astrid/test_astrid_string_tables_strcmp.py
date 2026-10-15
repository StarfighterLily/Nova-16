"""String tables in global initializers, and a working strcmp.

Both surfaced while reworking NovaDOS's shell (2026-10-15):

* `string names[] = {"HELP", "DIR"}` was rejected ("initializers must be
  compile-time constants") although a scalar `string s = "x"` and a
  function-pointer table `{ &f, &g }` were both accepted. Each element is
  now the literal's label, emitted as a DW.
* `strcmp` never returned a usable value: the STRCMP opcode leaves its
  result in R0, but the stub returned P1 (the first string's address). It
  also required a third (length) argument; a C-style two-argument call
  popped a stray stack word as the bound.
"""
import os
import tempfile

# Path setup is handled by tests/astrid/conftest.py
from nova_main import initialize_system


def _run(source):
    from astrid.compiler_api import compile_astrid
    from nova_assembler import Assembler
    tmpdir = tempfile.mkdtemp(prefix='astrid_strtab_')
    src = os.path.join(tmpdir, 'prog.ast')
    asm = os.path.join(tmpdir, 'prog.asm')
    with open(src, 'w', encoding='utf-8') as f:
        f.write(source)
    compile_astrid(src, asm, log=lambda m: None,
                   assemble_callback=lambda p, v, e: bool(Assembler().assemble(str(p))))
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    proc.pc = mem.load(asm[:-4] + '.bin')
    cycles = 0
    while not proc.halted and cycles < 200000:
        proc.step()
        cycles += 1
    assert proc.halted
    syms = {}
    with open(asm[:-4] + '.sym') as f:
        for line in f:
            parts = line.split()
            if len(parts) == 2:
                syms[parts[0].lower()] = int(parts[1], 16)
    return mem, syms


def _words(mem, addr, n):
    out = []
    for i in range(n):
        v = mem.read_word(addr + 2 * i)
        out.append(v - 0x10000 if v & 0x8000 else v)
    return out


def test_strcmp_two_and_three_argument_forms():
    mem, syms = _run("""
int r[6];
char buf[8];
void main() {
    buf[0] = 'D'; buf[1] = 'I'; buf[2] = 'R'; buf[3] = 0;
    r[0] = strcmp("HELP", "HELP");
    r[1] = strcmp("ABC", "ABD");
    r[2] = strcmp("ABD", "ABC");
    r[3] = strcmp(buf, "DIR");
    r[4] = strcmp("AB", "ABC");
    r[5] = strcmp("HELPX", "HELPY", 4);
}
""")
    assert _words(mem, syms['gvar_r'], 6) == [0, -1, 1, 0, -1, 0]


def test_struct_table_with_strings_and_function_pointers():
    # A dispatch table: one row per command, string + id + handler address.
    # Struct-array initializers used to accept numeric constants only.
    mem, syms = _run("""
struct Command { string name; int id; int handler; };
int calls = 0;
int f_help() { calls = calls + 1; return 0; }
int f_dir() { calls = calls + 10; return 0; }
const struct Command commands[] = {
    "HELP", 1, &f_help,
    "DIR",  5, &f_dir
};
int r[4];
void main() {
    int i;
    int (*h)();
    for (i = 0; i < sizeof(commands) / sizeof(struct Command); i++) {
        if (strcmp("DIR", commands[i].name) == 0) {
            r[0] = commands[i].id;
            h = commands[i].handler;
            h();
        }
    }
    r[1] = calls;
    r[2] = sizeof(commands);
    r[3] = strlen(commands[0].name);
}
""")
    assert _words(mem, syms['gvar_r'], 4) == [5, 10, 12, 4]


def test_global_string_tables_hold_literal_pointers():
    mem, syms = _run("""
string names[3] = {"HELP", "DIR", "BYE"};
const string ro[2] = {"ONE", "TWO"};
int r[5];
void main() {
    int i;
    for (i = 0; i < 3; i = i + 1) { r[i] = strlen(names[i]); }
    r[3] = strcmp(ro[1], "TWO");
    r[4] = peek(names[2]);
}
""")
    assert _words(mem, syms['gvar_r'], 5) == [4, 3, 3, 0, ord('B')]
