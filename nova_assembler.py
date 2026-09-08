#!/usr/bin/env python3
"""
Nova-16 Assembler — public entry point.

This module is a thin wrapper around the new token-based assembler package
(``nova.assembler``) that preserves the historical ``nova_assembler.py`` API
so existing callers, tests, and CLI invocations continue to work unchanged.

Backward-compatible exports:
    - ``Assembler``        : the new assembler class (with ``instruction_set``
                             property for legacy callers)
    - ``InstructionSet``   : old instruction-set metadata (from the legacy
                             assembler module)
    - ``OperandClassifier``: old operand classifier
    - ``OperandType``      : old operand type constants

The ``main()`` function routes sources that declare ``GLOBAL``/``EXTERN``
directives to the new assembler (which emits ``.nobj`` via the NOMF library)
and everything else to the legacy 2-pass assembler (which emits ``.bin`` +
``.org`` + ``.sym`` sidecars).
"""

import re
import sys
from typing import Callable, Optional

# ---------------------------------------------------------------------------
# New assembler (nova.assembler package)
# ---------------------------------------------------------------------------
from nova.assembler import Assembler as _NewAssembler

# ---------------------------------------------------------------------------
# Legacy assembler (nova_assembler1.py) — re-exported for backward compat
# ---------------------------------------------------------------------------
from nova_assembler1 import (
    InstructionSet,
    OperandClassifier,
    OperandType,
)


class Assembler(_NewAssembler):
    """New assembler with a backward-compatible ``instruction_set`` property.

    Legacy callers (and some tests) access ``assembler.instruction_set`` to
    obtain the instruction/register metadata object.  The new assembler's
    implementation is structurally different, so we expose a lazily-constructed
    legacy ``InstructionSet`` instance via this subclass.
    """

    def __init__(self, log: Optional[Callable[[str], None]] = print,
                 trace: bool = False,
                 emit_nomf: bool = True,
                 emit_legacy: bool = True):
        super().__init__(log=log, trace=trace,
                         emit_nomf=emit_nomf, emit_legacy=emit_legacy)
        self._instruction_set: Optional[InstructionSet] = None

    @property
    def instruction_set(self) -> InstructionSet:
        """Lazily construct and return a legacy ``InstructionSet``."""
        if self._instruction_set is None:
            self._instruction_set = InstructionSet()
        return self._instruction_set


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main() -> int:
    """Main entry point.

    Sources declaring ``GLOBAL``/``EXTERN`` directives are assembled as
    relocatable objects (``.nobj``) by the new assembler; everything else
    uses the legacy 2-pass assembler to produce ``.bin`` + ``.org`` + ``.sym``
    (plus NOMF siblings).
    """
    if len(sys.argv) != 2:
        print("Usage: python nova_assembler.py <file.asm>")
        return 1

    filename = sys.argv[1]

    # Detect GLOBAL/EXTERN directives to decide which assembler to use.
    try:
        with open(filename, "r", encoding="utf-8") as _f:
            declares_symbols = any(
                re.match(r"^\s*(GLOBAL|EXTERN)\s", line, re.IGNORECASE)
                for line in _f)
    except OSError as e:
        print(f"Cannot read {filename}: {e}")
        return 1

    if declares_symbols:
        # Relocatable-object path: delegate to the new assembler.
        return 0 if _NewAssembler(log=print).assemble(filename) else 1

    # Legacy executable path: use the old 2-pass assembler with tracing.
    from nova_assembler1 import Assembler as _LegacyAssembler
    assembler = _LegacyAssembler(log=print, trace=True)
    return 0 if assembler.assemble(filename) else 1


if __name__ == '__main__':
    sys.exit(main())
