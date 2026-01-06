; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV P7:, 0xFF
MOV :P7, 0xFF
MOV SP, P7
MOV FP, SP
CALL _func_teststringoperations_4
MOV VX, 0
MOV VC, 15
TEXT STR0
ADD VY, 8
HLT

_func_teststringlength_0:
; Function: teststringlength
; Parameters: 
PUSH FP
MOV FP, SP
MOV VX, 0
MOV VC, 15
TEXT STR1
ADD VY, 8
MOV P1, STR2
MOV P0, 288
MOV [P0], P1
MOV P0, 288
MOV P0, [P0]
STRLEN P0
MOV R1, R0
; Free P0 (last use)
MOV P0, 291
MOV [P0], R1
MOV P0, 290
MOV P0, [P0]
ITOS P1, P0
MOV VX, 0
MOV VC, 15
TEXT P1
ADD VY, 8
MOV R0, 0
MOV SP, FP
POP FP
RET


_func_teststringtoupper_1:
; Function: teststringtoupper
; Parameters: 
PUSH FP
MOV FP, SP
MOV VX, 0
MOV VC, 15
TEXT STR3
ADD VY, 8
MOV P1, STR2
MOV P0, 288
MOV [P0], P1
MOV P0, 288
MOV P0, [P0]
STRUPR P0
MOV R1, P0
; Free P0 (last use)
MOV P0, 293
MOV [P0], R1
MOV P0, 292
MOV P0, [P0]
ITOS P1, P0
MOV VX, 0
MOV VC, 15
TEXT P1
ADD VY, 8
MOV R0, 0
MOV SP, FP
POP FP
RET


_func_teststringtolower_2:
; Function: teststringtolower
; Parameters: 
PUSH FP
MOV FP, SP
MOV VX, 0
MOV VC, 15
TEXT STR4
ADD VY, 8
MOV P1, STR5
MOV P0, 288
MOV [P0], P1
MOV P0, 288
MOV P0, [P0]
STRLWR P0
MOV R1, P0
; Free P0 (last use)
MOV P0, 295
MOV [P0], R1
MOV P0, 294
MOV P0, [P0]
ITOS P1, P0
MOV VX, 0
MOV VC, 15
TEXT P1
ADD VY, 8
MOV R0, 0
MOV SP, FP
POP FP
RET


_func_teststringfind_3:
; Function: teststringfind
; Parameters: 
PUSH FP
MOV FP, SP
MOV VX, 0
MOV VC, 15
TEXT STR6
ADD VY, 8
MOV P0, STR7
MOV P0, 296
MOV [P0], P0
MOV P0, STR8
MOV P0, 298
MOV [P0], P0
MOV P0, 296
MOV P0, [P0]
MOV P0, 298
MOV P0, [P0]
STRFIND P0, P0
MOV R1, R0
MOV P0, 301
MOV [P0], R1
MOV P0, 300
MOV P0, [P0]
ITOS P1, P0
MOV VX, 0
MOV VC, 15
TEXT P1
ADD VY, 8
MOV R0, 0
MOV SP, FP
POP FP
RET


_func_teststringoperations_4:
; Function: teststringoperations
; Parameters: 
PUSH FP
MOV FP, SP
MOV VX, 0
MOV VC, 15
TEXT STR9
ADD VY, 8
CALL _func_teststringlength_0
CALL _func_teststringtoupper_1
CALL _func_teststringtolower_2
CALL _func_teststringfind_3
MOV VX, 0
MOV VC, 15
TEXT STR10
ADD VY, 8
MOV P0, STR2
MOV P0, 302
MOV [P0], P0
MOV P0, 302
MOV P0, [P0]
STRLEN P0
MOV R1, R0
MOV P0, 291
MOV [P0], R1
MOV P0, 290
MOV P0, [P0]
ITOS P1, P0
MOV VX, 0
MOV VC, 15
TEXT P1
ADD VY, 8
MOV P0, 302
MOV P0, [P0]
STRUPR P0
MOV R1, P0
MOV P0, 293
MOV [P0], R1
MOV P0, 292
MOV P0, [P0]
ITOS P1, P0
MOV VX, 0
MOV VC, 15
TEXT P1
ADD VY, 8
MOV VX, 0
MOV VC, 15
TEXT STR11
ADD VY, 8
MOV R0, 0
MOV SP, FP
POP FP
RET

STR0: DEFSTR "Done"
STR1: DEFSTR "Test STRLEN"
STR2: DEFSTR "hello"
STR3: DEFSTR "Test UPSTRING"
STR4: DEFSTR "Test LOWSTRING"
STR5: DEFSTR "WORLD"
STR6: DEFSTR "Test INSTRING"
STR7: DEFSTR "helloworld"
STR8: DEFSTR "world"
STR9: DEFSTR "=== String Test Suite ==="
STR10: DEFSTR "Combined test"
STR11: DEFSTR "=== Tests Complete ==="