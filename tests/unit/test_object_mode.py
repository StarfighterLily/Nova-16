"""
Unit tests for relocatable-object assembly (.nobj) and the linker.

Covers object-mode emission (GLOBAL/EXTERN, section-relative symbols,
relocations for backward and forward references), the linker (symbol
resolution, section placement, relocation application, error detection),
and end-to-end linked-program execution.
"""

import pytest

from nova.assembler import Assembler
import nova.nomf as nomf
from nova.linker import link, LinkError
from nova.memory import Memory


def _asm(tmp_path, text, name="prog"):
    path = tmp_path / f"{name}.asm"
    path.write_text(text, encoding="utf-8")
    asm = Assembler(log=None)
    assert asm.assemble(str(path)), f"assembly failed for {name}"
    return str(path)


class TestObjectMode:
    @pytest.mark.unit
    @pytest.mark.assembler
    def test_object_emits_nobj(self, tmp_path):
        """A GLOBAL/EXTERN source produces a .nobj, not .bin/.org/.sym."""
        path = _asm(tmp_path, "GLOBAL f\nf: MOV R0, 1\nHLT\n")
        assert (tmp_path / "prog.nobj").exists()
        assert not (tmp_path / "prog.bin").exists()

    @pytest.mark.unit
    @pytest.mark.assembler
    def test_object_symbols_and_relocs(self, tmp_path):
        """GLOBAL/EXTERN produce relocations."""
        path = _asm(tmp_path,
                    "GLOBAL myfunc\nEXTERN ext\n"
                    "myfunc: MOV P0, ext\nJNZ myfunc\nHLT\n")
        doc = nomf.read(str(path).replace(".asm", ".nobj"))
        assert doc.kind == nomf.KIND_OBJECT
        names = {s.name: s for s in doc.symbols}
        assert names["MYFUNC"].binding == nomf.BIND_GLOBAL
        assert names["EXT"].binding == nomf.BIND_EXTERN
        assert len(doc.relocs) == 2
        assert all(r.rtype == nomf.RELOC_ABS16 for r in doc.relocs)

    @pytest.mark.unit
    @pytest.mark.assembler
    def test_forward_reference_gets_reloc(self, tmp_path):
        path = _asm(tmp_path,
                    "GLOBAL myfunc\nJNZ myfunc\nNOP\nmyfunc: HLT\n")
        doc = nomf.read(str(path).replace(".asm", ".nobj"))
        assert any(r.rtype == nomf.RELOC_ABS16 for r in doc.relocs)

    @pytest.mark.unit
    @pytest.mark.assembler
    def test_local_label_no_reloc(self, tmp_path):
        path = _asm(tmp_path,
                    "GLOBAL START\nSTART: NOP\nJNZ local\nHLT\nlocal: NOP\n",
                    name="localref")
        doc = nomf.read(str(path).replace(".asm", ".nobj"))
        assert len(doc.relocs) == 1

    @pytest.mark.unit
    @pytest.mark.assembler
    def test_undefined_global_rejected(self, tmp_path):
        path = tmp_path / "bad.asm"
        path.write_text("GLOBAL missing\nNOP\nHLT\n", encoding="utf-8")
        assert not Assembler(log=None).assemble(str(path))


class TestLinker:
    @pytest.mark.unit
    def test_link_two_objects(self, tmp_path):
        lib = _asm(tmp_path, "GLOBAL addab\naddab: ADD R0, R1\nHLT\n",
                   name="lib")
        main = _asm(tmp_path,
                    "EXTERN addab\nGLOBAL START\n"
                    "START: MOV R0, 3\nMOV R1, 4\nMOV P0, addab\nJNZ P0\nHLT\n",
                    name="main")
        doc = link([main.replace(".asm", ".nobj"), lib.replace(".asm", ".nobj")])
        assert doc.kind == nomf.KIND_EXECUTABLE
        syms = doc.symbol_table()
        assert "ADDAB" in syms and "START" in syms
        addab_addr = int(syms["ADDAB"], 16)
        placed = False
        for s in doc.sections:
            for i in range(len(s.data) - 4):
                if s.data[i] == 0x06 and s.data[i + 1] == 0x08 \
                        and s.data[i + 2] == 0xF1:
                    imm = (s.data[i + 3] << 8) | s.data[i + 4]
                    if imm == addab_addr:
                        placed = True
        assert placed, "MOV P0, addab not relocated to ADDAB's address"

    @pytest.mark.unit
    def test_unresolved_external_errors(self, tmp_path):
        main = _asm(tmp_path, "EXTERN ghost\nMOV P0, ghost\nHLT\n",
                    name="undef")
        with pytest.raises(LinkError):
            link([main.replace(".asm", ".nobj")])

    @pytest.mark.unit
    def test_fixed_section_placement(self, tmp_path):
        lib = _asm(tmp_path, "GLOBAL f\nORG 0x3000\nf: HLT\n", name="fix")
        doc = link([lib.replace(".asm", ".nobj")])
        assert doc.symbol_table()["F"] == "0x3000"

    @pytest.mark.unit
    def test_link_produces_loadable_executable(self, tmp_path):
        lib = _asm(tmp_path, "GLOBAL addab\naddab: ADD R0, R1\nHLT\n",
                   name="lib2")
        main = _asm(tmp_path,
                    "EXTERN addab\nGLOBAL START\n"
                    "START: MOV R0, 3\nMOV R1, 4\nMOV P0, addab\nJNZ P0\nHLT\n",
                    name="main2")
        doc = link([main.replace(".asm", ".nobj"), lib.replace(".asm", ".nobj")])
        out = tmp_path / "linked.nex"
        doc.write(str(out))
        entry = memload(str(out))
        assert entry == doc.entry.addr


