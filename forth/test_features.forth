\ Test control flow and Nova-16 features
: TEST_CONTROL
  10 0 DO
    I DUP .
    I 2 = IF
      ." Found 2!" 
    THEN
  LOOP
;

: TEST_GRAPHICS
  0 VMODE
  1 LAYER
  100 50 15 PIXEL
  0 VX! 0 VY! 14 SWRITE
;

TEST_CONTROL
TEST_GRAPHICS
