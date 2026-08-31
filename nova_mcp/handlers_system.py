"""System and core CPU/memory MCP handlers."""

from __future__ import annotations

import contextlib
import io
import json
import shutil
from pathlib import Path
from typing import Any, List

from .parsing import parse_bool, parse_hex_bytes_arg, parse_int_arg, parse_optional_int, parse_register_arg


def handle_init_emulator(*, initialize_emulator, state) -> str:
    initialize_emulator()
    memory = state["memory"]
    gfx = state["gfx"]
    return json.dumps(
        {
            "status": "initialized",
            "memory_size": memory.size,
            "screen_width": gfx.width,
            "screen_height": gfx.height,
            "registers": "R0-R9 (8-bit), P0-P9 (16-bit)",
        }
    )


def handle_load_program(args, *, ensure_emulator, state, base_dir: Path) -> str:
    ensure_emulator()
    program_path = Path(args["program_path"])
    if not program_path.is_absolute():
        program_path = base_dir / program_path

    if not program_path.exists():
        return json.dumps({"error": f"File not found: {program_path}"})

    try:
        entry_point = state["memory"].load(str(program_path))
        state["program_path"] = program_path
        state["cpu"].pc = entry_point
        state["cpu"].halted = False
        state["cycle_count"] = 0
        state["debugger"] = None
        return json.dumps(
            {
                "status": "loaded",
                "program_path": str(program_path),
                "entry_point": f"0x{entry_point:04X}",
                "pc": f"0x{state['cpu'].pc:04X}",
            }
        )
    except Exception as exc:
        return json.dumps({"error": f"Failed to load program: {exc}"})


def handle_assemble(args, *, ensure_emulator, assembler_module, base_dir: Path) -> str:
    ensure_emulator()
    source_path = Path(args["source_path"])
    output_path_arg = args.get("output_path")

    if not source_path.is_absolute():
        source_path = base_dir / source_path

    if not source_path.exists():
        return json.dumps({"error": f"File not found: {source_path}"})

    if output_path_arg is None:
        output_path = source_path.with_suffix(".bin")
    else:
        output_path = Path(output_path_arg)
        if not output_path.is_absolute():
            output_path = base_dir / output_path

    try:
        assembler = assembler_module.Assembler(log=None, trace=False)
        success = assembler.assemble(str(source_path))
        if not success:
            return json.dumps({"error": "Assembly failed - check syntax"})

        generated_output = source_path.with_suffix(".bin")
        generated_org = source_path.with_suffix(".org")
        generated_sym = source_path.with_suffix(".sym")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        if generated_output.resolve() != output_path.resolve():
            shutil.move(str(generated_output), str(output_path))

        output_org = output_path.with_suffix(".org")
        output_sym = output_path.with_suffix(".sym")
        if generated_org.exists() and generated_org.resolve() != output_org.resolve():
            shutil.move(str(generated_org), str(output_org))
        if generated_sym.exists() and generated_sym.resolve() != output_sym.resolve():
            shutil.move(str(generated_sym), str(output_sym))

        return json.dumps({"status": "assembled", "source": str(source_path), "output": str(output_path)})
    except Exception as exc:
        import traceback

        return json.dumps({"error": f"Assembly failed: {exc}", "traceback": traceback.format_exc()})


def handle_cpu_step(args, *, ensure_emulator, state) -> str:
    ensure_emulator()
    try:
        count = parse_int_arg(args.get("count", 1), "count", minimum=0)
    except ValueError as exc:
        return json.dumps({"error": str(exc)})

    cpu = state["cpu"]
    old_pc = cpu.pc
    for _ in range(count):
        if cpu.halted:
            break
        cpu.step()
        state["cycle_count"] += 1

    return json.dumps(
        {
            "status": "stepped",
            "cycles": count,
            "old_pc": f"0x{old_pc:04X}",
            "new_pc": f"0x{cpu.pc:04X}",
            "halted": cpu.halted,
            "total_cycles": state["cycle_count"],
        }
    )


