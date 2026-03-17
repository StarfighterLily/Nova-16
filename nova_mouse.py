#!/usr/bin/env python3
"""Nova-16 mouse device with CPU-visible registers and hardware cursor state."""

from __future__ import annotations


class NovaMouse:
    """Track mouse position/buttons and synchronize the hardware cursor overlay."""

    CURSOR_BITMAP = (
        (1, 1, 1, 0),
        (1, 1, 0, 0),
        (1, 0, 1, 0),
        (0, 0, 0, 1),
    )

    LEFT_BUTTON_MASK = 0x01
    RIGHT_BUTTON_MASK = 0x02

    def __init__(self, gfx=None, cpu_ref=None, cursor_color=0xFF):
        self.gfx = gfx
        self.cpu = cpu_ref
        self.cursor_color = int(cursor_color) & 0xFF
        self.x = 0
        self.y = 0
        self.buttons = 0
        self.control = 0x01
        self.enabled = True
        self.cursor_enabled = False
        self.pending_interrupt = False
        self._interrupt_callback = None
        self.sync_cursor()

    def attach(self, gfx=None, cpu_ref=None):
        if gfx is not None:
            self.gfx = gfx
        if cpu_ref is not None:
            self.cpu = cpu_ref
        self.sync_cursor()

    def reset(self):
        self.x = 0
        self.y = 0
        self.buttons = 0
        self.control = 0x01
        self.enabled = True
        self.cursor_enabled = False
        self.pending_interrupt = False
        self.sync_cursor()
        self._notify_interrupt_change()

    def move_to(self, x, y, from_host=False):
        if from_host and not self.enabled:
            return
        self.x = int(x) & 0xFFFF
        self.y = int(y) & 0xFFFF
        if self.enabled:
            self.cursor_enabled = True
        self.sync_cursor()
        if from_host:
            self._set_pending_interrupt()

    def move_by(self, dx, dy):
        self.move_to(self.x + int(dx), self.y + int(dy))

    def set_buttons(self, buttons, from_host=False):
        if from_host and not self.enabled:
            return
        self.buttons = int(buttons) & 0xFF
        if self.enabled and self.buttons & 0x03:
            self.cursor_enabled = True
        self.sync_cursor()
        if from_host:
            self._set_pending_interrupt()

    def set_button(self, button_number, pressed, from_host=False):
        if from_host and not self.enabled:
            return
        mask = self._button_mask(button_number)
        if mask == 0:
            return
        if pressed:
            self.buttons |= mask
            if self.enabled:
                self.cursor_enabled = True
        else:
            self.buttons &= (~mask) & 0xFF
        self.sync_cursor()
        if from_host:
            self._set_pending_interrupt()

    def write_control(self, control):
        self.control = int(control) & 0xFF
        self.enabled = (self.control & 0x01) != 0
        if not self.enabled:
            self.cursor_enabled = False
            self.pending_interrupt = False
        self.sync_cursor()
        self._notify_interrupt_change()

    def clear_interrupt(self):
        self.pending_interrupt = False
        self._notify_interrupt_change()

    def set_interrupt_callback(self, callback):
        self._interrupt_callback = callback

    def _set_pending_interrupt(self):
        if not self.enabled:
            return
        self.pending_interrupt = True
        self._notify_interrupt_change()

    def _notify_interrupt_change(self):
        if self._interrupt_callback is not None:
            self._interrupt_callback()

    def sync_cursor(self):
        if self.gfx is None:
            return
        self.gfx.set_mouse_cursor_state(
            self.x,
            self.y,
            visible=self.enabled and self.cursor_enabled,
            color=self.cursor_color,
            bitmap=self.CURSOR_BITMAP,
        )

    @staticmethod
    def _button_mask(button_number):
        if int(button_number) == 1:
            return NovaMouse.LEFT_BUTTON_MASK
        if int(button_number) == 3:
            return NovaMouse.RIGHT_BUTTON_MASK
        return 0