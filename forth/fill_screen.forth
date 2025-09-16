VARIABLE X
VARIABLE Y
VARIABLE COLOR

: FILL_SCREEN
  0 VMODE        \ Set to coordinate mode
  0 LAYER        \ Use layer 0 (main screen)
  0 X !
  0 Y !
  0 COLOR !

  BEGIN
    0 VX !       \ Hardcode coordinates to test
    0 VY !
    255 SWRITE   \ Draw white pixel
    X @ 1 + X !  \ Increment counter
    X @ 10 =     \ Exit after 10 iterations
  UNTIL
;

FILL_SCREEN
