from pathlib import Path

p = Path(r"c:\Code\\projects\\Nova\\astrid\\NovaDOS\\src\\kernel\\kernel.ast")
c = p.read_text(encoding="utf-8")

old = '''    shell_puts("---");
    // Hold the disk bank open for the whole payload. shell_putc only touches
    // graphics registers / cursor globals (outside 0x8000-0xBFFF), so a live
    // BANK is safe; Pure Option B still covers a tick mid-stream.
    set_bank(bank);
    byte_i = 0;
    while (byte_i < file_size) {
        c = peek(ndf_window + data_off + byte_i);
        // Drop to bank 0 around the put so any future shell_putc side effect
        // that reads base RAM under the window stays correct, then re-enter.
        set_bank(0);
        shell_putc(c);
        set_bank(bank);
        byte_i = byte_i + 1;
    }
    set_bank(0);
    shell_newline();
    shell_puts("---");
}'''

new = '''    shell_puts("---");
    // Hold the disk bank open for the whole payload. shell_putc only touches
    // graphics + cursor globals (outside 0x8000-0xBFFF under bank-safe), so a
    // live BANK is safe; Pure Option B still covers a tick mid-stream. One
    // open/close pair replaces 2*N set_bank calls of the old ndf_read8 loop.
    set_bank(bank);
    byte_i = 0;
    while (byte_i < file_size) {
        c = peek(ndf_window + data_off + byte_i);
        shell_putc(c);
        byte_i = byte_i + 1;
    }
    set_bank(0);
    shell_newline();
    shell_puts("---");
}'''

if old not in c:
    # maybe p3 wasn't applied; check current type end
    if "set_bank(bank);" in c and "ndf_find" in c:
        print("already looking for alt form")
        idx = c.find("shell_puts(\"---\");", c.find("void shell_type"))
        print(repr(c[idx:idx+500]))
    raise SystemExit("pattern not found")
c = c.replace(old, new)
p.write_text(c, encoding="utf-8")
print("simplified hold-open type")
