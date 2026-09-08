"""
Unit tests for the Nova Object Module Format (NOMF).

Covers the format library (pack/unpack, integrity, forward
compatibility), the loader integration (NOMF executables load identically
to the legacy .bin + .org pair with an explicit entry point, objects are
rejected), and assembler emission (a .nex sibling is produced by default).
"""

import pytest

import nova.nomf as nomf
from nova.memory import Memory


# -- Format library: round-trip -----------------------------------------

class TestNomfRoundTrip:
    @pytest.mark.unit
    def test_executable_round_trip(self, tmp_path):
        """build_executable -> write -> read preserves everything."""
        doc = nomf.build_executable(
            "prog",
            segments=[(0x1000, b"\x06\x04\x2a"), (0x8000, b"\x01\x02")],
            symbols={"start": 0x1000, "table": 0x8000},
            entry_addr=0x1000,
            entry_symbol="start",
        )
        path = tmp_path / "prog.nex"
        doc.write(str(path))

        loaded = nomf.read(str(path))
        assert loaded.kind == nomf.KIND_EXECUTABLE
        assert loaded.module is not None and loaded.module.name == "prog"
        assert loaded.entry is not None
        assert loaded.entry.addr == 0x1000
        assert loaded.entry.symbol == "start"
        assert loaded.load_segments() == [(0x1000, b"\x06\x04\x2a"),
                                          (0x8000, b"\x01\x02")]
        assert loaded.symbol_table()["start"] == "0x1000"
        assert loaded.symbol_table()["table"] == "0x8000"

    @pytest.mark.unit
    def test_object_round_trip(self, tmp_path):
        """Relocatable objects keep section-relative symbols and relocs."""
        section = nomf.Section(id=0, type=nomf.SECTION_CODE, org_hint=0,
                               data=b"\x11\x22")
        symbols = [
            nomf.Symbol(name="local", kind=nomf.SYM_LABEL,
                        binding=nomf.BIND_LOCAL, section=0, value=0x00),
            nomf.Symbol(name="func", kind=nomf.SYM_FUNC,
                        binding=nomf.BIND_GLOBAL, section=0, value=0x01),
            nomf.Symbol(name="extern_fn", kind=nomf.SYM_LABEL,
                        binding=nomf.BIND_EXTERN, section=nomf.ABS_SECTION,
                        value=0),
        ]
        relocs = [
            nomf.Reloc(section=0, offset=0, width=16,
                       rtype=nomf.RELOC_ABS16, symbol_index=1),
        ]
        doc = nomf.build_object("mod", [section], symbols, relocs)
        path = tmp_path / "mod.nobj"
        doc.write(str(path))

        loaded = nomf.read(str(path))
        assert loaded.kind == nomf.KIND_OBJECT
        assert len(loaded.sections) == 1 and loaded.sections[0].data == b"\x11\x22"
        assert len(loaded.symbols) == 3
        assert loaded.symbols[2].binding == nomf.BIND_EXTERN
        assert len(loaded.relocs) == 1
        assert loaded.relocs[0].rtype == nomf.RELOC_ABS16
        assert loaded.relocs[0].symbol_index == 1

    @pytest.mark.unit
    def test_flat_image_matches_legacy_bin_layout(self):
        """flat_image must equal what the legacy .bin + .org pair describes.

        The legacy .bin starts at the first ORG address (no leading
        padding) and includes zero-fill for interior gaps: the second
        section sits at address 0x8000, so its byte offset equals
        ``0x8000 - 0x1000``.
        """
        doc = nomf.build_executable(
            "p", segments=[(0x1000, b"\xaa\xbb"), (0x8000, b"\xcc")],
            symbols={}, entry_addr=0x1000)
        flat = doc.flat_image()
        assert len(flat) == 2 + (0x8000 - 0x1002) + 1   # == 0x7001
        assert flat[0:2] == b"\xaa\xbb"
        assert flat[0x8000 - 0x1000] == 0xCC

    @pytest.mark.unit
    def test_unknown_chunk_is_skipped_and_preserved(self, tmp_path):
        """Unknown chunk tags are collected and round-tripped."""
        doc = nomf.build_executable("p", [(0x1000, b"\xc3")], {},
                                    entry_addr=0x1000)
        doc.unknown_chunks.append((b"NEW!", b"\xde\xad\xbe\xef"))
        path = tmp_path / "fut.nex"
        doc.write(str(path))

        loaded = nomf.read(str(path))
        assert loaded.unknown_chunks == [(b"NEW!", b"\xde\xad\xbe\xef")]
        assert loaded.entry.addr == 0x1000  # known chunks still parsed
        path2 = tmp_path / "fut2.nex"
        loaded.write(str(path2))
        assert path2.read_bytes() == path.read_bytes()


