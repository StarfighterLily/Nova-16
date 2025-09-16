; Simple NOVA-16 Performance Benchmark
; Tests basic performance metrics using confirmed working instructions

ORG 0x1000

; Result storage locations
RESULT_ADDR EQU 0x2000

MAIN:
    ; Simple instruction timing test
    MOV R0, 0        ; Initialize counter
    MOV R1, 100      ; Loop count

TIMING_LOOP:
    NOP              ; Simple instruction
    NOP
    NOP
    NOP
    NOP
    INC R0           ; Increment counter
    CMP R0, R1       ; Compare with limit
    JNZ TIMING_LOOP  ; Loop if not equal

    ; Store result (R0 should be 100)
    MOV P0, RESULT_ADDR
    MOV [P0], R0

    HLT              ; End benchmark</content>
<parameter name="filePath">c:\Code\Nova\asm\simple_benchmark.asm