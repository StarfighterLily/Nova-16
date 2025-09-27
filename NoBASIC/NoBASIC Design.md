```
// A sample NoBASIC program
ClrDraw
x = 0
y = 0
// Fill the screen one red pixel at a time
For y = 0 to 255
    For x = 0 to 255
        PxlOn(x, y, 31)
    End
End

Pause

If (x = 255) and (y = 255)
ClrDraw
```



NoBASIC - A TI-BASIC inspired language for the Nova-16.
NoBASIC feels like the TI-83/84 flavor of BASIC without the constraints, providing a nostalgic feeling while unleashing the power to utilize the Nova-16 hardware to its fullest potential. Relive the days of coding in math class with familiar syntax without the limitations of the calculator.

