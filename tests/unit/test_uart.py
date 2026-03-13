"""Unit tests for nova_uart.py - Nova-16 UART device."""

import nova_uart as uart


class MockBridge(uart.UARTHostBridge):
    def __init__(self, incoming=b""):
        self.incoming = bytearray(incoming)
        self.sent = bytearray()

    def send_bytes(self, data: bytes) -> None:
        self.sent.extend(data)

    def poll_rx(self) -> bytes:
        if not self.incoming:
            return b""
        payload = bytes(self.incoming)
        self.incoming.clear()
        return payload


class ClosableBridge(uart.UARTHostBridge):
    def __init__(self):
        self.closed = False

    def send_bytes(self, data: bytes) -> None:
        return None

    def close(self) -> None:
        self.closed = True


class TestUARTInitialization:
    def test_defaults(self):
        device = uart.NovaUART()
        assert device.get_data_register() == 0
        assert device.read_status_flags() == 0
        assert device.pending_interrupt is False
        assert device.protocol_mode == uart.NovaUART.MODE_RAW

    def test_reset_clears_state(self):
        device = uart.NovaUART()
        device.write_control(0x05)
        device.write_data(0x41)
        device.queue_rx_byte(0x42)
        device.reset()

        assert device.get_data_register() == 0
        assert device.read_status_flags() == 0
        assert device.pending_interrupt is False
        assert len(device.rx_fifo) == 0
        assert len(device.tx_fifo) == 0

    def test_set_host_bridge_closes_previous_bridge(self):
        first_bridge = ClosableBridge()
        second_bridge = ClosableBridge()
        device = uart.NovaUART(host_bridge=first_bridge)

        device.set_host_bridge(second_bridge)

        assert first_bridge.closed is True
        assert device.host_bridge is second_bridge


class TestUARTControlAndStatus:
    def test_control_updates_modes_and_irq(self):
        device = uart.NovaUART()
        device.write_control(0x05)  # IRQ + framed mode
        assert device.interrupt_enabled is True
        assert device.protocol_mode == uart.NovaUART.MODE_FRAMED

    def test_compat_status_register_roundtrip(self):
        device = uart.NovaUART()
        device.set_compat_status_control_register(0x83)
        status = device.get_compat_status_control_register()
        assert (status & 0x80) != 0
        assert (status & 0x01) != 0
        assert (status & 0x02) != 0

    def test_read_status_flags_returns_low_bits_only(self):
        device = uart.NovaUART()
        device.write_control(0x01)
        device.write_data(0x55)
        device.queue_rx_byte(0x66)
        assert device.read_status_flags() == 0x03


class TestUARTRxTxPaths:
    def test_rx_queue_and_read_data(self):
        device = uart.NovaUART()
        device.queue_rx_byte(0x41)
        device.queue_rx_byte(0x42)

        assert (device.read_status_flags() & 0x01) != 0
        assert device.read_data() == 0x41
        assert (device.read_status_flags() & 0x01) != 0
        assert device.read_data() == 0x42
        assert (device.read_status_flags() & 0x01) == 0

    def test_tx_sets_complete_and_interrupt_when_enabled(self):
        device = uart.NovaUART()
        device.write_control(0x01)
        device.write_data(0x5A)

        assert (device.read_status_flags() & 0x02) != 0
        assert device.pending_interrupt is True

    def test_tx_without_irq_does_not_set_pending(self):
        device = uart.NovaUART()
        device.write_control(0x00)
        device.write_data(0x5A)
        assert device.pending_interrupt is False


class TestUARTBridgesAndProtocols:
    def test_validate_tcp_config_requires_port(self):
        try:
            uart.validate_bridge_config(uart.UARTBridgeConfig(mode="tcp"))
        except ValueError as exc:
            assert str(exc) == "UART TCP bridge requires a port"
        else:
            raise AssertionError("Expected missing TCP port to fail validation")

    def test_describe_bridge_reports_tcp_target(self):
        config = uart.validate_bridge_config(
            uart.UARTBridgeConfig(mode="tcp", host="example.com", port=2323, timeout=0.25)
        )

        assert uart.describe_bridge(config) == "UART: TCP example.com:2323"

    def test_raw_mode_poll_reads_bridge_bytes(self):
        bridge = MockBridge(incoming=b"AB")
        device = uart.NovaUART(host_bridge=bridge)

        count = device.poll_host_bridge()
        assert count == 2
        assert device.read_data() == ord("A")
        assert device.read_data() == ord("B")

    def test_framed_mode_ingest_valid_frame(self):
        device = uart.NovaUART()
        device.write_control(0x04)
        frame = device.build_frame(b"OK")

        device.ingest_rx_stream(frame)

        assert len(device.received_frames) == 1
        assert device.received_frames[0] == b"OK"
        assert device.read_data() == ord("O")
        assert device.read_data() == ord("K")

    def test_framed_mode_bad_checksum_sets_error(self):
        device = uart.NovaUART()
        device.write_control(0x05)  # framed + irq enabled
        bad_frame = bytes([uart.NovaUART.FRAME_START, 2, ord("O"), ord("K"), 0x00])

        device.ingest_rx_stream(bad_frame)

        assert (device.control & uart.NovaUART.STATUS_CHECKSUM_ERROR) != 0
        assert device.pending_interrupt is True

    def test_send_payload_framed_to_bridge(self):
        bridge = MockBridge()
        device = uart.NovaUART(host_bridge=bridge)
        device.write_control(0x04)

        device.send_payload(b"HI")

        expected = device.build_frame(b"HI")
        assert bytes(bridge.sent) == expected


class TestSerialRegisterView:
    def test_register_view_maps_data_and_status(self):
        device = uart.NovaUART()
        view = uart.SerialRegisterView(device)

        view[0] = 0x33
        view[1] = 0x82
        status = int(view[1])

        assert view[0] == 0x33
        assert (status & 0x80) != 0
        assert (status & 0x02) != 0

    def test_register_view_slice_assignment(self):
        device = uart.NovaUART()
        view = uart.SerialRegisterView(device)

        view[:] = [0x11, 0x81]
        status = int(view[1])

        assert view[0] == 0x11
        assert (status & 0x80) != 0
        assert (status & 0x01) != 0


class TestUARTCpuIntegration:
    def test_uart_interrupt_callback_updates_cpu_gate(self, cpu):
        cpu.interrupts[1] = 1
        cpu.uart.write_control(0x01)
        cpu.uart.write_data(0x7A)

        assert cpu.has_pending_interrupt_sources is True