def memload(path):
    return Memory().load(path)


class TestLinkedExecution:
    @pytest.mark.integration
    def test_linked_program_runs(self, tmp_path):
        lib = _asm(tmp_path, "GLOBAL addab\naddab: ADD R0, R1\nMOV P2, R0\nHLT\n",
                   name="execlib")
        main = _asm(tmp_path,
                    "EXTERN addab\nGLOBAL START\n"
                    "START: MOV R0, 10\nMOV R1, 32\nMOV P0, addab\nJNZ P0\nHLT\n",
                    name="execmain")
        doc = link([main.replace(".asm", ".nobj"), lib.replace(".asm", ".nobj")])
        out = tmp_path / "run.nex"
        doc.write(str(out))
        mem = Memory()
        entry = mem.load(str(out))
        from nova_cpu import CPU
        from nova_keyboard import NovaKeyboard
        from nova_sound import NovaSound
        import nova_gfx as gfx
        from nova.bus.eventbus import EventBus
        bus = EventBus()
        cpu = CPU(mem, gfx.GFX(), NovaKeyboard(bus=bus), NovaSound(), bus=bus)
        cpu.pc = entry
        for _ in range(10000):
            if cpu.halted:
                break
            cpu.step()
        assert cpu.halted
        assert int(cpu.Rregisters[0]) == 42  # 10 + 32


# -- Relocation kinds -------------------------------------------------------

