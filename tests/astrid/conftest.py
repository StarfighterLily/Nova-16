"""Test configuration for Astrid compiler tests."""
import sys
from pathlib import Path

# Ensure the project root and astrid directory are importable
ROOT = Path(__file__).resolve().parent.parent.parent
ASTRID_DIR = ROOT / "astrid"

for path in (ROOT, ASTRID_DIR):
    str_path = str(path)
    if str_path not in sys.path:
        sys.path.insert(0, str_path)
