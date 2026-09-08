"""
Nova Object Module Format (NOMF)
================================

Single-file, versioned, CRC-protected container for Nova-16 binaries.
Replaces the loose ``.bin`` + ``.org`` + ``.sym`` sidecar trio with one
self-describing artifact, and adds the section/symbol/relocation model
needed for object files and linking.

Document kinds
--------------
- ``.nobj`` (KIND_OBJECT)     relocatable object: sections with
                              section-relative addresses, defined/extern
                              symbols, relocation records. Not loadable
                              directly.
- ``.nex``  (KIND_EXECUTABLE) linked executable: absolute load segments,
                              explicit entry point, merged symbol table,
                              optional link map. This is what
                              ``Memory.load()`` accepts.
- ``.nlib`` (KIND_ARCHIVE)    archive of objects (reserved for the
                              linker; not emitted yet).

Layout
------
The file is a 16-byte header followed by TLV chunks::

    Header:
      0x00  4   magic  b"NOMF"
      0x04  1   format version (currently 1)
      0x05  1   kind (0=object, 1=executable, 2=archive)
      0x06  2   flags (bit0 has-symbols, bit1 has-relocs, bit2 has-debug)
      0x08  4   CRC32 (zlib) of every byte after the header
      0x0C  4   chunk count
      0x10  ... chunks

    Chunk = 4-byte ASCII tag + u32 LE payload length + payload

Unknown chunk tags are skipped on read (forward compatibility); writers
may append new chunk types without bumping the format version.

Strings are encoded as ``u16 length + UTF-8 bytes``.  All integers are
little-endian.  16-bit values are used throughout because the Nova-16
address space is a flat 64KB.
"""

import time
import zlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# -- Format constants ----------------------------------------------------

MAGIC = b"NOMF"
FORMAT_VERSION = 1

KIND_OBJECT = 0      # .nobj -- relocatable object
KIND_EXECUTABLE = 1  # .nex  -- linked executable
KIND_ARCHIVE = 2     # .nlib -- archive of objects

FLAG_HAS_SYMBOLS = 0x0001
FLAG_HAS_RELOCS = 0x0002
FLAG_HAS_DEBUG = 0x0004

HEADER_SIZE = 16
_CHUNK_HEADER_SIZE = 8

# Section types
SECTION_CODE = 1
SECTION_DATA = 2
SECTION_BSS = 3      # occupies address space, no bytes in file
SECTION_SCB = 4      # sprite control block region (0xF000-0xF0FF)
SECTION_VEC = 5      # interrupt vectors (0x0100-0x011F)

SECTION_TYPE_NAMES = {
    SECTION_CODE: "CODE",
    SECTION_DATA: "DATA",
    SECTION_BSS: "BSS",
    SECTION_SCB: "SCB",
    SECTION_VEC: "VEC",
}

# Symbol kinds
SYM_LABEL = 1
SYM_EQU = 2
SYM_DATA = 3
SYM_FUNC = 4

# Symbol bindings
BIND_LOCAL = 0
BIND_GLOBAL = 1
BIND_EXTERN = 2

# Relocation types
RELOC_ABS16 = 1  # full 16-bit absolute address
RELOC_HI8 = 2    # high byte (P0: style)
RELOC_LO8 = 3    # low byte (:P0 style)
RELOC_REL16 = 4  # 16-bit PC-relative displacement

# Sentinel section id meaning "value is absolute" (used in merged
# executable symbol tables and for EQU constants that have no section).
ABS_SECTION = 0xFFFF

# Chunk tags (4 bytes each)
TAG_MODULE = b"MODL"
TAG_SECTION = b"SECT"
TAG_SYMBOLS = b"SYMT"
TAG_RELOCS = b"RELC"
TAG_ENTRY = b"ENTR"
TAG_DEBUG = b"DBG "  # space-padded to 4 bytes
TAG_MAP = b"MAP "    # space-padded to 4 bytes

OBJECT_EXT = ".nobj"
EXECUTABLE_EXT = ".nex"
ARCHIVE_EXT = ".nlib"