class TestObjectModeRelocations:
    """Relocation-kind coverage: backward refs, byte relocations, EQU
    constants, multi-section objects, and error paths."""

    @pytest.mark.unit
    @pytest.mark.assembler
    def test_backward_local_reference_gets_reloc(self, tmp_path):
        """A backward reference to a local label also gets a relocation."""
        path = _asm(tmp_path,
                    "GLOBAL START\n"
                    "START: NOP\n"
                    "back: NOP\n"
                    "JNZ back\n"
                    "HLT\n",
                    name="backref")
        doc = nomf.read(str(path).replace(".asm", ".nobj"))
        names = {s.name: s for s in doc.symbols}
        assert names["BACK"].binding == nomf.BIND_LOCAL
        assert len(doc.relocs) == 1
        assert doc.relocs[0].rtype == nomf.RELOC_ABS16
        # The relocation points at the BACK symbol-table entry.
        assert doc.symbols[doc.relocs[0].symbol_index].name == "BACK"

    @pytest.mark.unit
    @pytest.mark.assembler
    def test_lo8_reloc_form_in_instruction(self, tmp_path):
        """':sym' operand form emits a low-byte (LO8) relocation."""
        path = _asm(tmp_path,
                    "GLOBAL START\nEXTERN target\n"
                    "START: MOV R1, :target\n"
                    "HLT\n",
                    name="loform")
        doc = nomf.read(str(path).replace(".asm", ".nobj"))
        assert len(doc.relocs) == 1
        assert doc.relocs[0].rtype == nomf.RELOC_LO8
        assert doc.relocs[0].width == 8

    @pytest.mark.unit
    @pytest.mark.assembler
    def test_data_directive_relocs(self, tmp_path):
        """DW emits ABS16 for bare symbols; DB ':sym' emits LO8."""
        path = _asm(tmp_path,
                    "GLOBAL START\nEXTERN ext\n"
                    "START: DW ext\n"
                    "DB :ext\n",
                    name="datarel")
        doc = nomf.read(str(path).replace(".asm", ".nobj"))
        kinds = sorted(r.rtype for r in doc.relocs)
        assert kinds == [nomf.RELOC_ABS16, nomf.RELOC_LO8]

    @pytest.mark.unit
    @pytest.mark.assembler
    def test_db_full_symbol_rejected(self, tmp_path):
        """A full 16-bit symbol cannot be a DB value without byte selection."""
        path = tmp_path / "bad_db.asm"
        path.write_text("EXTERN ext\nDB ext\n", encoding="utf-8")
        assert not Assembler(log=None).assemble(str(path))

    @pytest.mark.unit
    @pytest.mark.assembler
    def test_equ_constant_encoded_directly(self, tmp_path):
        """EQU constants become absolute SYM_EQU symbols: encoded inline,
        no relocation, and carried through the merged symbol table."""
        path = _asm(tmp_path,
                    "GLOBAL START\n"
                    "MYCONST EQU 0x1234\n"
                    "START: MOV P0, MYCONST\n"
                    "HLT\n",
                    name="equconst")
        doc = nomf.read(str(path).replace(".asm", ".nobj"))
        assert doc.relocs == []
        sym = {s.name: s for s in doc.symbols}["MYCONST"]
        assert sym.kind == nomf.SYM_EQU
        assert sym.section == nomf.ABS_SECTION
        assert sym.value == 0x1234
        # MOV P0, imm16: opcode(06) mode(08) P0-code(F1) imm16(12 34), HLT.
        assert bytes(doc.sections[0].data)[:5] == b"\x06\x08\xF1\x12\x34"

    @pytest.mark.unit
    @pytest.mark.assembler
    def test_equ_lowercase_label(self, tmp_path):
        """EQU works for lowercase labels (symbol table is case-insensitive)."""
        path = _asm(tmp_path,
                    "GLOBAL START\n"
                    "myconst EQU 0x56\n"
                    "START: MOV R0, myconst\n"
                    "HLT\n",
                    name="eqlower")
        doc = nomf.read(str(path).replace(".asm", ".nobj"))
        assert doc.relocs == []
        sym = {s.name: s for s in doc.symbols}["MYCONST"]
        assert sym.kind == nomf.SYM_EQU and sym.value == 0x56

    @pytest.mark.unit
    @pytest.mark.assembler
    def test_global_on_equ_rejected(self, tmp_path):
        """Declaring an EQU constant GLOBAL is a hard assembly error."""
        path = tmp_path / "gloequ.asm"
        path.write_text("GLOBAL MYCONST\nMYCONST EQU 5\nNOP\n",
                        encoding="utf-8")
        assert not Assembler(log=None).assemble(str(path))

    @pytest.mark.unit
    @pytest.mark.assembler
    def test_multi_org_object_sections(self, tmp_path):
        """Multiple ORG regions produce separate sections with hints and
        per-section DATA/CODE typing and correct symbol section ids."""
        path = _asm(tmp_path,
                    "GLOBAL START\n"
                    "START: NOP\n"
                    "ORG 0x3000\n"
                    "GLOBAL DSYM\n"
                    "DSYM: DB 1, 2, 3\n",
                    name="multiorg")
        doc = nomf.read(str(path).replace(".asm", ".nobj"))
        assert len(doc.sections) == 2
        sec0, sec1 = doc.sections
        assert sec0.org_hint == 0xFFFF        # floating (no ORG yet)
        assert sec0.type == nomf.SECTION_CODE
        assert sec1.org_hint == 0x3000        # fixed by ORG
        assert sec1.type == nomf.SECTION_DATA
        assert bytes(sec1.data) == b"\x01\x02\x03"
        syms = {s.name: s for s in doc.symbols}
        assert syms["START"].section == sec0.id
        assert syms["DSYM"].section == sec1.id
        assert syms["DSYM"].value == 0        # section-relative

    @pytest.mark.unit
    @pytest.mark.assembler
    def test_undefined_symbol_reference_fails(self, tmp_path):
        """Referencing an undeclared, undefined symbol fails assembly."""
        path = tmp_path / "undefref.asm"
        path.write_text("GLOBAL START\nSTART: JNZ nowhere\nHLT\n",
                        encoding="utf-8")
        assert not Assembler(log=None).assemble(str(path))



# -- Linker behaviour --------------------------------------------------------

