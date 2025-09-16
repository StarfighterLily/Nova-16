# Nova-16 Sound System Documentation

## Overview

The Nova-16 Sound System is a hybrid register-based audio system that provides multiple waveforms, sound channels, and effects using pygame.mixer as the backend. It supports 8 simultaneous sound channels with various waveforms and built-in sound effects.

## Sound Registers

The sound system uses four main registers accessible via the CPU:

### SA - Sound Address (16-bit)
- **Opcode**: `0x9D` (direct), `0xA1` (high byte), `0xA2` (low byte)
- **Purpose**: Points to sound data in memory for sample-based playback
- **Range**: 0x0000 - 0xFFFF
- **Usage**: Used with waveform type 7 (memory-based samples)

### SF - Sound Frequency (8-bit)
- **Opcode**: `0x9E`
- **Purpose**: Sets the base frequency for waveform generation
- **Range**: 0-255 (maps to ~55Hz - 1760Hz exponentially)
- **Usage**: 0 = silence, 255 = highest frequency

### SV - Sound Volume (8-bit)
- **Opcode**: `0x9F`
- **Purpose**: Controls the volume level
- **Range**: 0-255 (0 = silent, 255 = maximum volume)
- **Usage**: Linear volume control

### SW - Sound Waveform/Control (8-bit)
- **Opcode**: `0xA0`
- **Purpose**: Waveform type and channel control
- **Bit Layout**:
  - Bits 0-2: Waveform type (0-7)
  - Bits 3-5: Channel number (0-7)
  - Bit 6: Loop flag (0=one-shot, 1=loop)
  - Bit 7: Enable flag (0=disabled, 1=enabled)

## Waveform Types

| Value | Waveform | Description |
|-------|----------|-------------|
| 0 | Silence | No sound output |
| 1 | Square | Digital square wave (retro game style) |
| 2 | Sine | Pure sine wave (smooth tone) |
| 3 | Sawtooth | Linear ramp waveform |
| 4 | Triangle | Triangle wave (soft square) |
| 5 | White Noise | Random noise |
| 6 | Pink Noise | 1/f filtered noise |
| 7 | Memory Sample | Sample data from memory at SA address |

## Sound Instructions

### SPLAY - Start Playing Sound
- **SPLAY** (`0x97`) - Play sound using current register values
- **SPLAY reg** (`0x98`) - Play sound on specific channel from register

**Usage:**
```assembly
MOV SF, 128     ; Set frequency
MOV SV, 200     ; Set volume  
MOV SW, 0x82    ; Sine wave (2) + enabled (0x80)
SPLAY           ; Start playing
```

### SSTOP - Stop Sound
- **SSTOP** (`0x99`) - Stop all sound channels
- **SSTOP reg** (`0x9A`) - Stop specific channel from register

**Usage:**
```assembly
SSTOP           ; Stop all channels
MOV R0, 3
SSTOP R0        ; Stop channel 3
```

### STRIG - Trigger Sound Effect
- **STRIG** (`0x9B`) - Trigger effect (type from SW register lower 3 bits)
- **STRIG imm8** (`0x9C`) - Trigger specific effect type

**Usage:**
```assembly
STRIG 6         ; Coin pickup sound
MOV SW, 3       ; Set explosion effect in SW
STRIG           ; Trigger effect from SW
```

## Sound Effects

| Effect | Name | Description |
|--------|------|-------------|
| 0 | Simple Beep | Basic 800Hz sine wave beep |
| 1 | Rising Tone | Frequency sweep upward |
| 2 | Falling Tone | Frequency sweep downward |
| 3 | Explosion | Filtered noise with decay envelope |
| 4 | Laser Shot | Descending frequency with modulation |
| 5 | Jump | Rising then falling square wave |
| 6 | Coin Pickup | Two-tone ascending (E5, A5) |
| 7 | Power-up | Ascending arpeggio progression |

## Programming Examples

### Basic Sound Generation
```assembly
; Play a 440Hz sine wave
MOV SF, 85      ; ~440Hz (calculated value)
MOV SV, 150     ; Medium volume
MOV SW, 0x82    ; Sine wave + enabled
SPLAY
```

### Multi-Channel Chord
```assembly
; Play C major chord (C-E-G)
; Channel 0: C note
MOV SF, 60      ; C frequency
MOV SV, 100     
MOV SW, 0x02    ; Sine wave, channel 0
SPLAY

; Channel 1: E note  
MOV SF, 76      ; E frequency
MOV SV, 100
MOV SW, 0x0A    ; Sine wave, channel 1 (bits 3-5 = 001)
SPLAY

; Channel 2: G note
MOV SF, 89      ; G frequency  
MOV SV, 100
MOV SW, 0x12    ; Sine wave, channel 2 (bits 3-5 = 010)
SPLAY
```

### Sound Effects Sequence
```assembly
STRIG 5         ; Jump sound
; Wait loop here
STRIG 6         ; Coin pickup
; Wait loop here  
STRIG 7         ; Power-up sound
```

### Memory-Based Samples
```assembly
; Load sample data at address 0x2000
MOV SA, 0x2000  ; Sample data address
MOV SF, 100     ; Playback rate
MOV SV, 200     ; Volume
MOV SW, 0x87    ; Memory sample (7) + enabled
SPLAY
```

## Technical Details

### Audio Specifications
- **Sample Rate**: 22050Hz (configurable)
- **Bit Depth**: 16-bit signed
- **Channels**: Stereo output
- **Buffer Size**: 512 samples (low latency)
- **Simultaneous Sounds**: 8 channels

### Frequency Mapping
The SF register maps to frequencies using an exponential scale:
```
frequency = 55.0 * (1760.0 / 55.0) ^ (SF / 255.0)
```
- SF=0: ~55Hz (A1)
- SF=128: ~440Hz (A4)  
- SF=255: ~1760Hz (A6)

### Memory Sample Format
When using waveform type 7 (memory samples):
- Samples are stored as 8-bit unsigned values (0-255)
- Converted to float range (-1.0 to 1.0) for playback
- Maximum sample length: 1024 bytes
- Samples loop if playback duration exceeds sample length

## Integration with CPU

The sound system is fully integrated with the Nova-16 CPU:

1. **Register Access**: Sound registers are accessible via standard register operations
2. **Instruction Dispatch**: Sound instructions are part of the main instruction table
3. **Memory Integration**: Sample data can be stored in main system memory
4. **Performance**: Optimized lookup tables and efficient waveform generation

## Error Handling

The sound system includes robust error handling:
- Invalid channel numbers are clipped to valid range (0-7)
- Invalid effect types are clipped to valid range (0-7)  
- Memory access errors default to silence
- Audio system failures are logged but don't crash the CPU

## Future Enhancements

Potential improvements for future versions:
- ADSR envelope control
- Additional waveform types
- Real-time frequency/volume modulation
- Audio filters (low-pass, high-pass, band-pass)
- Reverb and delay effects
- MIDI-style note control
- Sample compression/decompression

## Usage in Assembler

To use sound in Nova-16 assembly programs:

1. Include sound register definitions
2. Set up sound parameters using MOV instructions
3. Use SPLAY to start sound generation
4. Use SSTOP to stop sounds when needed
5. Use STRIG for quick sound effects

The sound system provides a rich audio environment for retro-style games and applications while maintaining the simplicity and performance characteristics of the Nova-16 architecture.
