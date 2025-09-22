0 LAYER
0 VMODE

: WFILL
    256 0 DO
        256 0 DO
            I J 15 PIXEL
        LOOP
    LOOP
;
: BFILL
    256 0 DO
        256 0 DO
            I J 0 PIXEL
        LOOP
    LOOP
;
5 0 DO
    WFILL
    BFILL
LOOP