# -- Format library: integrity / error handling -------------------------

class TestNomfErrors:
    @pytest.mark.unit
    def test_bad_magic_rejected(self, tmp_path):
        path = tmp_path / "junk.bin"
        path.write_bytes(b"NOT NOMF at all" + b"\x00" * 40)
        with pytest.raises(nomf.NomfError):
            nomf.read(str(path))

    @pytest.mark.unit
    def test_crc_mismatch_detected(self, tmp_path):
        doc = nomf.build_executable("p", [(0x1000, b"\x01\x02")], {},
                                    entry_addr=0x1000)
        path = tmp_path / "p.nex"
        doc.write(str(path))
        raw = bytearray(path.read_bytes())
        raw[-1] ^= 0xFF  # corrupt a payload byte without touching the CRC
        path.write_bytes(bytes(raw))
        with pytest.raises(nomf.NomfError):
            nomf.read(str(path))

    @pytest.mark.unit
    def test_truncated_file_rejected(self, tmp_path):
        doc = nomf.build_executable("p", [(0x1000, b"\x01\x02")], {},
                                    entry_addr=0x1000)
        path = tmp_path / "p.nex"
        doc.write(str(path))
        raw = path.read_bytes()
        path.write_bytes(raw[:len(raw) - 5])
        with pytest.raises(nomf.NomfError):
            nomf.read(str(path))

    @pytest.mark.unit
    def test_unsupported_version_rejected(self, tmp_path):
        doc = nomf.build_executable("p", [(0x1000, b"\x01")], {},
                                    entry_addr=0x1000)
        path = tmp_path / "p.nex"
        doc.write(str(path))
        raw = bytearray(path.read_bytes())
        raw[4] = 99  # version byte
        path.write_bytes(bytes(raw))
        with pytest.raises(nomf.NomfError):
            nomf.read(str(path))

    @pytest.mark.unit
    def test_file_kind_detection(self, tmp_path):
        doc = nomf.build_executable("p", [(0x1000, b"\x01")], {},
                                    entry_addr=0x1000)
        obj = nomf.build_object("m", [], [])
        exe_path = tmp_path / "p.nex"
        obj_path = tmp_path / "m.nobj"
        doc.write(str(exe_path))
        obj.write(str(obj_path))
        junk = tmp_path / "junk.bin"
        junk.write_bytes(b"hello world")
        assert nomf.file_kind(str(exe_path)) == nomf.KIND_EXECUTABLE
        assert nomf.file_kind(str(obj_path)) == nomf.KIND_OBJECT
        assert nomf.file_kind(str(junk)) is None
        assert nomf.file_kind(str(tmp_path / "missing.nex")) is None


# -- Loader integration -------------------------------------------------

