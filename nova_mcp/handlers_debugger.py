"""Debugger-oriented MCP handlers."""

from __future__ import annotations

import json


def handle_debugger_init(*, ensure_emulator, state, debugger_module) -> str:
    ensure_emulator()
    program = state.get("program_path")
    if not program:
        return json.dumps({"error": "No program loaded. Load a program first with load_program."})

    cpu = state["cpu"]
    debugger = debugger_module.NovaDebugger(state["cpu"], state["memory"], state["gfx"], state["sound"], str(program))
    state["debugger"] = debugger
    return json.dumps({"status": "debugger_initialized", "program": str(program), "pc": f"0x{cpu.pc:04X}", "symbols_loaded": len(debugger.symbol_table) > 0, "symbol_count": len(debugger.symbol_table)})


def handle_debugger_step(args, *, ensure_emulator, state, disassembler_module, debugger_module) -> str:
    ensure_emulator()
    count = args.get("count", 1)
    show_disasm = args.get("show_disasm", True)
    show_regs = args.get("show_regs", True)
    cpu = state["cpu"]
    debugger = state.get("debugger")
    memory = state["memory"]
    if not debugger:
        handle_debugger_init(ensure_emulator=ensure_emulator, state=state, debugger_module=debugger_module)
        debugger = state.get("debugger")
        if not debugger:
            return json.dumps({"error": "Failed to initialize debugger"})

    result = {"status": "stepped", "steps": count, "instructions": []}
    for _ in range(count):
        if cpu.halted:
            result["halted"] = True
            break
        old_pc = cpu.pc
        cpu.step()
        state["cycle_count"] += 1
        step_info = {"pc": f"0x{old_pc:04X}"}
        if show_disasm:
            try:
                opcode = memory.memory[old_pc]
                if opcode in debugger.opcode_map:
                    mnemonic, operands, _ = disassembler_module.disassemble_instruction_new(memory.memory, old_pc, debugger.opcode_map, debugger.register_map)
                    operand_str = ", ".join(operands) if operands else ""
                    step_info["instruction"] = f"{mnemonic} {operand_str}".strip()
            except Exception:
                pass
        result["instructions"].append(step_info)

    if show_regs:
        result["registers"] = {"pc": f"0x{cpu.pc:04X}", "r": [f"0x{register:02X}" for register in cpu.Rregisters[:10]], "p": [f"0x{register:04X}" for register in cpu.Pregisters[:10]]}
    return json.dumps(result)


def handle_debugger_run_until_breakpoint(args, *, ensure_emulator, state, debugger_module) -> str:
    ensure_emulator()
    max_cycles = args.get("max_cycles", 100000)
    cpu = state["cpu"]
    debugger = state.get("debugger")
    if not debugger:
        handle_debugger_init(ensure_emulator=ensure_emulator, state=state, debugger_module=debugger_module)
        debugger = state.get("debugger")
    if not debugger:
        return json.dumps({"error": "Failed to initialize debugger"})

    start_pc = cpu.pc
    cycles = 0
    breakpoint_hit = None
    while cycles < max_cycles and not cpu.halted:
        if cpu.pc in debugger.breakpoints:
            breakpoint_hit = f"0x{cpu.pc:04X}"
            break
        cpu.step()
        cycles += 1
        state["cycle_count"] += 1
    return json.dumps({"status": "ran_until_breakpoint", "start_pc": f"0x{start_pc:04X}", "final_pc": f"0x{cpu.pc:04X}", "cycles": cycles, "halted": cpu.halted, "breakpoint_hit": breakpoint_hit})


