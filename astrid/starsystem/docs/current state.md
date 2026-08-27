## StarSys1 Status

# Working
OS boots to show 'Star System 1' screen with command prompt.
'r' keystroke runs the builtin ramdisk test and passes.
Keystrokes echo to the screen.
'Esc' keystroke halts the program.
Multiline command window works and shows responses on new lines.
Console scrolls: consuming the bottom row shifts the text layer up one glyph
row (SSHFT 1, -8) and blanks the gutter row below the title bar, so history
scrolls away instead of wrapping over the prompt. The cursor stays pinned to
the bottom row. Window chrome (frame + titles) moved to static background
layer 2 so the layer-wide shift only scrolls text (sec5 layer discipline).

# Fixed this round
- Console scroll issue (was: window wrapped to the top and overwrote history).
- Emulator: SSHFT now treats its amount as a signed 16-bit immediate; the
  assembler encodes negative amounts as two's-complement imm16, and without
  sign handling `screen_shift(1, -8)` arrived as +65528 and wiped the layer.
  Regression test: tests/unit/test_sshft_negative_amount.py.
- starfield.ast demo: the parallax ISR ran a nop()x5000 busy loop with
  interrupts masked, so every subsequent timer fire was dropped (>=2-dispatch
  test got 1) and the ISR outlived the fire period; the explicit iret() in a
  non-ISR function also only unwound by accident. ISR is now short; the TS
  divisor throttles the rate.

# Verification (MCP server, headless)
Boot -> booted=1, ticks heartbeat, mount tables at 0x0010-0x0017.
'r' -> ramdisk_ok=1, bank_invariant=1, report on fresh line.
16x Enter -> cursor_row pinned at 21, gutter row y=48-55 clear, prompt
glyphs on the bottom row, chrome intact on layer 2.
'H' -> glyph ink at (48..55,168..175) on layer 5, last_key=104.
ESC -> halted in 470 cycles, HALT banner ink at (96..127,120..127).
pytest: tests 823 passed / 15 skipped; astrid 594 passed.