class NomfError(ValueError):
    """Raised for malformed NOMF documents (bad magic, CRC, truncation).

    Subclasses ``ValueError`` so it matches the error convention used by
    ``Memory.load`` (corrupt legacy ``.org`` sidecars also raise
    ``ValueError``), letting callers handle both uniformly.
    """


# -- Low-level encoding helpers ------------------------------------------

def _pack_str(value: str) -> bytes:
    raw = value.encode("utf-8")
    if len(raw) > 0xFFFF:
        raise NomfError(f"String too long for NOMF: {len(raw)} bytes")
    return len(raw).to_bytes(2, "little") + raw


class _PayloadReader:
    """Sequential little-endian reader over a chunk payload."""

    def __init__(self, payload: bytes):
        self._buf = payload
        self._pos = 0

    def _take(self, n: int) -> bytes:
        if self._pos + n > len(self._buf):
            raise NomfError("Truncated NOMF chunk payload")
        data = self._buf[self._pos:self._pos + n]
        self._pos += n
        return data

    def u8(self) -> int:
        return self._take(1)[0]

    def u16(self) -> int:
        return int.from_bytes(self._take(2), "little")

    def u64(self) -> int:
        return int.from_bytes(self._take(8), "little")

    def i16(self) -> int:
        return int.from_bytes(self._take(2), "little", signed=True)

    def s(self) -> str:
        length = self.u16()
        return self._take(length).decode("utf-8")

    def blob(self) -> bytes:
        return self._take(len(self._buf) - self._pos)


# -- Chunk payload dataclasses -------------------------------------------

@dataclass
class ModuleInfo:
    """MODL -- module identity and provenance."""
    name: str = ""
    source: str = ""
    timestamp: int = 0
    cpu_target: int = 16

    def encode(self) -> bytes:
        return (_pack_str(self.name) + _pack_str(self.source)
                + self.timestamp.to_bytes(8, "little")
                + self.cpu_target.to_bytes(2, "little"))

    @staticmethod
    def decode(payload: bytes) -> "ModuleInfo":
        r = _PayloadReader(payload)
        return ModuleInfo(name=r.s(), source=r.s(), timestamp=r.u64(),
                          cpu_target=r.u16())


@dataclass
class Section:
    """SECT -- one contiguous section of the module.

    For objects, ``data`` holds the emitted bytes and ``org_hint`` is the
    address preference from any ORG directive (0xFFFF = no preference).
    For executables, ``org_hint`` is the resolved load address.
    """
    id: int
    type: int = SECTION_CODE
    alignment: int = 1
    org_hint: int = 0xFFFF
    flags: int = 0
    data: bytes = b""

    def encode(self) -> bytes:
        header = (self.id.to_bytes(2, "little")
                  + self.type.to_bytes(1, "little")
                  + self.alignment.to_bytes(1, "little")
                  + self.org_hint.to_bytes(2, "little")
                  + self.flags.to_bytes(2, "little"))
        return header + self.data

    @staticmethod
    def decode(payload: bytes) -> "Section":
        r = _PayloadReader(payload)
        return Section(id=r.u16(), type=r.u8(), alignment=r.u8(),
                       org_hint=r.u16(), flags=r.u16(), data=r.blob())


@dataclass
class Symbol:
    """SYMT entry.

    ``value`` is section-relative when ``section`` is a real section id,
    or absolute when ``section == ABS_SECTION`` (linked executables and
    EQU constants).
    """
    name: str
    kind: int = SYM_LABEL
    binding: int = BIND_LOCAL
    section: int = ABS_SECTION
    value: int = 0

    def encode(self) -> bytes:
        return (_pack_str(self.name)
                + self.kind.to_bytes(1, "little")
                + self.binding.to_bytes(1, "little")
                + self.section.to_bytes(2, "little")
                + self.value.to_bytes(2, "little"))


@dataclass
class Reloc:
    """RELC entry -- one address constant to patch at link/load time."""
    section: int
    offset: int
    width: int          # 8 or 16
    rtype: int          # RELOC_ABS16 / HI8 / LO8 / REL16
    symbol_index: int
    addend: int = 0

    def encode(self) -> bytes:
        return (self.section.to_bytes(2, "little")
                + self.offset.to_bytes(2, "little")
                + self.width.to_bytes(1, "little")
                + self.rtype.to_bytes(1, "little")
                + self.symbol_index.to_bytes(2, "little")
                + (self.addend & 0xFFFF).to_bytes(2, "little"))


