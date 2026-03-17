import nova_mouse
from nova_assembler import Assembler


class TestNovaMouseDevice:
    def test_mouse_registers_round_trip_through_cpu_operands(self, cpu):
        assert cpu.reg_index(0xC0) == (0, 'MX')
        assert cpu.reg_index(0xC1) == (0, 'MY')
        assert cpu.reg_index(0xC2) == (0, 'MB')

        cpu._set_operand_value('MX', 0, 0x1234)
        cpu._set_operand_value('MY', 0, 0x00FE)
        cpu._set_operand_value('MB', 0, 0x03)

        assert cpu._get_operand_value('MX', 0) == 0x1234
        assert cpu._get_operand_value('MY', 0) == 0x00FE
        assert cpu._get_operand_value('MB', 0) == 0x03
        assert cpu.mx == 0x1234
        assert cpu.my == 0x00FE
        assert cpu.mb == 0x03

    def test_mouse_reset_clears_register_state(self, cpu):
        cpu.mx = 0x2201
        cpu.my = 0x1040
        cpu.mb = 0x03

        cpu.reinit()

        assert cpu.mx == 0
        assert cpu.my == 0
        assert cpu.mb == 0
        assert cpu.mouse.cursor_enabled is False

    def test_hardware_cursor_overlays_expected_4x4_pattern(self, graphics):
        mouse = nova_mouse.NovaMouse(graphics)
        mouse.move_to(10, 20)

        screen = graphics.get_screen()
        expected_pixels = {
            (10, 20), (11, 20), (12, 20),
            (10, 21), (11, 21),
            (10, 22), (12, 22),
            (13, 23),
        }

        for y in range(20, 24):
            for x in range(10, 14):
                expected = 0xFF if (x, y) in expected_pixels else 0x00
                assert int(screen[y, x]) == expected

    def test_hardware_cursor_respects_visibility(self, graphics):
        mouse = nova_mouse.NovaMouse(graphics)
        graphics.layer_0[4, 3] = 0x22
        graphics.layers_dirty = True

        mouse.move_to(3, 4)
        visible_screen = graphics.get_screen().copy()
        assert int(visible_screen[4, 3]) == 0xFF

        mouse.reset()
        hidden_screen = graphics.get_screen().copy()
        assert int(hidden_screen[4, 3]) == 0x22

    def test_host_events_raise_and_clear_pending_interrupt(self, graphics):
        mouse = nova_mouse.NovaMouse(graphics)
        callback_states = []
        mouse.set_interrupt_callback(lambda: callback_states.append(mouse.pending_interrupt))

        mouse.move_to(7, 9, from_host=True)

        assert mouse.pending_interrupt is True
        assert callback_states[-1] is True

        mouse.clear_interrupt()

        assert mouse.pending_interrupt is False
        assert callback_states[-1] is False

    def test_disabled_mouse_ignores_host_events_and_hides_cursor(self, graphics):
        mouse = nova_mouse.NovaMouse(graphics)
        mouse.move_to(3, 4)
        assert int(graphics.get_screen()[4, 3]) == 0xFF

        mouse.write_control(0)
        mouse.move_to(40, 50, from_host=True)
        mouse.set_button(1, True, from_host=True)

        screen = graphics.get_screen().copy()
        assert mouse.enabled is False
        assert mouse.x == 3
        assert mouse.y == 4
        assert mouse.buttons == 0
        assert mouse.pending_interrupt is False
        assert int(screen[4, 3]) == 0x00


def test_assembler_accepts_mouse_control_and_register_operands(tmp_path):
    source = tmp_path / 'mouse_registers.asm'
    source.write_text(
        'ORG 0x1000\n'
        'MOUSECTRL 1\n'
        'MOV MX, 0x1234\n'
        'MOV MY, 0x00FE\n'
        'MOV MB, 0x03\n'
        'HLT\n',
        encoding='ascii',
    )

    assembler = Assembler()
    assert assembler.assemble(str(source)) is True

    binary = source.with_suffix('.bin').read_bytes()
    assert 0xB3 in binary
    assert 0xC0 in binary
    assert 0xC1 in binary
    assert 0xC2 in binary