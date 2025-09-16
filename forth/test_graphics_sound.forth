: DRAW-PIXEL
    100 120 15 PIXEL
;

: SETUP-GRAPHICS
    0 VMODE
    1 LAYER
;

: PLAY-TONE
    8192 440 128 1 SOUND
    PLAY
;

: MAIN
    SETUP-GRAPHICS
    DRAW-PIXEL
    PLAY-TONE
    ." Graphics and sound test complete!"
;
