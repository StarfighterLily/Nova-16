; Test conditional assembly
DEBUG EQU 1

IFDEF DEBUG
    DEBUG_MSG DB "Debug mode"
ELSE
    RELEASE_MSG DB "Release mode"
ENDIF

IFNDEF RELEASE
    TEST_DATA DB 42
ENDIF

MAIN:
    HLT