@dataclass
class Entry:
    """ENTR -- explicit program entry point."""
    addr: int = 0
    symbol: str = ""    # non-empty when the entry is expressed symbolically

    @property
    def has_symbol(self) -> bool:
        return bool(self.symbol)

    def encode(self) -> bytes:
        return ((1 if self.symbol else 0).to_bytes(1, "little")
                + self.addr.to_bytes(2, "little")
                + _pack_str(self.symbol))

    @staticmethod
    def decode(payload: bytes) -> "Entry":
        r = _PayloadReader(payload)
        has_symbol = r.u8()
        addr = r.u16()
        return Entry(addr=addr, symbol=r.s() if has_symbol else "")


@dataclass
class MapEntry:
    """MAP entry -- final placement of one section after linking."""
    section: int
    base: int
    size: int

    def encode(self) -> bytes:
        return (self.section.to_bytes(2, "little")
                + self.base.to_bytes(2, "little")
                + self.size.to_bytes(2, "little"))


# -- Document ------------------------------------------------------------

@dataclass
class NomfDocument:
    """In-memory representation of a NOMF file."""
    kind: int = KIND_EXECUTABLE
    version: int = FORMAT_VERSION
    module: Optional[ModuleInfo] = None
    sections: List[Section] = field(default_factory=list)
    symbols: List[Symbol] = field(default_factory=list)
    relocs: List[Reloc] = field(default_factory=list)
    entry: Optional[Entry] = None
    map_entries: List[MapEntry] = field(default_factory=list)
    debug: bytes = b""
    unknown_chunks: List[Tuple[bytes, bytes]] = field(default_factory=list)

    def serialize(self) -> bytes:
        """Serialize to bytes: 16-byte header + TLV chunks."""
        chunks: List[Tuple[bytes, bytes]] = []
        if self.module is not None:
            chunks.append((TAG_MODULE, self.module.encode()))
        for sec in self.sections:
            chunks.append((TAG_SECTION, sec.encode()))
        if self.symbols:
            body = len(self.symbols).to_bytes(2, "little")
            for sym in self.symbols:
                body += sym.encode()
            chunks.append((TAG_SYMBOLS, body))
        if self.relocs:
            body = len(self.relocs).to_bytes(2, "little")
            for rel in self.relocs:
                body += rel.encode()
            chunks.append((TAG_RELOCS, body))
        if self.entry is not None:
            chunks.append((TAG_ENTRY, self.entry.encode()))
        if self.map_entries:
            body = len(self.map_entries).to_bytes(2, "little")
            for me in self.map_entries:
                body += me.encode()
            chunks.append((TAG_MAP, body))
        if self.debug:
            chunks.append((TAG_DEBUG, self.debug))
        chunks.extend(self.unknown_chunks)

        body = b"".join(tag + len(payload).to_bytes(4, "little") + payload
                        for tag, payload in chunks)

        flags = 0
        if self.symbols:
            flags |= FLAG_HAS_SYMBOLS
        if self.relocs:
            flags |= FLAG_HAS_RELOCS
        if self.debug:
            flags |= FLAG_HAS_DEBUG

        header = (MAGIC
                  + self.version.to_bytes(1, "little")
                  + self.kind.to_bytes(1, "little")
                  + flags.to_bytes(2, "little")
                  + (zlib.crc32(body) & 0xFFFFFFFF).to_bytes(4, "little")
                  + len(chunks).to_bytes(4, "little"))
        return header + body

    def write(self, path: str) -> None:
        with open(path, "wb") as f:
            f.write(self.serialize())

    def load_segments(self) -> List[Tuple[int, bytes]]:
        """Return [(load_address, bytes)] for executable placement."""
        return [(sec.org_hint, sec.data) for sec in self.sections]

    def flat_image(self) -> bytes:
        """Reconstruct the legacy .bin layout: segments concatenated in
        load-address order, starting at the lowest section base (no
        leading padding), with zero-fill for interior gaps so that
        byte offsets equal address deltas — byte-for-byte identical to
        what the legacy ``.bin`` + ``.org`` pair describes."""
        if not self.sections:
            return b""
        ordered = sorted(self.sections, key=lambda s: s.org_hint)
        out = bytearray()
        cursor = ordered[0].org_hint
        for sec in ordered:
            if sec.org_hint < cursor:
                raise NomfError(
                    f"Overlapping sections at 0x{sec.org_hint:04X}")
            out.extend(b"\x00" * (sec.org_hint - cursor))
            out.extend(sec.data)
            cursor = sec.org_hint + len(sec.data)
        return bytes(out)

    def symbol_table(self) -> Dict[str, str]:
        """{name: "0xVVVV"} -- same shape as the legacy .sym file."""
        table: Dict[str, str] = {}
        for sym in self.symbols:
            if sym.section != ABS_SECTION:
                base = self._section_base(sym.section)
                if base == 0xFFFF:
                    continue  # unknown section -- skip
                table[sym.name] = f"0x{((base + sym.value) & 0xFFFF):04X}"
            else:
                table[sym.name] = f"0x{sym.value:04X}"
        return table

    def _section_base(self, section_id: int) -> int:
        for sec in self.sections:
            if sec.id == section_id:
                return sec.org_hint
        return 0xFFFF

    def _decode_symbols(self, payload: bytes) -> None:
        r = _PayloadReader(payload)
        count = r.u16()
        for _ in range(count):
            name = r.s()
            kind = r.u8()
            binding = r.u8()
            section = r.u16()
            value = r.u16()
            self.symbols.append(Symbol(name=name, kind=kind,
                                       binding=binding, section=section,
                                       value=value))

    def _decode_relocs(self, payload: bytes) -> None:
        r = _PayloadReader(payload)
        count = r.u16()
        for _ in range(count):
            self.relocs.append(Reloc(
                section=r.u16(), offset=r.u16(), width=r.u8(),
                rtype=r.u8(), symbol_index=r.u16(), addend=r.i16()))

    def _decode_map(self, payload: bytes) -> None:
        r = _PayloadReader(payload)
        count = r.u16()
        for _ in range(count):
            self.map_entries.append(MapEntry(section=r.u16(),
                                             base=r.u16(), size=r.u16()))


