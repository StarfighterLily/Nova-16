# NoBASIC Struct Quick Reference

## Struct Declaration

```nobasic
STRUCT StructName
    field1
    field2
    field3
END
```

- Maximum 10 fields per struct
- All fields are 16-bit values
- Field names follow variable naming rules

## Using Structs

```nobasic
// Initialize struct fields
Player.x = 50
Player.y = 60
Player.health = 100

// Read struct fields
px = Player.x
py = Player.y

// Use in expressions
Player.x = Player.x + velocity
newPos = Player.x + offset

// Use in function calls
PxlOn(Player.x, Player.y, 31)

// Use in conditionals (⚠️ keep values < 127!)
If Player.x > 100 Then
    Player.x = 100
End
```

## ⚠️ Important Limitation

**Values > 127 may cause issues in comparisons!**

```nobasic
// ❌ PROBLEM - 128 treated as -128 in comparisons
Player.x = 128
If Player.x < 5 Then  // This will be TRUE! (because -128 < 5)
    // This code will execute incorrectly
End

// ✅ SOLUTION - Keep values under 127
Player.x = 100
If Player.x < 5 Then  // Works correctly
    // This won't execute
End
```

**Workaround**: Keep coordinates and compared values between 0-126.

## Complete Working Example

```nobasic
// Bouncing ball with structs
STRUCT Ball
    x
    y
    vx
    vy
END

SetLayer(0)
ClrDraw

// Initialize (values under 127!)
Ball.x = 60
Ball.y = 60
Ball.vx = 3
Ball.vy = 2

// Animation loop
For frame = 0 To 50
    // Draw ball
    PxlOn(Ball.x, Ball.y, 31)
    PxlOn(Ball.x + 1, Ball.y, 31)
    PxlOn(Ball.x, Ball.y + 1, 31)
    PxlOn(Ball.x + 1, Ball.y + 1, 31)
    
    // Update position
    Ball.x = Ball.x + Ball.vx
    Ball.y = Ball.y + Ball.vy
    
    // Bounce (all values < 127!)
    If Ball.x > 120 Then
        Ball.vx = 0 - Ball.vx
    End
    
    If Ball.y > 120 Then
        Ball.vy = 0 - Ball.vy
    End
    
    If Ball.x < 10 Then
        Ball.vx = 0 - Ball.vx
    End
    
    If Ball.y < 10 Then
        Ball.vy = 0 - Ball.vy
    End
    
    Pause  // See each frame
Next

Text(0, 0, "Done!", 15)
```

## Memory Layout

Structs are allocated sequentially starting at 0x0120:
- Each field occupies 2 bytes (16-bit word)
- Fields are stored in declaration order
- Example: `STRUCT Point x, y END` → x at 0x0120, y at 0x0122

## Tips

1. **Use Pause** in animation loops to see movement
2. **Draw on layer 0** (SetLayer(0)) for main graphics
3. **Keep coordinates < 127** to avoid signed comparison issues
4. **Use trail effects** (don't clear pixels) to visualize movement
5. **Start with small test programs** before complex animations

## Future Improvements

- Fix for values > 127 (use 16-bit unsigned comparisons)
- Support for struct arrays
- Nested struct support
- More than 10 fields per struct

---
*For more details, see STRUCT_STATUS.md*
