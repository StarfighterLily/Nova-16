"""
Nova-16 relocatable-object assembly.

Produces a ``.nobj`` (NOMF KIND_OBJECT) with section-relative symbols
and relocation records, ready for the linker.  Activated when the source
declares ``GLOBAL`` (exported symbols) or ``EXTERN`` (imported symbols)
directives.
"""

from typing import Dict, List, Set, Tuple

from . import codegen as cg
from . import symbols as sym
from .ir import IRNode, Label, Instruction, Directive, Data
from .. import nomf


class ObjectAsmError(Exception):
    """Raised when a relocatable object cannot be assembled."""


def _collect_decls(nodes: List[IRNode]) -> Tuple[Set[str], Set[str]]:
    """Return (globals, externs) declared in the source."""
    globals_set: Set[str] = set()
    externs_set: Set[str] = set()
    for node in nodes:
        if isinstance(node, Directive) and node.name in ("GLOBAL", "EXTERN"):
            for arg in node.args:
                name = arg.strip().upper()
                if name:
                    (globals_set if node.name == "GLOBAL" else externs_set).add(name)
    return globals_set, externs_set


def _classify_sections(nodes: List[IRNode]) -> List[str]:
    """Return one of 'CODE'/'DATA' per emitted ORG segment (unused hook)."""
    return []


def assemble_object(nodes, module_name, source):
    """Assemble IR nodes into a relocatable .nobj document."""
    globals_set, externs_set = _collect_decls(nodes)
    if not globals_set and not externs_set:
        raise ObjectAsmError(
            "assemble_object called with no GLOBAL/EXTERN declarations")

    # ------------------------------------------------------------------
    # Pass 1: assign sections and compute section-relative symbol values.
    # ------------------------------------------------------------------
    class _Section:
        def __init__(self, sid, org_hint):
            self.id = sid
            self.org_hint = org_hint
            self.is_data_only = False
            self.has_code = False
            self.size = 0

    sections = [_Section(0, 0xFFFF)]
    cur = sections[0]

    class _Sym:
        def __init__(self, name, kind, binding, section, value):
            self.name = name
            self.kind = kind
            self.binding = binding
            self.section = section
            self.value = value

    symbols_list = []
    name_to_index = {}

    def _add_sym(name, kind, binding, section, value):
        name = name.upper()
        name_to_index[name] = len(symbols_list)
        symbols_list.append(_Sym(name, kind, binding, section, value))

    for ext in externs_set:
        _add_sym(ext, nomf.SYM_LABEL, nomf.BIND_EXTERN, nomf.ABS_SECTION, 0)

    size_symbols = sym.SymbolTable()
    for ext in externs_set:
        size_symbols.define(ext, 0)

    location = 0
    seg_start = 0
    pending_equ = None

    def _new_section(addr):
        nonlocal cur, seg_start, location
        cur = _Section(len(sections), addr)
        sections.append(cur)
        seg_start = addr
        location = addr

