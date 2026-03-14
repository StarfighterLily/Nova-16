"""Graphics, keyboard, and sound MCP handlers."""

from __future__ import annotations

import base64
import io
import json

from .parsing import normalize_keyboard_key_arg, parse_int_arg


def handle_graphics_get_pixel(args, *, ensure_emulator, state) -> str:
    ensure_emulator()
    try:
        x = parse_int_arg(args["x"], "x")
        y = parse_int_arg(args["y"], "y")
        layer_value = args.get("layer")
        layer = None if layer_value is None else parse_int_arg(layer_value, "layer", minimum=0, maximum=8)
    except (KeyError, ValueError) as exc:
        return json.dumps({"error": str(exc)})

    gfx = state["gfx"]
    in_bounds = 0 <= x < gfx.width and 0 <= y < gfx.height
    if layer is not None:
        if layer == 0:
            color = int(gfx.layer_0[y, x]) if in_bounds else 0
        elif 1 <= layer <= 4:
            color = int(gfx.background_layers[layer - 1][y, x]) if in_bounds else 0
        else:
            color = int(gfx.sprite_layers[layer - 5][y, x]) if in_bounds else 0
    else:
        color = int(gfx.screen[y, x]) if in_bounds else 0
    return json.dumps({"x": x, "y": y, "color": color, "layer": layer})


def handle_graphics_get_screen(args, *, ensure_emulator, state, has_pil: bool, image_cls) -> str:
    ensure_emulator()
    format_type = args.get("format", "summary")
    gfx = state["gfx"]
    screen = gfx.screen
    if format_type == "summary":
        return json.dumps({"width": gfx.width, "height": gfx.height, "non_black_pixels": int((screen != 0).sum()), "format": "RGBA indexed"})
    if format_type == "raw":
        data = screen.flatten().tobytes()
        return json.dumps({"width": gfx.width, "height": gfx.height, "data_base64": base64.b64encode(data).decode("ascii"), "encoding": "raw uint8"})
    if format_type in {"base64", "png"}:
        try:
            if not has_pil:
                raise RuntimeError("Pillow not installed")
            image = image_cls.fromarray(screen.astype("uint8"), mode="L")
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            return json.dumps({"width": gfx.width, "height": gfx.height, "encoding": "png_base64", "png_base64": base64.b64encode(buffer.getvalue()).decode("ascii")})
        except Exception as exc:
            return json.dumps({"error": f"PNG export failed: {exc}"})
    return json.dumps({"error": f"Unknown format: {format_type}"})


def handle_graphics_set_pixel(args, *, ensure_emulator, state) -> str:
    ensure_emulator()
    try:
        x = parse_int_arg(args.get("x"), "x")
        y = parse_int_arg(args.get("y"), "y")
        color = parse_int_arg(args.get("color"), "color", minimum=0, maximum=0xFF)
        layer = parse_int_arg(args.get("layer", 0), "layer", minimum=0, maximum=8)
    except ValueError as exc:
        return json.dumps({"error": str(exc)})

    gfx = state["gfx"]
    old_vl = gfx.VL
    gfx.VL = layer
    if 0 <= x < gfx.width and 0 <= y < gfx.height:
        gfx._set_pixel_to_layer(x, y, color)
    gfx.VL = old_vl
    return json.dumps({"status": "set", "x": x, "y": y, "color": color, "layer": layer})


def handle_keyboard_inject_key(args, *, ensure_emulator, state) -> str:
    ensure_emulator()
    kbd = state["kbd"]
    try:
        key, scan_code = normalize_keyboard_key_arg(args.get("key"), kbd.key_mapping)
        count = parse_int_arg(args.get("count", 1), "count", minimum=0)
    except ValueError as exc:
        return json.dumps({"error": str(exc)})

    for _ in range(count):
        if scan_code is not None:
            state["cpu"].add_key_to_buffer(scan_code)
        else:
            kbd.press_key(key)

    response = {"status": "injected", "key": key, "count": count}
    if scan_code is not None:
        response["scan_code"] = f"0x{scan_code:02X}"
    return json.dumps(response)


