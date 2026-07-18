"""Additional edge-case coverage for live range scheduling and spill analysis."""

import sys
from pathlib import Path

# Add compiler to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from compiler.codegen.live_range_scheduler import IRInstruction, LiveRangeScheduler, SpillMinimizer


class TestIRInstructionMovementRules:
    def test_can_move_after_respects_barriers(self):
        movable = IRInstruction(index=0, opcode="MOV", operands=["R0", "1"], defines={"R0"})
        label = IRInstruction(index=1, opcode="LABEL", operands=["L0"], is_label=True)
        jump = IRInstruction(index=1, opcode="JMP", operands=["L0"], is_jump=True)
        side_effect = IRInstruction(index=1, opcode="SWRITE", operands=["R0"], has_side_effect=True)
        call = IRInstruction(index=1, opcode="CALL", operands=["func"], is_call=True)

        assert movable.can_move_after(label) is False
        assert movable.can_move_after(jump) is False
        assert movable.can_move_after(side_effect) is False
        assert movable.can_move_after(call) is False

    def test_can_move_after_detects_data_hazards(self):
        # RAW: other defines what self uses
        other_raw = IRInstruction(index=0, opcode="MOV", operands=["R1", "1"], defines={"R1"})
        self_raw = IRInstruction(index=1, opcode="ADD", operands=["R0", "R1"], uses={"R1"}, defines={"R0"})
        assert self_raw.can_move_after(other_raw) is False

        # WAR: self defines what other uses
        other_war = IRInstruction(index=0, opcode="ADD", operands=["R2", "R0"], uses={"R0"}, defines={"R2"})
        self_war = IRInstruction(index=1, opcode="MOV", operands=["R0", "5"], defines={"R0"})
        assert self_war.can_move_after(other_war) is False

        # WAW: both define same register
        other_waw = IRInstruction(index=0, opcode="MOV", operands=["R3", "1"], defines={"R3"})
        self_waw = IRInstruction(index=1, opcode="MOV", operands=["R3", "2"], defines={"R3"})
        assert self_waw.can_move_after(other_waw) is False

        independent_a = IRInstruction(index=0, opcode="MOV", operands=["R4", "1"], defines={"R4"})
        independent_b = IRInstruction(index=1, opcode="MOV", operands=["R5", "2"], defines={"R5"})
        assert independent_b.can_move_after(independent_a) is True