class TestNomfLoader:
    @pytest.mark.unit
    @pytest.mark.memory
    def test_nex_loads_identically_to_legacy_bin_org(self, memory, tmp_path):
        """A .nex produced by the assembler must reproduce the exact
        memory image of the legacy .bin + .org pair, plus its entry."""
        asm_path = tmp_path / "prog.asm"
        asm_path.write_text(
            "ORG 0x1000\n"
            "start: MOV R0, 42\n"
            "       HLT\n"
            "ORG 0x8000\n"
            "table: DB 0xEE, 0xFF\n",
            encoding="utf-8")

        from nova_assembler import Assembler
        assert Assembler(log=None).assemble(str(asm_path))

        legacy = Memory()
        legacy_entry = legacy.load(str(asm_path.with_suffix(".bin")))
        nex = Memory()
        nex_entry = nex.load(str(asm_path.with_suffix(".nex")))

        assert nex_entry == legacy_entry == 0x1000
        assert nex.memory == legacy.memory
        assert nex.memory[0x8000] == 0xEE and nex.memory[0x8001] == 0xFF

    @pytest.mark.unit
    @pytest.mark.memory
    def test_explicit_entry_overrides_first_segment(self, tmp_path):
        """The ENTR chunk wins over the old 'first segment' convention."""
        doc = nomf.build_executable(
            "p", segments=[(0x1000, b"\x01"), (0x2000, b"\x02")],
            symbols={"code": 0x1000, "main": 0x2000}, entry_addr=0x2000)
        path = tmp_path / "p.nex"
        doc.write(str(path))
        mem = Memory()
        assert mem.load(str(path)) == 0x2000

    @pytest.mark.unit
    @pytest.mark.memory
    def test_object_load_rejected(self, tmp_path):
        """Relocatable objects must not be loadable without linking."""
        doc = nomf.build_object("m", [nomf.Section(id=0, data=b"\x01")], [])
        path = tmp_path / "m.nobj"
        doc.write(str(path))
        mem = Memory()
        with pytest.raises(ValueError, match="nobj"):
            mem.load(str(path))

    @pytest.mark.unit
    @pytest.mark.memory
    def test_corrupted_nex_rejected(self, tmp_path):
        """A corrupted .nex must not silently misload (CRC guard)."""
        doc = nomf.build_executable("p", [(0x1000, b"\x06\x04\x2a")], {},
                                    entry_addr=0x1000)
        path = tmp_path / "p.nex"
        doc.write(str(path))
        raw = bytearray(path.read_bytes())
        raw[-1] ^= 0x01
        path.write_bytes(bytes(raw))
        mem = Memory()
        with pytest.raises(ValueError):
            mem.load(str(path))

    @pytest.mark.unit
    @pytest.mark.memory
    def test_legacy_bin_without_org_still_loads_at_zero(self, memory, tmp_path):
        """Legacy path remains: plain .bin with no .org loads at 0x0000."""
        data = bytes([0x01, 0x02, 0x03])
        path = tmp_path / "raw.bin"
        path.write_bytes(data)
        assert memory.load(str(path)) == 0x0000
        assert bytes(memory.memory[:3]) == data


# -- Assembler emission -------------------------------------------------

class TestNomfAssemblerEmission:
    @pytest.mark.unit
    @pytest.mark.assembler
    def test_asm_produces_nex_by_default(self, tmp_path):
        """The default assembler emits a .nex sibling with the legacy
        .bin/.org/.sym sidecars still written for compatibility."""
        asm_path = tmp_path / "demo.asm"
        asm_path.write_text("ORG 0x2000\nstart: MOV R0, 7\nHLT\n",
                            encoding="utf-8")

        from nova_assembler import Assembler
        assert Assembler(log=None).assemble(str(asm_path))

        assert asm_path.with_suffix(".nex").exists()
        assert asm_path.with_suffix(".bin").exists()
        assert asm_path.with_suffix(".org").exists()
        assert asm_path.with_suffix(".sym").exists()

        doc = nomf.read(str(asm_path.with_suffix(".nex")))
        assert doc.kind == nomf.KIND_EXECUTABLE
        assert doc.entry is not None and doc.entry.addr == 0x2000
        assert doc.symbol_table()["start"] == "0x2000"

    @pytest.mark.unit
    @pytest.mark.assembler
    def test_nex_flat_image_matches_bin(self, tmp_path):
        """flat_image of the emitted .nex equals the emitted .bin exactly."""
        asm_path = tmp_path / "cmp.asm"
        asm_path.write_text("ORG 0x3000\nfoo: MOV R0, 1\nMOV R1, 2\nHLT\n",
                            encoding="utf-8")

        from nova_assembler import Assembler
        assert Assembler(log=None).assemble(str(asm_path))

        bin_bytes = asm_path.with_suffix(".bin").read_bytes()
        doc = nomf.read(str(asm_path.with_suffix(".nex")))
        assert doc.flat_image() == bin_bytes


# -- Format extras ---------------------------------------------------------

