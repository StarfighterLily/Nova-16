ORG 0x0200

; Initialize graphics
MOV VM, 0          ; Coordinate mode
MOV VL, 5          ; Sprite layer (5-8 for sprites)

; Setup sprite 0
; Data address
MOV [0xF000], sprite_data

; X and Y positions (Y high byte, X low byte)
MOV [0xF002], 0x4040  ; Y=64, X=64

; Width and Height
MOV [0xF004], 0x0808  ; Height=8, Width=8

; Flags and Transparency
MOV [0xF006], 0x0001  ; Flags=1 (active), Transparency=0


; Enable interrupts
STI

; Setup keyboard interrupts
KEYCTRL 1

; Initial render
SPBLITALL

; Main loop - just wait
main_loop:
    NOP
    JMP main_loop

; keyboard interrupt handler
kbd_handler:
    
    ; Process all available keys in buffer
key_process_loop:
    MOV P0, [0xF002]
    KEYIN R0            ; Read the key
    
    ; Check if no key (buffer empty)
    CMP R0, 0
    JZ update_sprite
    
    ; Check for movement keys and update flags
    CMP R0, 'w'
    JZ set_move_up
    CMP R0, 's'
    JZ set_move_down
    CMP R0, 'a'
    JZ set_move_left
    CMP R0, 'd'
    JZ set_move_right
    ; Not a movement key, continue to next key
    JMP key_process_loop

set_move_up:
    DEC :P0
    JMP update_sprite

set_move_down:
    INC :P0
    JMP update_sprite

set_move_left:
    DEC P0:
    JMP update_sprite

set_move_right:
    INC P0:
    JMP update_sprite
    
update_sprite:
    ; Render all sprites
    MOV [0xF002], P0
    SPBLITALL
    IRET

; Sprite bitmap data (expanded to 64 bytes for 8x8 sprite)
sprite_data:
; Row 0: 00000000
DB 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
; Row 1: 00000000
DB 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
; Row 2: 00011000
DB 0x00, 0x00, 0x00, 0xFF, 0xFF, 0x00, 0x00, 0x00
; Row 3: 00111100
DB 0x00, 0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00
; Row 4: 00011000
DB 0x00, 0x00, 0x00, 0xFF, 0xFF, 0x00, 0x00, 0x00
; Row 5: 10011001
DB 0xFF, 0x00, 0x00, 0xFF, 0xFF, 0x00, 0x00, 0xFF
; Row 6: 10111101
DB 0xFF, 0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0xFF
; Row 7: 11100111
DB 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0xFF, 0xFF, 0xFF

ORG 0x0108
 DW kbd_handler