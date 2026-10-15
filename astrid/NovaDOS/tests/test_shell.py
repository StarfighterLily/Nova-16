"""NovaDOS shell tests: line editor, tokenizer, command table, commands.

Each test boots the default kernel, types a script, and reads the console
back as text (see novados_harness). shell_cmd holds the id of the last
command that ran (shell.ast enum ShellCmd); cmd_count counts entered lines.
"""
import pytest

from novados_harness import build_kernel, boot, BACKSPACE, ESC, ENTER

CMD = {"NONE": 0, "HELP": 1, "CLS": 2, "PEEK": 3, "BYE": 4, "DIR": 5,
       "TYPE": 6, "MEM": 7, "TIME": 8, "POKE": 9, "BANK": 10, "ECHO": 11,
       "PRINT": 12, "LIST": 13, "LET": 14, "LOAD": 15, "RUN": 16,
       "SAVE": 17, "CALL": 18, "NEW": 19, "FORMAT": 20}


@pytest.fixture(scope="module")
def kernel(tmp_path_factory):
    # A larger poll budget so longer scripts finish before the shell stops.
    return build_kernel(tmp_path_factory.mktemp("novados_shell"),
                        defines={"NOVADOS_POLL_LIMIT": 600})


def run_lines(kernel, script):
    run = boot(kernel, script)
    run.assert_clean_halt()
    return run


def output_of(run, command):
    """Console lines printed after `> command`, up to the next prompt."""
    text = run.text
    start = text.index(f"> {command}") + 1
    out = []
    for line in text[start:]:
        if line.startswith(">") or line == "System halted.":
            break
        out.append(line)
    return out


def test_help_lists_every_compiled_command(kernel):
    run = run_lines(kernel, "HELP\nBYE\n")
    assert output_of(run, "HELP") == [
        "HELP CLS PEEK POKE MEM TIME",
        "ECHO PRINT LIST DIR TYPE BANK",
        "FORMAT LOAD SAVE RUN CALL NEW",
        "BYE",
    ]
    assert run.word("cmd_count") == 2


@pytest.mark.parametrize("typed", ["help", "Help", "HELP"])
def test_commands_are_case_insensitive(kernel, typed):
    run = run_lines(kernel, f"{typed}\n")
    assert run.word("shell_cmd") == CMD["HELP"]


def test_unknown_command_reports_and_continues(kernel):
    run = run_lines(kernel, "FROB 1 2\nPEEK\n")
    assert output_of(run, "FROB 1 2") == ["bad command"]
    assert output_of(run, "PEEK") == ["4E 44"]
    assert run.word("cmd_count") == 2


def test_blank_and_space_only_lines(kernel):
    run = run_lines(kernel, "\n   \nPEEK\n")
    assert run.word("cmd_count") == 3
    assert run.word("shell_cmd") == CMD["PEEK"]


def test_extra_spaces_between_words(kernel):
    run = run_lines(kernel, "  ECHO   a    b  \n")
    assert output_of(run, "  ECHO   a    b") == ["a b"]


def test_backspace_edits_the_line(kernel):
    run = run_lines(kernel, [ord("X"), BACKSPACE] + [ord(c) for c in "PEEK"] + [ENTER])
    assert run.word("shell_cmd") == CMD["PEEK"]
    assert "4E 44" in run.text
    assert run.word("line_len") == 0


def test_backspace_on_empty_line_is_harmless(kernel):
    run = run_lines(kernel, [BACKSPACE, BACKSPACE] + [ord(c) for c in "MEM"] + [ENTER])
    assert run.word("shell_cmd") == CMD["MEM"]


def test_line_length_is_capped(kernel):
    # 27 characters fit; the rest of a long line is ignored, not wrapped.
    run = run_lines(kernel, "ECHO " + "x" * 40 + "\n")
    assert output_of(run, "ECHO " + "x" * 22) == ["x" * 22]


def test_bye_and_escape_leave_early(kernel):
    for script in ("BYE\nPEEK\n", [ESC, ord("P"), ENTER]):
        run = run_lines(kernel, script)
        assert run.word("shell_exit") == 1
        assert run.word("bg_runs") < 50          # far below the 600 budget
        assert run.text[-1] == "System halted."


def test_cls_clears_the_console(kernel):
    run = run_lines(kernel, "HELP\nCLS\n")
    assert run.word("shell_cmd") == CMD["CLS"]
    assert run.text == [">", "System halted."]


