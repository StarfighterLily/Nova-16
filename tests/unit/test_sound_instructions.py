"""
CPU-instruction-level tests for the Nova-16 sound system (SPLAY / SSTOP / STRIG).

Regression coverage for two classes of bugs:

1. Channel selection: the SPLAY/SSTOP handlers masked ``SW & 0x07`` (the
   WAVEFORM field) instead of extracting the channel from SW bits 3-5, so
   ``MOV SW, 0x87`` (waveform 7, channel 0, enable) wrongly played on
   channel 7. Per the SW layout (bits 0-2 waveform, 3-5 channel, 6 loop,
   7 enable -- see nova_sound.py's module docstring), the channel must come
   from bits 3-5.

2. Operand discipline: SPLAY/SSTOP are zero-operand opcodes; any operand
   bytes emitted after them are silently dropped by the assembler, so all
   sound parameters must travel through the SA/SF/SV/SW special registers.

Programs are written in assembly and run through the real assembler so the
full encode -> execute path is exercised.
"""
import pytest

from tests.conftest import run_cpu_cycles

pytestmark = [pytest.mark.unit, pytest.mark.sound, pytest.mark.cpu]


class _FakeMixerSound:
    """Stand-in for pygame.mixer.Sound so SSTOP's stop path is observable
    regardless of whether a real audio mixer is available in the test env."""

    def __init__(self):
        self.stopped = False

    def stop(self):
        self.stopped = True


def run_asm(cpu, memory, tmp_path, source, org=0x0200):
    """Assemble `source`, load it into `memory`, and run to halt."""
    from nova_assembler import Assembler

    asm_path = tmp_path / f"snd_{org:04X}.asm"
    asm_path.write_text(f"ORG 0x{org:04X}\n{source}\n")
    Assembler().assemble(str(asm_path))
    entry = memory.load(str(asm_path)[:-4] + ".bin")

    cpu.pc = entry
    cpu.halted = False  # clear sticky HLT from any previous program run
    run_cpu_cycles(cpu, 100000)
    assert cpu.halted, f"Program did not halt (PC=0x{cpu.pc:04X})"


def playing_channels(sound):
    return [i for i, st in enumerate(sound.channel_states) if st['playing']]


class TestSplayChannelSelection:
    """SPLAY must take the channel from SW bits 3-5, never bits 0-2."""

    def test_splay_uses_sw_bits_3_to_5_as_channel(self, cpu, memory, tmp_path):
        # SW=0x87: waveform 7, CHANNEL 0, enable. The historical bug played
        # this on channel 7 (the waveform field) instead of channel 0.
        run_asm(cpu, memory, tmp_path, (
            "MOV SF, 128\n"
            "MOV SV, 128\n"
            "MOV SW, 0x87\n"
            "SPLAY\n"
            "HLT\n"
        ))
        assert playing_channels(cpu.sound) == [0]

    def test_splay_waveform_field_never_selects_channel(self, cpu, memory, tmp_path):
        # SW=0x8D: waveform 5 (white noise), channel 1, enable. Channel 5
        # (matching the waveform, as the historical bug decoded it) must NOT
        # be touched.
        run_asm(cpu, memory, tmp_path, (
            "MOV SW, 0x8D\n"
            "SPLAY\n"
            "HLT\n"
        ))
        assert playing_channels(cpu.sound) == [1]

    def test_splay_handler_reads_bits_3_5_directly(self, cpu):
        # White-box regression: the handler extracts the channel, not the
        # waveform, from SW.
        from core.exec_handlers import _splay

        cpu.sound.SW = 0x87
        assert _splay(cpu) is True
        assert playing_channels(cpu.sound) == [0]

    @pytest.mark.parametrize("sw,expected_channel", [
        (0x80, 0),   # waveform 0, channel 0
        (0x8A, 1),   # waveform 2, channel 1
        (0x94, 2),   # waveform 4, channel 2
        (0xBF, 7),   # waveform 7, channel 7, loop
    ])
    def test_splay_channel_decoding_table(self, cpu, memory, tmp_path,
                                          sw, expected_channel):
        run_asm(cpu, memory, tmp_path, (
            f"MOV SW, 0x{sw:02X}\n"
            "SPLAY\n"
            "HLT\n"
        ))
        assert playing_channels(cpu.sound) == [expected_channel]


