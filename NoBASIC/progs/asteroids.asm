; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV P7:, 0xFF
MOV :P7, 0xFF
MOV SP, P7
MOV FP, SP
; Struct Ship declared with fields: x, y, dx, dy, angle, thrust, lives, invuln, counter, score
MOV P3, 12
MOV P2, 5
; GLOBAL variable: gameOver @ 0x023A
; GLOBAL variable: wave @ 0x023E
; GLOBAL variable: b1_active @ 0x0120
; GLOBAL variable: b1_x @ 0x012A
; GLOBAL variable: b1_y @ 0x012C
; GLOBAL variable: b1_dx @ 0x012E
; GLOBAL variable: b1_dy @ 0x0130
; GLOBAL variable: b1_life @ 0x0132
; GLOBAL variable: b2_active @ 0x0122
; GLOBAL variable: b2_x @ 0x0134
; GLOBAL variable: b2_y @ 0x0136
; GLOBAL variable: b2_dx @ 0x0138
; GLOBAL variable: b2_dy @ 0x013A
; GLOBAL variable: b2_life @ 0x013C
; GLOBAL variable: b3_active @ 0x0124
; GLOBAL variable: b3_x @ 0x013E
; GLOBAL variable: b3_y @ 0x0140
; GLOBAL variable: b3_dx @ 0x0142
; GLOBAL variable: b3_dy @ 0x0144
; GLOBAL variable: b3_life @ 0x0146
; GLOBAL variable: b4_active @ 0x0126
; GLOBAL variable: b4_x @ 0x0148
; GLOBAL variable: b4_y @ 0x014A
; GLOBAL variable: b4_dx @ 0x014C
; GLOBAL variable: b4_dy @ 0x014E
; GLOBAL variable: b4_life @ 0x0150
; GLOBAL variable: b5_active @ 0x0128
; GLOBAL variable: b5_x @ 0x0152
; GLOBAL variable: b5_y @ 0x0154
; GLOBAL variable: b5_dx @ 0x0156
; GLOBAL variable: b5_dy @ 0x0158
; GLOBAL variable: b5_life @ 0x015A
; GLOBAL variable: a1_active @ 0x0164
; GLOBAL variable: a1_x @ 0x017E
; GLOBAL variable: a1_y @ 0x0180
; GLOBAL variable: a1_dx @ 0x0184
; GLOBAL variable: a1_dy @ 0x0186
; GLOBAL variable: a1_size @ 0x0182
; GLOBAL variable: a2_active @ 0x0166
; GLOBAL variable: a2_x @ 0x0188
; GLOBAL variable: a2_y @ 0x018A
; GLOBAL variable: a2_dx @ 0x018E
; GLOBAL variable: a2_dy @ 0x0190
; GLOBAL variable: a2_size @ 0x018C
; GLOBAL variable: a3_active @ 0x0168
; GLOBAL variable: a3_x @ 0x0192
; GLOBAL variable: a3_y @ 0x0194
; GLOBAL variable: a3_dx @ 0x0198
; GLOBAL variable: a3_dy @ 0x019A
; GLOBAL variable: a3_size @ 0x0196
; GLOBAL variable: a4_active @ 0x016A
; GLOBAL variable: a4_x @ 0x019C
; GLOBAL variable: a4_y @ 0x019E
; GLOBAL variable: a4_dx @ 0x01A2
; GLOBAL variable: a4_dy @ 0x01A4
; GLOBAL variable: a4_size @ 0x01A0
; GLOBAL variable: a5_active @ 0x016C
; GLOBAL variable: a5_x @ 0x01A6
; GLOBAL variable: a5_y @ 0x01A8
; GLOBAL variable: a5_dx @ 0x01AC
; GLOBAL variable: a5_dy @ 0x01AE
; GLOBAL variable: a5_size @ 0x01AA
; GLOBAL variable: a6_active @ 0x016E
; GLOBAL variable: a6_x @ 0x01B0
; GLOBAL variable: a6_y @ 0x01B2
; GLOBAL variable: a6_dx @ 0x01B6
; GLOBAL variable: a6_dy @ 0x01B8
; GLOBAL variable: a6_size @ 0x01B4
; GLOBAL variable: a7_active @ 0x0170
; GLOBAL variable: a7_x @ 0x01BA
; GLOBAL variable: a7_y @ 0x01BC
; GLOBAL variable: a7_dx @ 0x01C0
; GLOBAL variable: a7_dy @ 0x01C2
; GLOBAL variable: a7_size @ 0x01BE
; GLOBAL variable: a8_active @ 0x0172
; GLOBAL variable: a8_x @ 0x01C4
; GLOBAL variable: a8_y @ 0x01C6
; GLOBAL variable: a8_dx @ 0x01CA
; GLOBAL variable: a8_dy @ 0x01CC
; GLOBAL variable: a8_size @ 0x01C8
; GLOBAL variable: a9_active @ 0x0174
; GLOBAL variable: a9_x @ 0x01CE
; GLOBAL variable: a9_y @ 0x01D0
; GLOBAL variable: a9_dx @ 0x01D4
; GLOBAL variable: a9_dy @ 0x01D6
; GLOBAL variable: a9_size @ 0x01D2
; GLOBAL variable: a10_active @ 0x0176
; GLOBAL variable: a10_x @ 0x01D8
; GLOBAL variable: a10_y @ 0x01DA
; GLOBAL variable: a10_dx @ 0x01DE
; GLOBAL variable: a10_dy @ 0x01E0
; GLOBAL variable: a10_size @ 0x01DC
; GLOBAL variable: a11_active @ 0x0178
; GLOBAL variable: a11_x @ 0x01E2
; GLOBAL variable: a11_y @ 0x01E4
; GLOBAL variable: a11_dx @ 0x01E8
; GLOBAL variable: a11_dy @ 0x01EA
; GLOBAL variable: a11_size @ 0x01E6
; GLOBAL variable: a12_active @ 0x017A
; GLOBAL variable: a12_x @ 0x01EC
; GLOBAL variable: a12_y @ 0x01EE
; GLOBAL variable: a12_dx @ 0x01F2
; GLOBAL variable: a12_dy @ 0x01F4
; GLOBAL variable: a12_size @ 0x01F0
MOV R1, 1
SHL R1, 7
; Store to Ship.x
MOV P0, 528
MOV P1, R1
MOV [P0], P1
MOV R1, 1
SHL R1, 7
; Store to Ship.y
MOV P0, 530
MOV P1, R1
MOV [P0], P1
XOR R1, R1
; Store to Ship.dx
MOV P0, 532
MOV P1, R1
MOV [P0], P1
XOR R1, R1
; Store to Ship.dy
MOV P0, 534
MOV P1, R1
MOV [P0], P1
XOR R1, R1
; Store to Ship.angle
MOV P0, 536
MOV P1, R1
MOV [P0], P1
XOR R1, R1
; Store to Ship.thrust
MOV P0, 538
MOV P1, R1
MOV [P0], P1
MOV R1, 3
; Store to Ship.lives
MOV P0, 540
MOV P1, R1
MOV [P0], P1
MOV R1, 120
; Store to Ship.invuln
MOV P0, 542
MOV P1, R1
MOV [P0], P1
XOR R1, R1
; Store to Ship.counter
MOV P0, 544
MOV P1, R1
MOV [P0], P1
XOR R1, R1
; Store to Ship.score
MOV P0, 546
MOV P1, R1
MOV [P0], P1
XOR R1, R1
MOV P4, R1
MOV P5, 1
MOV VM, 0
XOR VL, VL
; ClrDraw
MOV VM, 0
MOV VL, 1
SFILL 0x00
MOV VM, 0
MOV VL, 1
SHL VL, 2
; ClrDraw
MOV VM, 0
MOV VL, 1
SFILL 0x00
MOV VM, 0
MOV VL, 5
; ClrDraw
MOV VM, 0
MOV VL, 1
SFILL 0x00
PUSH P2
PUSH P3
PUSH P4
PUSH P5
CALL _func_initgame_27
POP P5
POP P4
POP P3
POP P2
MOV VM, 0
XOR VL, VL
MOV VX, 60
MOV VY, 100
MOV VC, 31
TEXT STR410
MOV VX, 40
MOV VY, 120
MOV VC, 15
TEXT STR411
L413:
KEYSTAT R0
CMP R0, 0
JZ L413
L414:
MOV R1, 1
WHILE R1
JZ L415
MOV P1, P4
XOR R0, R0
CMP P1, R0
; Free P1 (last use)
; Free R0 (last use)
JNZ L416
PUSH P2
PUSH P3
PUSH P4
PUSH P5
CALL _func_handleinput_21
POP P5
POP P4
POP P3
POP P2
PUSH P2
PUSH P3
PUSH P4
PUSH P5
CALL _func_updatephysics_22
POP P5
POP P4
POP P3
POP P2
MOV P4, 1
MOV R0, P2
L418:
CMP P4, R0
JGT L419
PUSH P2
PUSH P3
PUSH P4
PUSH P5
PUSH P4
CALL _func_bulletupdate_4
ADD SP, 2
POP P5
POP P4
POP P3
POP P2
INC P4
JMP L418
L419:
MOV P4, 1
MOV P2, P3
L420:
CMP P4, P2
JGT L421
PUSH P2
PUSH P3
PUSH P4
PUSH P5
PUSH P4
CALL _func_asteroidupdatepos_18
ADD SP, 2
POP P5
POP P4
POP P3
POP P2
INC P4
JMP L420
L421:
PUSH P2
PUSH P3
PUSH P4
PUSH P5
CALL _func_checkcollisions_24
POP P5
POP P4
POP P3
POP P2
PUSH P2
PUSH P3
PUSH P4
PUSH P5
CALL _func_asteroidcount_17
POP P5
POP P4
POP P3
POP P2
MOV P1, R0
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
JNZ L422
MOV R0, 1
; Preserve left operand in register across right-side evaluation
MOV R1, R0
ADD R1, P5
MOV P5, R1
PUSH P2
PUSH P3
PUSH P4
PUSH P5
PUSH P5
CALL _func_spawnwave_19
ADD SP, 2
POP P5
POP P4
POP P3
POP P2
MOV R1, 60
; Store to Ship.invuln
MOV P0, 542
MOV P1, R1
MOV [P0], P1
L422:
PUSH P2
PUSH P3
PUSH P4
PUSH P5
CALL _func_renderframe_25
POP P5
POP P4
POP P3
POP P2
JMP L417
L416:
PUSH P2
PUSH P3
PUSH P4
PUSH P5
CALL _func_rendergameover_26
POP P5
POP P4
POP P3
POP P2
KEYIN R0
MOV R1, R0
MOV P2, R1
MOV P1, P2
MOV R0, 114
CMP P1, R0
; Free P1 (last use)
; Free R0 (last use)
JNZ L424
MOV VM, 0
XOR VL, VL
; ClrDraw
MOV VM, 0
MOV VL, 1
SFILL 0x00
MOV VM, 0
MOV VL, 1
SHL VL, 2
; ClrDraw
MOV VM, 0
MOV VL, 1
SFILL 0x00
MOV VM, 0
MOV VL, 5
; ClrDraw
MOV VM, 0
MOV VL, 1
SFILL 0x00
PUSH P2
PUSH P3
PUSH P4
PUSH P5
CALL _func_initgame_27
POP P5
POP P4
POP P3
POP P2
L424:
L417:
JMP L414
L415:
HLT
_func_bulletinitall_0:
; Function: bulletinitall
; Parameters:
; Locals:  (0 bytes)
ENTER 0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 288
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 290
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 292
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 294
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 296
MOV [P1], P0
MOV SP, FP
POP FP
RETN 0
_func_bulletinit_1:
; Function: bulletinit
; Parameters: idx
; Locals:  (0 bytes)
ENTER 0
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L1
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 288
MOV [P1], P0
L1:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
SHL P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L3
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 290
MOV [P1], P0
L3:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 3
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L5
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 292
MOV [P1], P0
L5:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
SHL P2, 2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L7
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 294
MOV [P1], P0
L7:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 5
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L9
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 296
MOV [P1], P0
L9:
MOV SP, FP
POP FP
RETN 0
_func_bulletgetslot_2:
; Function: bulletgetslot
; Parameters:
; Locals:  (0 bytes)
ENTER 0
MOV P0, 288
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L11
MOV R0, 1
MOV SP, FP
POP FP
RETN R0
L11:
MOV P0, 290
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L13
MOV R0, 1
SHL R0, 1
MOV SP, FP
POP FP
RETN R0
L13:
MOV P0, 292
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L15
MOV R0, 3
MOV SP, FP
POP FP
RETN R0
L15:
MOV P0, 294
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L17
MOV R0, 1
SHL R0, 2
MOV SP, FP
POP FP
RETN R0
L17:
MOV P0, 296
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L19
MOV R0, 5
MOV SP, FP
POP FP
RETN R0
L19:
XOR R0, R0
MOV SP, FP
POP FP
RETN R0
_func_bulletspawn_3:
; Function: bulletspawn
; Parameters: idx, x, y
; Locals:  (0 bytes)
ENTER 0
MOV P0, FP
ADD P0, 8
MOV P1, [P0]
MOV P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L21
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
MOV P0, 298
MOV [P0], P1
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P0, 300
MOV [P0], P1
MOV R1, 6
MOV P0, 0
MOV :P0, R1
MOV P1, 302
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 304
MOV [P1], P0
MOV R1, 1
MOV P0, 0
MOV :P0, R1
MOV P1, 288
MOV [P1], P0
MOV R1, 48
MOV P0, 0
MOV :P0, R1
MOV P1, 306
MOV [P1], P0
L21:
MOV P0, FP
ADD P0, 8
MOV P1, [P0]
MOV P2, 1
SHL P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L23
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
MOV P0, 308
MOV [P0], P1
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P0, 310
MOV [P0], P1
MOV R1, 6
MOV P0, 0
MOV :P0, R1
MOV P1, 312
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 314
MOV [P1], P0
MOV R1, 1
MOV P0, 0
MOV :P0, R1
MOV P1, 290
MOV [P1], P0
MOV R1, 48
MOV P0, 0
MOV :P0, R1
MOV P1, 316
MOV [P1], P0
L23:
MOV P0, FP
ADD P0, 8
MOV P1, [P0]
MOV P2, 3
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L25
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
MOV P0, 318
MOV [P0], P1
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P0, 320
MOV [P0], P1
MOV R1, 6
MOV P0, 0
MOV :P0, R1
MOV P1, 322
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 324
MOV [P1], P0
MOV R1, 1
MOV P0, 0
MOV :P0, R1
MOV P1, 292
MOV [P1], P0
MOV R1, 48
MOV P0, 0
MOV :P0, R1
MOV P1, 326
MOV [P1], P0
L25:
MOV P0, FP
ADD P0, 8
MOV P1, [P0]
MOV P2, 1
SHL P2, 2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L27
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
MOV P0, 328
MOV [P0], P1
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P0, 330
MOV [P0], P1
MOV R1, 6
MOV P0, 0
MOV :P0, R1
MOV P1, 332
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 334
MOV [P1], P0
MOV R1, 1
MOV P0, 0
MOV :P0, R1
MOV P1, 294
MOV [P1], P0
MOV R1, 48
MOV P0, 0
MOV :P0, R1
MOV P1, 336
MOV [P1], P0
L27:
MOV P0, FP
ADD P0, 8
MOV P1, [P0]
MOV P2, 5
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L29
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
MOV P0, 338
MOV [P0], P1
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P0, 340
MOV [P0], P1
MOV R1, 6
MOV P0, 0
MOV :P0, R1
MOV P1, 342
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 344
MOV [P1], P0
MOV R1, 1
MOV P0, 0
MOV :P0, R1
MOV P1, 296
MOV [P1], P0
MOV R1, 48
MOV P0, 0
MOV :P0, R1
MOV P1, 346
MOV [P1], P0
L29:
MOV SP, FP
POP FP
RETN 0
_func_bulletupdate_4:
; Function: bulletupdate
; Parameters: idx
; Locals:  (0 bytes)
ENTER 0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 348
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 350
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 352
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 354
MOV [P1], P0
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L31
MOV P0, 288
MOV P0, [P0]
MOV P1, 348
MOV [P1], P0
MOV P0, 298
MOV P0, [P0]
MOV P1, 350
MOV [P1], P0
MOV P0, 300
MOV P0, [P0]
MOV P1, 352
MOV [P1], P0
MOV P0, 306
MOV P0, [P0]
MOV P1, 354
MOV [P1], P0
L31:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
SHL P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L33
MOV P0, 290
MOV P0, [P0]
MOV P1, 348
MOV [P1], P0
MOV P0, 308
MOV P0, [P0]
MOV P1, 350
MOV [P1], P0
MOV P0, 310
MOV P0, [P0]
MOV P1, 352
MOV [P1], P0
MOV P0, 316
MOV P0, [P0]
MOV P1, 354
MOV [P1], P0
L33:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 3
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L35
MOV P0, 292
MOV P0, [P0]
MOV P1, 348
MOV [P1], P0
MOV P0, 318
MOV P0, [P0]
MOV P1, 350
MOV [P1], P0
MOV P0, 320
MOV P0, [P0]
MOV P1, 352
MOV [P1], P0
MOV P0, 326
MOV P0, [P0]
MOV P1, 354
MOV [P1], P0
L35:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
SHL P2, 2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L37
MOV P0, 294
MOV P0, [P0]
MOV P1, 348
MOV [P1], P0
MOV P0, 328
MOV P0, [P0]
MOV P1, 350
MOV [P1], P0
MOV P0, 330
MOV P0, [P0]
MOV P1, 352
MOV [P1], P0
MOV P0, 336
MOV P0, [P0]
MOV P1, 354
MOV [P1], P0
L37:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 5
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L39
MOV P0, 296
MOV P0, [P0]
MOV P1, 348
MOV [P1], P0
MOV P0, 338
MOV P0, [P0]
MOV P1, 350
MOV [P1], P0
MOV P0, 340
MOV P0, [P0]
MOV P1, 352
MOV [P1], P0
MOV P0, 346
MOV P0, [P0]
MOV P1, 354
MOV [P1], P0
L39:
MOV P0, 348
MOV P1, [P0]
MOV P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L41
MOV P0, 354
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P0
MOV R3, 1
MOV R1, R2
SUB R1, R3
; Free R3 (last use)
MOV P0, 0
MOV :P0, R1
MOV P1, 354
MOV [P1], P0
MOV P0, 354
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JGT L43
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 348
MOV [P1], P0
L43:
L41:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L45
MOV P0, 348
MOV P0, [P0]
MOV P1, 288
MOV [P1], P0
MOV P0, 354
MOV P0, [P0]
MOV P1, 306
MOV [P1], P0
L45:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
SHL P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L47
MOV P0, 348
MOV P0, [P0]
MOV P1, 290
MOV [P1], P0
MOV P0, 354
MOV P0, [P0]
MOV P1, 316
MOV [P1], P0
L47:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 3
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L49
MOV P0, 348
MOV P0, [P0]
MOV P1, 292
MOV [P1], P0
MOV P0, 354
MOV P0, [P0]
MOV P1, 326
MOV [P1], P0
L49:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
SHL P2, 2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L51
MOV P0, 348
MOV P0, [P0]
MOV P1, 294
MOV [P1], P0
MOV P0, 354
MOV P0, [P0]
MOV P1, 336
MOV [P1], P0
L51:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 5
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L53
MOV P0, 348
MOV P0, [P0]
MOV P1, 296
MOV [P1], P0
MOV P0, 354
MOV P0, [P0]
MOV P1, 346
MOV [P1], P0
L53:
MOV SP, FP
POP FP
RETN 0
_func_bulletgetactive_5:
; Function: bulletgetactive
; Parameters: idx
; Locals:  (0 bytes)
ENTER 0
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L55
MOV P0, 288
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L55:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
SHL P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L57
MOV P0, 290
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L57:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 3
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L59
MOV P0, 292
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L59:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
SHL P2, 2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L61
MOV P0, 294
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L61:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 5
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L63
MOV P0, 296
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L63:
XOR R0, R0
MOV SP, FP
POP FP
RETN R0
_func_bulletgetx_6:
; Function: bulletgetx
; Parameters: idx
; Locals:  (0 bytes)
ENTER 0
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L65
MOV P0, 298
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L65:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
SHL P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L67
MOV P0, 308
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L67:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 3
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L69
MOV P0, 318
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L69:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
SHL P2, 2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L71
MOV P0, 328
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L71:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 5
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L73
MOV P0, 338
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L73:
XOR R0, R0
MOV SP, FP
POP FP
RETN R0
_func_bulletgety_7:
; Function: bulletgety
; Parameters: idx
; Locals:  (0 bytes)
ENTER 0
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L75
MOV P0, 300
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L75:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
SHL P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L77
MOV P0, 310
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L77:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 3
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L79
MOV P0, 320
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L79:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
SHL P2, 2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L81
MOV P0, 330
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L81:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 5
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L83
MOV P0, 340
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L83:
XOR R0, R0
MOV SP, FP
POP FP
RETN R0
_func_bulletremove_8:
; Function: bulletremove
; Parameters: idx
; Locals:  (0 bytes)
ENTER 0
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L85
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 288
MOV [P1], P0
L85:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
SHL P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L87
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 290
MOV [P1], P0
L87:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 3
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L89
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 292
MOV [P1], P0
L89:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
SHL P2, 2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L91
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 294
MOV [P1], P0
L91:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 5
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L93
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 296
MOV [P1], P0
L93:
MOV SP, FP
POP FP
RETN 0
_func_asteroidinitall_9:
; Function: asteroidinitall
; Parameters:
; Locals:  (0 bytes)
ENTER 0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 356
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 358
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 360
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 362
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 364
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 366
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 368
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 370
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 372
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 374
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 376
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 378
MOV [P1], P0
MOV SP, FP
POP FP
RETN 0
_func_asteroidgetslot_10:
; Function: asteroidgetslot
; Parameters:
; Locals:  (0 bytes)
ENTER 0
MOV P0, 356
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L95
MOV R0, 1
MOV SP, FP
POP FP
RETN R0
L95:
MOV P0, 358
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L97
MOV R0, 1
SHL R0, 1
MOV SP, FP
POP FP
RETN R0
L97:
MOV P0, 360
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L99
MOV R0, 3
MOV SP, FP
POP FP
RETN R0
L99:
MOV P0, 362
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L101
MOV R0, 1
SHL R0, 2
MOV SP, FP
POP FP
RETN R0
L101:
MOV P0, 364
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L103
MOV R0, 5
MOV SP, FP
POP FP
RETN R0
L103:
MOV P0, 366
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L105
MOV R0, 6
MOV SP, FP
POP FP
RETN R0
L105:
MOV P0, 368
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L107
MOV R0, 7
MOV SP, FP
POP FP
RETN R0
L107:
MOV P0, 370
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L109
MOV R0, 1
SHL R0, 3
MOV SP, FP
POP FP
RETN R0
L109:
MOV P0, 372
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L111
MOV R0, 9
MOV SP, FP
POP FP
RETN R0
L111:
MOV P0, 374
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L113
MOV R0, 10
MOV SP, FP
POP FP
RETN R0
L113:
MOV P0, 376
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L115
MOV R0, 11
MOV SP, FP
POP FP
RETN R0
L115:
MOV P0, 378
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L117
MOV R0, 12
MOV SP, FP
POP FP
RETN R0
L117:
XOR R0, R0
MOV SP, FP
POP FP
RETN R0
_func_asteroidspawn_11:
; Function: asteroidspawn
; Parameters: idx, x, y, sz
; Locals:  (0 bytes)
ENTER 0
XOR R0, R0
MOV P0, 359
RNDR R1, R0, P0
; Free R0 (last use)
; Free P0 (last use)
MOV P0, 0
MOV :P0, R1
MOV P1, 380
MOV [P1], P0
MOV P0, FP
ADD P0, 10
MOV P1, [P0]
MOV P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L119
MOV P0, FP
ADD P0, 8
MOV P1, [P0]
MOV P0, 382
MOV [P0], P1
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
MOV P0, 384
MOV [P0], P1
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P0, 386
MOV [P0], P1
MOV R1, 1
MOV P0, 0
MOV :P0, R1
MOV P1, 388
MOV [P1], P0
MOV R1, 1
MOV P0, 0
MOV :P0, R1
MOV P1, 390
MOV [P1], P0
MOV R1, 1
MOV P0, 0
MOV :P0, R1
MOV P1, 356
MOV [P1], P0
L119:
MOV P0, FP
ADD P0, 10
MOV P1, [P0]
MOV P2, 1
SHL P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L121
MOV P0, FP
ADD P0, 8
MOV P1, [P0]
MOV P0, 392
MOV [P0], P1
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
MOV P0, 394
MOV [P0], P1
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P0, 396
MOV [P0], P1
MOV R1, 1
MOV P0, 0
MOV :P0, R1
MOV P1, 398
MOV [P1], P0
MOV R1, 1
MOV P0, 0
MOV :P0, R1
MOV P1, 400
MOV [P1], P0
MOV R1, 1
MOV P0, 0
MOV :P0, R1
MOV P1, 358
MOV [P1], P0
L121:
MOV P0, FP
ADD P0, 10
MOV P1, [P0]
MOV P2, 3
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L123
MOV P0, FP
ADD P0, 8
MOV P1, [P0]
MOV P0, 402
MOV [P0], P1
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
MOV P0, 404
MOV [P0], P1
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P0, 406
MOV [P0], P1
MOV R1, 1
MOV P0, 0
MOV :P0, R1
MOV P1, 408
MOV [P1], P0
; Constant folded: -(1) = -1
MOV R1, -1
MOV P0, 0
MOV :P0, R1
MOV P1, 410
MOV [P1], P0
MOV R1, 1
MOV P0, 0
MOV :P0, R1
MOV P1, 360
MOV [P1], P0
L123:
MOV P0, FP
ADD P0, 10
MOV P1, [P0]
MOV P2, 1
SHL P2, 2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L125
MOV P0, FP
ADD P0, 8
MOV P1, [P0]
MOV P0, 412
MOV [P0], P1
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
MOV P0, 414
MOV [P0], P1
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P0, 416
MOV [P0], P1
; Constant folded: -(1) = -1
MOV R1, -1
MOV P0, 0
MOV :P0, R1
MOV P1, 418
MOV [P1], P0
MOV R1, 1
MOV P0, 0
MOV :P0, R1
MOV P1, 420
MOV [P1], P0
MOV R1, 1
MOV P0, 0
MOV :P0, R1
MOV P1, 362
MOV [P1], P0
L125:
MOV P0, FP
ADD P0, 10
MOV P1, [P0]
MOV P2, 5
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L127
MOV P0, FP
ADD P0, 8
MOV P1, [P0]
MOV P0, 422
MOV [P0], P1
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
MOV P0, 424
MOV [P0], P1
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P0, 426
MOV [P0], P1
; Constant folded: -(1) = -1
MOV R1, -1
MOV P0, 0
MOV :P0, R1
MOV P1, 428
MOV [P1], P0
; Constant folded: -(1) = -1
MOV R1, -1
MOV P0, 0
MOV :P0, R1
MOV P1, 430
MOV [P1], P0
MOV R1, 1
MOV P0, 0
MOV :P0, R1
MOV P1, 364
MOV [P1], P0
L127:
MOV P0, FP
ADD P0, 10
MOV P1, [P0]
MOV P2, 6
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L129
MOV P0, FP
ADD P0, 8
MOV P1, [P0]
MOV P0, 432
MOV [P0], P1
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
MOV P0, 434
MOV [P0], P1
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P0, 436
MOV [P0], P1
MOV R1, 1
MOV P0, 0
MOV :P0, R1
MOV P1, 438
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 440
MOV [P1], P0
MOV R1, 1
MOV P0, 0
MOV :P0, R1
MOV P1, 366
MOV [P1], P0
L129:
MOV P0, FP
ADD P0, 10
MOV P1, [P0]
MOV P2, 7
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L131
MOV P0, FP
ADD P0, 8
MOV P1, [P0]
MOV P0, 442
MOV [P0], P1
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
MOV P0, 444
MOV [P0], P1
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P0, 446
MOV [P0], P1
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 448
MOV [P1], P0
MOV R1, 1
MOV P0, 0
MOV :P0, R1
MOV P1, 450
MOV [P1], P0
MOV R1, 1
MOV P0, 0
MOV :P0, R1
MOV P1, 368
MOV [P1], P0
L131:
MOV P0, FP
ADD P0, 10
MOV P1, [P0]
MOV P2, 1
SHL P2, 3
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L133
MOV P0, FP
ADD P0, 8
MOV P1, [P0]
MOV P0, 452
MOV [P0], P1
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
MOV P0, 454
MOV [P0], P1
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P0, 456
MOV [P0], P1
; Constant folded: -(1) = -1
MOV R1, -1
MOV P0, 0
MOV :P0, R1
MOV P1, 458
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 460
MOV [P1], P0
MOV R1, 1
MOV P0, 0
MOV :P0, R1
MOV P1, 370
MOV [P1], P0
L133:
MOV P0, FP
ADD P0, 10
MOV P1, [P0]
MOV P2, 9
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L135
MOV P0, FP
ADD P0, 8
MOV P1, [P0]
MOV P0, 462
MOV [P0], P1
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
MOV P0, 464
MOV [P0], P1
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P0, 466
MOV [P0], P1
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 468
MOV [P1], P0
; Constant folded: -(1) = -1
MOV R1, -1
MOV P0, 0
MOV :P0, R1
MOV P1, 470
MOV [P1], P0
MOV R1, 1
MOV P0, 0
MOV :P0, R1
MOV P1, 372
MOV [P1], P0
L135:
MOV P0, FP
ADD P0, 10
MOV P1, [P0]
MOV P2, 10
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L137
MOV P0, FP
ADD P0, 8
MOV P1, [P0]
MOV P0, 472
MOV [P0], P1
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
MOV P0, 474
MOV [P0], P1
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P0, 476
MOV [P0], P1
MOV R1, 1
MOV P0, 0
MOV :P0, R1
MOV P1, 478
MOV [P1], P0
; Constant folded: -(1) = -1
MOV R1, -1
MOV P0, 0
MOV :P0, R1
MOV P1, 480
MOV [P1], P0
MOV R1, 1
MOV P0, 0
MOV :P0, R1
MOV P1, 374
MOV [P1], P0
L137:
MOV P0, FP
ADD P0, 10
MOV P1, [P0]
MOV P2, 11
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L139
MOV P0, FP
ADD P0, 8
MOV P1, [P0]
MOV P0, 482
MOV [P0], P1
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
MOV P0, 484
MOV [P0], P1
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P0, 486
MOV [P0], P1
; Constant folded: -(1) = -1
MOV R1, -1
MOV P0, 0
MOV :P0, R1
MOV P1, 488
MOV [P1], P0
MOV R1, 1
MOV P0, 0
MOV :P0, R1
MOV P1, 490
MOV [P1], P0
MOV R1, 1
MOV P0, 0
MOV :P0, R1
MOV P1, 376
MOV [P1], P0
L139:
MOV P0, FP
ADD P0, 10
MOV P1, [P0]
MOV P2, 12
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L141
MOV P0, FP
ADD P0, 8
MOV P1, [P0]
MOV P0, 492
MOV [P0], P1
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
MOV P0, 494
MOV [P0], P1
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P0, 496
MOV [P0], P1
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 498
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 500
MOV [P1], P0
MOV R1, 1
MOV P0, 0
MOV :P0, R1
MOV P1, 378
MOV [P1], P0
L141:
MOV SP, FP
POP FP
RETN 0
_func_asteroidgetactive_12:
; Function: asteroidgetactive
; Parameters: idx
; Locals:  (0 bytes)
ENTER 0
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L143
MOV P0, 356
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L143:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
SHL P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L145
MOV P0, 358
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L145:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 3
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L147
MOV P0, 360
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L147:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
SHL P2, 2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L149
MOV P0, 362
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L149:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 5
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L151
MOV P0, 364
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L151:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 6
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L153
MOV P0, 366
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L153:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 7
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L155
MOV P0, 368
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L155:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
SHL P2, 3
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L157
MOV P0, 370
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L157:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 9
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L159
MOV P0, 372
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L159:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 10
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L161
MOV P0, 374
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L161:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 11
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L163
MOV P0, 376
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L163:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 12
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L165
MOV P0, 378
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L165:
XOR R0, R0
MOV SP, FP
POP FP
RETN R0
_func_asteroidgetx_13:
; Function: asteroidgetx
; Parameters: idx
; Locals:  (0 bytes)
ENTER 0
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L167
MOV P0, 382
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L167:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
SHL P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L169
MOV P0, 392
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L169:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 3
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L171
MOV P0, 402
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L171:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
SHL P2, 2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L173
MOV P0, 412
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L173:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 5
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L175
MOV P0, 422
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L175:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 6
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L177
MOV P0, 432
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L177:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 7
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L179
MOV P0, 442
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L179:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
SHL P2, 3
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L181
MOV P0, 452
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L181:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 9
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L183
MOV P0, 462
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L183:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 10
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L185
MOV P0, 472
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L185:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 11
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L187
MOV P0, 482
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L187:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 12
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L189
MOV P0, 492
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L189:
XOR R0, R0
MOV SP, FP
POP FP
RETN R0
_func_asteroidgety_14:
; Function: asteroidgety
; Parameters: idx
; Locals:  (0 bytes)
ENTER 0
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L191
MOV P0, 384
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L191:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
SHL P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L193
MOV P0, 394
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L193:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 3
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L195
MOV P0, 404
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L195:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
SHL P2, 2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L197
MOV P0, 414
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L197:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 5
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L199
MOV P0, 424
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L199:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 6
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L201
MOV P0, 434
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L201:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 7
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L203
MOV P0, 444
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L203:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
SHL P2, 3
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L205
MOV P0, 454
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L205:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 9
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L207
MOV P0, 464
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L207:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 10
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L209
MOV P0, 474
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L209:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 11
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L211
MOV P0, 484
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L211:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 12
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L213
MOV P0, 494
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L213:
XOR R0, R0
MOV SP, FP
POP FP
RETN R0
_func_asteroidgetsize_15:
; Function: asteroidgetsize
; Parameters: idx
; Locals:  (0 bytes)
ENTER 0
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L215
MOV P0, 386
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L215:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
SHL P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L217
MOV P0, 396
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L217:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 3
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L219
MOV P0, 406
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L219:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
SHL P2, 2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L221
MOV P0, 416
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L221:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 5
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L223
MOV P0, 426
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L223:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 6
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L225
MOV P0, 436
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L225:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 7
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L227
MOV P0, 446
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L227:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
SHL P2, 3
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L229
MOV P0, 456
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L229:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 9
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L231
MOV P0, 466
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L231:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 10
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L233
MOV P0, 476
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L233:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 11
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L235
MOV P0, 486
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L235:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 12
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L237
MOV P0, 496
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
L237:
XOR R0, R0
MOV SP, FP
POP FP
RETN R0
_func_asteroidremove_16:
; Function: asteroidremove
; Parameters: idx
; Locals:  (0 bytes)
ENTER 0
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L239
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 356
MOV [P1], P0
L239:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
SHL P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L241
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 358
MOV [P1], P0
L241:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 3
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L243
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 360
MOV [P1], P0
L243:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
SHL P2, 2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L245
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 362
MOV [P1], P0
L245:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 5
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L247
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 364
MOV [P1], P0
L247:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 6
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L249
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 366
MOV [P1], P0
L249:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 7
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L251
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 368
MOV [P1], P0
L251:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
SHL P2, 3
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L253
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 370
MOV [P1], P0
L253:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 9
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L255
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 372
MOV [P1], P0
L255:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 10
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L257
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 374
MOV [P1], P0
L257:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 11
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L259
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 376
MOV [P1], P0
L259:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 12
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L261
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 378
MOV [P1], P0
L261:
MOV SP, FP
POP FP
RETN 0
_func_asteroidcount_17:
; Function: asteroidcount
; Parameters:
; Locals:  (0 bytes)
ENTER 0
MOV P0, 356
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R4, P0
MOV P0, 358
MOV P0, [P0]
MOV R2, R4
ADD R2, P0
; Free P0 (last use)
; Preserve left operand in register across right-side evaluation
MOV R4, R2
MOV P0, 360
MOV P0, [P0]
MOV R0, R4
ADD R0, P0
; Free P0 (last use)
; Preserve left operand in register across right-side evaluation
MOV R4, R0
MOV P0, 362
MOV P0, [P0]
MOV R1, R4
ADD R1, P0
; Free P0 (last use)
MOV P0, 0
MOV :P0, R1
MOV P1, 502
MOV [P1], P0
MOV P0, 502
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R5, P0
MOV P0, 364
MOV P0, [P0]
MOV R3, R5
ADD R3, P0
; Free P0 (last use)
; Preserve left operand in register across right-side evaluation
MOV R5, R3
MOV P0, 366
MOV P0, [P0]
MOV R2, R5
ADD R2, P0
; Free P0 (last use)
; Preserve left operand in register across right-side evaluation
MOV R5, R2
MOV P0, 368
MOV P0, [P0]
MOV R0, R5
ADD R0, P0
; Free P0 (last use)
; Preserve left operand in register across right-side evaluation
MOV R5, R0
MOV P0, 370
MOV P0, [P0]
MOV R1, R5
ADD R1, P0
; Free P0 (last use)
MOV P0, 0
MOV :P0, R1
MOV P1, 502
MOV [P1], P0
MOV P0, 502
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R5, P0
MOV P0, 372
MOV P0, [P0]
MOV R3, R5
ADD R3, P0
; Free P0 (last use)
; Preserve left operand in register across right-side evaluation
MOV R5, R3
MOV P0, 374
MOV P0, [P0]
MOV R2, R5
ADD R2, P0
; Free P0 (last use)
; Preserve left operand in register across right-side evaluation
MOV R5, R2
MOV P0, 376
MOV P0, [P0]
MOV R0, R5
ADD R0, P0
; Free P0 (last use)
; Preserve left operand in register across right-side evaluation
MOV R5, R0
MOV P0, 378
MOV P0, [P0]
MOV R1, R5
ADD R1, P0
; Free P0 (last use)
MOV P0, 0
MOV :P0, R1
MOV P1, 502
MOV [P1], P0
MOV P0, 502
MOV P0, [P0]
MOV SP, FP
POP FP
RETN P0
_func_asteroidupdatepos_18:
; Function: asteroidupdatepos
; Parameters: idx
; Locals:  (0 bytes)
ENTER 0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 350
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 352
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 504
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 506
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 348
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 508
MOV [P1], P0
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L263
MOV P0, 356
MOV P0, [P0]
MOV P1, 348
MOV [P1], P0
MOV P0, 382
MOV P0, [P0]
MOV P1, 350
MOV [P1], P0
MOV P0, 384
MOV P0, [P0]
MOV P1, 352
MOV [P1], P0
MOV P0, 388
MOV P0, [P0]
MOV P1, 504
MOV [P1], P0
MOV P0, 390
MOV P0, [P0]
MOV P1, 506
MOV [P1], P0
MOV P0, 386
MOV P0, [P0]
MOV P1, 508
MOV [P1], P0
L263:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
SHL P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L265
MOV P0, 358
MOV P0, [P0]
MOV P1, 348
MOV [P1], P0
MOV P0, 392
MOV P0, [P0]
MOV P1, 350
MOV [P1], P0
MOV P0, 394
MOV P0, [P0]
MOV P1, 352
MOV [P1], P0
MOV P0, 398
MOV P0, [P0]
MOV P1, 504
MOV [P1], P0
MOV P0, 400
MOV P0, [P0]
MOV P1, 506
MOV [P1], P0
MOV P0, 396
MOV P0, [P0]
MOV P1, 508
MOV [P1], P0
L265:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 3
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L267
MOV P0, 360
MOV P0, [P0]
MOV P1, 348
MOV [P1], P0
MOV P0, 402
MOV P0, [P0]
MOV P1, 350
MOV [P1], P0
MOV P0, 404
MOV P0, [P0]
MOV P1, 352
MOV [P1], P0
MOV P0, 408
MOV P0, [P0]
MOV P1, 504
MOV [P1], P0
MOV P0, 410
MOV P0, [P0]
MOV P1, 506
MOV [P1], P0
MOV P0, 406
MOV P0, [P0]
MOV P1, 508
MOV [P1], P0
L267:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
SHL P2, 2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L269
MOV P0, 362
MOV P0, [P0]
MOV P1, 348
MOV [P1], P0
MOV P0, 412
MOV P0, [P0]
MOV P1, 350
MOV [P1], P0
MOV P0, 414
MOV P0, [P0]
MOV P1, 352
MOV [P1], P0
MOV P0, 418
MOV P0, [P0]
MOV P1, 504
MOV [P1], P0
MOV P0, 420
MOV P0, [P0]
MOV P1, 506
MOV [P1], P0
MOV P0, 416
MOV P0, [P0]
MOV P1, 508
MOV [P1], P0
L269:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 5
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L271
MOV P0, 364
MOV P0, [P0]
MOV P1, 348
MOV [P1], P0
MOV P0, 422
MOV P0, [P0]
MOV P1, 350
MOV [P1], P0
MOV P0, 424
MOV P0, [P0]
MOV P1, 352
MOV [P1], P0
MOV P0, 428
MOV P0, [P0]
MOV P1, 504
MOV [P1], P0
MOV P0, 430
MOV P0, [P0]
MOV P1, 506
MOV [P1], P0
MOV P0, 426
MOV P0, [P0]
MOV P1, 508
MOV [P1], P0
L271:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 6
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L273
MOV P0, 366
MOV P0, [P0]
MOV P1, 348
MOV [P1], P0
MOV P0, 432
MOV P0, [P0]
MOV P1, 350
MOV [P1], P0
MOV P0, 434
MOV P0, [P0]
MOV P1, 352
MOV [P1], P0
MOV P0, 438
MOV P0, [P0]
MOV P1, 504
MOV [P1], P0
MOV P0, 440
MOV P0, [P0]
MOV P1, 506
MOV [P1], P0
MOV P0, 436
MOV P0, [P0]
MOV P1, 508
MOV [P1], P0
L273:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 7
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L275
MOV P0, 368
MOV P0, [P0]
MOV P1, 348
MOV [P1], P0
MOV P0, 442
MOV P0, [P0]
MOV P1, 350
MOV [P1], P0
MOV P0, 444
MOV P0, [P0]
MOV P1, 352
MOV [P1], P0
MOV P0, 448
MOV P0, [P0]
MOV P1, 504
MOV [P1], P0
MOV P0, 450
MOV P0, [P0]
MOV P1, 506
MOV [P1], P0
MOV P0, 446
MOV P0, [P0]
MOV P1, 508
MOV [P1], P0
L275:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
SHL P2, 3
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L277
MOV P0, 370
MOV P0, [P0]
MOV P1, 348
MOV [P1], P0
MOV P0, 452
MOV P0, [P0]
MOV P1, 350
MOV [P1], P0
MOV P0, 454
MOV P0, [P0]
MOV P1, 352
MOV [P1], P0
MOV P0, 458
MOV P0, [P0]
MOV P1, 504
MOV [P1], P0
MOV P0, 460
MOV P0, [P0]
MOV P1, 506
MOV [P1], P0
MOV P0, 456
MOV P0, [P0]
MOV P1, 508
MOV [P1], P0
L277:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 9
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L279
MOV P0, 372
MOV P0, [P0]
MOV P1, 348
MOV [P1], P0
MOV P0, 462
MOV P0, [P0]
MOV P1, 350
MOV [P1], P0
MOV P0, 464
MOV P0, [P0]
MOV P1, 352
MOV [P1], P0
MOV P0, 468
MOV P0, [P0]
MOV P1, 504
MOV [P1], P0
MOV P0, 470
MOV P0, [P0]
MOV P1, 506
MOV [P1], P0
MOV P0, 466
MOV P0, [P0]
MOV P1, 508
MOV [P1], P0
L279:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 10
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L281
MOV P0, 374
MOV P0, [P0]
MOV P1, 348
MOV [P1], P0
MOV P0, 472
MOV P0, [P0]
MOV P1, 350
MOV [P1], P0
MOV P0, 474
MOV P0, [P0]
MOV P1, 352
MOV [P1], P0
MOV P0, 478
MOV P0, [P0]
MOV P1, 504
MOV [P1], P0
MOV P0, 480
MOV P0, [P0]
MOV P1, 506
MOV [P1], P0
MOV P0, 476
MOV P0, [P0]
MOV P1, 508
MOV [P1], P0
L281:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 11
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L283
MOV P0, 376
MOV P0, [P0]
MOV P1, 348
MOV [P1], P0
MOV P0, 482
MOV P0, [P0]
MOV P1, 350
MOV [P1], P0
MOV P0, 484
MOV P0, [P0]
MOV P1, 352
MOV [P1], P0
MOV P0, 488
MOV P0, [P0]
MOV P1, 504
MOV [P1], P0
MOV P0, 490
MOV P0, [P0]
MOV P1, 506
MOV [P1], P0
MOV P0, 486
MOV P0, [P0]
MOV P1, 508
MOV [P1], P0
L283:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 12
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L285
MOV P0, 378
MOV P0, [P0]
MOV P1, 348
MOV [P1], P0
MOV P0, 492
MOV P0, [P0]
MOV P1, 350
MOV [P1], P0
MOV P0, 494
MOV P0, [P0]
MOV P1, 352
MOV [P1], P0
MOV P0, 498
MOV P0, [P0]
MOV P1, 504
MOV [P1], P0
MOV P0, 500
MOV P0, [P0]
MOV P1, 506
MOV [P1], P0
MOV P0, 496
MOV P0, [P0]
MOV P1, 508
MOV [P1], P0
L285:
MOV P0, 348
MOV P1, [P0]
MOV P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L287
MOV P0, 350
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P0
MOV P0, 504
MOV P0, [P0]
MOV R1, R2
ADD R1, P0
; Free P0 (last use)
MOV P0, 0
MOV :P0, R1
MOV P1, 350
MOV [P1], P0
MOV P0, 350
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JGE L289
MOV P0, 350
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P0
MOV P1, 1
SHL P1, 8
MOV R1, R2
ADD R1, P1
; Free P1 (last use)
MOV P0, 0
MOV :P0, R1
MOV P1, 350
MOV [P1], P0
L289:
MOV P0, 350
MOV P1, [P0]
MOV P2, 255
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JLE L291
MOV P0, 350
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P0
MOV P1, 1
SHL P1, 8
MOV R1, R2
SUB R1, P1
; Free P1 (last use)
MOV P0, 0
MOV :P0, R1
MOV P1, 350
MOV [P1], P0
L291:
MOV P0, 352
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P0
MOV P0, 506
MOV P0, [P0]
MOV R1, R2
ADD R1, P0
; Free P0 (last use)
MOV P0, 0
MOV :P0, R1
MOV P1, 352
MOV [P1], P0
MOV P0, 352
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JGE L293
MOV P0, 352
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P0
MOV P1, 1
SHL P1, 8
MOV R1, R2
ADD R1, P1
; Free P1 (last use)
MOV P0, 0
MOV :P0, R1
MOV P1, 352
MOV [P1], P0
L293:
MOV P0, 352
MOV P1, [P0]
MOV P2, 255
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JLE L295
MOV P0, 352
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P0
MOV P1, 1
SHL P1, 8
MOV R1, R2
SUB R1, P1
; Free P1 (last use)
MOV P0, 0
MOV :P0, R1
MOV P1, 352
MOV [P1], P0
L295:
L287:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L297
MOV P0, 350
MOV P0, [P0]
MOV P1, 382
MOV [P1], P0
MOV P0, 352
MOV P0, [P0]
MOV P1, 384
MOV [P1], P0
L297:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
SHL P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L299
MOV P0, 350
MOV P0, [P0]
MOV P1, 392
MOV [P1], P0
MOV P0, 352
MOV P0, [P0]
MOV P1, 394
MOV [P1], P0
L299:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 3
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L301
MOV P0, 350
MOV P0, [P0]
MOV P1, 402
MOV [P1], P0
MOV P0, 352
MOV P0, [P0]
MOV P1, 404
MOV [P1], P0
L301:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
SHL P2, 2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L303
MOV P0, 350
MOV P0, [P0]
MOV P1, 412
MOV [P1], P0
MOV P0, 352
MOV P0, [P0]
MOV P1, 414
MOV [P1], P0
L303:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 5
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L305
MOV P0, 350
MOV P0, [P0]
MOV P1, 422
MOV [P1], P0
MOV P0, 352
MOV P0, [P0]
MOV P1, 424
MOV [P1], P0
L305:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 6
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L307
MOV P0, 350
MOV P0, [P0]
MOV P1, 432
MOV [P1], P0
MOV P0, 352
MOV P0, [P0]
MOV P1, 434
MOV [P1], P0
L307:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 7
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L309
MOV P0, 350
MOV P0, [P0]
MOV P1, 442
MOV [P1], P0
MOV P0, 352
MOV P0, [P0]
MOV P1, 444
MOV [P1], P0
L309:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
SHL P2, 3
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L311
MOV P0, 350
MOV P0, [P0]
MOV P1, 452
MOV [P1], P0
MOV P0, 352
MOV P0, [P0]
MOV P1, 454
MOV [P1], P0
L311:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 9
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L313
MOV P0, 350
MOV P0, [P0]
MOV P1, 462
MOV [P1], P0
MOV P0, 352
MOV P0, [P0]
MOV P1, 464
MOV [P1], P0
L313:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 10
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L315
MOV P0, 350
MOV P0, [P0]
MOV P1, 472
MOV [P1], P0
MOV P0, 352
MOV P0, [P0]
MOV P1, 474
MOV [P1], P0
L315:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 11
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L317
MOV P0, 350
MOV P0, [P0]
MOV P1, 482
MOV [P1], P0
MOV P0, 352
MOV P0, [P0]
MOV P1, 484
MOV [P1], P0
L317:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 12
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L319
MOV P0, 350
MOV P0, [P0]
MOV P1, 492
MOV [P1], P0
MOV P0, 352
MOV P0, [P0]
MOV P1, 494
MOV [P1], P0
L319:
MOV SP, FP
POP FP
RETN 0
_func_spawnwave_19:
; Function: spawnwave
; Parameters: n
; Locals:  (0 bytes)
ENTER 0
MOV P1, 1
MOV P0, FP
ADD P0, 4
MOV P3, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P3
MOV R3, 1
SHL R3, 1
MOV R0, R2
ADD R0, R3
; Free R3 (last use)
MOV P2, R0
L321:
CMP P1, P2
JGT L322
PUSH P1
CALL _func_asteroidgetslot_10
POP P1
MOV R1, R0
MOV P0, 0
MOV :P0, R1
MOV P3, 510
MOV [P3], P0
MOV P0, 510
MOV P0, [P0]
XOR R1, R1
CMP P0, R1
; Free P0 (last use)
; Free R1 (last use)
JLE L323
XOR R0, R0
MOV R2, 3
RNDR R1, R0, R2
; Free R0 (last use)
; Free R2 (last use)
MOV P0, 0
MOV :P0, R1
MOV P3, 512
MOV [P3], P0
MOV P0, 512
MOV P0, [P0]
XOR R1, R1
CMP P0, R1
; Free P0 (last use)
; Free R1 (last use)
JNZ L325
PUSH P1
MOV P0, 510
MOV P0, [P0]
PUSH P0
; Free P0 (last use)
XOR R3, R3
MOV R4, 255
RNDR R2, R3, R4
; Free R3 (last use)
; Free R4 (last use)
MOV P3, R2
PUSH P3
; Free R2 (last use)
XOR R2, R2
MOV P3, R2
PUSH P3
; Free R2 (last use)
MOV R3, 10
MOV R4, 18
RNDR R2, R3, R4
; Free R3 (last use)
; Free R4 (last use)
MOV P3, R2
PUSH P3
; Free R2 (last use)
CALL _func_asteroidspawn_11
ADD SP, 8
POP P1
L325:
MOV P0, 512
MOV P0, [P0]
MOV R1, 1
CMP P0, R1
; Free P0 (last use)
; Free R1 (last use)
JNZ L327
PUSH P1
MOV P0, 510
MOV P0, [P0]
PUSH P0
; Free P0 (last use)
MOV P3, 255
PUSH P3
; Free R2 (last use)
XOR R3, R3
MOV R4, 255
RNDR R2, R3, R4
; Free R3 (last use)
; Free R4 (last use)
MOV P3, R2
PUSH P3
; Free R2 (last use)
MOV R3, 10
MOV R4, 18
RNDR R2, R3, R4
; Free R3 (last use)
; Free R4 (last use)
MOV P3, R2
PUSH P3
; Free R2 (last use)
CALL _func_asteroidspawn_11
ADD SP, 8
POP P1
L327:
MOV P0, 512
MOV P0, [P0]
MOV R1, 1
SHL R1, 1
CMP P0, R1
; Free P0 (last use)
; Free R1 (last use)
JNZ L329
PUSH P1
MOV P0, 510
MOV P0, [P0]
PUSH P0
; Free P0 (last use)
XOR R3, R3
MOV R4, 255
RNDR R2, R3, R4
; Free R3 (last use)
; Free R4 (last use)
MOV P3, R2
PUSH P3
; Free R2 (last use)
MOV P3, 255
PUSH P3
; Free R2 (last use)
MOV R3, 10
MOV R4, 18
RNDR R2, R3, R4
; Free R3 (last use)
; Free R4 (last use)
MOV P3, R2
PUSH P3
; Free R2 (last use)
CALL _func_asteroidspawn_11
ADD SP, 8
POP P1
L329:
MOV P0, 512
MOV P0, [P0]
MOV R1, 3
CMP P0, R1
; Free P0 (last use)
; Free R1 (last use)
JNZ L331
PUSH P1
MOV P0, 510
MOV P0, [P0]
PUSH P0
; Free P0 (last use)
XOR R2, R2
MOV P3, R2
PUSH P3
; Free R2 (last use)
XOR R3, R3
MOV R4, 255
RNDR R2, R3, R4
; Free R3 (last use)
; Free R4 (last use)
MOV P3, R2
PUSH P3
; Free R2 (last use)
MOV R3, 10
MOV R4, 18
RNDR R2, R3, R4
; Free R3 (last use)
; Free R4 (last use)
MOV P3, R2
PUSH P3
; Free R2 (last use)
CALL _func_asteroidspawn_11
ADD SP, 8
POP P1
L331:
L323:
INC P1
JMP L321
L322:
MOV SP, FP
POP FP
RETN 0
_func_drawship_20:
; Function: drawship
; Parameters: x, y, angle, color
; Locals:  (0 bytes)
ENTER 0
MOV P0, FP
ADD P0, 10
MOV P1, [P0]
MOV P0, 514
MOV [P0], P1
MOV P0, FP
ADD P0, 8
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R1, R2
SUB R1, R3
; Free R3 (last use)
MOV P0, 0
MOV :P0, R1
MOV P2, 516
MOV [P2], P0
MOV P0, FP
ADD P0, 10
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 5
MOV R1, R2
SUB R1, R3
; Free R3 (last use)
MOV P0, 0
MOV :P0, R1
MOV P2, 518
MOV [P2], P0
MOV P0, FP
ADD P0, 8
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 5
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
MOV P0, 0
MOV :P0, R1
MOV P2, 520
MOV [P2], P0
MOV P0, FP
ADD P0, 10
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 5
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
MOV P0, 0
MOV :P0, R1
MOV P2, 522
MOV [P2], P0
MOV P0, FP
ADD P0, 8
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 5
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
MOV P0, 0
MOV :P0, R1
MOV P2, 524
MOV [P2], P0
MOV VM, 0
MOV VL, 5
MOV P0, 514
MOV P0, [P0]
MOV VX, :P0
MOV P0, 516
MOV P0, [P0]
MOV VY, :P0
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV VC, :P1
MOV P0, 518
MOV P0, [P0]
MOV P0, 520
MOV P0, [P0]
SLINE P0, P0
MOV P0, 518
MOV P0, [P0]
MOV VX, :P0
MOV P0, 520
MOV P0, [P0]
MOV VY, :P0
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV VC, :P1
MOV P0, 522
MOV P0, [P0]
MOV P0, 524
MOV P0, [P0]
SLINE P0, P0
MOV P0, 522
MOV P0, [P0]
MOV VX, :P0
MOV P0, 524
MOV P0, [P0]
MOV VY, :P0
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV VC, :P1
MOV P0, 514
MOV P0, [P0]
MOV P0, 516
MOV P0, [P0]
SLINE P0, P0
MOV SP, FP
POP FP
RETN 0
_func_handleinput_21:
; Function: handleinput
; Parameters:
; Locals:  (0 bytes)
ENTER 0
KEYIN R0
MOV R1, R0
MOV P0, 0
MOV :P0, R1
MOV P1, 526
MOV [P1], P0
MOV P0, 526
MOV P1, [P0]
MOV P2, 97
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L333
JMP rotLeft
L333:
MOV P0, 526
MOV P1, [P0]
MOV P2, 1
SHL P2, 7
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L335
JMP rotLeft
L335:
JMP rotDone
rotLeft:
; Allocate struct Ship (Ship) at 0x0210
; Load Ship.angle
MOV P0, 536
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R1, R2
SUB R1, R3
; Free R3 (last use)
; Store to Ship.angle
MOV P0, 536
MOV P1, R1
MOV [P0], P1
; Load Ship.angle
MOV P0, 536
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JGE L337
; Load Ship.angle
MOV P0, 536
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV P0, 360
MOV R1, R2
ADD R1, P0
; Free P0 (last use)
; Store to Ship.angle
MOV P0, 536
MOV P1, R1
MOV [P0], P1
L337:
rotDone:
MOV P0, 526
MOV P1, [P0]
MOV P2, 100
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L339
JMP rotRight
L339:
MOV P0, 526
MOV P1, [P0]
MOV P2, 129
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L341
JMP rotRight
L341:
JMP rotRightDone
rotRight:
; Load Ship.angle
MOV P0, 536
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
; Store to Ship.angle
MOV P0, 536
MOV P1, R1
MOV [P0], P1
; Load Ship.angle
MOV P0, 536
MOV P1, [P0]
MOV P2, 359
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JLE L343
; Load Ship.angle
MOV P0, 536
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV P0, 360
MOV R1, R2
SUB R1, P0
; Free P0 (last use)
; Store to Ship.angle
MOV P0, 536
MOV P1, R1
MOV [P0], P1
L343:
rotRightDone:
MOV P0, 526
MOV P1, [P0]
MOV P2, 119
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L345
JMP doThrust
L345:
MOV P0, 526
MOV P1, [P0]
MOV P2, 130
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L347
JMP doThrust
L347:
JMP noThrust
doThrust:
; Load Ship.dx
MOV P0, 532
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 1
MOV R1, R2
SUB R1, R3
; Free R3 (last use)
; Store to Ship.dx
MOV P0, 532
MOV P1, R1
MOV [P0], P1
; Load Ship.dy
MOV P0, 534
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 1
MOV R1, R2
SUB R1, R3
; Free R3 (last use)
; Store to Ship.dy
MOV P0, 534
MOV P1, R1
MOV [P0], P1
MOV R1, 1
SHL R1, 3
; Store to Ship.thrust
MOV P0, 538
MOV P1, R1
MOV [P0], P1
noThrust:
; Load Ship.thrust
MOV P0, 538
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JLE L349
; Load Ship.thrust
MOV P0, 538
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
MOV R1, R2
SUB R1, R3
; Free R3 (last use)
; Store to Ship.thrust
MOV P0, 538
MOV P1, R1
MOV [P0], P1
L349:
MOV P0, 526
MOV P1, [P0]
MOV P2, 101
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L351
JMP doFire
L351:
JMP noFire
doFire:
CALL _func_bulletgetslot_2
MOV R1, R0
MOV P0, 0
MOV :P0, R1
MOV P1, 510
MOV [P1], P0
MOV P0, 510
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JLE L353
MOV P0, 510
MOV P0, [P0]
PUSH P0
; Free P0 (last use)
; Load Ship.x
MOV P0, 528
MOV P1, [P0]
PUSH P1
; Load Ship.y
MOV P0, 530
MOV P1, [P0]
PUSH P1
CALL _func_bulletspawn_3
ADD SP, 6
L353:
noFire:
MOV SP, FP
POP FP
RETN 0
_func_updatephysics_22:
; Function: updatephysics
; Parameters:
; Locals:  (0 bytes)
ENTER 0
; Load Ship.dx
MOV P0, 532
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R3, P1
MOV R4, 3
MOV R0, R3
MUL R0, R4
; Free R4 (last use)
; Preserve left operand in register across right-side evaluation
MOV R3, R0
MOV R4, 1
SHL R4, 2
MOV R1, R3
DIV R1, R4
; Free R4 (last use)
; Store to Ship.dx
MOV P0, 532
MOV P1, R1
MOV [P0], P1
; Load Ship.dy
MOV P0, 534
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R3, P1
MOV R4, 3
MOV R0, R3
MUL R0, R4
; Free R4 (last use)
; Preserve left operand in register across right-side evaluation
MOV R3, R0
MOV R4, 1
SHL R4, 2
MOV R1, R3
DIV R1, R4
; Free R4 (last use)
; Store to Ship.dy
MOV P0, 534
MOV P1, R1
MOV [P0], P1
; Load Ship.x
MOV P0, 528
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
; Load Ship.dx
MOV P0, 532
MOV P1, [P0]
MOV R1, R2
ADD R1, P1
; Store to Ship.x
MOV P0, 528
MOV P1, R1
MOV [P0], P1
; Load Ship.y
MOV P0, 530
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
; Load Ship.dy
MOV P0, 534
MOV P1, [P0]
MOV R1, R2
ADD R1, P1
; Store to Ship.y
MOV P0, 530
MOV P1, R1
MOV [P0], P1
; Load Ship.x
MOV P0, 528
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JGE L355
; Load Ship.x
MOV P0, 528
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV P0, 1
SHL P0, 8
MOV R1, R2
ADD R1, P0
; Free P0 (last use)
; Store to Ship.x
MOV P0, 528
MOV P1, R1
MOV [P0], P1
L355:
; Load Ship.x
MOV P0, 528
MOV P1, [P0]
MOV P2, 255
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JLE L357
; Load Ship.x
MOV P0, 528
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV P0, 1
SHL P0, 8
MOV R1, R2
SUB R1, P0
; Free P0 (last use)
; Store to Ship.x
MOV P0, 528
MOV P1, R1
MOV [P0], P1
L357:
; Load Ship.y
MOV P0, 530
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JGE L359
; Load Ship.y
MOV P0, 530
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV P0, 1
SHL P0, 8
MOV R1, R2
ADD R1, P0
; Free P0 (last use)
; Store to Ship.y
MOV P0, 530
MOV P1, R1
MOV [P0], P1
L359:
; Load Ship.y
MOV P0, 530
MOV P1, [P0]
MOV P2, 255
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JLE L361
; Load Ship.y
MOV P0, 530
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV P0, 1
SHL P0, 8
MOV R1, R2
SUB R1, P0
; Free P0 (last use)
; Store to Ship.y
MOV P0, 530
MOV P1, R1
MOV [P0], P1
L361:
; Load Ship.invuln
MOV P0, 542
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JLE L363
; Load Ship.invuln
MOV P0, 542
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
MOV R1, R2
SUB R1, R3
; Free R3 (last use)
; Store to Ship.invuln
MOV P0, 542
MOV P1, R1
MOV [P0], P1
L363:
MOV SP, FP
POP FP
RETN 0
_func_checkasteroidcollision_23:
; Function: checkasteroidcollision
; Parameters: ax, ay, asize, px, py, pr
; Locals:  (0 bytes)
ENTER 0
MOV P0, FP
ADD P0, 8
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV P0, FP
ADD P0, 14
MOV P2, [P0]
MOV R1, R2
SUB R1, P2
; Free P2 (last use)
MOV P0, 0
MOV :P0, R1
MOV P2, 504
MOV [P2], P0
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV P0, FP
ADD P0, 12
MOV P2, [P0]
MOV R1, R2
SUB R1, P2
; Free P2 (last use)
MOV P0, 0
MOV :P0, R1
MOV P2, 506
MOV [P2], P0
MOV P0, 504
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R3, P0
MOV P0, 504
MOV P0, [P0]
MOV R0, R3
MUL R0, P0
; Free P0 (last use)
; Preserve left operand in register across right-side evaluation
MOV R3, R0
MOV P0, 506
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R7, P0
MOV P0, 506
MOV P0, [P0]
MOV R5, R7
MUL R5, P0
; Free P0 (last use)
MOV R1, R3
ADD R1, R5
; Free R5 (last use)
MOV P0, 0
MOV :P0, R1
MOV P1, 548
MOV [P1], P0
MOV P0, 548
MOV P1, [P0]
MOV R0, 0
; Preserve left operand in register across right-side evaluation
MOV R1, R0
MOV R2, 0
MOV P2, R1
MUL P2, R2
; Free R2 (last use)
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JGE L365
MOV R0, 1
MOV SP, FP
POP FP
RETN R0
L365:
XOR R0, R0
MOV SP, FP
POP FP
RETN R0
_func_checkcollisions_24:
; Function: checkcollisions
; Parameters:
; Locals:  (0 bytes)
ENTER 0
MOV P1, 1
MOV P0, 550
MOV P2, [P0]
L367:
CMP P1, P2
JGT L368
PUSH P1
PUSH P1
CALL _func_bulletgetactive_5
ADD SP, 2
POP P1
MOV R1, R0
MOV P0, 0
MOV :P0, R1
MOV P3, 552
MOV [P3], P0
MOV P0, 552
MOV P0, [P0]
MOV R1, 1
CMP P0, R1
; Free P0 (last use)
; Free R1 (last use)
JNZ L369
PUSH P1
PUSH P1
CALL _func_bulletgetx_6
ADD SP, 2
POP P1
MOV R1, R0
MOV P0, 0
MOV :P0, R1
MOV P3, 554
MOV [P3], P0
PUSH P1
PUSH P1
CALL _func_bulletgety_7
ADD SP, 2
POP P1
MOV R1, R0
MOV P0, 0
MOV :P0, R1
MOV P3, 556
MOV [P3], P0
MOV P4, 1
MOV P0, 558
MOV P5, [P0]
L371:
CMP P4, P5
JGT L372
PUSH P1
PUSH P4
PUSH P4
CALL _func_asteroidgetactive_12
ADD SP, 2
POP P4
POP P1
MOV R1, R0
MOV P0, 0
MOV :P0, R1
MOV P3, 560
MOV [P3], P0
MOV P0, 560
MOV P0, [P0]
MOV R1, 1
CMP P0, R1
; Free P0 (last use)
; Free R1 (last use)
JNZ L373
PUSH P1
PUSH P4
PUSH P4
CALL _func_asteroidgetx_13
ADD SP, 2
POP P4
POP P1
MOV R1, R0
MOV P0, 0
MOV :P0, R1
MOV P3, 562
MOV [P3], P0
PUSH P1
PUSH P4
PUSH P4
CALL _func_asteroidgety_14
ADD SP, 2
POP P4
POP P1
MOV R1, R0
MOV P0, 0
MOV :P0, R1
MOV P3, 564
MOV [P3], P0
PUSH P1
PUSH P4
PUSH P4
CALL _func_asteroidgetsize_15
ADD SP, 2
POP P4
POP P1
MOV R1, R0
MOV P0, 0
MOV :P0, R1
MOV P3, 566
MOV [P3], P0
PUSH P1
PUSH P4
MOV P0, 562
MOV P0, [P0]
PUSH P0
; Free P0 (last use)
MOV P0, 564
MOV P0, [P0]
PUSH P0
; Free P0 (last use)
MOV P0, 566
MOV P0, [P0]
PUSH P0
; Free P0 (last use)
MOV P0, 554
MOV P0, [P0]
PUSH P0
; Free P0 (last use)
MOV P0, 556
MOV P0, [P0]
PUSH P0
; Free P0 (last use)
MOV R6, 1
SHL R6, 1
MOV P3, R6
PUSH P3
; Free R6 (last use)
CALL _func_checkasteroidcollision_23
ADD SP, 12
POP P4
POP P1
MOV R1, R0
MOV P0, 0
MOV :P0, R1
MOV P3, 568
MOV [P3], P0
MOV P0, 568
MOV P0, [P0]
MOV R1, 1
CMP P0, R1
; Free P0 (last use)
; Free R1 (last use)
JNZ L375
PUSH P1
PUSH P4
PUSH P4
CALL _func_asteroidremove_16
ADD SP, 2
POP P4
POP P1
PUSH P1
PUSH P4
PUSH P1
CALL _func_bulletremove_8
ADD SP, 2
POP P4
POP P1
; Load Ship.score
MOV P0, 546
MOV P3, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P3
MOV R3, 10
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
; Store to Ship.score
MOV P0, 546
MOV P1, R1
MOV [P0], P1
MOV P0, 880
MOV R0, 100
MOV R1, 192
MOV SF, P0
MOV SV, R1
MOV SW, 0
SPLAY
; Duration handling - simplified
L375:
L373:
INC P4
JMP L371
L372:
L369:
INC P1
JMP L367
L368:
; Load Ship.invuln
MOV P0, 542
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JGT L377
MOV P1, 1
MOV P0, 558
MOV P2, [P0]
L379:
CMP P1, P2
JGT L380
PUSH P1
PUSH P1
CALL _func_asteroidgetactive_12
ADD SP, 2
POP P1
MOV R1, R0
MOV P0, 0
MOV :P0, R1
MOV P3, 560
MOV [P3], P0
MOV P0, 560
MOV P0, [P0]
MOV R1, 1
CMP P0, R1
; Free P0 (last use)
; Free R1 (last use)
JNZ L381
PUSH P1
PUSH P1
CALL _func_asteroidgetx_13
ADD SP, 2
POP P1
MOV R1, R0
MOV P0, 0
MOV :P0, R1
MOV P3, 562
MOV [P3], P0
PUSH P1
PUSH P1
CALL _func_asteroidgety_14
ADD SP, 2
POP P1
MOV R1, R0
MOV P0, 0
MOV :P0, R1
MOV P3, 564
MOV [P3], P0
PUSH P1
PUSH P1
CALL _func_asteroidgetsize_15
ADD SP, 2
POP P1
MOV R1, R0
MOV P0, 0
MOV :P0, R1
MOV P3, 566
MOV [P3], P0
PUSH P1
MOV P0, 562
MOV P0, [P0]
PUSH P0
; Free P0 (last use)
MOV P0, 564
MOV P0, [P0]
PUSH P0
; Free P0 (last use)
MOV P0, 566
MOV P0, [P0]
PUSH P0
; Free P0 (last use)
; Load Ship.x
MOV P0, 528
MOV P3, [P0]
PUSH P3
; Load Ship.y
MOV P0, 530
MOV P3, [P0]
PUSH P3
MOV R6, 1
SHL R6, 2
MOV P3, R6
PUSH P3
; Free R6 (last use)
CALL _func_checkasteroidcollision_23
ADD SP, 12
POP P1
MOV R1, R0
MOV P0, 0
MOV :P0, R1
MOV P3, 568
MOV [P3], P0
MOV P0, 568
MOV P0, [P0]
MOV R1, 1
CMP P0, R1
; Free P0 (last use)
; Free R1 (last use)
JNZ L383
; Load Ship.lives
MOV P0, 540
MOV P3, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P3
MOV R3, 1
MOV R1, R2
SUB R1, R3
; Free R3 (last use)
; Store to Ship.lives
MOV P0, 540
MOV P1, R1
MOV [P0], P1
MOV R1, 120
; Store to Ship.invuln
MOV P0, 542
MOV P1, R1
MOV [P0], P1
; Load Ship.dx
MOV P0, 532
MOV P3, [P0]
MOV R0, P3
NEG R0
MOV R1, R0
SHL R1, 1
; Free R0 (last use)
; Store to Ship.dx
MOV P0, 532
MOV P1, R1
MOV [P0], P1
; Load Ship.dy
MOV P0, 534
MOV P3, [P0]
MOV R0, P3
NEG R0
MOV R1, R0
SHL R1, 1
; Free R0 (last use)
; Store to Ship.dy
MOV P0, 534
MOV P1, R1
MOV [P0], P1
MOV R0, 220
MOV P0, 300
MOV R1, 255
MOV SF, R0
MOV SV, R1
MOV SW, 0
SPLAY
; Duration handling - simplified
; Load Ship.lives
MOV P0, 540
MOV P3, [P0]
XOR R1, R1
CMP P3, R1
; Free R1 (last use)
JGT L385
MOV R1, 1
MOV P0, 0
MOV :P0, R1
MOV P3, 570
MOV [P3], P0
L385:
L383:
L381:
INC P1
JMP L379
L380:
L377:
MOV SP, FP
POP FP
RETN 0
_func_renderframe_25:
; Function: renderframe
; Parameters:
; Locals:  (0 bytes)
ENTER 0
MOV VM, 0
MOV VL, 1
SHL VL, 2
; ClrDraw
MOV VM, 0
MOV VL, 1
SFILL 0x00
MOV VM, 0
MOV VL, 5
; ClrDraw
MOV VM, 0
MOV VL, 1
SFILL 0x00
MOV VM, 0
MOV VL, 1
SHL VL, 2
MOV P1, 1
MOV P0, 558
MOV P2, [P0]
L387:
CMP P1, P2
JGT L388
PUSH P1
PUSH P1
CALL _func_asteroidgetactive_12
ADD SP, 2
POP P1
MOV R1, R0
MOV P0, 0
MOV :P0, R1
MOV P3, 560
MOV [P3], P0
MOV P0, 560
MOV P0, [P0]
MOV R1, 1
CMP P0, R1
; Free P0 (last use)
; Free R1 (last use)
JNZ L389
PUSH P1
PUSH P1
CALL _func_asteroidgetx_13
ADD SP, 2
POP P1
MOV VX, R0
PUSH P1
PUSH P1
CALL _func_asteroidgety_14
ADD SP, 2
POP P1
MOV VY, R0
MOV VC, 14
PUSH P1
PUSH P1
CALL _func_asteroidgetsize_15
ADD SP, 2
POP P1
SCIRC R0, 1
L389:
INC P1
JMP L387
L388:
MOV VM, 0
MOV VL, 5
MOV P0, 570
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L391
MOV R1, 1
MOV P0, 0
MOV :P0, R1
MOV P1, 572
MOV [P1], P0
; Load Ship.invuln
MOV P0, 542
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JLE L393
; Load Ship.invuln
MOV P0, 542
MOV P2, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P2
MOV R3, 1
SHL R3, 2
MOV R0, R2
DIV R0, R3
; Free R3 (last use)
MOV P1, R0
SHL P1, 2
; Free R0 (last use)
; Load Ship.invuln
MOV P0, 542
MOV P2, [P0]
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L395
MOV R1, 1
MOV P0, 0
MOV :P0, R1
MOV P1, 572
MOV [P1], P0
JMP L396
L395:
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 572
MOV [P1], P0
L396:
L393:
MOV P0, 572
MOV P1, [P0]
MOV P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L397
; Load Ship.x
MOV P0, 528
MOV P1, [P0]
PUSH P1
; Load Ship.y
MOV P0, 530
MOV P1, [P0]
PUSH P1
; Load Ship.angle
MOV P0, 536
MOV P1, [P0]
PUSH P1
MOV P1, 31
PUSH P1
; Free R4 (last use)
CALL _func_drawship_20
ADD SP, 8
; Load Ship.thrust
MOV P0, 538
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JLE L399
; Load Ship.x
MOV P0, 528
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
MOV R0, R2
ADD R0, R3
; Free R3 (last use)
MOV VX, R0
; Load Ship.y
MOV P0, 530
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R3, P1
MOV R4, 10
MOV R0, R3
ADD R0, R4
; Free R4 (last use)
MOV VY, R0
MOV VC, 11
SWRITE VC
; Load Ship.x
MOV P0, 528
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
MOV R0, R2
SUB R0, R3
; Free R3 (last use)
MOV VX, R0
; Load Ship.y
MOV P0, 530
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R3, P1
MOV R4, 10
MOV R0, R3
ADD R0, R4
; Free R4 (last use)
MOV VY, R0
MOV VC, 11
SWRITE VC
L399:
L397:
L391:
MOV P1, 1
MOV P0, 550
MOV P2, [P0]
L401:
CMP P1, P2
JGT L402
PUSH P1
PUSH P1
CALL _func_bulletgetactive_5
ADD SP, 2
POP P1
MOV R1, R0
MOV P0, 0
MOV :P0, R1
MOV P3, 552
MOV [P3], P0
MOV P0, 552
MOV P0, [P0]
MOV R1, 1
CMP P0, R1
; Free P0 (last use)
; Free R1 (last use)
JNZ L403
PUSH P1
PUSH P1
CALL _func_bulletgetx_6
ADD SP, 2
POP P1
MOV VX, R0
PUSH P1
PUSH P1
CALL _func_bulletgety_7
ADD SP, 2
POP P1
MOV VY, R0
MOV VC, 31
SWRITE VC
L403:
INC P1
JMP L401
L402:
MOV VM, 0
XOR VL, VL
XOR VX, VX
XOR VY, VY
MOV VC, 15
TEXT STR404
MOV VX, 48
XOR VY, VY
MOV VC, 15
; Load Ship.score
MOV P0, 546
MOV P1, [P0]
MOV R0, P1
ITOS P1, R0
TEXT P1
MOV VX, 140
XOR VY, VY
MOV VC, 15
TEXT STR405
MOV VX, 188
XOR VY, VY
MOV VC, 15
; Load Ship.lives
MOV P0, 540
MOV P1, [P0]
MOV R0, P1
ITOS P1, R0
TEXT P1
XOR VX, VX
MOV VY, 248
MOV VC, 10
TEXT STR406
MOV VX, 36
MOV VY, 248
MOV VC, 10
MOV P0, 574
MOV P0, [P0]
MOV R0, P0
ITOS P1, R0
TEXT P1
MOV SP, FP
POP FP
RETN 0
_func_rendergameover_26:
; Function: rendergameover
; Parameters:
; Locals:  (0 bytes)
ENTER 0
MOV VM, 0
MOV VL, 1
SHL VL, 2
; ClrDraw
MOV VM, 0
MOV VL, 1
SFILL 0x00
MOV VM, 0
MOV VL, 5
; ClrDraw
MOV VM, 0
MOV VL, 1
SFILL 0x00
MOV VM, 0
XOR VL, VL
MOV VX, 80
MOV VY, 120
MOV VC, 31
TEXT STR407
MOV VX, 1
SHL VX, 6
MOV VY, 136
MOV VC, 15
TEXT STR408
MOV VX, 112
MOV VY, 136
MOV VC, 15
; Load Ship.score
MOV P0, 546
MOV P1, [P0]
MOV R0, P1
ITOS P1, R0
TEXT P1
MOV VX, 48
MOV VY, 160
MOV VC, 10
TEXT STR409
MOV SP, FP
POP FP
RETN 0
_func_initgame_27:
; Function: initgame
; Parameters:
; Locals:  (0 bytes)
ENTER 0
MOV R1, 1
SHL R1, 7
; Store to Ship.x
MOV P0, 528
MOV P1, R1
MOV [P0], P1
MOV R1, 1
SHL R1, 7
; Store to Ship.y
MOV P0, 530
MOV P1, R1
MOV [P0], P1
XOR R1, R1
; Store to Ship.dx
MOV P0, 532
MOV P1, R1
MOV [P0], P1
XOR R1, R1
; Store to Ship.dy
MOV P0, 534
MOV P1, R1
MOV [P0], P1
XOR R1, R1
; Store to Ship.angle
MOV P0, 536
MOV P1, R1
MOV [P0], P1
XOR R1, R1
; Store to Ship.thrust
MOV P0, 538
MOV P1, R1
MOV [P0], P1
MOV R1, 3
; Store to Ship.lives
MOV P0, 540
MOV P1, R1
MOV [P0], P1
MOV R1, 120
; Store to Ship.invuln
MOV P0, 542
MOV P1, R1
MOV [P0], P1
XOR R1, R1
; Store to Ship.score
MOV P0, 546
MOV P1, R1
MOV [P0], P1
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 570
MOV [P1], P0
MOV R1, 1
MOV P0, 0
MOV :P0, R1
MOV P1, 574
MOV [P1], P0
CALL _func_asteroidinitall_9
CALL _func_bulletinitall_0
MOV P0, 574
MOV P0, [P0]
PUSH P0
; Free P0 (last use)
CALL _func_spawnwave_19
ADD SP, 2
MOV SP, FP
POP FP
RETN 0
STR404: DEFSTR "SCORE:"
STR405: DEFSTR "LIVES:"
STR406: DEFSTR "WAVE:"
STR407: DEFSTR "GAME OVER"
STR408: DEFSTR "Score:"
STR409: DEFSTR "Press R to restart"
STR410: DEFSTR "ASTEROIDS"
STR411: DEFSTR "Press any key"