def test_peek_forms(kernel):
    run = run_lines(kernel, "PEEK\nPEEK 0 4\nPEEK $0001\nPEEK 0x0000 9\nPEEK zz\n")
    assert output_of(run, "PEEK") == ["4E 44"]
    assert output_of(run, "PEEK 0 4") == ["4E 44 01 00"]
    assert output_of(run, "PEEK $0001") == ["44"]
    assert output_of(run, "PEEK 0x0000 9") == ["usage: PEEK [addr] [1-8]"]
    assert output_of(run, "PEEK zz") == ["usage: PEEK [addr] [1-8]"]


def test_poke_writes_bytes(kernel):
    run = run_lines(kernel, "POKE 0x6000 1 0x22 $FF 300\nPEEK 0x6000 4\nPOKE 1\n")
    assert output_of(run, "PEEK 0x6000 4") == ["01 22 FF 2C"]   # 300 & 0xFF
    assert bytes(run.mem._mem[0x6000:0x6004]) == b"\x01\x22\xFF\x2C"
    assert output_of(run, "POKE 1") == ["usage: POKE addr byte..."]


def test_mem_and_time(kernel):
    run = run_lines(kernel, "MEM\nTIME\n")
    assert output_of(run, "MEM") == ["MEM heap=0800 prog=2700"]
    (time_line,) = output_of(run, "TIME")
    assert time_line.startswith("TIME ") and int(time_line[5:], 16) > 0


def test_echo(kernel):
    run = run_lines(kernel, "ECHO Hello, world\nECHO\n")
    assert output_of(run, "ECHO Hello, world") == ["Hello, world"]
    assert output_of(run, "ECHO") == []


def test_variables_print_and_list(kernel):
    run = run_lines(kernel, "A = 5\nb = A + 0x10 - 1\nC = -3\n"
                            "PRINT A + B + C\nPRINT -32768\nLIST\nPRINT A +\nX = Q Q\n")
    assert run.signed("vars") == 5
    assert output_of(run, "PRINT A + B + C") == ["22"]
    assert output_of(run, "PRINT -32768") == ["-32768"]
    assert output_of(run, "LIST") == ["A=5 B=20 C=-3"]
    assert output_of(run, "PRINT A +") == ["usage: PRINT expr"]
    assert output_of(run, "X = Q Q") == ["usage: X = expr"]


def test_dir_lists_the_boot_volume(kernel):
    run = run_lines(kernel, "DIR\n")
    assert output_of(run, "DIR") == [
        "DIR bank 1",
        "BOOT      TXT 5",
        "HI        PRG 36",
        "2 files, 15319 free",
    ]
    assert run.mem.current_bank == 0


@pytest.mark.parametrize("typed", ["TYPE BOOT", "type boot"])
def test_type_shows_a_file(kernel, typed):
    run = run_lines(kernel, typed + "\n")
    assert output_of(run, typed) == ["HELLO"]
    assert run.word("shell_cmd") == CMD["TYPE"]


@pytest.mark.parametrize("name", ["MISSING", "BOO", "BOOTX", "ABCDEFGHIJ"])
def test_type_missing_file(kernel, name):
    run = run_lines(kernel, f"TYPE {name}\n")
    assert output_of(run, f"TYPE {name}") == ["file not found"]


def test_type_without_name(kernel):
    run = run_lines(kernel, "TYPE\n")
    assert output_of(run, "TYPE") == ["usage: TYPE name"]


def test_bank_select_format_and_errors(kernel):
    run = run_lines(kernel, "BANK\nBANK 2\nDIR\nFORMAT\nDIR\nBANK 0\nBANK 16\nBANK zz\n")
    assert output_of(run, "BANK") == ["BANK 1"]
    assert output_of(run, "BANK 2") == ["BANK 2 (no volume)"]
    dirs = [i for i, line in enumerate(run.text) if line == "> DIR"]
    assert run.text[dirs[0] + 1] == "no volume in bank 2"
    assert output_of(run, "FORMAT") == ["formatted bank 2"]
    assert run.text[dirs[1] + 1:dirs[1] + 3] == ["DIR bank 2", "0 files, 15360 free"]
    assert output_of(run, "BANK 0") == ["usage: BANK [1-15]"]
    assert output_of(run, "BANK 16") == ["usage: BANK [1-15]"]
    assert output_of(run, "BANK zz") == ["usage: BANK [1-15]"]
    assert run.word("cur_bank") == 2
    assert bytes(run.mem._bank_pages[2][:4]) == b"NDF1"
    assert bytes(run.mem._bank_pages[1][:4]) == b"NDF1"   # boot volume untouched


def test_console_scrolls_by_clearing(kernel):
    # 29 scrolling rows (3-31); 20 two-line commands overflow them once.
    run = run_lines(kernel, "PEEK\n" * 20)
    assert run.word("cmd_count") == 20
    assert run.text[0] != "NovaDOS v0.2"          # banner scrolled away
    assert run.text[-1] == "System halted."
