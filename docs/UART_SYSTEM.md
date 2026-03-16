# Nova-16 UART System

## Overview

The Nova-16 UART is implemented as a dedicated device module in `nova_uart.py` and integrated into CPU execution and interrupt handling.

It provides:

- 8-bit data path for TX/RX.
- Status/control semantics compatible with existing `SER*` instructions.
- RX/TX event-driven interrupt pending behavior.
- Two protocol modes:
  - Raw byte stream mode.
  - Framed mode (start byte + length + payload + checksum).
- Host bridge support:
  - Local terminal bridge.
  - TCP socket bridge in client or server mode.

## Source Layout

- `nova_uart.py`
  - `UARTHostBridge`: abstract host transport interface.
  - `LocalTerminalBridge`: stdout TX + injected RX queue.
  - `TCPSocketBridge`: remote UART bridge over TCP.
  - `TCPServerBridge`: listening TCP UART bridge for inbound peers.
  - `SerialRegisterView`: compatibility adapter for `cpu.serial[0..1]`.
  - `NovaUART`: main UART device implementation.
- `nova_cpu.py`
  - CPU owns `self.uart` and exposes compatibility `self.serial` view.
  - UART pending interrupt state is included in CPU interrupt scan path.
  - CPU polls host bridge each cycle (`step`) for inbound data.
- `instructions.py`
  - `SERIN`, `SEROUT`, `SERSTAT`, `SERCTRL` dispatch directly to UART methods.

## Register Model

The UART device tracks these logical fields:

- Data register (`8-bit`)
- Status flags (`8-bit` view from `read_status_flags`)
- Control bits (`7-bit` stored control)
- Interrupt pending bit (`bit 7`, internal pending state)

### Status Bits

- `0x01`: RX data available
- `0x02`: TX complete
- `0x04`: Overrun (reserved for future handling)
- `0x08`: Frame error (reserved for future handling)
- `0x10`: Checksum error (framed mode parse error)
- `0x80`: Interrupt pending

### Control Bits

- `0x01`: UART interrupt enable
- `0x04`: Framed mode enable

## CPU Integration Details

CPU constructor now supports optional UART injection:

- `CPU(memory, gfx, keyboard=None, sound_system=None, uart_device=None, stack_size=65535)`

Behavior:

- If `uart_device` is omitted, CPU creates `NovaUART()`.
- `cpu.serial` remains available via `SerialRegisterView` for legacy code/tests.
- UART sets callback to CPU `_refresh_pending_interrupt_sources`, so RX/TX events can immediately gate pending interrupt checks.
- CPU interrupt logic checks `self.uart.pending_interrupt` for serial IRQ source.

## Instruction Semantics

Serial opcodes are unchanged from ISA perspective:

- `SERIN` (`0xA2`): reads UART data into destination operand.
- `SEROUT` (`0xA3`): writes operand value to UART TX.
- `SERSTAT` (`0xA4`): returns status low bits (`RX available`, `TX complete`).
- `SERCTRL` (`0xA5`): updates UART control bits and CPU serial interrupt enable (`interrupts[1]`).

## Protocol Modes

### Raw Mode

Default mode. Bytes are pushed directly into RX FIFO and read with `SERIN`.

### Framed Mode

Frame format:

- `START` byte: `0x7E`
- `LENGTH` byte: payload length (`0..255`)
- `PAYLOAD` bytes
- `CHECKSUM` byte: `sum(payload) & 0xFF`

On valid frame:

- Payload is appended to `received_frames`.
- Payload bytes are pushed into RX FIFO.

On checksum mismatch:

- Checksum error bit is set.
- Interrupt pending is asserted if IRQ is enabled.

## Host Bridge Usage

### Local Terminal Bridge

`LocalTerminalBridge` writes TX bytes to stdout and allows RX injection:

- `inject_input(b"...")`
- `poll_rx()`

### TCP Socket Bridge

`TCPSocketBridge(host, port, timeout=0.01)` sends/receives bytes over a non-blocking TCP connection as a client.

`TCPServerBridge(host, port, timeout=0.01)` binds and listens for a single remote TCP peer, allowing Nova-16 to host the UART endpoint.

Use these for remote consoles, host tools, or file transfer protocols over UART. A typical two-instance setup is one Nova-16 process running TCP server mode and a second Nova-16 process running TCP client mode against the same host/port.

### Shared Configuration

`UARTBridgeConfig` carries the TCP role in addition to the transport mode:

- `mode="tcp", tcp_role="client"`: connect to a listening peer.
- `mode="tcp", tcp_role="server"`: listen for an inbound peer and exchange bytes once connected.

CLI support:

```powershell
py -3.13 nova.py --uart-bridge tcp --uart-tcp-role server --uart-host 127.0.0.1 --uart-port 2323
py -3.13 nova.py --uart-bridge tcp --uart-tcp-role client --uart-host 127.0.0.1 --uart-port 2323
```

## Assembly Usage

### Minimal Serial TX/RX Example

```asm
ORG 0x1000

START:
    SERCTRL 0x01      ; enable UART interrupt control bit
    SEROUT 0x41       ; transmit 'A'
    SERSTAT R1        ; read status
    AND R1, 0x02      ; check TX complete bit
    SERIN R2          ; read data path
    HLT
```

### Integration Test Program

The repository includes:

- `asm/uart_integration_test.asm`

This test sets:

- `P0 = 0xBEEF` on pass
- `P0 = 0xDEAD` on fail

## Build and Run the Integration Test

```powershell
py -3.13 nova_assembler.py asm/uart_integration_test.asm
py -3.13 nova.py --headless asm/uart_integration_test.bin --cycles 500
```

Expected success marker in output:

- `P0-P9` includes `0xBEEF` in `P0`.

## Python Usage

### Use default UART

```python
import nova_cpu as cpu
import nova_memory as ram
import nova_gfx as gpu

mem = ram.Memory()
gfx = gpu.GFX()
proc = cpu.CPU(mem, gfx)
```

### Inject custom UART/bridge

```python
import nova_cpu as cpu
import nova_memory as ram
import nova_gfx as gpu
import nova_uart as uart

mem = ram.Memory()
gfx = gpu.GFX()
bridge = uart.LocalTerminalBridge()
device = uart.NovaUART(host_bridge=bridge)
proc = cpu.CPU(mem, gfx, uart_device=device)
```

## Test Coverage

UART unit coverage is in:

- `tests/unit/test_uart.py`

Coverage includes:

- Initialization/reset.
- Control and status handling.
- RX/TX paths.
- Raw and framed protocol behavior.
- Host bridge polling.
- Legacy serial register compatibility view.
- CPU pending-interrupt integration callback.

## Notes and Compatibility

- `cpu.serial` is preserved for compatibility and forwards to the UART implementation.
- `SERSTAT` reports low status bits only (`0x01`, `0x02`), so assembly checks should generally mask bits when asserting expected status.
- Framed mode is intentionally simple and intended as a base for structured UART payload protocols (including file transfer framing).