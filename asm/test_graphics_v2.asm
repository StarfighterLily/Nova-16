; Test program for new graphics instructions
; This program tests SLINE, SRECT, SCIRC, and SINV instructions

; Set video mode to coordinate mode
MOV VM, 0

; Set up coordinates in registers
MOV R0, 10   ; x1
MOV R1, 10   ; y1
MOV R2, 100  ; x2
MOV R3, 50   ; y2
MOV R4, 1    ; color

; Draw a line from (10,10) to (100,50) in red (color 1)
SLINE R0, R1, R2, R3, R4

; Set up rectangle coordinates
MOV R0, 20   ; x1
MOV R1, 20   ; y1
MOV R2, 80   ; x2
MOV R3, 40   ; y2
MOV R4, 2    ; color
MOV R5, 1    ; filled

; Draw a filled rectangle from (20,20) to (80,40) in blue (color 2)
SRECT R0, R1, R2, R3, R4, R5

; Set up circle parameters
MOV R0, 150  ; x
MOV R1, 100  ; y
MOV R2, 30   ; radius
MOV R3, 3    ; color
MOV R4, 0    ; outline

; Draw an outline circle at (150,100) with radius 30 in green (color 3)
SCIRC R0, R1, R2, R3, R4

; Set up filled circle
MOV R0, 200  ; x
MOV R1, 150  ; y
MOV R2, 20   ; radius
MOV R3, 4    ; color
MOV R4, 1    ; filled

; Draw a filled circle at (200,150) with radius 20 in yellow (color 4)
SCIRC R0, R1, R2, R3, R4

; Wait a bit (simple delay loop)
MOV R0, 100  ; Use smaller value
delay_loop:
DEC R0
JNZ delay_loop

; Invert the screen colors
SINV

; Another delay
MOV R0, 100
delay_loop2:
DEC R0
JNZ delay_loop2

; Invert back to original
SINV

; Test layer operations
; Copy layer 0 to layer 1
LCPY 1, 0

; Clear layer 0 to black
MOV R0, 0
LCLR 0, R0

; Wait
MOV R0, 50
delay_loop3:
DEC R0
JNZ delay_loop3

; Copy back from layer 1 to layer 0
LCPY 0, 1

; Test layer shifting
MOV R0, 10
LSHFT 0, 0, R0  ; Shift layer 0 right by 10 pixels
MOV R0, 5
LSHFT 0, 1, R0   ; Shift layer 0 down by 5 pixels

; Test layer flipping
LFLIP 0, 0  ; Flip layer 0 horizontally

; Wait
MOV R0, 100
delay_loop4:
DEC R0
JNZ delay_loop4

LFLIP 0, 1  ; Flip layer 0 vertically

; Test layer rotation
MOV R0, 90
LROT 0, 0, R0   ; Rotate layer 0 left by 90 degrees

; Wait
MOV R0, 100
delay_loop5:
DEC R0
JNZ delay_loop5

MOV R0, 90
LROT 0, 1, R0   ; Rotate layer 0 right by 90 degrees

; Test layer swapping
; First fill layer 1 with a different color
MOV R0, 5
LCLR 1, R0
LSWAP 0, 1

; Infinite loop to keep the program running
main_loop:
JMP main_loop

HLT