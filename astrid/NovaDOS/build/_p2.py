from pathlib import Path

p = Path(r"c:\Code\projects\Nova\astrid\NovaDOS\src\kernel\kernel.ast")
c = p.read_text(encoding="utf-8")

# Insert MEM/TIME before HELP, and update HELP text.
old_help = '''// HELP: only advertise commands compiled into this build.
void shell_help() {
#if NOVADOS_ENABLE_NDF
    shell_puts("HELP PEEK CLS DIR TYPE BYE");
#else
    shell_puts("HELP PEEK CLS BYE");
#endif
}'''

new_help = '''// MEM: report kmalloc bump-allocator free bytes as 4 hex digits.
void shell_mem() {
    int freeb;
    freeb = kmalloc_free();
    shell_col = 2;
    shell_goto(shell_col, shell_row);
    write_text("MEM free=", 0x0F);
    shell_col = 11;
    shell_puthex((freeb >> 8) & 0xFF);
    shell_puthex(freeb & 0xFF);
    shell_newline();
}

// TIME: print system_ticks (ISR counter) as 4 hex digits.
// First-char dispatch uses 'I' because 'T' is already TYPE.
void shell_time() {
    int t;
    t = system_ticks;
    shell_col = 2;
    shell_goto(shell_col, shell_row);
    write_text("TIME ", 0x0F);
    shell_col = 7;
    shell_puthex((t >> 8) & 0xFF);
    shell_puthex(t & 0xFF);
    shell_newline();
}

// HELP: only advertise commands compiled into this build.
void shell_help() {
#if NOVADOS_ENABLE_NDF
    shell_puts("HELP PEEK CLS DIR TYPE MEM TIME BYE");
#else
    shell_puts("HELP PEEK CLS MEM TIME BYE");
#endif
}'''

if old_help not in c:
    raise SystemExit("old help block not found")
c = c.replace(old_help, new_help)

old_disp_tail = '''    } else if (c == 66 || c == 98) {    // 'B' / 'b'
        shell_cmd = 4;
        shell_exit = 1;                 // graceful shutdown: main halts after the loop
#if NOVADOS_ENABLE_NDF
    } else if (c == 68 || c == 100) {   // 'D' / 'd'
        shell_cmd = 5;
        shell_dir();
    } else if (c == 84 || c == 116) {   // 'T' / 't'
        shell_cmd = 6;
        shell_type();
#endif
    }'''

new_disp_tail = '''    } else if (c == 66 || c == 98) {    // 'B' / 'b'
        shell_cmd = 4;
        shell_exit = 1;                 // graceful shutdown: main halts after the loop
    } else if (c == 77 || c == 109) {   // 'M' / 'm'
        shell_cmd = 7;
        shell_mem();
    } else if (c == 73 || c == 105) {   // 'I' / 'i'  (tIme -- T is TYPE)
        shell_cmd = 8;
        shell_time();
#if NOVADOS_ENABLE_NDF
    } else if (c == 68 || c == 100) {   // 'D' / 'd'
        shell_cmd = 5;
        shell_dir();
    } else if (c == 84 || c == 116) {   // 'T' / 't'
        shell_cmd = 6;
        shell_type();
#endif
    }'''

if old_disp_tail not in c:
    raise SystemExit("dispatch tail not found")
c = c.replace(old_disp_tail, new_disp_tail)

p.write_text(c, encoding="utf-8")
print("help+dispatch OK")
print("mem", "void shell_mem" in c)
print("time", "void shell_time" in c)
print("help_n", c.count("void shell_help()"))