def handle_cpu_run(args, *, ensure_emulator, state) -> str:
    ensure_emulator()
    try:
        cycles = parse_int_arg(args.get("cycles", 10000), "cycles", minimum=0)
    except ValueError as exc:
        return json.dumps({"error": str(exc)})

    cpu = state["cpu"]
    old_pc = cpu.pc
    cycle_count = 0
    for _ in range(cycles):
        if cpu.halted:
            break
        cpu.step()
        cycle_count += 1
        state["cycle_count"] += 1

    return json.dumps(
        {
            "status": "ran",
            "cycles_executed": cycle_count,
            "old_pc": f"0x{old_pc:04X}",
            "final_pc": f"0x{cpu.pc:04X}",
            "halted": cpu.halted,
            "total_cycles": state["cycle_count"],
        }
    )


def handle_cpu_halt(*, ensure_emulator, state) -> str:
    ensure_emulator()
    state["cpu"].halted = True
    return json.dumps({"status": "halted"})


def handle_cpu_reset(*, ensure_emulator, state) -> str:
    ensure_emulator()
    cpu = state["cpu"]
    cpu.pc = 0x0000
    cpu.halted = False
    for index in range(10):
        cpu.Rregisters[index] = 0
        cpu.Pregisters[index] = 0
    cpu.Pregisters[8] = 0xFFFF
    cpu.Pregisters[9] = 0xFFFF
    state["cycle_count"] = 0
    return json.dumps({"status": "reset", "pc": "0x0000"})


def handle_clear_memory(*, ensure_emulator, state) -> str:
    ensure_emulator()
    mem = state["memory"]
    mem.reset()
    return json.dumps({"status": "memory cleared", "size": mem.size, "bytes_cleared": mem.size})


def handle_full_reset(*, ensure_emulator, state) -> str:
    ensure_emulator()
    cpu = state["cpu"]
    cpu.pc = 0x0000
    cpu.halted = False
    for index in range(10):
        cpu.Rregisters[index] = 0
        cpu.Pregisters[index] = 0
    cpu.Pregisters[8] = 0xFFFF
    cpu.Pregisters[9] = 0xFFFF
    for index in range(12):
        cpu.flags[index] = 0

    mem = state["memory"]
    mem.reset()

    gfx = state["gfx"]
    gfx.screen.fill(0)
    gfx.layer_0.fill(0)
    for layer in gfx.background_layers:
        layer.fill(0)
    for layer in gfx.sprite_layers:
        layer.fill(0)
    gfx.layers_dirty = False

    sound = state["sound"]
    try:
        sound.sstop()
        sound.SA = 0
        sound.SF = 0
        sound.SV = 0
        sound.SW = 0
        for index in range(len(sound.sound_registers)):
            sound.sound_registers[index] = 0
    except Exception as exc:
        import sys

        print(f"[MCP] Warning during sound reset: {exc}", file=sys.stderr)

    kbd = state["kbd"]
    if kbd.cpu:
        kbd.cpu.key_buffer.clear()
    for index in range(4):
        cpu.keyboard[index] = 0

    state["cycle_count"] = 0
    state["program_path"] = None
    state["running"] = False
    state["debugger"] = None

    return json.dumps(
        {
            "status": "full system reset complete",
            "components_reset": ["cpu", "memory", "graphics", "sound", "keyboard"],
            "pc": "0x0000",
            "sp": "0xFFFF",
            "memory_cleared": mem.size,
        }
    )


