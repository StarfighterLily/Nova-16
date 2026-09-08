"""
Nova-16 linker.

Combines one or more relocatable ``.nobj`` objects (and optional
pre-built ``.nexe`` inputs) into a single executable ``.nex``.
Resolves GLOBAL/EXTERN symbols, lays out sections (respecting ORG hints
and allocating floating sections), applies relocations, and emits an
executable with a merged symbol table and a link map.
"""

from typing import Dict, List, Optional

from . import nomf


class LinkError(Exception):
    """Raised when objects cannot be linked."""


def _overlaps(start, end, occupied):
    for a, b in occupied:
        if start < b and end > a:
            return True
    return False


def link(inputs: List[str],
         entry: Optional[str] = None,
         origin: int = 0x0400) -> nomf.NomfDocument:
    """Link object files into an executable .nex document.

    ``inputs`` are paths to ``.nobj`` (and/or ``.nex``) files.  ``entry``
    names the entry-point symbol (defaults to ``START``/``MAIN``/``ENTRY``
    or the lowest section base).  ``origin`` is where the first floating
    section is placed; sections with an explicit ORG hint are placed at
    that address.
    """
    docs = []
    for path in inputs:
        try:
            docs.append(nomf.read(path))
        except nomf.NomfError as e:
            raise LinkError(f"Cannot read {path}: {e}") from e

    # Flatten sections: (input_idx, local_sec_id, base_hint, data, kind).
    flat_sections = []
    for inp_idx, doc in enumerate(docs):
        for sec in doc.sections:
            flat_sections.append(
                (inp_idx, sec.id, sec.org_hint, bytearray(sec.data),
                 sec.type))

    # Placement: fixed (explicit ORG) then floating.
    fixed = [s for s in flat_sections if s[2] != 0xFFFF]
    floating = [s for s in flat_sections if s[2] == 0xFFFF]
    occupied: List[tuple] = []
    placement: Dict[tuple, int] = {}
    cursor = origin

    for inp_idx, loc_id, hint, data, kind in fixed:
        base = hint & 0xFFFF
        if _overlaps(base, base + len(data), occupied):
            raise LinkError(
                f"Fixed section at 0x{base:04X} (input {inp_idx}) overlaps "
                f"an already-placed section")
        placement[(inp_idx, loc_id)] = base
        occupied.append((base, base + len(data)))

    for inp_idx, loc_id, hint, data, kind in floating:
        base = cursor
        while _overlaps(base, base + len(data), occupied):
            for a, b in occupied:
                if base < b and base + len(data) > a:
                    base = b
        placement[(inp_idx, loc_id)] = base
        occupied.append((base, base + len(data)))
        cursor = base + len(data)

    section_bases: Dict[tuple, int] = dict(placement)

    # Global symbol definitions: name -> (input_idx, sym_index).
    globals_def: Dict[str, tuple] = {}
    flat_symbol_map: Dict[tuple, int] = {}
    for inp_idx, doc in enumerate(docs):
        for s_i, sym in enumerate(doc.symbols):
            local_base = section_bases.get((inp_idx, sym.section))
            if sym.section == nomf.ABS_SECTION:
                addr = sym.value & 0xFFFF
            elif local_base is None:
                continue
            else:
                addr = (local_base + sym.value) & 0xFFFF
            flat_symbol_map[(inp_idx, s_i)] = addr
            if sym.binding == nomf.BIND_GLOBAL:
                if sym.name in globals_def:
                    prev_inp, _ = globals_def[sym.name]
                    raise LinkError(
                        f"Duplicate GLOBAL '{sym.name}' (inputs {prev_inp} "
                        f"and {inp_idx})")
                globals_def[sym.name] = (inp_idx, s_i)

# Apply relocations.
    for inp_idx, doc in enumerate(docs):
        for rel in doc.relocs:
            if rel.symbol_index >= len(doc.symbols):
                raise LinkError(
                    f"Input {inp_idx}: relocation references symbol index "
                    f"{rel.symbol_index} (out of range)")
            sym = doc.symbols[rel.symbol_index]
            if sym.binding == nomf.BIND_EXTERN:
                if sym.name not in globals_def:
                    raise LinkError(
                        f"Unresolved external '{sym.name}' in input {inp_idx}")
                def_inp, def_idx = globals_def[sym.name]
                target = flat_symbol_map[(def_inp, def_idx)]
            else:
                target = flat_symbol_map.get((inp_idx, rel.symbol_index))
                if target is None:
                    raise LinkError(
                        f"Input {inp_idx}: cannot resolve '{sym.name}'")
            target = (target + rel.addend) & 0xFFFF

            sec_data = None
            for fs in flat_sections:
                if fs[0] == inp_idx and fs[1] == rel.section:
                    sec_data = fs[3]
                    break
            if sec_data is None or rel.offset + rel.width // 8 > len(sec_data):
                raise LinkError(
                    f"Input {inp_idx}: reloc at {rel.offset} out of bounds")
            if rel.width == 16:
                sec_data[rel.offset] = (target >> 8) & 0xFF
                sec_data[rel.offset + 1] = target & 0xFF
            elif rel.width == 8:
                if rel.rtype == nomf.RELOC_HI8:
                    sec_data[rel.offset] = (target >> 8) & 0xFF
                else:
                    sec_data[rel.offset] = target & 0xFF
            else:
                raise LinkError(
                    f"Input {inp_idx}: unsupported reloc width {rel.width}")

    # Check unresolved externals.
    for inp_idx, doc in enumerate(docs):
        for sym in doc.symbols:
            if (sym.binding == nomf.BIND_EXTERN
                    and sym.name not in globals_def):
                raise LinkError(f"Unresolved external '{sym.name}'")

    # Build executable sections sorted by base address.
    exe_sections = []
    for inp_idx, loc_id, hint, data, kind in flat_sections:
        base = placement[(inp_idx, loc_id)]
        exe_sections.append((base, bytes(data), kind))
    exe_sections = sorted(exe_sections, key=lambda s: s[0])

    exe_symbols: Dict[str, int] = {}
    for (inp_idx, s_i), addr in flat_symbol_map.items():
        sym_obj = docs[inp_idx].symbols[s_i]
        # Extern declarations are imports, not definitions: their symbol
        # value is a placeholder (0) and must not leak into the merged
        # executable symbol table (where it could shadow the real
        # definition depending on input order).
        if sym_obj.binding == nomf.BIND_EXTERN:
            continue
        exe_symbols[sym_obj.name] = addr

    # Entry point.
    entry_addr = None
    if entry:
        if entry.upper() in exe_symbols:
            entry_addr = exe_symbols[entry.upper()]
        else:
            raise LinkError(f"Entry symbol '{entry}' not found")
    else:
        for candidate in ("START", "MAIN", "ENTRY"):
            if candidate in exe_symbols:
                entry_addr = exe_symbols[candidate]
                break
    if entry_addr is None and exe_sections:
        entry_addr = min(base for base, data, kind in exe_sections if data)

    segments = [(base, data) for base, data, kind in exe_sections if data]
    section_types = [kind for base, data, kind in exe_sections if data]

    doc = nomf.build_executable(
        "linked", segments, exe_symbols, entry_addr or 0,
        section_types=section_types)
    # build_executable already derives a complete link map from the placed
    # sections (id/base/size).  Do not append a second, input-local copy —
    # duplicate MAP entries with colliding section ids would make the map
    # ambiguous for consumers.

    return doc


def link_to_file(inputs: List[str], output: str, **kwargs) -> None:
    """Link objects and write the executable to ``output``."""
    link(inputs, **kwargs).write(output)