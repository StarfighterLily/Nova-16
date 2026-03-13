#!/usr/bin/env python3
"""Nova-16 UART device and host bridge helpers."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import socket
import sys
from typing import Callable, Deque, List, Optional, Union, overload


DEFAULT_TCP_HOST = "127.0.0.1"
DEFAULT_TCP_TIMEOUT = 0.01


@dataclass(frozen=True)
class UARTBridgeConfig:
    """Serializable UART host-bridge settings shared by CLI and GUI."""

    mode: str = "none"
    host: str = DEFAULT_TCP_HOST
    port: Optional[int] = None
    timeout: float = DEFAULT_TCP_TIMEOUT


def validate_bridge_config(config: Optional[UARTBridgeConfig]) -> UARTBridgeConfig:
    normalized = config or UARTBridgeConfig()
    mode = str(normalized.mode).strip().lower() or "none"
    host = str(normalized.host).strip() or DEFAULT_TCP_HOST
    timeout = float(normalized.timeout)

    if mode not in {"none", "terminal", "tcp"}:
        raise ValueError(f"Unsupported UART bridge mode: {normalized.mode}")
    if timeout <= 0:
        raise ValueError("UART bridge timeout must be greater than zero")

    port = normalized.port
    if mode == "tcp":
        if port is None:
            raise ValueError("UART TCP bridge requires a port")
        port = int(port)
        if port < 1 or port > 65535:
            raise ValueError("UART TCP bridge port must be between 1 and 65535")
    else:
        port = None

    return UARTBridgeConfig(mode=mode, host=host, port=port, timeout=timeout)


def create_host_bridge(config: Optional[UARTBridgeConfig]) -> Optional["UARTHostBridge"]:
    normalized = validate_bridge_config(config)
    if normalized.mode == "none":
        return None
    if normalized.mode == "terminal":
        return LocalTerminalBridge()
    return TCPSocketBridge(normalized.host, normalized.port, timeout=normalized.timeout)


def describe_bridge(config: Optional[UARTBridgeConfig]) -> str:
    normalized = validate_bridge_config(config)
    if normalized.mode == "none":
        return "UART: Off"
    if normalized.mode == "terminal":
        return "UART: Terminal"
    return f"UART: TCP {normalized.host}:{normalized.port}"


def get_bridge_config(host_bridge: Optional["UARTHostBridge"]) -> UARTBridgeConfig:
    if host_bridge is None:
        return UARTBridgeConfig()
    if isinstance(host_bridge, LocalTerminalBridge):
        return UARTBridgeConfig(mode="terminal")
    if isinstance(host_bridge, TCPSocketBridge):
        return UARTBridgeConfig(
            mode="tcp",
            host=host_bridge.host,
            port=host_bridge.port,
            timeout=host_bridge.timeout,
        )
    return UARTBridgeConfig(mode=host_bridge.__class__.__name__.lower())


class UARTHostBridge:
    """Base host bridge interface for UART transport integration."""

    def send_bytes(self, data: bytes) -> None:
        raise NotImplementedError

    def poll_rx(self) -> bytes:
        return b""

    def close(self) -> None:
        return None


class LocalTerminalBridge(UARTHostBridge):
    """Local terminal bridge using stdout for TX and an injectable RX queue."""

    def __init__(self) -> None:
        self._rx_queue: Deque[int] = deque()

    def inject_input(self, data: bytes) -> None:
        for value in data:
            self._rx_queue.append(value & 0xFF)

    def send_bytes(self, data: bytes) -> None:
        if not data:
            return
        sys.stdout.write(data.decode("latin1", errors="replace"))
        sys.stdout.flush()

    def poll_rx(self) -> bytes:
        if not self._rx_queue:
            return b""
        out = bytearray()
        while self._rx_queue:
            out.append(self._rx_queue.popleft())
        return bytes(out)


class TCPSocketBridge(UARTHostBridge):
    """TCP socket bridge for remote UART terminal/console integration."""

    def __init__(self, host: str, port: int, timeout: float = 0.01) -> None:
        self.host = host
        self.port = int(port)
        self.timeout = float(timeout)
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(self.timeout)
        self._sock.connect((self.host, self.port))
        self._sock.setblocking(False)

    def send_bytes(self, data: bytes) -> None:
        if data:
            self._sock.sendall(data)

    def poll_rx(self) -> bytes:
        try:
            return self._sock.recv(4096)
        except BlockingIOError:
            return b""
        except socket.timeout:
            return b""

    def close(self) -> None:
        try:
            self._sock.close()
        except OSError:
            pass


class SerialRegisterView:
    """Compatibility view mapping legacy cpu.serial registers to UART state."""

    def __init__(self, uart: "NovaUART") -> None:
        self._uart = uart

    def __len__(self) -> int:
        return 2

    @overload
    def __getitem__(self, key: int) -> int:
        ...

    @overload
    def __getitem__(self, key: slice) -> List[int]:
        ...

    def __getitem__(self, key: Union[int, slice]) -> Union[int, List[int]]:
        if isinstance(key, slice):
            indices = range(*key.indices(2))
            return [self.__getitem__(idx) for idx in indices]
        if key == 0:
            return self._uart.get_data_register()
        if key == 1:
            return self._uart.get_compat_status_control_register()
        raise IndexError("serial register index out of range")

    def __setitem__(self, key: Union[int, slice], value) -> None:
        if isinstance(key, slice):
            values = list(value)
            indices = range(*key.indices(2))
            if len(values) != len(list(indices)):
                raise ValueError("slice assignment size mismatch")
            for idx, item in zip(indices, values):
                self.__setitem__(idx, item)
            return
        if key == 0:
            self._uart.set_data_register(value)
            return
        if key == 1:
            self._uart.set_compat_status_control_register(value)
            return
        raise IndexError("serial register index out of range")


class NovaUART:
    """Virtual UART (8-bit data, status/control, RX/TX interrupt signaling)."""

    FRAME_START = 0x7E

    STATUS_RX_AVAILABLE = 0x01
    STATUS_TX_COMPLETE = 0x02
    STATUS_OVERRUN = 0x04
    STATUS_FRAME_ERROR = 0x08
    STATUS_CHECKSUM_ERROR = 0x10
    STATUS_IRQ_PENDING = 0x80

    CONTROL_IRQ_ENABLE = 0x01
    CONTROL_FRAMED_MODE = 0x04

    MODE_RAW = 0
    MODE_FRAMED = 1

    def __init__(
        self,
        host_bridge: Optional[UARTHostBridge] = None,
        rx_fifo_size: int = 256,
        tx_fifo_size: int = 256,
    ) -> None:
        self.host_bridge = None
        self.rx_fifo: Deque[int] = deque(maxlen=max(1, rx_fifo_size))
        self.tx_fifo: Deque[int] = deque(maxlen=max(1, tx_fifo_size))
        self.received_frames: Deque[bytes] = deque(maxlen=64)

        self.data_register = 0
        self.control = 0
        self.interrupt_enabled = False
        self.rx_available = False
        self.tx_complete = False
        self.pending_interrupt = False

        self.protocol_mode = self.MODE_RAW
        self._frame_length = 0
        self._frame_payload = bytearray()
        self._frame_state = "WAIT_START"

        self.interrupt_callback: Optional[Callable[[], None]] = None
        self.set_host_bridge(host_bridge)

    def set_host_bridge(self, host_bridge: Optional[UARTHostBridge]) -> None:
        if self.host_bridge is host_bridge:
            return
        if self.host_bridge is not None:
            self.host_bridge.close()
        self.host_bridge = host_bridge

    def close_host_bridge(self) -> None:
        self.set_host_bridge(None)

    def set_interrupt_callback(self, callback: Optional[Callable[[], None]]) -> None:
        self.interrupt_callback = callback

    def _notify_interrupt_state_changed(self) -> None:
        if self.interrupt_callback is not None:
            self.interrupt_callback()

    def _set_pending_interrupt(self) -> None:
        if self.interrupt_enabled:
            self.pending_interrupt = True
            self._notify_interrupt_state_changed()

    def _clear_pending_interrupt(self) -> None:
        self.pending_interrupt = False
        self._notify_interrupt_state_changed()

    def reset(self) -> None:
        self.rx_fifo.clear()
        self.tx_fifo.clear()
        self.received_frames.clear()

        self.data_register = 0
        self.control = 0
        self.interrupt_enabled = False
        self.rx_available = False
        self.tx_complete = False
        self.pending_interrupt = False

        self.protocol_mode = self.MODE_RAW
        self._frame_length = 0
        self._frame_payload.clear()
        self._frame_state = "WAIT_START"

    def set_data_register(self, value: int) -> None:
        self.data_register = int(value) & 0xFF

    def get_data_register(self) -> int:
        return int(self.data_register) & 0xFF

    def set_compat_status_control_register(self, value: int) -> None:
        value = int(value) & 0xFF
        self.pending_interrupt = bool(value & self.STATUS_IRQ_PENDING)
        self.rx_available = bool(value & self.STATUS_RX_AVAILABLE)
        self.tx_complete = bool(value & self.STATUS_TX_COMPLETE)
        self.control = value & 0x7C
        self.protocol_mode = self.MODE_FRAMED if (self.control & self.CONTROL_FRAMED_MODE) else self.MODE_RAW
        self._notify_interrupt_state_changed()

    def get_compat_status_control_register(self) -> int:
        value = self.control & 0x7C
        if self.rx_available:
            value |= self.STATUS_RX_AVAILABLE
        if self.tx_complete:
            value |= self.STATUS_TX_COMPLETE
        if self.pending_interrupt:
            value |= self.STATUS_IRQ_PENDING
        return value & 0xFF

    def read_status_flags(self) -> int:
        value = 0
        if self.rx_available:
            value |= self.STATUS_RX_AVAILABLE
        if self.tx_complete:
            value |= self.STATUS_TX_COMPLETE
        return value

    def write_control(self, control: int) -> None:
        control = int(control) & 0x7F
        self.control = control & 0x7C
        self.interrupt_enabled = bool(control & self.CONTROL_IRQ_ENABLE)
        self.protocol_mode = self.MODE_FRAMED if (control & self.CONTROL_FRAMED_MODE) else self.MODE_RAW

        # Preserve legacy behavior where low bits are directly reflected in serial control/status.
        self.rx_available = bool(control & self.STATUS_RX_AVAILABLE)
        self.tx_complete = bool(control & self.STATUS_TX_COMPLETE)
        self._notify_interrupt_state_changed()

    def read_data(self) -> int:
        if self.rx_fifo:
            value = self.rx_fifo.popleft()
            self.data_register = value
        else:
            value = self.data_register

        self.rx_available = bool(self.rx_fifo)
        if not self.rx_available:
            self.data_register = value
        return value & 0xFF

    def write_data(self, value: int) -> None:
        value = int(value) & 0xFF
        self.data_register = value

        if len(self.tx_fifo) == self.tx_fifo.maxlen:
            self.tx_fifo.popleft()
        self.tx_fifo.append(value)

        self.tx_complete = True
        if self.host_bridge is not None:
            self.host_bridge.send_bytes(bytes([value]))

        self._set_pending_interrupt()

    def queue_rx_byte(self, value: int) -> None:
        value = int(value) & 0xFF
        if len(self.rx_fifo) == self.rx_fifo.maxlen:
            self.rx_fifo.popleft()
        self.rx_fifo.append(value)
        self.data_register = self.rx_fifo[0]
        self.rx_available = True
        self._set_pending_interrupt()

    def queue_rx_bytes(self, payload: bytes) -> None:
        for value in payload:
            self.queue_rx_byte(value)

    def clear_interrupt(self) -> None:
        self._clear_pending_interrupt()

    def build_frame(self, payload: bytes) -> bytes:
        data = bytes(payload)
        length = len(data) & 0xFF
        checksum = sum(data) & 0xFF
        return bytes([self.FRAME_START, length]) + data + bytes([checksum])

    def send_payload(self, payload: bytes) -> None:
        outgoing = payload
        if self.protocol_mode == self.MODE_FRAMED:
            outgoing = self.build_frame(payload)

        for value in outgoing:
            self.write_data(value)

    def _ingest_framed_byte(self, value: int) -> None:
        if self._frame_state == "WAIT_START":
            if value == self.FRAME_START:
                self._frame_payload.clear()
                self._frame_state = "WAIT_LENGTH"
            return

        if self._frame_state == "WAIT_LENGTH":
            self._frame_length = value & 0xFF
            if self._frame_length == 0:
                self._frame_state = "WAIT_CHECKSUM"
            else:
                self._frame_state = "WAIT_PAYLOAD"
            return

        if self._frame_state == "WAIT_PAYLOAD":
            self._frame_payload.append(value)
            if len(self._frame_payload) >= self._frame_length:
                self._frame_state = "WAIT_CHECKSUM"
            return

        if self._frame_state == "WAIT_CHECKSUM":
            checksum = sum(self._frame_payload) & 0xFF
            if checksum == (value & 0xFF):
                frame_payload = bytes(self._frame_payload)
                self.received_frames.append(frame_payload)
                self.queue_rx_bytes(frame_payload)
            else:
                self.control |= self.STATUS_CHECKSUM_ERROR
                self._set_pending_interrupt()

            self._frame_payload.clear()
            self._frame_state = "WAIT_START"

    def ingest_rx_stream(self, payload: bytes) -> None:
        for value in payload:
            if self.protocol_mode == self.MODE_FRAMED:
                self._ingest_framed_byte(value)
            else:
                self.queue_rx_byte(value)

    def poll_host_bridge(self) -> int:
        if self.host_bridge is None:
            return 0
        incoming = self.host_bridge.poll_rx()
        if not incoming:
            return 0
        self.ingest_rx_stream(incoming)
        return len(incoming)
