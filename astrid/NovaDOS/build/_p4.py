from pathlib import Path

# Shrink NDF: drop ndf_find (8-arg, ~1KB) and unused ndf_read_into.
ndf = Path(r"c:\Code\projects\Nova\astrid\NovaDOS\src\fs\ndf.ast")
c = ndf.read_text(encoding="utf-8")
# Keep through ndf_add; drop find + read_into.
cut = c.find("\n// Find a directory entry")
if cut < 0:
    cut = c.find("\nint ndf_find(")
assert cut > 0, "find marker missing"
ndf.write_text(c[:cut] + "\n", encoding="utf-8")
print("ndf trimmed to", cut, "chars")

# Compact shell_type: one banked name scan, no ndf_find; hold bank for payload.
k = Path(r"c:\Code\projects\Nova\astrid\NovaDOS\src\kernel\kernel.ast")
kc = k.read_text(encoding="utf-8")
start = kc.find("void shell_type() {")
end = kc.find("#endif", start)
assert start > 0 and end > start
new_type = '''void shell_type() {
    int bank;
    int count;
    int slot;
    int name_i;
    int match;
    int file_size;
    int data_off;
    int byte_i;
    int c;
    int want;
    bank = 1;
    if (ndf_mounted(bank) == 0) {
        shell_puts("no NDF volume in bank 1");
        return;
    }
    count = ndf_entry_count(bank);
    // One bank open for the whole directory name scan (was 16 flips/slot).
    set_bank(bank);
    slot = 0;
    match = 0;
    while (slot < count) {
        name_i = 0;
        match = 1;
        while (name_i < 8) {
            if (name_i < line_len - 1) {
                want = line_buf[name_i + 1];
            } else {
                want = 0;
            }
            if (peek(ndf_window + ndf_entry_base + slot * ndf_entry_size + name_i) != want) {
                match = 0;
            }
            name_i = name_i + 1;
        }
        if (match != 0) {
            break;
        }
        slot = slot + 1;
    }
    set_bank(0);
    if (match == 0) {
        shell_puts("file not found");
        return;
    }
    file_size = ndf_entry_size(bank, slot);
    data_off = ndf_entry_data(bank, slot);
    shell_puts("---");
    // Hold bank for payload stream; shell_putc only touches graphics/cursor.
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
}

'''
kc = kc[:start] + new_type + kc[end:]
k.write_text(kc, encoding="utf-8")
print("type compacted")
