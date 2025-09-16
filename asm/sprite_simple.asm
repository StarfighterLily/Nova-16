; Simple Sprite Test
; Basic demonstration of the sprite system

; Constants
SPRITE_BASE EQU 0xF000

ORG 0x1000

MAIN:
    STI                 ; Enable interrupts
    MOV VM, 0           ; Coordinate mode
    
    ; Clear screen
    MOV VL, 0           ; Main screen
    SFILL 0x00          ; Fill with black
    MOV VL, 5           ; Sprite layer
    SFILL 0x00          ; Clear sprite layer
    
    ; Show title
    MOV VL, 0
    MOV VX, 80
    MOV VY, 10
    MOV R0, 0x1F        ; White
    TEXT TITLE, R0
    
    ; Setup one simple sprite
    CALL SETUP_SPRITE
    
    ; Render the sprite
    SPBLIT 0            ; Blit sprite 0
    
    ; Main loop
LOOP:
    NOP
    JMP LOOP

SETUP_SPRITE:
    ; Setup sprite 0 - a simple red square
    MOV P0, SPRITE_BASE ; Sprite 0 control block
    
    ; Data address - point to sprite data
    MOV R0, SPRITE_DATA:
    STOR P0, R0         ; High byte
    INC P0
    MOV R0, :SPRITE_DATA
    STOR P0, R0         ; Low byte
    INC P0
    
    ; X position
    MOV R0, 100
    STOR P0, R0
    INC P0
    
    ; Y position  
    MOV R0, 100
    STOR P0, R0
    INC P0
    
    ; Width
    MOV R0, 8
    STOR P0, R0
    INC P0
    
    ; Height
    MOV R0, 8
    STOR P0, R0
    INC P0
    
    ; Flags: active (bit 0 = 1)
    MOV R0, 0x01
    STOR P0, R0
    INC P0
    
    ; Transparency color (not used since transparency bit 1 = 0)
    MOV R0, 0x00
    STOR P0, R0
    
    RET

; Sprite data
ORG 0x3000
SPRITE_DATA:
    ; 8x8 red square
    DB 0x1C, 0x1C, 0x1C, 0x1C, 0x1C, 0x1C, 0x1C, 0x1C  ; Row 0
    DB 0x1C, 0x1C, 0x1C, 0x1C, 0x1C, 0x1C, 0x1C, 0x1C  ; Row 1
    DB 0x1C, 0x1C, 0x1C, 0x1C, 0x1C, 0x1C, 0x1C, 0x1C  ; Row 2
    DB 0x1C, 0x1C, 0x1C, 0x1C, 0x1C, 0x1C, 0x1C, 0x1C  ; Row 3
    DB 0x1C, 0x1C, 0x1C, 0x1C, 0x1C, 0x1C, 0x1C, 0x1C  ; Row 4
    DB 0x1C, 0x1C, 0x1C, 0x1C, 0x1C, 0x1C, 0x1C, 0x1C  ; Row 5
    DB 0x1C, 0x1C, 0x1C, 0x1C, 0x1C, 0x1C, 0x1C, 0x1C  ; Row 6
    DB 0x1C, 0x1C, 0x1C, 0x1C, 0x1C, 0x1C, 0x1C, 0x1C  ; Row 7

TITLE: DEFSTR "Simple Sprite Test"
