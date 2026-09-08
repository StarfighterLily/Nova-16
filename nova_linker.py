#!/usr/bin/env python3
"""
Nova-16 Linker CLI.

Combines relocatable .nobj objects into a single executable .nex.

Usage:
    py -3.13 nova_linker.py -o out.nex main.nobj lib.nobj [more.nobj ...]
    py -3.13 nova_linker.py -o out.nex --entry START main.nobj lib.nobj
    py -3.13 nova_linker.py -o out.nex --origin 0x2000 main.nobj lib.nobj
"""

import argparse
import sys

from nova.linker import link, LinkError


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Link Nova-16 .nobj objects into a .nex executable")
    ap.add_argument("-o", "--output", required=True,
                    help="output .nex file")
    ap.add_argument("inputs", nargs="+",
                    help="input .nobj (and/or .nex) files")
    ap.add_argument("--entry", default=None,
                    help="entry-point symbol name (default: START/MAIN/ENTRY "
                         "or lowest section)")
    ap.add_argument("--origin", default="0x0400",
                    help="base address for floating sections (hex, "
                         "default 0x0400)")
    args = ap.parse_args()

    try:
        origin = int(args.origin, 0) & 0xFFFF
    except ValueError:
        print(f"Invalid --origin value: {args.origin}", file=sys.stderr)
        return 2

    try:
        doc = link(args.inputs, entry=args.entry, origin=origin)
    except LinkError as e:
        print(f"Link error: {e}", file=sys.stderr)
        return 1

    doc.write(args.output)

    print(f"Wrote {args.output}")
    print(f"  entry point: 0x{doc.entry.addr:04X}")
    print(f"  sections:    {len(doc.sections)}")
    print(f"  symbols:     {len(doc.symbols)}")
    # Count total relocations across all inputs (consumed during linking).
    try:
        import nova.nomf as nomf
        total_relocs = sum(len(nomf.read(p).relocs) for p in args.inputs
                           if nomf.file_kind(p) == nomf.KIND_OBJECT)
    except Exception:
        total_relocs = 0
    print(f"  relocations applied: {total_relocs}")
    print("  layout:")
    # Dedupe: multiple input sections can share a local id; display by
    # (base, size) so each placed region appears once.
    shown = set()
    for me in sorted(doc.map_entries, key=lambda m: m.base):
        key = (me.base, me.size)
        if key in shown:
            continue
        shown.add(key)
        print(f"    0x{me.base:04X}: size {me.size}")
    return 0


if __name__ == "__main__":
    sys.exit(main())