# Pass 1 walker: sizes and symbols.
    for node in nodes:
        if isinstance(node, Directive):
            if node.name == "ORG":
                _new_section(sym._parse_value(node.args[0], size_symbols)
                             if node.args else 0)
                continue
            if node.name == "EQU" and pending_equ:
                # "NAME EQU value": retro-convert the pending label into an
                # absolute constant (kind SYM_EQU, section-less).  Must run
                # *before* the generic directive skip below, or EQU values
                # are silently lost and the label stays a section-relative
                # LABEL at the wrong offset.
                val = sym._parse_value(node.args[0], size_symbols)
                s = symbols_list[name_to_index[pending_equ.upper()]]
                s.kind = nomf.SYM_EQU
                s.section = nomf.ABS_SECTION
                s.value = val & 0xFFFF
                size_symbols.define(pending_equ, val)
                pending_equ = None
                continue
            if node.name in ("EQU", "GLOBAL", "EXTERN"):
                continue
        if isinstance(node, Label):
            offset = (location - seg_start) & 0xFFFF
            binding = (nomf.BIND_GLOBAL if node.name.upper() in globals_set
                       else nomf.BIND_LOCAL)
            _add_sym(node.name, nomf.SYM_LABEL, binding, cur.id, offset)
            size_symbols.define(node.name, offset)
            pending_equ = node.name
            continue
        if isinstance(node, Data):
            cur.is_data_only = True
            location += cg.data_size(node, size_symbols)
            continue
        if isinstance(node, Instruction):
            cur.has_code = True
            location += 1 + cg.operand_size(node, size_symbols)
            continue

    # Derive per-section sizes from boundary deltas.
    section_sizes = [0] * len(sections)
    idx = 0
    loc = sections[0].org_hint if sections[0].org_hint != 0xFFFF else 0
    for node in nodes:
        if isinstance(node, Directive):
            if node.name == "ORG":
                addr = sym._parse_value(node.args[0], size_symbols) if node.args else 0
                if idx + 1 < len(sections):
                    idx += 1
                loc = addr
                continue
            if node.name in ("EQU", "GLOBAL", "EXTERN"):
                continue
        if isinstance(node, Label):
            continue
        if isinstance(node, Data):
            sz = cg.data_size(node, size_symbols)
            section_sizes[idx] += sz
            loc += sz
            continue
        if isinstance(node, Instruction):
            sz = 1 + cg.operand_size(node, size_symbols)
            section_sizes[idx] += sz
            loc += sz
            continue
    for i, sec in enumerate(sections):
        sec.size = section_sizes[i]

    # ------------------------------------------------------------------
    # Pass 2: emit code into per-section buffers, recording relocations.
    # ------------------------------------------------------------------
    for sec in sections:
        sec.data = bytearray(sec.size)
    relocs = []
    # All *label* symbols (local, global, extern) must be relocatable in
    # object mode because the section base address is unknown until linking.
    # Even a local label referenced via an absolute address (e.g. JNZ label)
    # needs a relocation so the linker can patch it once the section is
    # placed.  EQU constants are absolute values known at assembly time and
    # are excluded — they encode directly, no relocation required.
    _relocatable = {s.name for s in symbols_list
                    if s.kind != nomf.SYM_EQU}

    def _ctx_for(section):
        return cg.ObjectEmitContext(
            section_id=section.id, symbol_index=name_to_index,
            relocatable=_relocatable, relocs=relocs)

    emit_ctx = _ctx_for(sections[0])
    idx = 0
    location = sections[0].org_hint if sections[0].org_hint != 0xFFFF else 0
    seg_start = location
    pending_equ = None

    for node in nodes:
        if isinstance(node, Directive):
            if node.name == "ORG":
                addr = sym._parse_value(node.args[0], size_symbols) if node.args else 0
                if idx + 1 < len(sections):
                    idx += 1
                emit_ctx = _ctx_for(sections[idx])
                location = addr
                seg_start = addr
                continue
            if node.name in ("EQU", "GLOBAL", "EXTERN"):
                continue
        if isinstance(node, Label):
            pending_equ = node.name
            continue
        if isinstance(node, Directive) and node.name == "EQU" and pending_equ:
            pending_equ = None
            continue
        if isinstance(node, Data):
            encoded = cg.generate_data(node, size_symbols, emit_ctx)
            off = (location - seg_start) & 0xFFFF
            sections[idx].data[off:off + len(encoded)] = encoded
            location += len(encoded)
            continue
        if isinstance(node, Instruction):
            encoded = cg.generate_instruction(node, size_symbols, location,
                                              emit_ctx)
            off = (location - seg_start) & 0xFFFF
            sections[idx].data[off:off + len(encoded)] = encoded
            location += len(encoded)
            continue
    pending_equ = None

    for g in globals_set:
        if g not in name_to_index:
            raise ObjectAsmError(f"GLOBAL symbol '{g}' is not defined")
        if symbols_list[name_to_index[g]].kind == nomf.SYM_EQU:
            raise ObjectAsmError(f"GLOBAL '{g}' is an EQU, not a code label")

    nomf_sections = []
    for sec in sections:
        data = bytes(sec.data)
        if not data:
            continue
        kind = (nomf.SECTION_DATA
                if (sec.is_data_only and not sec.has_code) else nomf.SECTION_CODE)
        nomf_sections.append(nomf.Section(
            id=sec.id, type=kind, org_hint=sec.org_hint, data=data))

    nomf_symbols = [
        nomf.Symbol(name=s.name, kind=s.kind, binding=s.binding,
                    section=s.section, value=s.value)
        for s in symbols_list
    ]

    return nomf.build_object(
        module_name, nomf_sections, nomf_symbols, relocs, source=source)