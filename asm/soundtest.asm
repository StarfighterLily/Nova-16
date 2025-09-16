; Nova Sound System Test Program
; This program tests the basic sound functionality

ORG 0x1000

MAIN:
    ; Test 1: Play a simple sine wave
    MOV SF, 128         ; Set frequency to middle range
    MOV SV, 128         ; Set volume to half
    MOV SW, 0x82        ; Sine wave (2) + enabled (0x80)
    SPLAY               ; Play the sound
    
    ; Wait a bit (simple loop delay)
    MOV R0, 255
WAIT1:
    DEC R0
    JNZ WAIT1
    
    ; Stop the sound
    SSTOP
    
    ; Test 2: Play different waveforms
    MOV SF, 100         ; Lower frequency
    MOV SV, 100         ; Lower volume
    
    ; Square wave
    MOV SW, 0x81        ; Square wave (1) + enabled (0x80)
    SPLAY
    MOV R0, 200
WAIT2:
    DEC R0
    JNZ WAIT2
    SSTOP
    
    ; Triangle wave
    MOV SW, 0x84        ; Triangle wave (4) + enabled (0x80)
    SPLAY
    MOV R0, 200
WAIT3:
    DEC R0
    JNZ WAIT3
    SSTOP
    
    ; Test 3: Sound effects
    STRIG 0             ; Simple beep
    MOV R0, 200
WAIT4:
    DEC R0
    JNZ WAIT4
    
    STRIG 1             ; Rising tone
    MOV R0, 200
WAIT5:
    DEC R0
    JNZ WAIT5
    
    STRIG 6             ; Coin pickup sound
    MOV R0, 200
WAIT6:
    DEC R0
    JNZ WAIT6
    
    ; Test complete
    HLT