def handle_keyboard_get_buffer(*, ensure_emulator, state) -> str:
    ensure_emulator()
    kbd = state["kbd"]
    try:
        status = kbd.get_buffer_status() if hasattr(kbd, "get_buffer_status") else {}
    except Exception:
        status = {}
    return json.dumps({"status": status})


def handle_graphics_export_png(args, *, ensure_emulator, state, has_pil: bool, image_cls) -> str:
    ensure_emulator()
    palette = (args.get("palette") or "grayscale").lower()
    gfx = state["gfx"]
    screen = gfx.screen.astype("uint8")
    try:
        if not has_pil:
            raise RuntimeError("Pillow not installed")
        if palette == "grayscale":
            image = image_cls.fromarray(screen, mode="L")
        elif palette == "heatmap":
            import numpy as np

            red = np.clip(screen * 2, 0, 255).astype("uint8")
            green = np.clip(255 - abs(screen - 128) * 2, 0, 255).astype("uint8")
            blue = (255 - screen).astype("uint8")
            image = image_cls.fromarray(np.dstack((red, green, blue)), mode="RGB")
        else:
            image = image_cls.fromarray(screen, mode="L")
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return json.dumps({"png_base64": base64.b64encode(buffer.getvalue()).decode("ascii"), "palette": palette})
    except Exception as exc:
        return json.dumps({"error": f"PNG export failed: {exc}"})


def handle_graphics_set_blend_mode(args, *, ensure_emulator, state) -> str:
    ensure_emulator()
    try:
        mode = parse_int_arg(args.get("mode"), "mode", minimum=0, maximum=4)
    except ValueError as exc:
        return json.dumps({"error": str(exc)})

    gfx = state["gfx"]
    gfx.blend_mode = mode
    return json.dumps({"status": "blend_set", "mode": gfx.blend_mode})


def handle_sound_control(args, *, ensure_emulator, state) -> str:
    ensure_emulator()
    action = args["action"]
    sound = state["sound"]
    if action == "play":
        address = int(args.get("address", 0x2000))
        frequency_reg = int(args.get("frequency", 220)) & 0xFF
        volume_reg = int(args.get("volume", 128)) & 0xFF
        waveform_reg = int(args.get("waveform", 1)) & 0xFF
        if hasattr(sound, "update_registers"):
            sound.update_registers(sa=address, sf=frequency_reg, sv=volume_reg, sw=waveform_reg | 0x80)
        played = sound.splay() if hasattr(sound, "splay") else False
        return json.dumps({"status": "playing" if played else "play_failed", "frequency_reg": frequency_reg, "volume_reg": volume_reg, "waveform_reg": waveform_reg})
    if action == "stop":
        stopped = sound.sstop() if hasattr(sound, "sstop") else False
        return json.dumps({"status": "stopped" if stopped else "stop_failed"})
    if action == "get_state":
        return json.dumps({
            "frequency": sound.get_register("SF") if hasattr(sound, "get_register") else 0,
            "volume": sound.get_register("SV") if hasattr(sound, "get_register") else 0,
            "waveform": sound.get_register("SW") if hasattr(sound, "get_register") else 0,
        })
    return json.dumps({"error": f"Unknown action: {action}"})


def handle_keyboard_type_string(args, *, ensure_emulator, state) -> str:
    ensure_emulator()
    text = args.get("text")
    if not isinstance(text, str):
        return json.dumps({"error": "text must be a string"})
    try:
        text.encode("ascii")
    except UnicodeEncodeError:
        return json.dumps({"error": "text must contain only ASCII characters"})

    state["kbd"].type_string(text)
    return json.dumps({"status": "typed", "length": len(text)})