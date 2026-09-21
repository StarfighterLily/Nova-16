from pathlib import Path

p = Path(r"c:\Code\projects\Nova\astrid\NovaDOS\tests\test_kernel_compile.py")
t = p.read_text(encoding="utf-8")

# Diskless HELP string
t = t.replace(
    '_assert_shell_text(gfx, "HELP PEEK CLS BYE", 2, 5)',
    '_assert_shell_text(gfx, "HELP PEEK CLS MEM TIME BYE", 2, 5)',
)

# If any bare string remains for diskless path
t = t.replace('"HELP PEEK CLS BYE"', '"HELP PEEK CLS MEM TIME BYE"')

# Add MEM/TIME tests before the diskless fixture if not present
if "test_shell_mem_command" not in t:
    insert_at = t.find("# Build variants exercise the real CLI")
    assert insert_at > 0
    extra = '''
@pytest.mark.integration
@pytest.mark.graphics
def test_shell_mem_command(kernel_binary):
    """MEM prints free heap bytes and records shell_cmd = 7."""
    proc, mem, gfx, kbd, cycles = boot_with_keys(
        kernel_binary, (ord("M"), ENTER))
    _assert_clean_halt(proc)
    syms = _load_syms(kernel_binary)
    assert mem.read_word(syms["gvar_shell_cmd"]) == 7
    assert mem.read_word(syms["gvar_cmd_count"]) == 1
    _assert_shell_text(gfx, "MEM free=", 2, 5)


@pytest.mark.integration
@pytest.mark.graphics
def test_shell_time_command(kernel_binary):
    """TIME (first-char I) prints system_ticks and records shell_cmd = 8."""
    proc, mem, gfx, kbd, cycles = boot_with_keys(
        kernel_binary, (ord("I"), ENTER))
    _assert_clean_halt(proc)
    syms = _load_syms(kernel_binary)
    assert mem.read_word(syms["gvar_shell_cmd"]) == 8
    assert mem.read_word(syms["gvar_cmd_count"]) == 1
    ticks = mem.read_word(syms["gvar_system_ticks"])
    assert ticks > 0
    _assert_shell_text(gfx, "TIME ", 2, 5)


'''
    t = t[:insert_at] + extra + t[insert_at:]

p.write_text(t, encoding="utf-8")
print("tests updated")
print("MEM TIME help refs", t.count("MEM TIME"))
print("has mem test", "test_shell_mem_command" in t)