# -- Reader --------------------------------------------------------------

def read(path: str) -> NomfDocument:
    """Read and validate a NOMF file.

    Raises NomfError on bad magic, unsupported version/kind, CRC
    mismatch, truncation, or malformed chunks.  Unknown chunk tags are
    collected into ``doc.unknown_chunks`` and skipped (forward
    compatibility).
    """
    with open(path, "rb") as f:
        raw = f.read()

    if len(raw) < HEADER_SIZE:
        raise NomfError(f"{path}: file too small to be NOMF "
                        f"({len(raw)} bytes)")
    if raw[:4] != MAGIC:
        raise NomfError(f"{path}: bad magic {raw[:4]!r} (expected NOMF)")

    version = raw[4]
    kind = raw[5]
    stored_crc = int.from_bytes(raw[8:12], "little")
    chunk_count = int.from_bytes(raw[12:16], "little")

    if version != FORMAT_VERSION:
        raise NomfError(f"{path}: unsupported NOMF version {version} "
                        f"(this build reads version {FORMAT_VERSION})")
    if kind not in (KIND_OBJECT, KIND_EXECUTABLE, KIND_ARCHIVE):
        raise NomfError(f"{path}: unknown NOMF kind {kind}")

    body = raw[HEADER_SIZE:]
    if (zlib.crc32(body) & 0xFFFFFFFF) != stored_crc:
        raise NomfError(f"{path}: CRC32 mismatch -- file is corrupted")

    doc = NomfDocument(kind=kind, version=version)

    pos = 0
    seen = 0
    while pos < len(body):
        if seen >= chunk_count:
            raise NomfError(f"{path}: more chunks than declared chunk "
                            f"count {chunk_count}")
        if pos + _CHUNK_HEADER_SIZE > len(body):
            raise NomfError(f"{path}: truncated chunk header at body "
                            f"offset {pos}")
        tag = body[pos:pos + 4]
        length = int.from_bytes(body[pos + 4:pos + 8], "little")
        pos += _CHUNK_HEADER_SIZE
        if pos + length > len(body):
            raise NomfError(f"{path}: chunk {tag!r} payload overruns file")
        payload = body[pos:pos + length]
        pos += length
        seen += 1

        try:
            if tag == TAG_MODULE:
                doc.module = ModuleInfo.decode(payload)
            elif tag == TAG_SECTION:
                doc.sections.append(Section.decode(payload))
            elif tag == TAG_SYMBOLS:
                doc._decode_symbols(payload)
            elif tag == TAG_RELOCS:
                doc._decode_relocs(payload)
            elif tag == TAG_ENTRY:
                doc.entry = Entry.decode(payload)
            elif tag == TAG_MAP:
                doc._decode_map(payload)
            elif tag == TAG_DEBUG:
                doc.debug = payload
            else:
                # Unknown tag: keep verbatim so re-serialize round-trips.
                doc.unknown_chunks.append((tag, payload))
        except NomfError:
            raise
        except Exception as e:
            raise NomfError(f"{path}: malformed {tag!r} chunk: {e}")

    if seen != chunk_count:
        raise NomfError(f"{path}: expected {chunk_count} chunks, "
                        f"found {seen}")

    return doc


