; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV P7:, 0xFF
MOV :P7, 0xFF
MOV SP, P7
MOV FP, SP
CALL _func_teststringoperations_4
MOV VC, 15
MOV VX, 0
TEXT STR11
ADD VY, 8
HLT
_func_teststringlength_0:
; Function: teststringlength
; Parameters:
; Locals:  (0 bytes)
ENTER 0
MOV VC, 15
MOV VX, 0
TEXT STR0
ADD VY, 8
MOV P0, 288
MOV P1, STR1
MOV [P0], P1
MOV P0, 288
MOV P0, [P0]
STRLEN P0
MOV R1, R0
; Free P0 (last use)
MOV P0, 0
MOV P1, 290
MOV :P0, R1
MOV [P1], P0
MOV P0, 290
MOV P0, [P0]
ITOS P1, R0
MOV VC, 15
MOV R0, P0
MOV VX, 0
TEXT P1
ADD VY, 8
MOV SP, FP
POP FP
RETN 0
_func_teststringtoupper_1:
; Function: teststringtoupper
; Parameters:
; Locals:  (0 bytes)
ENTER 0
MOV VC, 15
MOV VX, 0
TEXT STR2
ADD VY, 8
MOV P0, 288
MOV P1, STR1
MOV [P0], P1
MOV P0, 288
MOV P0, [P0]
STRUPR P0
MOV R1, P0
; Free P0 (last use)
MOV P0, 0
MOV P1, 292
MOV :P0, R1
MOV [P1], P0
MOV P0, 292
MOV P0, [P0]
ITOS P1, R0
MOV VC, 15
MOV R0, P0
MOV VX, 0
TEXT P1
ADD VY, 8
MOV SP, FP
POP FP
RETN 0
_func_teststringtolower_2:
; Function: teststringtolower
; Parameters:
; Locals:  (0 bytes)
ENTER 0
MOV VC, 15
MOV VX, 0
TEXT STR3
ADD VY, 8
MOV P0, 288
MOV P1, STR4
MOV [P0], P1
MOV P0, 288
MOV P0, [P0]
STRLWR P0
MOV R1, P0
; Free P0 (last use)
MOV P0, 0
MOV P1, 294
MOV :P0, R1
MOV [P1], P0
MOV P0, 294
MOV P0, [P0]
ITOS P1, R0
MOV VC, 15
MOV R0, P0
MOV VX, 0
TEXT P1
ADD VY, 8
MOV SP, FP
POP FP
RETN 0
_func_teststringfind_3:
; Function: teststringfind
; Parameters:
; Locals:  (0 bytes)
ENTER 0
MOV VC, 15
MOV VX, 0
TEXT STR5
ADD VY, 8
MOV P1, 296
MOV P0, STR6
MOV [P1], P0
MOV P1, 298
MOV P0, STR7
MOV [P1], P0
MOV P0, 296
MOV P0, [P0]
MOV P0, 298
MOV P0, [P0]
STRFIND P0, P0
MOV R1, R0
; Free P0 (last use)
MOV P0, 0
MOV P1, 300
MOV :P0, R1
MOV [P1], P0
MOV P0, 300
MOV P0, [P0]
ITOS P1, R0
MOV VC, 15
MOV R0, P0
MOV VX, 0
TEXT P1
ADD VY, 8
MOV SP, FP
POP FP
RETN 0
_func_teststringoperations_4:
; Function: teststringoperations
; Parameters:
; Locals:  (0 bytes)
ENTER 0
MOV VC, 15
MOV VX, 0
TEXT STR8
ADD VY, 8
CALL _func_teststringlength_0
CALL _func_teststringtoupper_1
CALL _func_teststringtolower_2
CALL _func_teststringfind_3
MOV VC, 15
MOV VX, 0
TEXT STR9
ADD VY, 8
MOV P1, 302
MOV P0, STR1
MOV [P1], P0
MOV P0, 302
MOV P0, [P0]
STRLEN P0
MOV R1, R0
; Free P0 (last use)
MOV P0, 0
MOV P1, 290
MOV :P0, R1
MOV [P1], P0
MOV P0, 290
MOV P0, [P0]
ITOS P1, R0
MOV VC, 15
MOV R0, P0
MOV VX, 0
TEXT P1
ADD VY, 8
MOV P0, 302
MOV P0, [P0]
STRUPR P0
MOV R1, P0
; Free P0 (last use)
MOV P0, 0
MOV P1, 292
MOV :P0, R1
MOV [P1], P0
MOV P0, 292
MOV P0, [P0]
ITOS P1, R0
MOV VC, 15
MOV R0, P0
MOV VX, 0
TEXT P1
ADD VY, 8
MOV VC, 15
MOV VX, 0
TEXT STR10
ADD VY, 8
MOV SP, FP
POP FP
RETN 0
STR0: DEFSTR "Test STRLEN"
STR1: DEFSTR "hello"
STR2: DEFSTR "Test UPSTRING"
STR3: DEFSTR "Test LOWSTRING"
STR4: DEFSTR "WORLD"
STR5: DEFSTR "Test INSTRING"
STR6: DEFSTR "helloworld"
STR7: DEFSTR "world"
STR8: DEFSTR "=== String Test Suite ==="
STR9: DEFSTR "Combined test"
STR10: DEFSTR "=== Tests Complete ==="
STR11: DEFSTR "Done"