class TestSplayParameterPropagation:
    """SF/SV/SW fields must reach the channel state as documented."""

    def test_frequency_and_volume_mapping(self, cpu, memory, tmp_path):
        run_asm(cpu, memory, tmp_path, (
            "MOV SF, 128\n"
            "MOV SV, 128\n"
            "MOV SW, 0x82\n"   # sine, channel 0, enable
            "SPLAY\n"
            "HLT\n"
        ))
        status = cpu.sound.get_channel_status(0)
        assert status['playing'] is True
        # 0-255 register maps exponentially onto 55..1760 Hz.
        expected_freq = 55.0 * (1760.0 / 55.0) ** (128 / 255.0)
        assert status['frequency'] == pytest.approx(expected_freq)
        assert status['volume'] == pytest.approx(128 / 255.0)
        assert status['waveform'] == 2  # sine

    def test_loop_flag_recorded(self, cpu, memory, tmp_path):
        run_asm(cpu, memory, tmp_path, (
            "MOV SW, 0xC2\n"   # sine, channel 0, LOOP + enable
            "SPLAY\n"
            "HLT\n"
        ))
        assert cpu.sound.get_channel_status(0)['loop'] is True

    def test_one_shot_default_has_no_loop_flag(self, cpu, memory, tmp_path):
        run_asm(cpu, memory, tmp_path, (
            "MOV SW, 0x82\n"
            "SPLAY\n"
            "HLT\n"
        ))
        assert cpu.sound.get_channel_status(0)['loop'] is False

    def test_enable_bit_gates_playback(self, cpu, memory, tmp_path):
        # SW=0x07: waveform 7, channel 0, but ENABLE CLEAR -> no play.
        run_asm(cpu, memory, tmp_path, (
            "MOV SF, 100\n"
            "MOV SV, 100\n"
            "MOV SW, 0x07\n"
            "SPLAY\n"
            "HLT\n"
        ))
        assert playing_channels(cpu.sound) == []


class TestSstopChannelSelection:
    """SSTOP must stop the channel from SW bits 3-5 and leave others alone."""

    def test_sstop_targets_only_sw_selected_channel(self, cpu, memory, tmp_path):
        # Play on channel 0, then stop channel 3. Channel 0 must still be
        # playing afterwards: SSTOP read bits 3-5 (0x98 -> channel 3), not
        # the waveform field.
        fake3 = _FakeMixerSound()
        cpu.sound.sound_channels[3] = fake3
        cpu.sound.channel_states[3]['playing'] = True

        run_asm(cpu, memory, tmp_path, (
            "MOV SW, 0x82\n"   # play sine on channel 0
            "SPLAY\n"
            "MOV SW, 0x98\n"   # stop channel 3
            "SSTOP\n"
            "HLT\n"
        ))
        status = cpu.sound.get_channel_status(0)
        assert status['playing'] is True, "SSTOP hit the wrong channel"
        # The SW-selected channel was stopped and torn down.
        assert fake3.stopped is True
        assert cpu.sound.sound_channels[3] is None
        assert cpu.sound.get_channel_status(3)['playing'] is False

    def test_sstop_never_touches_other_channels_even_without_mixer(self, cpu, monkeypatch):
        # Even with the audio mixer unavailable, a targeted SSTOP must not
        # reset every channel. The old implementation reset ALL channel state
        # whenever pygame.mixer was down, so on headless machines SSTOP ch3
        # would silence ch0-ch7.
        import nova_sound
        monkeypatch.setattr(nova_sound.pygame.mixer, 'get_init', lambda: None)

        fakes = {ch: _FakeMixerSound() for ch in (0, 3, 7)}
        for ch, fake in fakes.items():
            cpu.sound.sound_channels[ch] = fake
            cpu.sound.channel_states[ch]['playing'] = True

        assert cpu.sound.sstop(3) is True
        assert fakes[3].stopped is True
        assert cpu.sound.get_channel_status(3)['playing'] is False
        # Neighbours are completely untouched.
        for ch in (0, 7):
            assert cpu.sound.get_channel_status(ch)['playing'] is True
            assert fakes[ch].stopped is False

    def test_sstop_out_of_range_channel_is_a_safe_noop(self, cpu):
        cpu.sound.channel_states[0]['playing'] = True
        assert cpu.sound.sstop(-1) is True
        assert cpu.sound.sstop(8) is True
        assert cpu.sound.sstop(255) is True
        assert cpu.sound.get_channel_status(0)['playing'] is True

    def test_play_then_stop_roundtrip(self, cpu, memory, tmp_path):
        # Same channel across two programs: play on channel 6, then stop it.
        run_asm(cpu, memory, tmp_path, (
            "MOV SW, 0xB5\n"   # waveform 5, channel 6, loop + enable
            "SPLAY\n"
            "HLT\n"
        ), org=0x0200)
        assert playing_channels(cpu.sound) == [6]

        run_asm(cpu, memory, tmp_path, (
            "MOV SW, 0x30\n"   # channel 6 (enable bit irrelevant for SSTOP)
            "SSTOP\n"
            "HLT\n"
        ), org=0x0300)
        assert playing_channels(cpu.sound) == []


class TestStrig:
    """STRIG triggers effect 0-7 and rejects anything else."""

    @pytest.mark.parametrize("effect", list(range(8)))
    def test_valid_effects_report_success(self, cpu, effect):
        assert cpu.sound.strig(effect) is True

    @pytest.mark.parametrize("effect", [8, 9, 255, -1])
    def test_invalid_effects_report_failure(self, cpu, effect):
        assert cpu.sound.strig(effect) is False

    def test_strig_instruction_runs_to_halt(self, cpu, memory, tmp_path):
        run_asm(cpu, memory, tmp_path, (
            "STRIG 3\n"
            "HLT\n"
        ))
        # No crash and clean halt is the observable contract at ISA level.



