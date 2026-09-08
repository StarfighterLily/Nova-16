"""Astrid MCP handlers.

Mirrors the NoBASIC handler contract: compile an Astrid source file to
assembly and (optionally) binary in-process, with optional auto-load of
the resulting binary into the emulator.

NOMF compliance: the Astrid codegen always emits ``ORG 0x1000`` (and
``ORG 0x0100``/``ORG 0x0120`` when a ``timer_interrupt`` handler exists),
so the assembler produces a NOMF ``.nex`` executable as the primary
artifact.  The handler surfaces that artifact in the response and prefers
it for auto-load, falling back to the legacy ``.bin`` only when NOMF
emission is suppressed.
"""

from __future__ import annotations

import json
from pathlib import Path


def _assemble_in_process(assembly_file: Path, verbose_flag: bool, emit) -> bool:
    """Assemble generated assembly in-process; returns True on success.

    The assembler defaults to emitting both a NOMF ``.nex`` executable (the
    primary artifact for ORG'd sources) and the legacy ``.bin``/``.org``/
    ``.sym`` sidecars.  Astrid output is always ORG'd, so a ``.nex`` is
    expected alongside the ``.bin``.
    """
    import nova_assembler as assembler_module

    assembler = assembler_module.Assembler(log=None, trace=False)
    return bool(assembler.assemble(str(assembly_file)))


def _find_loadable_artifact(assembly_path: Path):
    """Return the best loadable artifact for the given assembly path.

    Prefers the NOMF ``.nex`` executable (primary artifact for ORG'd
    sources) over the legacy ``.bin`` sidecar.  Returns a 3-tuple:
    ``(load_path, artifact_kind, display_suffix)`` where ``artifact_kind``
    is ``"nomf"`` or ``"legacy"``.
    """
    nomf_path = assembly_path.with_suffix(".nex")
    if nomf_path.exists():
        return nomf_path, "nomf", ".nex"

    bin_path = assembly_path.with_suffix(".bin")
    if bin_path.exists():
        return bin_path, "legacy", ".bin"

    return None, None, None


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

    # Prefer the NOMF .nex executable (primary artifact for ORG'd sources)
    # over the legacy .bin sidecar.  The Astrid codegen always emits ORG
    # directives, so a .nex is the canonical loadable artifact.
    load_path, artifact_kind, _ = _find_loadable_artifact(output_path)
    if load_path is None:
        # Neither .nex nor .bin was produced — surface the legacy path in
        # the error for backward compatibility with existing diagnostics.
        binary_path = output_path.with_suffix(".bin")
        return json.dumps({
            "error": f"Binary file not created at {binary_path}",
            "assembly_created": str(output_path),
        })

    result = {
        "status": "compiled",
        "source": str(source_path),
        "assembly": str(output_path),
        "binary": str(load_path),
    }
    # Surface the NOMF artifact path explicitly so callers can distinguish
    # the primary (.nex) artifact from a legacy (.bin) fallback.
    if artifact_kind == "nomf":
        result["nomf"] = str(load_path)
    if verbose and compiler_messages:
        result["compiler_output"] = "\n".join(compiler_messages)[:100000]

    if auto_load:
        ensure_emulator()
        try:
            entry_point = state["memory"].load(str(load_path))
            state["program_path"] = load_path
            state["cpu"].pc = entry_point
            state["cpu"].halted = False
            state["cycle_count"] = 0
            state["debugger"] = None
            result["auto_loaded"] = True
            result["entry_point"] = f"0x{entry_point:04X}"
            result["loaded_artifact"] = artifact_kind
        except Exception as exc:
            result["auto_load_error"] = str(exc)

    return json.dumps(result)

