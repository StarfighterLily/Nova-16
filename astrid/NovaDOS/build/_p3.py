from pathlib import Path

p = Path(r"c:\Code\projects\Nova\astrid\NovaDOS\src\kernel\kernel.ast")
c = p.read_text(encoding="utf-8")

# Fix TYPE: int chunk[n] reads words, not bytes. Use a held-bank print loop
# after metadata is fetched -- graphics builtins never touch the bank window.
old = '''void shell_type() {
    int bank;
    int slot;
    int file_size;
    int data_off;
    int byte_i;
    int n0;
    int n1;
    int n2;
    int n3;
    int n4;
    int n5;
    int n6;
    int n7;
    int chunk[16];
    int got;
    int n;
    int left;
    int take;
    bank = 1;
    if (ndf_mounted(bank) == 0) {
        shell_puts("no NDF volume in bank 1");
        return;
    }
    n0 = 0; n1 = 0; n2 = 0; n3 = 0; n4 = 0; n5 = 0; n6 = 0; n7 = 0;
    n = line_len - 1;
    if (n > 8) { n = 8; }
    if (n > 0) { n0 = line_buf[1]; }
    if (n > 1) { n1 = line_buf[2]; }
    if (n > 2) { n2 = line_buf[3]; }
    if (n > 3) { n3 = line_buf[4]; }
    if (n > 4) { n4 = line_buf[5]; }
    if (n > 5) { n5 = line_buf[6]; }
    if (n > 6) { n6 = line_buf[7]; }
    if (n > 7) { n7 = line_buf[8]; }
    slot = ndf_find(bank, n0, n1, n2, n3, n4, n5, n6, n7);
    if (slot < 0) {
        shell_puts("file not found");
        return;
    }
    file_size = ndf_entry_size(bank, slot);
    data_off = ndf_entry_data(bank, slot);
    shell_puts("---");
    byte_i = 0;
    while (byte_i < file_size) {
        left = file_size - byte_i;
        take = left;
        if (take > 16) { take = 16; }
        got = ndf_read_into(bank, data_off + byte_i, &chunk[0], take);
        n = 0;
        while (n < got) {
            shell_putc(chunk[n] & 0xFF);
            n = n + 1;
        }
        byte_i = byte_i + got;
    }
    shell_newline();
    shell_puts("---");
}'''

new = '''void shell_type() {
    int bank;
    int slot;
    int file_size;
    int data_off;
    int byte_i;
    int n0;
    int n1;
    int n2;
    int n3;
    int n4;
    int n5;
    int n6;
    int n7;
    int n;
    int c;
    bank = 1;
    if (ndf_mounted(bank) == 0) {
        shell_puts("no NDF volume in bank 1");
        return;
    }
    // Pad the typed name to 8 NUL bytes for ndf_find.
    n0 = 0; n1 = 0; n2 = 0; n3 = 0; n4 = 0; n5 = 0; n6 = 0; n7 = 0;
    n = line_len - 1;
    if (n > 8) { n = 8; }
    if (n > 0) { n0 = line_buf[1]; }
    if (n > 1) { n1 = line_buf[2]; }
    if (n > 2) { n2 = line_buf[3]; }
    if (n > 3) { n3 = line_buf[4]; }
    if (n > 4) { n4 = line_buf[5]; }
    if (n > 5) { n5 = line_buf[6]; }
    if (n > 6) { n6 = line_buf[7]; }
    if (n > 7) { n7 = line_buf[8]; }
    slot = ndf_find(bank, n0, n1, n2, n3, n4, n5, n6, n7);
    if (slot < 0) {
        shell_puts("file not found");
        return;
    }
    file_size = ndf_entry_size(bank, slot);
    data_off = ndf_entry_data(bank, slot);
    shell_puts("---");
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

if old not in c:
    raise SystemExit("old type not found")
c = c.replace(old, new)
p.write_text(c, encoding="utf-8")
print("type fixed")
