( Enhanced Nova-16 Graphics Test )
( Demonstrates new hardware features in FORTH compiler )

( Setup graphics mode )
0 VMODE      ( Set coordinate mode )
1 LAYER      ( Set to layer 1 )

( Draw some pixels using new VX!/VY! words )
50 VX!       ( Set X coordinate )
60 VY!       ( Set Y coordinate )
15 SWRITE    ( Write bright white pixel )

( Use advanced sprite functionality )
0 10 20 12 SPRITE    ( Sprite 0 at (10,20) with color 12 )

( Get sprite control block address for direct manipulation )
0 SPRITEBLOCK        ( Get address of sprite 0 control block )
42 SWAP !            ( Store value 42 in first byte of control block )

( Use direct graphics memory access )
0x8000 5 GFXMEM     ( Write color 5 to graphics memory at 0x8000 )

( Advanced sound with multiple parameters )
440 128 1 SOUNDREG   ( Frequency 440Hz, volume 128, waveform 1 )

( Timer operation )
1000 TIMER!          ( Set timer to 1000 )

( Test memory mode graphics )
1 VM!                ( Switch to memory mode )
0x9000 VX!          ( Set memory address in VX )
7 SWRITE            ( Write color 7 to memory location )

." Enhanced graphics test complete!" CR