def handle_debugger_print_state(args, *, ensure_emulator, state, disassembler_module) -> str:
    ensure_emulator()
    show_stack = args.get("show_stack", True)
    stack_entries = args.get("stack_entries", 16)
    cpu = state["cpu"]
    memory = state["memory"]
    debugger = state.get("debugger")
    if not debugger:
        return json.dumps({"error": "Debugger not initialized. Call debugger_init first."})

    result = {
        "pc": f"0x{cpu.pc:04X}",
        "halted": cpu.halted,
        "cycles": state["cycle_count"],
        "r_registers": [f"0x{register:02X}" for register in cpu.Rregisters[:10]],
        "p_registers": [f"0x{register:04X}" for register in cpu.Pregisters[:10]],
        "flags": {"Z": int(cpu.flags[7]), "C": int(cpu.flags[6]), "S": int(cpu.flags[1]), "O": int(cpu.flags[2]), "I": int(cpu.flags[5]), "D": int(cpu.flags[4]), "B": int(cpu.flags[3])},
    }

    try:
        opcode = memory.memory[cpu.pc]
        if opcode in debugger.opcode_map:
            mnemonic, operands, size = disassembler_module.disassemble_instruction_new(memory.memory, cpu.pc, debugger.opcode_map, debugger.register_map)
            operand_str = ", ".join(operands) if operands else ""
            result["current_instruction"] = f"{mnemonic} {operand_str}".strip()
            result["instruction_size"] = size
    except Exception:
        pass

    if show_stack:
        sp = cpu.Pregisters[8]
        stack_data = []
        for index in range(stack_entries):
            addr = (int(sp) + index * 2) & 0xFFFF
            try:
                value = memory.read_word(addr)
                stack_data.append({"offset": index, "address": f"0x{addr:04X}", "value": f"0x{value:04X}"})
            except Exception:
                break
        result["stack"] = stack_data
    return json.dumps(result)


def handle_debugger_get_symbol_table(*, ensure_emulator, state) -> str:
    ensure_emulator()
    debugger = state.get("debugger")
    if not debugger:
        return json.dumps({"error": "Debugger not initialized. Call debugger_init first."})
    symbols = {key: value for key, value in debugger.symbol_table.items()}
    reverse_symbols = {f"0x{key:04X}": value for key, value in debugger.reverse_symbol_table.items()}
    return json.dumps({"symbols": symbols, "reverse_symbols": reverse_symbols, "total": len(debugger.symbol_table)})


def handle_debugger_inspect_instruction(args, *, ensure_emulator, state, disassembler_module, debugger_module) -> str:
    ensure_emulator()
    address = args.get("address")
    cpu = state["cpu"]
    memory = state["memory"]
    debugger = state.get("debugger")
    if not debugger:
        handle_debugger_init(ensure_emulator=ensure_emulator, state=state, debugger_module=debugger_module)
        debugger = state.get("debugger")

    if address is None:
        address = cpu.pc
    address = int(address) & 0xFFFF
    if address >= len(memory.memory):
        return json.dumps({"error": f"Address 0x{address:04X} is beyond memory bounds"})

    result = {"address": f"0x{address:04X}"}
    try:
        opcode = memory.memory[address]
        is_string, string_length = disassembler_module.is_string_data(memory.memory, address)
        if is_string and string_length > 1:
            result["type"] = "string"
            result["length"] = string_length
            result["directive"] = disassembler_module.format_string_data(memory.memory, address, string_length)
        elif opcode in debugger.opcode_map:
            mnemonic, operands, size = disassembler_module.disassemble_instruction_new(memory.memory, address, debugger.opcode_map, debugger.register_map)
            result["type"] = "instruction"
            result["mnemonic"] = mnemonic
            result["operands"] = operands
            result["size"] = size
            result["hex"] = " ".join(f"{memory.memory[address + offset]:02X}" for offset in range(size))
        else:
            result["type"] = "data"
            result["byte_value"] = f"0x{opcode:02X}"
            result["hex"] = f"{opcode:02X}"
        if address in debugger.reverse_symbol_table:
            result["symbol"] = debugger.reverse_symbol_table[address]
    except Exception as exc:
        result["error"] = str(exc)
    return json.dumps(result)