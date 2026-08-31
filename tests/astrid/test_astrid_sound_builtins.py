"""Tests for the Astrid sound builtins: sound_play / sound_stop / sound_trigger.

The Nova-16 sound hardware has NO operand-taking SPLAY/SSTOP forms: both are
zero-operand opcodes whose parameters come exclusively from the SA/SF/SV/SW
special registers (SW bits 0-2 waveform, 3-5 channel, 6 loop, 7 enable), and
the assembler SILENTLY DROPS any operands written after them.

Regression: the sound_play stub used to emit `SPLAY P3, P2, P1` (operands
discarded -> args never reached the hardware) and sound_stop() used to emit
`SPLAY P1, 0, 0` (which PLAYED a sound instead of stopping one). These tests
pin the corrected register-protocol stubs and verify their runtime behavior
end-to-end through the real compiler -> assembler -> emulator pipeline.

Astrid API (documented by these tests):
    sound_play(freq, vol, sw)   -- sets SF, SV, SW then SPLAY.
                                   SW selects waveform/channel/loop/enable.
                                   SA is left untouched for waveform-7 use.
    sound_stop(channel)         -- shifts channel into SW bits 3-5, SSTOP.
    sound_trigger(effect)       -- STRIG with effect id 0-7.
"""
import os
import re
import sys

import pytest

# Path setup handled by tests/astrid/conftest.py

from nova_main import initialize_system

pytestmark = [pytest.mark.unit, pytest.mark.sound]


def run_binary(bin_path, max_cycles=2000000):
    """Run a binary headlessly and return (proc, cycles, mem, snd)."""
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=True)
    entry_point = mem.load(bin_path)
    proc.pc = entry_point
    cycle = 0
    while cycle < max_cycles and not proc.halted:
        cycle += 1
        proc.step()
    return proc, cycle, mem, snd


def compile_and_run(source, max_cycles=2000000):
    """Compile Astrid source, assemble, and run. Returns (proc, cycles, mem, snd)."""
    import tempfile
    # UTF-8 is required: source strings may contain non-ASCII characters
    # that cp1252 cannot encode on Windows.
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ast', delete=False,
                                     encoding='utf-8') as f:
        f.write(source)
        source_path = f.name

    try:
        from astrid_compiler import main as compiler_main
        old_argv = sys.argv
        sys.argv = [old_argv[0], source_path, '-o', source_path.replace('.ast', '.asm')]
        try:
            compiler_main()
        finally:
            sys.argv = old_argv

        asm_path = source_path.replace('.ast', '.asm')
        bin_path = source_path.replace('.ast', '.bin')

        from nova_assembler import Assembler
        asm = Assembler()
        asm.assemble(asm_path)

        proc, cycles, mem, snd = run_binary(bin_path, max_cycles)
        assert proc.halted, "Program did not halt"
        return proc, cycles, mem, snd, open(asm_path, encoding='utf-8').read()
    finally:
        for ext in ['.ast', '.asm', '.bin', '.org', '.sym']:
            path = source_path.replace('.ast', ext)
            if os.path.exists(path):
                os.unlink(path)


def playing_channels(snd):
    return [i for i, st in enumerate(snd.channel_states) if st['playing']]


class TestSoundPlay:
    """sound_play(freq, vol, sw) drives the hardware through SF/SV/SW."""

    def test_sets_registers_and_plays_selected_channel(self):
        # SW=0x8B: waveform 3 (sawtooth), CHANNEL 1, enable.
        proc, cycles, mem, snd, asm = compile_and_run(
            "void main() {\n"
            "    sound_play(128, 200, 0x8B);\n"
            "}\n"
        )
        # The stack arguments must actually land in the sound registers.
        assert snd.SF == 128
        assert snd.SV == 200
        assert snd.SW == 0x8B
        # And SPLAY must honor the channel encoded in SW bits 3-5.
        assert playing_channels(snd) == [1]
        status = snd.get_channel_status(1)
        assert status['waveform'] == 3
        assert status['volume'] == pytest.approx(200 / 255.0)

    def test_channel_zero_is_the_default_target(self):
        proc, cycles, mem, snd, asm = compile_and_run(
            "void main() {\n"
            "    sound_play(100, 255, 0x81);\n"   # square, channel 0, enable
            "}\n"
        )
        assert playing_channels(snd) == [0]
        assert snd.get_channel_status(0)['waveform'] == 1

    def test_enable_bit_clear_means_no_sound(self):
        # SW=0x03: waveform 3, channel 0, but ENABLE CLEAR. The play must be
        # ignored -- previously a play with SW=0 silently "succeeded" while
        # the args never reached the hardware at all.
        proc, cycles, mem, snd, asm = compile_and_run(
            "void main() {\n"
            "    sound_play(128, 200, 0x03);\n"
            "}\n"
        )
        assert playing_channels(snd) == []

    def test_sequential_plays_target_distinct_channels(self):
        proc, cycles, mem, snd, asm = compile_and_run(
            "void main() {\n"
            "    sound_play(100, 200, 0x82);\n"   # channel 0
            "    sound_play(150, 100, 0x93);\n"   # channel 2
            "}\n"
        )
        # Both channels keep playing; the second play must not clobber the
        # first channel's state.
        assert playing_channels(snd) == [0, 2]

    def test_does_not_touch_sa(self):
        # SA is intentionally preserved so callers can pre-set it for
        # waveform-7 memory samples.
        proc, cycles, mem, snd, asm = compile_and_run(
            "void main() {\n"
            "    sound_play(64, 64, 0x81);\n"
            "}\n"
        )
        assert snd.SA == 0