def handle_get_cpu_state(*, ensure_emulator, state) -> str:
    ensure_emulator()
    cpu = state["cpu"]
    return json.dumps(
        {
            "pc": f"0x{cpu.pc:04X}",
            "halted": cpu.halted,
            "cycles": state["cycle_count"],
            "r_registers": [f"0x{register:02X}" for register in cpu.Rregisters[:10]],
            "p_registers": [f"0x{register:04X}" for register in cpu.Pregisters[:10]],
            "flags": {
                "Z": bool(cpu.flags[7]),
                "C": bool(cpu.flags[6]),
                "S": bool(cpu.flags[1]),
                "O": bool(cpu.flags[2]),
                "I": bool(cpu.flags[5]),
            },
            "sp": f"0x{cpu.Pregisters[8]:04X}",
            "fp": f"0x{cpu.Pregisters[9]:04X}",
        }
    )


def handle_set_register(args, *, ensure_emulator, state) -> str:
    ensure_emulator()
    try:
        register, index = parse_register_arg(args["register"])
        value = parse_int_arg(args["value"], "value")
    except (KeyError, ValueError) as exc:
        return json.dumps({"error": str(exc)})

    cpu = state["cpu"]
    if register == "PC":
        cpu.pc = value & 0xFFFF
    elif register.startswith("R"):
        cpu.Rregisters[index] = value & 0xFF
    else:
        cpu.Pregisters[index] = value & 0xFFFF

    formatted = f"0x{value & 0xFFFF:04X}" if register == "PC" or register.startswith("P") else f"0x{value & 0xFF:02X}"
    return json.dumps({"status": "set", "register": register, "value": formatted})


def handle_read_memory(args, *, ensure_emulator, state) -> str:
    ensure_emulator()
    memory = state["memory"]
    try:
        address = parse_int_arg(args.get("address"), "address", minimum=0, maximum=memory.size - 1)
        size = parse_int_arg(args.get("size"), "size", minimum=0, maximum=memory.size)
    except ValueError as exc:
        return json.dumps({"error": str(exc)})

    if address + size > memory.size:
        return json.dumps({"error": "address + size exceeds memory bounds"})

    format_type = args.get("format", "hex")
    data = [memory.read_byte(address + offset) for offset in range(size)]
    if format_type == "hex":
        return json.dumps({"address": f"0x{address:04X}", "size": size, "data": "".join(f"{byte:02X}" for byte in data)})
    if format_type == "bytes":
        return json.dumps({"address": f"0x{address:04X}", "size": size, "data": data})
    if format_type == "ascii":
        ascii_str = "".join(chr(byte) if 32 <= byte < 127 else "." for byte in data)
        return json.dumps({"address": f"0x{address:04X}", "size": size, "data": ascii_str})
    if format_type == "words":
        words = []
        for index in range(0, len(data), 2):
            if index + 1 < len(data):
                word = data[index] | (data[index + 1] << 8)
                words.append(f"0x{word:04X}")
        return json.dumps({"address": f"0x{address:04X}", "data": words})
    return json.dumps({"error": f"Unknown format: {format_type}"})


def handle_write_memory(args, *, ensure_emulator, state) -> str:
    ensure_emulator()
    memory = state["memory"]
    try:
        address = parse_int_arg(args.get("address"), "address", minimum=0, maximum=memory.size - 1)
    except ValueError as exc:
        return json.dumps({"error": str(exc)})

    data_str = args.get("data")
    if not isinstance(data_str, str):
        return json.dumps({"error": "data must be a string"})

    try:
        data = data_str[1:].encode("ascii") if data_str.startswith("@") else bytes.fromhex(data_str)
    except UnicodeEncodeError:
        return json.dumps({"error": "ASCII data must contain only ASCII characters"})
    except ValueError as exc:
        return json.dumps({"error": f"Invalid data payload: {exc}"})

    if address + len(data) > memory.size:
        return json.dumps({"error": "address + data size exceeds memory bounds"})

    for offset, byte in enumerate(data):
        memory.write(address + offset, byte)

    return json.dumps(
        {
            "status": "written",
            "address": f"0x{address:04X}",
            "size": len(data),
            "data": data_str[:50] + ("..." if len(data_str) > 50 else ""),
        }
    )


