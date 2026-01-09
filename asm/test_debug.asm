ORG 0x0000

; Test hardware breakpoints and single-step trap

SETBP R0, 0x0010  ; Set breakpoint 0 at address 0x0010
ENABRK           ; Enable breakpoints
ENATRAP          ; Enable single-step trap

MOV R0, 0x42     ; Some instruction
MOV R1, 0x43     ; Another

; At 0x0010
MOV R2, 0x44     ; This should trigger breakpoint

DISATRAP         ; Disable trap
DISBRK           ; Disable breakpoints

HLT