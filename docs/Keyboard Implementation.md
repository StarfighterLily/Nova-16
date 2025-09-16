# Nova-16 Keyboard Implementation

This document describes the complete keyboard support implementation for the Nova-16 system.

## Overview

The Nova-16 keyboard system provides interrupt-driven keyboard input with the following features:

- 16-key circular buffer for key storage
- Interrupt-driven architecture
- Support for ASCII and special keys
- Hardware registers for status and control
- Six dedicated I/O instructions

## Hardware Registers

The keyboard system uses 4 hardware registers in the CPU:

| Register | Purpose | Address | Description |
|----------|---------|---------|-------------|
| keyboard[0] | Data | - | Current/next key in buffer |
| keyboard[1] | Status | - | Status flags and buffer state |
| keyboard[2] | Control | - | Interrupt enable and control settings |
| keyboard[3] | Count | - | Number of keys in buffer |

### Status Register (keyboard[1]) Bit Layout

| Bit | Name | Description |
|-----|------|-------------|
| 0 | KEY_AVAILABLE | Set when keys are available in buffer |
| 1 | BUFFER_FULL | Set when buffer is full (16 keys) |
| 2-6 | Reserved | Reserved for future use |
| 7 | INT_PENDING | Set when keyboard interrupt is pending |

### Control Register (keyboard[2]) Bit Layout

| Bit | Name | Description |
|-----|------|-------------|
| 0 | INT_ENABLE | Enable keyboard interrupts |
| 1 | Reserved | Reserved for future use |
| 2 | KEYBOARD_IRQ | Set to trigger keyboard interrupt |
| 3-7 | Reserved | Reserved for future use |

## I/O Instructions

### KEYIN reg (0x80)
**Syntax:** `KEYIN R0`
**Description:** Read the oldest key from the keyboard buffer into specified register
**Flags:** Sets Zero flag if no key available
**Example:** 
```assembly
KEYIN R0    ; Read key into register A
```

### KEYSTAT reg (0x81)
**Syntax:** `KEYSTAT R0`
**Description:** Get keyboard status (1 if keys available, 0 if empty)
**Flags:** None modified
**Example:**
```assembly
KEYSTAT R0  ; Check if keys available
CMP R0, 0   ; Compare with 0
JEQ no_keys ; Jump if no keys available
```

### KEYCOUNT reg (0x82)
**Syntax:** `KEYCOUNT R0`
**Description:** Get number of keys currently in buffer (0-16)
**Flags:** None modified
**Example:**
```assembly
KEYCOUNT R0 ; Get buffer count
CMP R0, 16  ; Check if buffer full
```

### KEYCLEAR (0x83)
**Syntax:** `KEYCLEAR`
**Description:** Clear the keyboard buffer and reset all status flags
**Flags:** None modified
**Example:**
```assembly
KEYCLEAR    ; Clear keyboard buffer
```

### KEYCTRL reg (0x84)
**Syntax:** `KEYCTRL R0`
**Description:** Set keyboard control register from specified register
**Flags:** None modified
**Example:**
```assembly
LOAD R0, 1  ; Load interrupt enable flag
KEYCTRL R0  ; Enable keyboard interrupts
```

### KEYCTRL imm8 (0x85)
**Syntax:** `KEYCTRL value`
**Description:** Set keyboard control register with immediate value
**Flags:** None modified
**Example:**
```assembly
KEYCTRL 1   ; Enable keyboard interrupts
KEYCTRL 0   ; Disable keyboard interrupts
```

## Key Codes

The keyboard system uses the following key code mappings:

### ASCII Characters (0x20-0x7E)
Standard ASCII printable characters are mapped directly to their ASCII values.

### Control Characters
| Key | Code | Description |
|-----|------|-------------|
| NULL | 0x00 | Null character |
| Backspace | 0x08 | Backspace |
| Tab | 0x09 | Tab character |
| Enter | 0x0A | Line feed/Enter |
| Escape | 0x1B | Escape character |

### Special Keys (0x80-0xFF)
| Key | Code | Description |
|-----|------|-------------|
| Left Arrow | 0x80 | Left arrow key |
| Right Arrow | 0x81 | Right arrow key |
| Up Arrow | 0x82 | Up arrow key |
| Down Arrow | 0x83 | Down arrow key |
| F1-F12 | 0x84-0x8F | Function keys F1 through F12 |
| Insert | 0x90 | Insert key |
| Delete | 0x91 | Delete key |
| Backspace | 0x92 | Backspace key (alternative) |
| Enter | 0x93 | Enter key (alternative) |
| Page Up | 0x94 | Page Up key |
| Page Down | 0x95 | Page Down key |
| Tab | 0x96 | Tab key (alternative) |
| Shift | 0x97 | Shift modifier |
| Home | 0x98 | Home key |
| End | 0x99 | End key |
| Escape | 0x9A | Escape key (alternative) |
| Space | 0x9B | Space key (alternative) |
| Caps Lock | 0x9C | Caps Lock toggle |
| Num Lock | 0x9D | Num Lock toggle |
| Scroll Lock | 0x9E | Scroll Lock toggle |
| Pause/Break | 0x9F | Pause/Break key |

## Interrupt Handling

The keyboard system integrates with the Nova-16 interrupt system:

- **Interrupt Vector:** 2 (keyboard interrupt)
- **Trigger Condition:** Key press when interrupts are enabled
- **Enable Control:** Control register bit 0
- **Status Indication:** Status register bit 7

To enable keyboard interrupts:
```assembly
KEYCTRL 1   ; Enable keyboard interrupts
```

When a key is pressed and interrupts are enabled, the keyboard interrupt (vector 2) will be triggered.

## Programming Examples

### Simple Key Reading
```assembly
loop:
    KEYSTAT R0      ; Check if key available
    CMP R0, 0
    JEQ loop        ; Wait for key
    KEYIN R0        ; Read the key
    ; Process key in R0
    JMP loop
```

### Interrupt-Driven Input
```assembly
main:
    KEYCTRL 1       ; Enable keyboard interrupts
    ; Main program continues...
    
keyboard_isr:
    KEYIN R0        ; Read the key
    ; Process key in R0
    IRET            ; Return from interrupt
```

### Buffer Management
```assembly
check_buffer:
    KEYCOUNT R0     ; Get buffer count
    CMP R0, 10      ; Check if buffer getting full
    JGE clear_some  ; Clear some keys if >10
    RET
    
clear_some:
    KEYIN R0        ; Read and discard key
    KEYCOUNT R0     ; Check count again
    CMP R0, 5       ; Keep clearing until <5 keys
    JGE clear_some
    RET
```

## Integration with Main System

The keyboard system is integrated into the main Nova-16 system through:

1. **nova_keyboard.py** - Keyboard module with key mapping and event handling
2. **nova_cpu.py** - CPU integration with keyboard registers and instructions
3. **nova.py** - Main system integration

To use the keyboard in your Nova-16 program:

```python
import nova_keyboard as keyboard

# Create keyboard instance with CPU reference
kbd = keyboard.NovaKeyboard(cpu_instance)

# Simulate key presses
kbd.press_key('a')
kbd.type_string("Hello World!")

# Check buffer status
status = kbd.get_buffer_status()
print(f"Keys available: {status['available']}")
print(f"Buffer count: {status['count']}")
```

## Testing

The keyboard implementation includes comprehensive tests in `test_keyboard.py`:

- Buffer operations (add/read/clear)
- I/O instruction functionality  
- Special key mapping
- Interrupt setup
- Buffer overflow handling

Run tests with:
```bash
python test_keyboard.py
```

All tests should pass, confirming proper keyboard functionality.