# -- High-level builders -------------------------------------------------

def build_executable(module_name: str,
                     segments: List[Tuple[int, bytes]],
                     symbols: Dict[str, int],
                     entry_addr: int,
                     entry_symbol: str = "",
                     source: str = "",
                     section_types: Optional[List[int]] = None
                     ) -> NomfDocument:
    """Build a .nex document from absolute load segments.

    ``segments`` is [(address, bytes)] in emission order; ``symbols``
    maps names to absolute addresses; ``entry_addr`` is the explicit
    entry point (replaces the old "first ORG segment" convention).
    """
    doc = NomfDocument(kind=KIND_EXECUTABLE)
    doc.module = ModuleInfo(name=module_name, source=source,
                            timestamp=int(time.time()))
    for i, (addr, data) in enumerate(segments):
        sec_type = SECTION_CODE
        if section_types and i < len(section_types):
            sec_type = section_types[i]
        doc.sections.append(Section(id=i, type=sec_type, org_hint=addr,
                                    data=data))
    doc.symbols = [Symbol(name=name, kind=SYM_LABEL, binding=BIND_GLOBAL,
                          section=ABS_SECTION, value=addr & 0xFFFF)
                   for name, addr in symbols.items()]
    doc.entry = Entry(addr=entry_addr & 0xFFFF, symbol=entry_symbol)
    doc.map_entries = [MapEntry(section=sec.id, base=sec.org_hint,
                                size=len(sec.data))
                       for sec in doc.sections]
    return doc


def build_object(module_name: str,
                 sections: List[Section],
                 symbols: List[Symbol],
                 relocs: Optional[List[Reloc]] = None,
                 source: str = "") -> NomfDocument:
    """Build a .nobj document (relocatable object)."""
    doc = NomfDocument(kind=KIND_OBJECT)
    doc.module = ModuleInfo(name=module_name, source=source,
                            timestamp=int(time.time()))
    doc.sections = list(sections)
    doc.symbols = list(symbols)
    doc.relocs = list(relocs or [])
    return doc


def read_symbols(path: str) -> Dict[str, str]:
    """Read {name: "0xVVVV"} from a NOMF file.

    Convenience wrapper used by the debugger/disassembler as a drop-in
    replacement for legacy ``.sym`` parsing.
    """
    return read(path).symbol_table()


def file_kind(path: str) -> Optional[int]:
    """Return the NOMF kind of a file, or None if it is not NOMF.

    Cheaper than a full read(): only the header is inspected.
    """
    try:
        with open(path, "rb") as f:
            head = f.read(6)
    except (FileNotFoundError, IsADirectoryError, PermissionError):
        return None
    if len(head) < 6 or head[:4] != MAGIC:
        return None
    return head[5]



