; Test program for new graphics instructions
; This program tests SLINE, SRECT, SCIRC, and SINV instructions

; Set video mode to coordinate mode
MOV VM, 0

; Draw a line from (10,10) to (100,50) in red (color 1)
MOV VX, 10
MOV VY, 10
SLINE 100, 50, 1

; Draw a filled rectangle from (20,20) to (80,40) in blue (color 2)
SRECT 20, 20, 80, 40, 2, 1

; Draw an outline circle at (150,100) with radius 30 in green (color 3)
SCIRC 150, 100, 30, 3, 0

; Draw a filled circle at (200,150) with radius 20 in yellow (color 4)
SCIRC 200, 150, 20, 4, 1

; Wait a bit (simple delay loop)
MOV R0, 10000
delay_loop:
DEC R0
JNZ delay_loop

; Invert the screen colors
SINV

; Another delay
MOV R0, 10000
delay_loop2:
DEC R0
JNZ delay_loop2

; Invert back to original
SINV

; Test layer operations
; Copy layer 0 to layer 1
LCPY 1, 0

; Clear layer 0 to black
LCLR 0, 0

; Wait
MOV R0, 5000
delay_loop3:
DEC R0
JNZ delay_loop3

; Copy back from layer 1 to layer 0
LCPY 0, 1

; Test layer shifting
LSHFT 0, 0, 10  ; Shift layer 0 right by 10 pixels
LSHFT 0, 1, 5   ; Shift layer 0 down by 5 pixels

; Test layer flipping
LFLIP 0, 0  ; Flip layer 0 horizontally

; Wait
MOV R0, 10000
delay_loop4:
DEC R0
JNZ delay_loop4

LFLIP 0, 1  ; Flip layer 0 vertically

; Test layer rotation
LROT 0, 0, 90   ; Rotate layer 0 left by 90 degrees

; Wait
MOV R0, 10000
delay_loop5:
DEC R0
JNZ delay_loop5

LROT 0, 1, 90   ; Rotate layer 0 right by 90 degrees

; Test layer swapping
; First fill layer 1 with a different color
LCLR 1, 5
LSWAP 0, 1

; Infinite loop to keep the program running
main_loop:
JMP main_loop

HLT