class TestLinkerExtended:
    """Extended linker coverage: multi-object links, placement control,
    byte relocations, and merged-symbol-table hygiene."""

    @pytest.mark.unit
    def test_link_three_objects_chain(self, tmp_path):
        """Three-object extern chain resolves every import."""
        leaf = _asm(tmp_path, "GLOBAL LEAFFN\nLEAFFN: ADD R0, R1\nHLT\n",
                    name="leaf3")
        mid = _asm(tmp_path,
                   "EXTERN LEAFFN\nGLOBAL MIDFN\n"
                   "MIDFN: MOV R1, 32\nMOV P0, LEAFFN\nJNZ P0\nHLT\n",
                   name="mid3")
        main = _asm(tmp_path,
                    "EXTERN MIDFN\nGLOBAL START\n"
                    "START: MOV R0, 10\nMOV P0, MIDFN\nJNZ P0\nHLT\n",
                    name="main3")
        doc = link([main.replace(".asm", ".nobj"),
                    mid.replace(".asm", ".nobj"),
                    leaf.replace(".asm", ".nobj")])
        syms = doc.symbol_table()
        assert {"START", "MIDFN", "LEAFFN"} <= set(syms)
        addrs = {name: int(syms[name], 16) for name in syms}
        # All three definitions live at distinct, non-zero addresses.
        assert len({addrs["START"], addrs["MIDFN"], addrs["LEAFFN"]}) == 3
        assert all(a != 0 for a in addrs.values())
        assert doc.entry.addr == addrs["START"]

    @pytest.mark.unit
    def test_duplicate_global_rejected(self, tmp_path):
        """Two objects exporting the same GLOBAL name is a link error."""
        a = _asm(tmp_path, "GLOBAL DUP\nDUP: NOP\nHLT\n", name="dup_a")
        b = _asm(tmp_path, "GLOBAL DUP\nDUP: NOP\nHLT\n", name="dup_b")
        with pytest.raises(LinkError, match="Duplicate"):
            link([a.replace(".asm", ".nobj"), b.replace(".asm", ".nobj")])

    @pytest.mark.unit
    def test_explicit_entry_symbol(self, tmp_path):
        """--entry overrides the START/MAIN/ENTRY candidate scan."""
        lib = _asm(tmp_path, "GLOBAL ADDAB\nADDAB: ADD R0, R1\nHLT\n",
                   name="entrylib")
        main = _asm(tmp_path,
                    "EXTERN ADDAB\nGLOBAL START\n"
                    "START: MOV P0, ADDAB\nJNZ P0\nHLT\n",
                    name="entrymain")
        doc = link([main.replace(".asm", ".nobj"),
                    lib.replace(".asm", ".nobj")], entry="ADDAB")
        assert doc.entry.addr == int(doc.symbol_table()["ADDAB"], 16)

    @pytest.mark.unit
    def test_local_symbol_reloc_resolved_by_linker(self, tmp_path):
        """A local-label jump is patched with section base + offset."""
        obj = _asm(tmp_path,
                   "GLOBAL START\n"
                   "START: JNZ local_fn\n"
                   "HLT\n"
                   "local_fn: NOP\n"
                   "HLT\n",
                   name="localres")
        doc = link([obj.replace(".asm", ".nobj")])
        # Entry START is at the floating origin (0x0400); local_fn sits at
        # +5 (JNZ=4 bytes, HLT=1).  The JNZ imm16 field lives at offset 2.
        assert doc.entry.addr == 0x0400
        data = doc.sections[0].data
        assert bytes(data[2:4]) == b"\x04\x05"

    @pytest.mark.unit
    def test_hi8_lo8_relocs_patched_by_linker(self, tmp_path):
        """RELOC_HI8 patches the high byte, RELOC_LO8 the low byte."""
        lib = _asm(tmp_path, "GLOBAL TARGET\nORG 0x1234\nTARGET: HLT\n",
                   name="hilolib")
        # The trailing-colon 'sym:' HI8 source form is not yet expressible
        # through the parser, so build the consumer object directly to
        # exercise the linker's byte-relocation paths.
        sec = nomf.Section(id=0, type=nomf.SECTION_CODE, org_hint=0xFFFF,
                           data=b"\x00\x00")
        syms = [
            nomf.Symbol(name="START", kind=nomf.SYM_LABEL,
                        binding=nomf.BIND_GLOBAL, section=0, value=0),
            nomf.Symbol(name="TARGET", kind=nomf.SYM_LABEL,
                        binding=nomf.BIND_EXTERN, section=nomf.ABS_SECTION,
                        value=0),
        ]
        relocs = [
            nomf.Reloc(section=0, offset=0, width=8, rtype=nomf.RELOC_HI8,
                       symbol_index=1),
            nomf.Reloc(section=0, offset=1, width=8, rtype=nomf.RELOC_LO8,
                       symbol_index=1),
        ]
        consumer = str(tmp_path / "consumer.nobj")
        nomf.build_object("consumer", [sec], syms, relocs).write(consumer)
        doc = link([consumer, lib.replace(".asm", ".nobj")])
        # Sections are sorted by base: the consumer (floating, 0x0400)
        # comes before the lib (fixed at 0x1234).
        data = doc.sections[0].data
        assert data[0] == 0x12   # high byte of 0x1234
        assert data[1] == 0x34   # low byte of 0x1234

    @pytest.mark.unit
    def test_origin_parameter_controls_floating_base(self, tmp_path):
        """The first floating section lands at the requested origin."""
        obj = _asm(tmp_path, "GLOBAL START\nSTART: NOP\nHLT\n",
                   name="orig")
        doc = link([obj.replace(".asm", ".nobj")], origin=0x2000)
        assert doc.entry.addr == 0x2000

    @pytest.mark.unit
    def test_mixed_fixed_and_floating_placement(self, tmp_path):
        """Fixed (ORG) and floating sections coexist without overlap."""
        lib = _asm(tmp_path, "GLOBAL FN\nORG 0x3000\nFN: HLT\n",
                   name="mixlib")
        main = _asm(tmp_path,
                    "EXTERN FN\nGLOBAL START\n"
                    "START: MOV P0, FN\nJNZ P0\nHLT\n",
                    name="mixmain")
        doc = link([main.replace(".asm", ".nobj"),
                    lib.replace(".asm", ".nobj")])
        syms = doc.symbol_table()
        assert syms["FN"] == "0x3000"            # fixed placement honoured
        assert int(syms["START"], 16) == 0x0400  # floating at origin
        bases = sorted(m.base for m in doc.map_entries)
        assert bases == [0x0400, 0x3000]
        # MOV P0, FN immediate patched to 0x3000 (field at section offset 3).
        main_data = doc.sections[0].data
        assert bytes(main_data[3:5]) == b"\x30\x00"

    @pytest.mark.unit
    def test_extern_never_shadows_definition(self, tmp_path):
        """Import (EXTERN) placeholder values must not overwrite real
        definitions in the merged symbol table, regardless of input order."""
        # Fixed ORG makes HELPER's address independent of placement order.
        lib = _asm(tmp_path, "GLOBAL HELPER\nORG 0x5000\nHELPER: NOP\nHLT\n",
                   name="shadlib")
        main = _asm(tmp_path,
                    "EXTERN HELPER\nGLOBAL START\n"
                    "START: NOP\nJNZ HELPER\nHLT\n",
                    name="shadmain")
        lib_obj = lib.replace(".asm", ".nobj")
        main_obj = main.replace(".asm", ".nobj")
        for order in ([lib_obj, main_obj], [main_obj, lib_obj]):
            doc = link(order)
            assert doc.symbol_table()["HELPER"] == "0x5000"

    @pytest.mark.unit
    def test_link_to_file_helper(self, tmp_path):
        """link_to_file writes a loadable executable and returns nothing."""
        from nova.linker import link_to_file
        lib = _asm(tmp_path, "GLOBAL ADDAB\nADDAB: ADD R0, R1\nHLT\n",
                   name="f2flib")
        main = _asm(tmp_path,
                    "EXTERN ADDAB\nGLOBAL START\n"
                    "START: MOV R0, 1\nMOV R1, 2\n"
                    "MOV P0, ADDAB\nJNZ P0\nHLT\n",
                    name="f2fmain")
        out = str(tmp_path / "f2f.nex")
        link_to_file([main.replace(".asm", ".nobj"),
                      lib.replace(".asm", ".nobj")], out)
        entry = Memory().load(out)
        doc = nomf.read(out)
        assert entry == doc.entry.addr


    @pytest.mark.unit
    def test_unknown_entry_symbol_rejected(self, tmp_path):
        """A missing entry symbol is a link error, not a silent fallback."""
        obj = _asm(tmp_path, "GLOBAL START\nSTART: NOP\nHLT\n",
                   name="entrymiss")
        with pytest.raises(LinkError, match="Entry symbol"):
            link([obj.replace(".asm", ".nobj")], entry="NOPE")



