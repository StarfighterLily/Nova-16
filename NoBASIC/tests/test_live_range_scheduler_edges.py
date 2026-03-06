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
            "CALL func",
            "RET",
            "HLT",
            "done:",
        ]

        ir = self.scheduler._parse_ir(lines)

        assert all(not inst.original_line.startswith(";") for inst in ir)
        assert ir[0].opcode == "DIRECTIVE"
        assert ir[1].is_label is True
        assert ir[2].has_side_effect is True  # memory write via []
        assert ir[3].is_jump is True
        assert ir[3].uses == {"FLAGS"}  # JZ reads flags
        assert ir[4].is_call is True
        assert ir[5].is_call is True
        assert ir[6].is_call is True

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