class TestLiveRangeSchedulerEdges:
    def setup_method(self):
        self.scheduler = LiveRangeScheduler(debug=False)

    def test_extract_register_handles_byte_selectors_and_immediates(self):
        assert self.scheduler._extract_register("P0:") == "P0"
        assert self.scheduler._extract_register(":p1") == "P1"
        assert self.scheduler._extract_register("[R7]") == "R7"
        assert self.scheduler._extract_register("0x2A") == ""
        assert self.scheduler._extract_register("-10") == ""
        assert self.scheduler._extract_register("UNKNOWN") == ""

    def test_parse_ir_classifies_directives_labels_jumps_calls_and_side_effects(self):
        lines = [
            "   ; comment-only line",
            "ORG 0x0200",
            "start:",
            "MOV [P0], R1",
            "JZ done",
            "CALLZ func",
            "LOOPZ P1, start",
            "RETN R0",
            "HLT",
            "done:",
        ]

        ir = self.scheduler._parse_ir(lines)

        assert ir[0].opcode == "DIRECTIVE"
        assert ir[0].has_side_effect is True
        assert ir[1].opcode == "DIRECTIVE"
        assert ir[1].has_side_effect is True
        assert ir[2].is_label is True
        assert ir[3].has_side_effect is True  # memory write via []
        assert ir[4].is_jump is True
        assert ir[4].uses == {"FLAGS"}  # JZ reads flags
        assert ir[5].is_call is True
        assert ir[5].uses == {"FLAGS"}
        assert ir[6].is_jump is True
        assert "FLAGS" in ir[6].uses
        assert ir[7].is_call is True
        assert ir[8].is_call is True

    def test_analyze_operands_tracks_flags_and_memory_operands(self):
        defines, uses = self.scheduler._analyze_operands("CMP", ["R0", "R1"])
        assert "FLAGS" in defines
        assert uses == {"R0", "R1"}

        defines, uses = self.scheduler._analyze_operands("JNZ", ["target"])
        assert defines == set()
        assert uses == {"FLAGS"}

        defines, uses = self.scheduler._analyze_operands("MOV", ["[P2]", "R1"])
        assert "P2" in uses
        assert "R1" in uses
        assert defines == set()

        defines, uses = self.scheduler._analyze_operands("MOV", ["R3", "[P4]"])
        assert "R3" in defines
        assert "P4" in uses

        defines, uses = self.scheduler._analyze_operands("WHILE", ["R5"])
        assert "FLAGS" in defines
        assert uses == {"R5"}

        defines, uses = self.scheduler._analyze_operands("RETN", ["R2"])
        assert {"R0", "P0", "FLAGS"}.issubset(defines)
        assert "R2" in uses

        defines, uses = self.scheduler._analyze_operands("LOOPZ", ["P3", "loop"])
        assert "P3" in defines
        assert {"P3", "FLAGS"}.issubset(uses)

    def test_build_dependencies_sets_raw_war_and_waw_edges(self):
        code = [
            "MOV R0, 1",   # defines R0
            "ADD R1, R0",  # uses R0 (RAW from instruction 0)
            "MOV R0, 2",   # defines R0 (WAR/WAW relative to earlier uses/defs)
        ]

        self.scheduler.instructions = self.scheduler._parse_ir(code)
        self.scheduler._build_dependencies()

        instr0 = self.scheduler.instructions[0]
        instr1 = self.scheduler.instructions[1]
        instr2 = self.scheduler.instructions[2]

        assert 0 in instr1.dependencies  # RAW dependency from first MOV
        assert 0 in instr2.dependencies  # WAW on R0
        assert 1 in instr2.dependencies  # WAR: instr1 reads R0 before instr2 writes R0

    def test_analyze_liveness_propagates_pressure_hints(self):
        code = ["MOV R0, 1", "MOV R1, 2", "ADD R0, R1"]
        self.scheduler.instructions = self.scheduler._parse_ir(code)

        self.scheduler._analyze_liveness({"a": (0, 1), "b": (1, 2)})

        # point 1 should have both vars live
        assert self.scheduler.pressure_at_point[1] == 2
        # each instruction gets mapped pressure by original index
        pressure_hints = [i.pressure_hint for i in self.scheduler.instructions]
        assert pressure_hints[0] >= 1
        assert pressure_hints[1] >= 2

    def test_move_reduces_pressure_requires_liveness_and_def_only_instruction(self):
        self.scheduler.instructions = self.scheduler._parse_ir(["MOV R0, 1", "MOV R1, 2"])

        # No liveness analysis yet => cannot estimate pressure reduction
        assert self.scheduler._move_reduces_pressure(0, 1) is False

        self.scheduler._analyze_liveness({"x": (0, 2)})
        # MOV defines destination without reading it, so move can reduce pressure estimate
        assert self.scheduler._move_reduces_pressure(0, 1) is True

        # ADD reads and defines same destination -> not considered pressure-reducing move
        self.scheduler.instructions = self.scheduler._parse_ir(["ADD R0, R1", "MOV R2, 3"])
        self.scheduler._analyze_liveness({"x": (0, 1)})
        assert self.scheduler._move_reduces_pressure(0, 1) is False