# -- Linked execution ---------------------------------------------------------

class TestLinkedExecutionChain:
    """End-to-end: assemble -> link -> load -> execute across modules."""

    def _make_cpu(self, mem):
        from nova_cpu import CPU
        from nova_keyboard import NovaKeyboard
        from nova_sound import NovaSound
        import nova_gfx as gfx
        from nova.bus.eventbus import EventBus
        bus = EventBus()
        return CPU(mem, gfx.GFX(), NovaKeyboard(bus=bus), NovaSound(),
                   bus=bus)

    @pytest.mark.integration
    def test_three_module_call_chain(self, tmp_path):
        """main -> mid -> leaf jump chain computes R0 = 10 + 32 = 42."""
        leaf = _asm(tmp_path, "GLOBAL LEAFFN\nLEAFFN: ADD R0, R1\nHLT\n",
                    name="chainleaf")
        mid = _asm(tmp_path,
                   "EXTERN LEAFFN\nGLOBAL MIDFN\n"
                   "MIDFN: MOV R1, 32\nMOV P0, LEAFFN\nJNZ P0\nHLT\n",
                   name="chainmid")
        main = _asm(tmp_path,
                    "EXTERN MIDFN\nGLOBAL START\n"
                    "START: MOV R0, 10\nMOV P0, MIDFN\nJNZ P0\nHLT\n",
                    name="chainmain")
        doc = link([main.replace(".asm", ".nobj"),
                    mid.replace(".asm", ".nobj"),
                    leaf.replace(".asm", ".nobj")])
        out = tmp_path / "chain.nex"
        doc.write(str(out))
        mem = Memory()
        entry = mem.load(str(out))
        cpu = self._make_cpu(mem)
        cpu.pc = entry
        for _ in range(10000):
            if cpu.halted:
                break
            cpu.step()
        assert cpu.halted
        assert int(cpu.Rregisters[0]) == 42  # 10 + 32, accumulated in leaf

    @pytest.mark.integration
    def test_linked_data_section_readback(self, tmp_path):
        """A linked DATA section is readable at its merged symbol address."""
        lib = _asm(tmp_path,
                   "GLOBAL TABLE\nORG 0x8000\n"
                   "TABLE: DB 0xDE, 0xAD, 0xBE, 0xEF\n",
                   name="datalib")
        main = _asm(tmp_path,
                    "EXTERN TABLE\nGLOBAL START\n"
                    "START: MOV P0, TABLE\n"
                    "MOV R0, [P0]\n"
                    "MOV R1, [P0+3]\n"
                    "HLT\n",
                    name="datamain")
        doc = link([main.replace(".asm", ".nobj"),
                    lib.replace(".asm", ".nobj")])
        out = tmp_path / "data.nex"
        doc.write(str(out))
        mem = Memory()
        entry = mem.load(str(out))
        cpu = self._make_cpu(mem)
        cpu.pc = entry
        for _ in range(10000):
            if cpu.halted:
                break
            cpu.step()
        assert cpu.halted
        assert int(cpu.Rregisters[0]) == 0xDE
        assert int(cpu.Rregisters[1]) == 0xEF




