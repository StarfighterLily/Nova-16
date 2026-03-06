"""Test configuration for NoBASIC compiler tests."""
import sys
from pathlib import Path

# Ensure the NoBASIC root and compiler package are importable when tests run from repo root
ROOT = Path(__file__).resolve().parent.parent
COMPILER_DIR = ROOT / "compiler"

for path in (ROOT, COMPILER_DIR):
    str_path = str(path)
    if str_path not in sys.path:
        sys.path.insert(0, str_path)

collect_ignore = ["test_text_disp_disasm.txt"]
