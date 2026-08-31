"""Test configuration for NoBASIC compiler tests."""
import sys
from pathlib import Path

# Ensure the NoBASIC root and compiler package are importable when tests run from repo root
ROOT = Path(__file__).resolve().parent.parent.parent
NOBASIC_DIR = ROOT / "NoBASIC"
COMPILER_DIR = NOBASIC_DIR / "compiler"

for path in (ROOT, NOBASIC_DIR, COMPILER_DIR):
    str_path = str(path)
    if str_path not in sys.path:
        sys.path.insert(0, str_path)

# Disassembly output fixture, not a pytest module
collect_ignore = ["fixtures/test_text_disp_disasm.txt"]