def handle_disassemble(args, *, ensure_emulator, state, disassembler_module) -> str:
    ensure_emulator()
    start_addr = parse_int_arg(args.get("start_addr", 0x0000), "start_addr") & 0xFFFF
    num_instructions = max(1, parse_int_arg(args.get("num_instructions", 100), "num_instructions", minimum=0))

    memory = state["memory"]
    bytecode = bytes(memory.read_byte(index) for index in range(0x10000))
    opcode_map, register_map = disassembler_module.create_reverse_maps()

    lines: List[str] = []
    pc = start_addr
    for _ in range(num_instructions):
        if pc >= len(bytecode):
            break
        opcode = bytecode[pc]
        if opcode in opcode_map:
            mnemonic, operands, size = disassembler_module.disassemble_instruction_new(bytecode, pc, opcode_map, register_map)
            size = max(1, int(size))
            instruction_bytes = bytecode[pc : pc + size]
            hex_dump = " ".join(f"{byte:02X}" for byte in instruction_bytes)
            operand_str = ", ".join(operands) if operands else ""
            lines.append(f"{pc:04X}: {hex_dump:<15} {f'{mnemonic} {operand_str}'.strip()}")
            pc += size
        else:
            lines.append(f"{pc:04X}: {opcode:02X}              DB 0x{opcode:02X}")
            pc += 1
        if pc >= 0x10000:
            break

    return json.dumps(
        {
            "start_addr": f"0x{start_addr:04X}",
            "num_instructions": num_instructions,
            "decoded_instructions": len(lines),
            "assembly": "\n".join(lines),
        }
    )


def handle_memory_dump(args, *, ensure_emulator, state) -> str:
    ensure_emulator()
    start_addr = args.get("start_addr", 0x0000)
    size = args.get("size", 256)
    memory = state["memory"]

    dump = []
    for offset in range(0, size, 16):
        addr = start_addr + offset
        line_data = [memory.read_byte(addr + inner) for inner in range(16) if addr + inner < 0x10000]
        hex_part = " ".join(f"{byte:02X}" for byte in line_data)
        ascii_part = "".join(chr(byte) if 32 <= byte < 127 else "." for byte in line_data)
        dump.append(f"0x{addr:04X}: {hex_part:<48} {ascii_part}")

    return json.dumps({"start_addr": f"0x{start_addr:04X}", "size": size, "dump": "\n".join(dump)})


def handle_breakpoint_set(args, *, ensure_emulator, state) -> str:
    ensure_emulator()
    try:
        address = parse_int_arg(args["address"], "address", minimum=0, maximum=0xFFFF)
    except (KeyError, ValueError) as exc:
        return json.dumps({"error": str(exc)})

    cpu = state["cpu"]
    if not hasattr(cpu, "breakpoints"):
        cpu.breakpoints = set()
    cpu.breakpoints.add(address)
    return json.dumps({"status": "breakpoint_set", "address": f"0x{address:04X}", "total_breakpoints": len(cpu.breakpoints)})


def handle_breakpoint_clear(args, *, ensure_emulator, state) -> str:
    ensure_emulator()
    cpu = state["cpu"]
    addr = args.get("address")
    if not hasattr(cpu, "breakpoints"):
        cpu.breakpoints = set()
    if addr is None:
        cpu.breakpoints.clear()
        return json.dumps({"status": "breakpoints_cleared", "total_breakpoints": 0})
    try:
        address = parse_int_arg(addr, "address", minimum=0, maximum=0xFFFF)
    except ValueError as exc:
        return json.dumps({"error": str(exc)})
    cpu.breakpoints.discard(address)
    return json.dumps({"status": "breakpoint_cleared", "address": f"0x{address:04X}", "total_breakpoints": len(cpu.breakpoints)})