# -- Assembler CLI delegation -------------------------------------------------

class TestAssemblerCLIDelegation:
    """nova_assembler.py main() routes GLOBAL/EXTERN sources to the
    object assembler while keeping the legacy path untouched."""

    @pytest.mark.unit
    @pytest.mark.assembler
    def test_cli_assembles_object_sources(self, tmp_path, monkeypatch):
        """A GLOBAL/EXTERN source produces a .nobj through the CLI."""
        import sys
        import nova_assembler as legacy
        src = tmp_path / "cliobj.asm"
        src.write_text("GLOBAL FN\nFN: NOP\nHLT\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["nova_assembler.py", str(src)])
        assert legacy.main() == 0
        assert (tmp_path / "cliobj.nobj").exists()
        assert not (tmp_path / "cliobj.bin").exists()

    @pytest.mark.unit
    @pytest.mark.assembler
    def test_cli_plain_source_uses_legacy_path(self, tmp_path, monkeypatch):
        """Sources without symbol declarations keep the legacy .bin flow."""
        import sys
        import nova_assembler as legacy
        src = tmp_path / "cliexe.asm"
        src.write_text("ORG 0x2000\nNOP\nHLT\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["nova_assembler.py", str(src)])
        assert legacy.main() == 0
        assert (tmp_path / "cliexe.bin").exists()
        assert (tmp_path / "cliexe.nex").exists()   # NOMF sibling