class TestRelativeBranchSchedulingRegression:
    """Regression: BR/BRZ/BRNZ (relative branches, reachable from NoBASIC
    inline ``asm`` blocks -- see generator.py::generate_asm_block, which
    splices raw assembly text straight into the instruction stream the
    scheduler reorders) were absent from both ``is_jump`` and
    ``flag_reading`` in ``_parse_ir``/``_analyze_operands``. The scheduler
    therefore treated them as ordinary, freely-movable instructions: they
    could be hoisted ahead of the flag-setting instruction they depend on,
    or ordinary instructions could be hoisted past them -- silently
    rewriting control flow. Confirmed by scheduling a CMP/MOV/BRZ/MOV/label
    sequence with liveness data attached (mirroring what generator.py
    actually passes); pre-fix, BRZ was hoisted to the very first line.
    """

    def setup_method(self):
        self.scheduler = LiveRangeScheduler(debug=False)

    def test_brz_is_not_hoisted_ahead_of_the_flags_it_reads(self):
        code = [
            "CMP R0, R1",
            "MOV R2, 5",
            "BRZ target",
            "MOV R3, 1",
            "target:",
        ]
        result = self.scheduler.schedule(code, variable_lifetimes={"R2": (0, 4)})

        brz_idx = next(i for i, l in enumerate(result) if l.startswith("BRZ"))
        cmp_idx = next(i for i, l in enumerate(result) if l.startswith("CMP"))
        mov_r3_idx = next(i for i, l in enumerate(result) if "MOV R3" in l)

        # BRZ must still read the flags CMP set, and the fall-through
        # instruction (MOV R3, 1) must still only run when BRZ doesn't branch.
        assert cmp_idx < brz_idx, "BRZ must not be hoisted ahead of the CMP that sets its flags"
        assert brz_idx < mov_r3_idx, "MOV R3 must not be hoisted ahead of the branch that guards it"

    def test_brnz_blocks_reordering_like_a_conditional_jump(self):
        instr = IRInstruction(index=0, opcode="MOV", operands=["R0", "1"], defines={"R0"})
        brnz = IRInstruction(index=1, opcode="BRNZ", operands=["L0"], is_jump=True)
        assert instr.can_move_after(brnz) is False

    def test_br_is_classified_as_jump_and_reads_no_flags(self):
        parsed = LiveRangeScheduler()._parse_ir(["BR target", "target:"])
        br_instr = parsed[0]
        assert br_instr.is_jump is True
        # Unconditional branch: doesn't read FLAGS (unlike BRZ/BRNZ).
        assert "FLAGS" not in br_instr.uses

    def test_brz_brnz_are_flagged_as_flag_readers(self):
        parsed = LiveRangeScheduler()._parse_ir(["BRZ target", "BRNZ target", "target:"])
        assert "FLAGS" in parsed[0].uses
        assert "FLAGS" in parsed[1].uses

    def test_int_is_treated_as_a_call_boundary(self):
        parsed = LiveRangeScheduler()._parse_ir(["INT 5"])
        assert parsed[0].is_call is True


class TestP8P9RegisterNameRecognition:
    """Regression: REGISTER_NAMES only listed 'SP'/'FP', not the equivalent
    raw 'P8'/'P9' mnemonics that core/regfile.py maps to the same physical
    registers and that nova_assembler.py accepts as valid operand text.
    Code using 'P8'/'P9' directly (e.g. inline asm) was invisible to
    dependency tracking -- both as a define and a use.
    """

    def test_p8_p9_recognized_as_registers(self):
        scheduler = LiveRangeScheduler()
        assert scheduler._extract_register("P8") == "P8"
        assert scheduler._extract_register("P9") == "P9"

    def test_p8_dependency_tracked_like_sp(self):
        scheduler = LiveRangeScheduler()
        parsed = scheduler._parse_ir(["MOV P8, 100", "MOV R0, P8"])
        defines, uses = parsed[0].defines, parsed[1].uses
        assert "P8" in defines
        assert "P8" in uses


class TestSpillMinimizerEdges:
    def test_suggest_optimizations_threshold_buckets(self):
        minimizer = SpillMinimizer(debug=False)
        candidates = {
            "very_long": 25,
            "moderate": 15,
            "short": 5,
        }

        suggestions = minimizer.suggest_optimizations(candidates)

        assert any("very_long" in s and "long live range" in s for s in suggestions)
        assert any("moderate" in s and "spill candidate" in s for s in suggestions)
        assert all("short" not in s for s in suggestions)

    def test_analyze_returns_priority_sorted_descending(self):
        minimizer = SpillMinimizer(debug=False)
        priorities = minimizer.analyze({"a": (0, 2), "b": (0, 10), "c": (5, 6)})

        keys = list(priorities.keys())
        assert keys[0] == "b"
        assert priorities["b"] >= priorities["a"] >= priorities["c"]