def handle_breakpoint_list(*, ensure_emulator, state) -> str:
    ensure_emulator()
    cpu = state["cpu"]
    breakpoints = sorted(f"0x{address:04X}" for address in getattr(cpu, "breakpoints", set()))
    return json.dumps({"breakpoints": breakpoints, "count": len(breakpoints)})


def handle_cpu_run_until(args, *, ensure_emulator, state) -> str:
    ensure_emulator()
    try:
        target = parse_int_arg(args.get("address"), "address", minimum=0, maximum=0xFFFF)
        max_cycles = parse_int_arg(args.get("max_cycles", 100000), "max_cycles", minimum=0)
    except ValueError as exc:
        return json.dumps({"error": str(exc)})

    cpu = state["cpu"]
    cycles = 0
    start_pc = cpu.pc
    while cycles < max_cycles and not cpu.halted and cpu.pc != target:
        cpu.step()
        cycles += 1
        state["cycle_count"] += 1
        if hasattr(cpu, "breakpoints") and cpu.pc in cpu.breakpoints:
            break
    return json.dumps(
        {
            "status": "ran_until",
            "start_pc": f"0x{start_pc:04X}",
            "final_pc": f"0x{cpu.pc:04X}",
            "cycles": cycles,
            "halted": cpu.halted,
            "hit_breakpoint": bool(getattr(cpu, "breakpoints", set()) and cpu.pc in cpu.breakpoints),
            "reached_target": cpu.pc == target,
        }
    )


def handle_assert_memory(args, *, ensure_emulator, state) -> str:
    ensure_emulator()
    memory = state["memory"]
    try:
        address = parse_int_arg(args.get("address"), "address", minimum=0, maximum=memory.size - 1)
        _, expected_bytes = parse_hex_bytes_arg(args.get("expected"), "expected")
    except ValueError as exc:
        return json.dumps({"error": str(exc)})

    if address + len(expected_bytes) > memory.size:
        return json.dumps({"error": "address + expected size exceeds memory bounds"})

    actual = bytes(memory.read_byte(address + index) for index in range(len(expected_bytes)))
    diff = [
        {"offset": index, "expected": f"{expected_bytes[index]:02X}", "actual": f"{actual[index]:02X}"}
        for index in range(len(expected_bytes))
        if expected_bytes[index] != actual[index]
    ]
    return json.dumps(
        {
            "status": "assert_memory",
            "address": f"0x{address:04X}",
            "length": len(expected_bytes),
            "passed": actual == expected_bytes,
            "diff": diff,
        }
    )


def handle_memory_search(args, *, ensure_emulator, state) -> str:
    ensure_emulator()
    memory = state["memory"]
    try:
        pattern_hex, pattern = parse_hex_bytes_arg(args.get("pattern"), "pattern")
        start = parse_int_arg(args.get("start", 0), "start", minimum=0, maximum=memory.size - 1)
        end = parse_int_arg(args.get("end", memory.size - 1), "end", minimum=0, maximum=memory.size - 1)
        max_results = parse_int_arg(args.get("max_results", 16), "max_results", minimum=1)
    except ValueError as exc:
        return json.dumps({"error": str(exc)})

    if end < start:
        return json.dumps({"error": "end must be >= start"})

    data = bytes(memory.read_bytes_direct(start, end - start + 1))
    matches: List[int] = []
    idx = 0
    while idx <= len(data) - len(pattern) and len(matches) < max_results:
        if data[idx : idx + len(pattern)] == pattern:
            matches.append(start + idx)
            idx += len(pattern)
        else:
            idx += 1
    return json.dumps({"pattern": pattern_hex.upper(), "start": f"0x{start:04X}", "end": f"0x{end:04X}", "matches": [f"0x{match:04X}" for match in matches]})


