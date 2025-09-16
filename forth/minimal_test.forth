VARIABLE X
VARIABLE Y
VARIABLE COLOR

: FILL_SCREEN
  1 VMODE !     \ Memory mode
  1 LAYER !     \ Layer 1

  0 X !
  0 Y !
  0 COLOR !

  BEGIN
    X @ VX !
    Y @ VY !
    COLOR @ SWRITE

    1 X +!
    X @ 4 = IF
      0 X !
      1 Y +!
      Y @ 4 = IF
        EXIT
      THEN
    THEN
  AGAIN
;