class TestNomfFormatExtras:
    """Additional NOMF container coverage: multi-section docs, flags,
    helper APIs, and flat-image gap semantics."""

    @pytest.mark.unit
    def test_multi_section_executable_round_trip(self, tmp_path):
        """Segments, per-section types, hints, map, and entry all survive."""
        doc = nomf.build_executable(
            "multi",
            segments=[(0x0400, b"\x01\x02"), (0x8000, b"\xaa"),
                      (0xF000, b"\xbb\xcc")],
            symbols={"start": 0x0400, "tbl": 0x8000},
            entry_addr=0x0400, entry_symbol="start",
            section_types=[nomf.SECTION_CODE, nomf.SECTION_DATA,
                           nomf.SECTION_SCB])
        path = tmp_path / "multi.nex"
        doc.write(str(path))
        loaded = nomf.read(str(path))
        assert [s.type for s in loaded.sections] == [
            nomf.SECTION_CODE, nomf.SECTION_DATA, nomf.SECTION_SCB]
        assert [s.org_hint for s in loaded.sections] == [
            0x0400, 0x8000, 0xF000]
        assert [bytes(s.data) for s in loaded.sections] == [
            b"\x01\x02", b"\xaa", b"\xbb\xcc"]
        assert loaded.load_segments() == [(0x0400, b"\x01\x02"),
                                          (0x8000, b"\xaa"),
                                          (0xF000, b"\xbb\xcc")]
        assert [(m.section, m.base, m.size) for m in loaded.map_entries] == [
            (0, 0x0400, 2), (1, 0x8000, 1), (2, 0xF000, 2)]

    @pytest.mark.unit
    def test_flags_reflect_content(self):
        """Header flags are derived from document content at serialize time."""
        doc = nomf.build_object(
            "m", [nomf.Section(id=0, data=b"\x01")],
            [nomf.Symbol(name="f", kind=nomf.SYM_LABEL,
                         binding=nomf.BIND_GLOBAL, section=0, value=0)],
            relocs=[nomf.Reloc(section=0, offset=0, width=16,
                               rtype=nomf.RELOC_ABS16, symbol_index=0)])
        blob = doc.serialize()
        flags = int.from_bytes(blob[6:8], "little")
        assert flags & nomf.FLAG_HAS_SYMBOLS
        assert flags & nomf.FLAG_HAS_RELOCS
        assert not flags & nomf.FLAG_HAS_DEBUG

    @pytest.mark.unit
    def test_read_symbols_helper(self, tmp_path):
        """read_symbols returns {name: '0xVVVV'} like a legacy .sym parse."""
        doc = nomf.build_executable("p", [(0x1000, b"\x00")],
                                    {"alpha": 0x1000}, 0x1000)
        path = tmp_path / "p.nex"
        doc.write(str(path))
        assert nomf.read_symbols(str(path)) == {"alpha": "0x1000"}

    @pytest.mark.unit
    def test_file_kind_variants(self, tmp_path):
        """file_kind distinguishes NOMF kinds; None for non-NOMF/missing."""
        nex = tmp_path / "a.nex"
        nomf.build_executable("a", [(0x10, b"\x00")], {},
                              0x10).write(str(nex))
        nobj = tmp_path / "b.nobj"
        nomf.build_object("b", [nomf.Section(id=0, data=b"\x00")],
                          []).write(str(nobj))
        plain = tmp_path / "c.bin"
        plain.write_bytes(b"\x00\x01")
        missing = tmp_path / "missing.nex"
        assert nomf.file_kind(str(nex)) == nomf.KIND_EXECUTABLE
        assert nomf.file_kind(str(nobj)) == nomf.KIND_OBJECT
        assert nomf.file_kind(str(plain)) is None
        assert nomf.file_kind(str(missing)) is None

    @pytest.mark.unit
    def test_flat_image_interior_gap_zero_fill(self):
        """flat_image starts at the lowest base and zero-fills interior gaps."""
        doc = nomf.build_executable(
            "p", segments=[(0x2000, b"\xaa"), (0x2003, b"\xbb")],
            symbols={}, entry_addr=0x2000)
        assert doc.flat_image() == b"\xaa\x00\x00\xbb"

    @pytest.mark.unit
    def test_object_symbols_survive_round_trip_with_sections(self, tmp_path):
        """Section-relative symbol values and section ids round-trip."""
        sections = [
            nomf.Section(id=0, type=nomf.SECTION_CODE, org_hint=0xFFFF,
                         data=b"\xff\xff"),
            nomf.Section(id=1, type=nomf.SECTION_DATA, org_hint=0x3000,
                         data=b"\x01\x02\x03"),
        ]
        symbols = [
            nomf.Symbol(name="code_start", kind=nomf.SYM_LABEL,
                        binding=nomf.BIND_GLOBAL, section=0, value=0),
            nomf.Symbol(name="data_tbl", kind=nomf.SYM_DATA,
                        binding=nomf.BIND_GLOBAL, section=1, value=2),
        ]
        doc = nomf.build_object("m", sections, symbols)
        path = tmp_path / "m.nobj"
        doc.write(str(path))
        loaded = nomf.read(str(path))
        assert loaded.symbols[0].section == 0
        assert loaded.symbols[0].value == 0
        assert loaded.symbols[1].section == 1
        assert loaded.symbols[1].value == 2
        assert loaded.symbols[1].kind == nomf.SYM_DATA
        assert loaded.sections[1].type == nomf.SECTION_DATA
