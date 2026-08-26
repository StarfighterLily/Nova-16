"""Astrid MCP handlers.

Mirrors the NoBASIC handler contract: compile an Astrid source file to
assembly and (optionally) binary in-process, with optional auto-load of
the resulting binary into the emulator.
"""

from __future__ import annotations

import json
from pathlib import Path


def _assemble_in_process(assembly_file: Path, verbose_flag: bool, emit) -> bool:
    """Assemble generated assembly in-process; returns True on success."""
    import nova_assembler as assembler_module

    assembler = assembler_module.Assembler(log=None, trace=False)
    return bool(assembler.assemble(str(assembly_file)))


def handle_astrid_compile(
    args,
    *,
    has_astrid: bool,
    compile_astrid,
    ensure_emulator,
    state,
    base_dir: Path,
) -> str:
    if not has_astrid or compile_astrid is None:
        return json.dumps({"error": "Astrid compiler not available. Check installation in astrid/ directory."})

    source_path_arg = args.get("source_path")
    if not isinstance(source_path_arg, str):
        return json.dumps({"error": "source_path must be a string"})

    output_path_arg = args.get("output_path")
    verbose = bool(args.get("verbose", False))
    auto_load = bool(args.get("auto_load", False))

    source_path = Path(source_path_arg)
    if not source_path.is_absolute():
        source_path = base_dir / source_path
    if not source_path.exists():
        return json.dumps({"error": f"Source file not found: {source_path}"})
    if source_path.suffix.lower() not in (".ast", ".as", ".astrid"):
        return json.dumps({"error": f"Source file must have .ast/.as/.astrid extension, got '{source_path.suffix}'"})

    if output_path_arg is None:
        output_path = source_path.with_suffix(".asm")
    else:
        output_path = Path(output_path_arg)
        if not output_path.is_absolute():
            output_path = base_dir / output_path

    compiler_messages: list[str] = []

    def capture_compiler_output(message: str) -> None:
        compiler_messages.append(message)

    try:
        compile_astrid(
            str(source_path),
            str(output_path),
            verbose=verbose,
            log=capture_compiler_output,
            assemble_callback=_assemble_in_process,
        )
    except Exception as exc:
        import traceback

        result = {
            "error": f"Astrid compilation failed: {exc}",
            "traceback": traceback.format_exc(),
            "source": str(source_path),
            "assembly": str(output_path),
        }
        compiler_output = "\n".join(compiler_messages).strip()
        if compiler_output:
            result["compiler_output"] = compiler_output[:100000]
        return json.dumps(result)

    binary_path = output_path.with_suffix(".bin")
    if not binary_path.exists():
        return json.dumps({
            "error": f"Binary file not created at {binary_path}",
            "assembly_created": str(output_path),
        })

    result = {
        "status": "compiled",
        "source": str(source_path),
        "assembly": str(output_path),
        "binary": str(binary_path),
    }
    if verbose and compiler_messages:
        result["compiler_output"] = "\n".join(compiler_messages)[:100000]

    if auto_load:
        ensure_emulator()
        try:
            entry_point = state["memory"].load(str(binary_path))
            state["program_path"] = binary_path
            state["cpu"].pc = entry_point
            state["cpu"].halted = False
            state["cycle_count"] = 0
            state["debugger"] = None
            result["auto_loaded"] = True
            result["entry_point"] = f"0x{entry_point:04X}"
        except Exception as exc:
            result["auto_load_error"] = str(exc)

    return json.dumps(result)