def handle_run_until_memory(args, *, ensure_emulator, state) -> str:
    ensure_emulator()
    memory = state["memory"]
    try:
        address = parse_int_arg(args.get("address"), "address", minimum=0, maximum=memory.size - 1)
        _, expected = parse_hex_bytes_arg(args.get("value"), "value")
        max_cycles = parse_int_arg(args.get("max_cycles", 100000), "max_cycles", minimum=0)
    except ValueError as exc:
        return json.dumps({"error": str(exc)})

    if address + len(expected) > memory.size:
        return json.dumps({"error": "address + value size exceeds memory bounds"})

    cpu = state["cpu"]
    cycles = 0
    start_pc = cpu.pc

    def read_slice(addr: int, count: int) -> bytes:
        # memory.read() is a legacy alias that wraps bytes in np.array with the
        # default int64 dtype, so tobytes() would emit 8 bytes per value. Use
        # read_bytes_direct(), which returns plain ints 0-255.
        return bytes(memory.read_bytes_direct(addr, count))

    while cycles < max_cycles and not cpu.halted:
        if read_slice(address, len(expected)) == expected:
            break
        cpu.step()
        cycles += 1
        state["cycle_count"] += 1

    return json.dumps(
        {
            "status": "ran_until_memory",
            "start_pc": f"0x{start_pc:04X}",
            "final_pc": f"0x{cpu.pc:04X}",
            "cycles": cycles,
            "matched": read_slice(address, len(expected)) == expected,
        }
    )


def handle_set_flags(args, *, ensure_emulator, state) -> str:
    ensure_emulator()
    flags_map = args.get("flags", {})
    cpu = state["cpu"]
    letter_to_index = {"E": 11, "A": 10, "H": 9, "P": 8, "Z": 7, "C": 6, "I": 5, "D": 4, "B": 3, "O": 2, "S": 1, "T": 0}
    updated = {}
    for key, value in flags_map.items():
        normalized = str(key).upper()
        if normalized in letter_to_index:
            index = letter_to_index[normalized]
            cpu.flags[index] = 1 if int(value) != 0 else 0
            updated[normalized] = cpu.flags[index]
    return json.dumps({"status": "flags_set", "updated": updated})


def handle_timer_control(args, *, ensure_emulator, state) -> str:
    ensure_emulator()
    cpu = state["cpu"]
    try:
        parsed_values = {
            name: parse_int_arg(args[name], name, minimum=0, maximum=0xFFFF)
            for name in ("TT", "TM", "TC", "TS")
            if name in args
        }
    except ValueError as exc:
        return json.dumps({"error": str(exc)})

    for name, index in (("TT", 0), ("TM", 1), ("TC", 2), ("TS", 3)):
        if name in parsed_values:
            cpu.timer[index] = parsed_values[name]
    return json.dumps({"status": "timer_set", "timer": {"TT": cpu.timer[0], "TM": cpu.timer[1], "TC": cpu.timer[2], "TS": cpu.timer[3]}})


def handle_disassemble_program(args, *, ensure_emulator, state, disassembler_module) -> str:
    ensure_emulator()
    program = state.get("program_path")
    if not program:
        return json.dumps({"error": "No program loaded"})

    class _Args:
        def __init__(self, values):
            self.start = parse_optional_int(values.get("start"))
            self.end = parse_optional_int(values.get("end"))
            self.show_hex = parse_bool(values.get("show_hex"), True)
            self.show_addresses = parse_bool(values.get("show_addresses"), True)
            self.filter_instructions = values.get("filter_instructions")
            self.exclude_instructions = values.get("exclude_instructions")
            self.format = "text"
            self.output = None
            self.quiet = True
            self.interactive = False
            self.analyze_dataflow = False
            self.analyze_liveness = False
            self.analyze_functions = False
            self.analyze_loops = False
            self.analyze_deadcode = False
            self.analyze_security = False
            self.analyze_patterns = False

    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer):
            disassembler_module.disassemble(str(program), _Args(args))
    except Exception as exc:
        return json.dumps({"error": f"Disassembly failed: {exc}"})

    return json.dumps({"assembly": buffer.getvalue()[:100000]})