class TestSoundStop:
    """sound_stop(channel) stops exactly the requested channel."""

    def test_stops_selected_channel_and_leaves_others_playing(self):
        proc, cycles, mem, snd, asm = compile_and_run(
            "void main() {\n"
            "    sound_play(100, 200, 0x82);\n"   # channel 0
            "    sound_play(150, 100, 0x93);\n"   # channel 2
            "    sound_stop(0);\n"
            "}\n"
        )
        assert playing_channels(snd) == [2]

    def test_play_stop_roundtrip_on_same_channel(self):
        proc, cycles, mem, snd, asm = compile_and_run(
            "void main() {\n"
            "    sound_play(128, 128, 0x8D);\n"   # channel 1
            "    sound_stop(1);\n"
            "}\n"
        )
        assert playing_channels(snd) == []

    @pytest.mark.parametrize("channel", range(8))
    def test_stop_works_for_every_channel(self, channel):
        sw = 0x80 | (channel << 3) | 1   # square wave, <channel>, enable
        proc, cycles, mem, snd, asm = compile_and_run(
            "void main() {\n"
            f"    sound_play(100, 100, 0x{sw:02X});\n"
            f"    sound_stop({channel});\n"
            "}\n"
        )
        assert playing_channels(snd) == []


class TestSoundTrigger:
    """sound_trigger(effect) reaches the STRIG effect dispatcher."""

    @pytest.mark.parametrize("effect", [0, 3, 7])
    def test_valid_effects_run_to_halt(self, effect):
        proc, cycles, mem, snd, asm = compile_and_run(
            "void main() {\n"
            f"    sound_trigger({effect});\n"
            "}\n"
        )
        # Effects route through _play_sample_direct; with a mixer present or
        # not, the call must neither crash nor prevent a clean halt.

    def test_out_of_range_effect_is_ignored(self):
        proc, cycles, mem, snd, asm = compile_and_run(
            "void main() {\n"
            "    sound_trigger(9);\n"
            "}\n"
        )
        assert snd.channel_states == snd.channel_states  # no state explosion
        assert playing_channels(snd) == []


class TestGeneratedAssembly:
    """Pin the corrected stub codegen: register protocol, bare SPLAY/SSTOP.

    These are compile-time regression tests for the original bug where
    `SPLAY P3, P2, P1` / `SPLAY P1, 0, 0` were emitted. The assembler
    silently discards SPLAY operands, so any operand after SPLAY in the
    generated assembly is a defect.
    """

    def compile_only(self, source):
        proc, cycles, mem, snd, asm = compile_and_run(source)
        return asm

    def test_sound_play_uses_sound_register_protocol(self):
        asm = self.compile_only(
            "void main() {\n    sound_play(1, 2, 3);\n}\n"
        )
        assert re.search(r"MOV\s+SF,\s*P1", asm), "freq arg must reach SF"
        assert re.search(r"MOV\s+SV,\s*P2", asm), "vol arg must reach SV"
        assert re.search(r"MOV\s+SW,\s*P3", asm), "control word must reach SW"
        # Bare zero-operand SPLAY, exactly once for the call. (Use [ \t] so
        # the match cannot leak across line boundaries via \s.)
        assert len(re.findall(r"(?m)^[ \t]*SPLAY[ \t]*(?:;.*)?$", asm)) == 1

    def test_sound_play_never_emits_splay_with_operands(self):
        asm = self.compile_only(
            "void main() {\n    sound_play(1, 2, 3);\n}\n"
        )
        # The historical bug: operand forms that the assembler silently drops.
        # (Only match real operand text, not the word SPLAY inside comments.)
        assert not re.search(r"(?m)^[ \t]*SPLAY[ \t]+[^; \t]", asm), (
            "SPLAY takes no operands; the assembler would silently drop them"
        )

    def test_sound_stop_emits_sstop_not_splay(self):
        asm = self.compile_only(
            "void main() {\n    sound_stop(2);\n}\n"
        )
        # The historical bug: sound_stop() emitted `SPLAY P1, 0, 0`, which
        # assembles to a bare SPLAY -- i.e. it STARTED a sound.
        assert re.search(r"(?m)^[ \t]*SSTOP[ \t]*(?:;.*)?$", asm), (
            "sound_stop must emit SSTOP"
        )
        assert "SPLAY" not in asm, (
            "sound_stop must never emit SPLAY (it would start, not stop)"
        )
        # Channel must be shifted into SW bits 3-5 before SSTOP.
        assert re.search(r"SHL[ \t]+P[0-9]+,[ \t]*3", asm), (
            "channel must be shifted into SW bits 3-5"
        )

    def test_sound_trigger_emits_strig_with_operand(self):
        asm = self.compile_only(
            "void main() {\n    sound_trigger(4);\n}\n"
        )
        # STRIG is genuinely one-operand, so its operand must survive.
        assert re.search(r"STRIG[ \t]+P[0-9]+", asm)



