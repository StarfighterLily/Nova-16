from pathlib import Path

p = Path(r"c:\Code\projects\Nova\astrid\NovaDOS\src\kernel\kernel.ast")
c = p.read_text(encoding="utf-8")

c = c.replace(
    "int shell_cmd = 0;      // last dispatched command: 0 none, 1 HELP, 2 CLS, 3 PEEK, 4 BYE, 5 DIR, 6 TYPE",
    "int shell_cmd = 0;      // 0 none, 1 HELP, 2 CLS, 3 PEEK, 4 BYE, 5 DIR, 6 TYPE, 7 MEM, 8 TIME",
)

# Replace shell_type body only (keep DIR as-is for now).
old_type_start = c.find("void shell_type() {")
old_type_end = c.find("#endif", old_type_start)
assert old_type_start > 0 and old_type_end > old_type_start

new_type = '''void shell_type() {
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
}

'''

c = c[:old_type_start] + new_type + c[old_type_end:]
p.write_text(c, encoding="utf-8")
print("type replaced", "ndf_find" in c)
