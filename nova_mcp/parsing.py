"""Argument parsing helpers for Nova MCP handlers."""

from __future__ import annotations

from typing import Any, Dict, Optional


def parse_int_arg(
    value: Any,
    name: str,
    *,
    minimum: Optional[int] = None,
    maximum: Optional[int] = None,
) -> int:
    """Parse an integer argument with optional bounds checks."""
    try:
        parsed = int(value, 0) if isinstance(value, str) else int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer") from exc

    if minimum is not None and parsed < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    if maximum is not None and parsed > maximum:
        raise ValueError(f"{name} must be <= {maximum}")
    return parsed


def parse_register_arg(value: Any) -> tuple[str, Optional[int]]:
    """Normalize a register argument and validate supported names."""
    if not isinstance(value, str):
        raise ValueError("register must be a string")

    register = value.strip().upper()
    if register == "PC":
        return register, None

    if len(register) >= 2 and register[0] in {"R", "P"} and register[1:].isdigit():
        index = int(register[1:])
        if 0 <= index <= 9:
            return register, index

    raise ValueError(f"Unknown register: {register}")


def normalize_keyboard_key_arg(value: Any, key_mapping: Dict[str, int]) -> tuple[str, Optional[int]]:
    """Normalize MCP keyboard input to a Nova key name or raw scan code."""
    if not isinstance(value, str):
        raise ValueError("key must be a string")

    raw_key = value.strip()
    if not raw_key:
        raise ValueError("key must not be empty")

    if raw_key.lower().startswith("0x"):
        scan_code = parse_int_arg(raw_key, "key", minimum=0, maximum=0xFF)
        return f"0x{scan_code:02X}", scan_code

    if len(raw_key) == 1:
        return raw_key, None

    normalized = raw_key.lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "return": "enter",
        "esc": "escape",
        "space": " ",
        "arrowleft": "left",
        "arrowright": "right",
        "arrowup": "up",
        "arrowdown": "down",
        "left_arrow": "left",
        "right_arrow": "right",
        "up_arrow": "up",
        "down_arrow": "down",
    }
    normalized = aliases.get(normalized, normalized)

    if normalized in {"shift", "ctrl", "alt"} or normalized in key_mapping:
        return normalized, None

    raise ValueError(f"Unknown key: {raw_key}")


def parse_hex_bytes_arg(value: Any, name: str) -> tuple[str, bytes]:
    """Parse a required hex string argument, allowing embedded spaces."""
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")

    normalized = value.replace(" ", "").strip()
    if not normalized:
        raise ValueError(f"{name} must not be empty")

    try:
        return normalized.upper(), bytes.fromhex(normalized)
    except ValueError as exc:
        raise ValueError(f"Invalid hex {name}: {exc}") from exc


def parse_optional_int(value: Any) -> Optional[int]:
    """Parse an integer or return None."""
    if value is None:
        return None
    if isinstance(value, str):
        return int(value, 0)
    return int(value)


def parse_bool(value: Any, default: bool) -> bool:
    """Parse flexible bool-like arguments."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)