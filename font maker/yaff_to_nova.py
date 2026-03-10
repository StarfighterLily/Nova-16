#!/usr/bin/env python3
"""Convert YAFF bitmap fonts to Nova-16 flat bytes-list format.

YAFF glyph rows are expected to use '.' for off pixels and any non-dot marker
(typically '@') for on pixels. Output is a Python file containing:

font_data = [
    0x..,0x..,... # code N
]
"""

from __future__ import annotations

import argparse
import pathlib
import re
from typing import Dict, List

GLYPH_HEADER_RE = re.compile(r"^\s*0x([0-9a-fA-F]{1,4})\s*:\s*$")
ON_PIXEL_MARKERS = {"@", "#", "X", "x", "*", "1"}
OFF_PIXEL_MARKERS = {"."}


def row_to_byte(row: str, width: int) -> int:
    """Convert a YAFF row string to one byte using MSB-left ordering.

    YAFF can contain proportional glyph rows whose width differs from 8.
    We normalize by right-padding short rows with '.' and cropping long rows
    on the right so the left edge stays anchored.
    """
    row = row.rstrip("\n")
    row_len = len(row)
    if row_len < width:
        row = row + ("." * (width - row_len))
    elif row_len > width:
        row = row[:width]

    value = 0
    for x, ch in enumerate(row):
        if ch in ON_PIXEL_MARKERS:
            value |= 0x80 >> x
        elif ch in OFF_PIXEL_MARKERS:
            continue
        else:
            raise ValueError(f"Unsupported pixel marker {ch!r} in row {row!r}")
    return value


def parse_yaff(path: pathlib.Path, width: int = 8, height: int = 8) -> Dict[int, List[int]]:
    """Parse a YAFF file into {codepoint: [byte0..byte7]} mapping."""
    glyphs: Dict[int, List[int]] = {}
    lines = path.read_text(encoding="utf-8").splitlines()

    i = 0
    while i < len(lines):
        header_match = GLYPH_HEADER_RE.match(lines[i])
        if not header_match:
            i += 1
            continue

        codepoint = int(header_match.group(1), 16)
        i += 1

        rows: List[str] = []
        while i < len(lines) and len(rows) < height:
            line = lines[i]
            if not line.strip():
                i += 1
                if rows:
                    break
                continue

            # YAFF rows are indented; trim outer spaces only.
            candidate = line.strip()
            if candidate and all(
                (ch in ON_PIXEL_MARKERS or ch in OFF_PIXEL_MARKERS) for ch in candidate
            ):
                rows.append(candidate)
                i += 1
                continue

            # Another header started unexpectedly.
            if GLYPH_HEADER_RE.match(line):
                break

            # Ignore metadata and comments outside glyph pixel rows.
            if line.lstrip().startswith("#") or ":" in line:
                i += 1
                continue

            raise ValueError(
                f"Unexpected line while parsing glyph 0x{codepoint:02X}: {line!r}"
            )

        if len(rows) != height:
            raise ValueError(
                f"Glyph 0x{codepoint:02X} has {len(rows)} rows, expected {height}"
            )

        glyphs[codepoint] = [row_to_byte(row, width) for row in rows]

    if not glyphs:
        raise ValueError("No glyph blocks found in YAFF file")

    return glyphs


def glyph_comment(code: int) -> str:
    """Return readable glyph comments similar to existing Nova font files."""
    if 32 <= code <= 126:
        ch = chr(code)
        if ch == "'":
            return f"\\' ({code})"
        if ch == "\\":
            return f"\\\\ ({code})"
        return f"{ch} ({code})"
    return f"code {code}"


def build_flat_font_data(glyphs: Dict[int, List[int]], start: int, end: int) -> List[int]:
    """Create contiguous flat font bytes list for [start, end] inclusive."""
    flat: List[int] = []
    for code in range(start, end + 1):
        flat.extend(glyphs.get(code, [0] * 8))
    return flat


def write_nova_python(
    output_path: pathlib.Path,
    flat_font_data: List[int],
    start: int,
    end: int,
    variable_name: str,
) -> None:
    """Write Nova-compatible Python bytes list file."""
    with output_path.open("w", encoding="utf-8", newline="\n") as f:
        f.write("# Nova Font Data - Converted from YAFF\n")
        f.write("# 8x8 pixel characters, 8 bytes per character\n")
        f.write(f"# Includes codepoints {start}..{end}\n\n")
        f.write(f"{variable_name} = [\n")

        for idx, code in enumerate(range(start, end + 1)):
            offset = idx * 8
            glyph_bytes = flat_font_data[offset : offset + 8]
            hex_bytes = ",".join(f"0x{b:02X}" for b in glyph_bytes)
            f.write(f"    {hex_bytes}, # {glyph_comment(code)}\n")

        f.write("]\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert YAFF font file to Nova-16 bytes list Python format"
    )
    parser.add_argument("input", type=pathlib.Path, help="Input YAFF file path")
    parser.add_argument(
        "-o",
        "--output",
        type=pathlib.Path,
        default=None,
        help="Output Python file (default: <input_stem>_nova_font.py)",
    )
    parser.add_argument(
        "--start",
        type=int,
        default=0,
        help="Start codepoint to export (inclusive, default: 0)",
    )
    parser.add_argument(
        "--end",
        type=int,
        default=255,
        help="End codepoint to export (inclusive, default: 255)",
    )
    parser.add_argument(
        "--var",
        type=str,
        default="font_data",
        help="Python variable name for exported bytes list (default: font_data)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.start < 0 or args.end > 65535 or args.start > args.end:
        raise SystemExit("Invalid range: expected 0 <= start <= end <= 65535")

    input_path = args.input
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    output_path = args.output or input_path.with_name(f"{input_path.stem}_nova_font.py")

    glyphs = parse_yaff(input_path)
    flat_font_data = build_flat_font_data(glyphs, args.start, args.end)
    write_nova_python(output_path, flat_font_data, args.start, args.end, args.var)

    print(
        f"Converted {len(glyphs)} glyphs from {input_path} to {output_path} "
        f"for range {args.start}..{args.end} ({len(flat_font_data)} bytes)."
    )


if __name__ == "__main__":
    main()
