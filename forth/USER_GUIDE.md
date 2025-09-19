# NOVA-16 FORTH User Guide

## Welcome to NOVA-16 FORTH

FORTH is a powerful, stack-based programming language that runs on the NOVA-16 CPU emulator. This guide will help you get started with FORTH programming, from basic concepts to advanced techniques and hardware integration.

## Getting Started

### Starting FORTH

```bash
# Navigate to the FORTH directory
cd forth

# Start the FORTH interpreter
python forth_interpreter.py
```

You'll see the FORTH prompt:
```
NOVA-16 FORTH Interpreter v1.0
>
```

### Your First FORTH Program

Let's start with a simple arithmetic calculation:

```
5 3 + .
```

This program:
1. Pushes `5` onto the stack
2. Pushes `3` onto the stack
3. Adds the top two numbers (`5 + 3 = 8`)
4. Prints the result followed by a space

**Output:** `8 `

The `.` (dot) word prints the top number on the stack and removes it.

## Understanding the Stack

FORTH uses a **parameter stack** for data manipulation. Think of it as a stack of numbers:

```
Command: 5 3 +
Stack:   [5, 3]  →  [8]

Command: .
Stack:   [8]     →  []
```

### Stack Manipulation Words

#### Basic Operations
```
DUP     ( n -- n n )           Duplicate top item
DROP    ( n -- )               Remove top item
SWAP    ( a b -- b a )         Exchange top two items
OVER    ( a b -- a b a )       Copy second item to top
ROT     ( a b c -- b c a )     Rotate top three items
```

**Examples:**
```
10 DUP . . CR     → 10 10
1 2 3 SWAP . . . CR  → 1 3 2
5 6 OVER . . . CR    → 5 6 5
```

#### Stack Inspection
```
.S      ( -- )                  Show entire stack contents
DEPTH   ( -- n )               Get stack depth
```

## Arithmetic and Logic

### Arithmetic Operations
```
+       ( a b -- sum )          Addition
-       ( a b -- diff )         Subtraction (a - b)
*       ( a b -- prod )         Multiplication
/       ( a b -- quot )         Division
MOD     ( a b -- rem )          Modulo (remainder)
```

**Examples:**
```
7 3 + . CR       → 10
15 4 - . CR      → 11
6 7 * . CR       → 42
17 5 / . CR      → 3
17 5 MOD . CR    → 2
```

### Comparison Operations
```
=       ( a b -- flag )         Equality test
<       ( a b -- flag )         Less than
>       ( a b -- flag )         Greater than
<>      ( a b -- flag )         Not equal
<=      ( a b -- flag )         Less than or equal
>=      ( a b -- flag )         Greater than or equal
```

**Note:** FORTH uses -1 for TRUE and 0 for FALSE.

**Examples:**
```
5 5 = . CR       → -1 (true)
5 3 = . CR       → 0 (false)
3 5 < . CR       → -1 (true)
```

### Logic Operations
```
AND     ( a b -- result )       Bitwise AND
OR      ( a b -- result )       Bitwise OR
XOR     ( a b -- result )       Bitwise XOR
INVERT  ( n -- ~n )            Bitwise NOT
```

## Word Definition

### Creating New Words

Use `:` to start a word definition and `;` to end it:

```
: SQUARE DUP * ;
```

This defines a new word `SQUARE` that:
1. Duplicates the top stack item
2. Multiplies the two numbers
3. Returns the result

**Usage:**
```
7 SQUARE . CR    → 49
```

### More Complex Definitions

```
: DOUBLE DUP + ;
: TRIPLE DUP DUP + + ;
: AVG 2 / ;      \ Integer division

10 DOUBLE . CR   → 20
15 TRIPLE . CR   → 45
26 AVG . CR      → 13
```

### Recursive Definitions

```
: FACTORIAL
  DUP 1 > IF
    DUP 1 - RECURSE *
  ELSE
    DROP 1
  THEN ;

5 FACTORIAL . CR   → 120
```

## Control Flow

### Conditional Execution

#### IF/THEN Structure
```
: TEST-NEGATIVE DUP 0 < IF ." Negative" CR THEN ;

-5 TEST-NEGATIVE    → Negative
10 TEST-NEGATIVE    → (no output)
```

#### IF/ELSE/THEN Structure
```
: SIGN DUP 0 < IF ." Negative" ELSE 0 > IF ." Positive" ELSE ." Zero" THEN THEN ;

-5 SIGN CR    → Negative
10 SIGN CR    → Positive
0 SIGN CR     → Zero
```

### Loops

#### BEGIN/UNTIL Loop
```
: COUNTDOWN DUP . CR 1 - DUP 0 = UNTIL DROP ;

5 COUNTDOWN
→ 5
  4
  3
  2
  1
```

#### DO/LOOP Structure
```
: SUM 0 SWAP 0 DO + LOOP ;

5 SUM . CR    → 15 (0+1+2+3+4+5)
```

#### Loop Indices
```
: TABLE 11 1 DO DUP I * . SPACE LOOP DROP CR ;

6 TABLE    → 6 12 18 24 30 36 42 48 54 60
```

## Variables and Constants

### Variables
```
VARIABLE SCORE
42 SCORE !        \ Store 42 in SCORE
SCORE @ . CR      \ Print SCORE → 42
10 SCORE +!       \ Add 10 to SCORE
SCORE @ . CR      \ Print SCORE → 52
```

### Constants
```
314 CONSTANT PI
PI . CR           → 314
```

### Arrays (Using Variables)
```
VARIABLE ARRAY
: [] ARRAY + ;    \ Array access word

10 0 [] !         \ ARRAY[0] = 10
20 1 [] !         \ ARRAY[1] = 20
0 [] @ . CR       → 10
1 [] @ . CR       → 20
```

## String Handling

### String Literals
```
." Hello World" CR
S" Test String"   \ Creates string on stack
```

### String Variables
```
VARIABLE GREETING
S" Hello, FORTH!" GREETING !

\ Print the string
GREETING @ COUNT TYPE CR
```

## Advanced Examples

### Factorial Function
```
: FACT DUP 1 > IF DUP 1 - RECURSE * ELSE DROP 1 THEN ;

: FACT-TEST
  ." Factorial Calculator" CR
  10 1 DO
    I . ." ! = " I FACT . CR
  LOOP ;

FACT-TEST
```

### Prime Number Tester
```
: PRIME?
  DUP 2 < IF DROP 0 EXIT THEN    \ 0, 1 not prime
  DUP 2 = IF DROP -1 EXIT THEN   \ 2 is prime
  DUP 2 MOD 0 = IF DROP 0 EXIT THEN  \ Even numbers > 2 not prime

  \ Check odd divisors from 3 to sqrt(n)
  DUP DUP SQRT 3 DO
    DUP I MOD 0 = IF DROP 0 UNLOOP EXIT THEN
  2 +LOOP
  DROP -1 ;  \ Is prime

17 PRIME? . CR   → -1 (true)
18 PRIME? . CR   → 0 (false)
```

### Simple Graphics Demo
```
\ Set up graphics
0 LAYER          \ Use layer 0
0 VMODE          \ Coordinate mode

\ Draw a diagonal line
: DRAW-LINE
  20 0 DO
    I I 15 PIXEL  \ White pixel at (I,I)
  LOOP ;

DRAW-LINE
```

### Sound Demo
```
\ Play a tone
0x2000 440 128 0 SOUND  \ Address, frequency, volume, waveform
SPLAY                   \ Start playback

\ Wait a bit
1000 0 DO LOOP

\ Stop sound
SSTOP
```

## Hardware Integration

### Graphics System

#### Basic Graphics
```
0 LAYER          \ Select layer 0
0 VMODE          \ Coordinate mode (x,y)
100 120 15 PIXEL \ White pixel at (100,120)
```

#### Graphics Registers
```
100 VX!          \ Set X coordinate
120 VY!          \ Set Y coordinate
1 VL!            \ Set active layer
```

#### Drawing Shapes
```
: DRAW-BOX ( x y width height color -- )
  LOCALS| color height width y x |
  height 0 DO
    width 0 DO
      x I + y J + color PIXEL
    LOOP
  LOOP ;

50 50 20 10 15 DRAW-BOX  \ 20x10 white box at (50,50)
```

### Sound System

#### Playing Tones
```
\ Play 440Hz sine wave
0x2000 440 128 0 SOUND
SPLAY

\ Play 880Hz square wave
0x2000 880 96 1 SOUND
SPLAY
```

#### Sound Registers
```
0x2000 SA!       \ Set sound address
440 SF!          \ Set frequency
128 SV!          \ Set volume
0 SW!            \ Set waveform (0=sine, 1=square, 2=triangle, 3=sawtooth)
```

### Input System

#### Keyboard Input
```
KEYSTAT . CR     \ Check if key available (0=no, 1=yes)
KEYIN . CR       \ Read key (blocks until key pressed)
```

#### Non-blocking Input
```
: WAIT-KEY
  BEGIN
    KEYSTAT
  UNTIL
  KEYIN ;

WAIT-KEY . CR    \ Wait for and read a key
```

### Timer System

#### Basic Timing
```
1000 TT!         \ Set timer to 1000
1 TC!            \ Enable timer
TM!              \ Set match value
```

#### Delay Function
```
: DELAY ( ms -- )
  TT!             \ Set timer value
  1 TC!           \ Enable timer
  BEGIN
    TT @ 0 =      \ Wait for timer to reach 0
  UNTIL ;

1000 DELAY       \ Delay 1000ms (1 second)
```

## Debugging Techniques

### Stack Inspection
```
.S                \ Show current stack
DEPTH . CR        \ Show stack depth
```

### Tracing Execution
```
\ Add debug output to words
: DEBUG-SQUARE
  ." Input: " DUP . CR
  DUP *
  ." Result: " DUP . CR ;

5 DEBUG-SQUARE
```

### Error Recovery
```
\ Handle stack underflow gracefully
: SAFE-DROP
  DEPTH 0 > IF DROP THEN ;

\ Test it
SAFE-DROP         \ No error even if stack empty
```

## Performance Optimization

### Efficient Stack Usage
```
\ Inefficient (uses extra stack space)
: BAD-SUM DUP DUP + + ;

\ Efficient (minimal stack usage)
: GOOD-SUM DUP + ;
```

### Loop Optimization
```
\ Inefficient (recalculates limit each iteration)
: BAD-LOOP 100 0 DO I 50 > IF LEAVE THEN LOOP ;

\ Efficient (calculate once)
: GOOD-LOOP 0 BEGIN DUP 100 < WHILE DUP . 1 + REPEAT DROP ;
```

### Memory Access Optimization
```
\ Use zero page for frequently accessed variables
VARIABLE COUNTER  \ Automatically uses efficient memory
42 COUNTER !      \ Fast access
COUNTER @         \ Fast access
```

## Common Patterns

### State Machines
```
VARIABLE STATE

: PROCESS-INPUT
  STATE @
  CASE
    0 OF ." Menu" CR 1 STATE ! ENDOF
    1 OF ." Game" CR 2 STATE ! ENDOF
    2 OF ." Exit" CR 0 STATE ! ENDOF
  ENDCASE ;

0 STATE !
PROCESS-INPUT    \ Menu
PROCESS-INPUT    \ Game
PROCESS-INPUT    \ Exit
```

### Data Structures
```
\ Simple linked list
VARIABLE LIST-HEAD

: ADD-TO-LIST ( value -- )
  HERE                    \ Get current memory location
  LIST-HEAD @ ,           \ Store next pointer
  ,                       \ Store value
  LIST-HEAD ! ;           \ Update head

: PRINT-LIST
  LIST-HEAD @
  BEGIN
    DUP
  WHILE
    DUP CELL + @ .        \ Print value
    @                     \ Get next pointer
  REPEAT DROP ;
```

### Mathematical Functions
```
: SIN ( degrees -- sine )
  3.14159 * 180 / SIN ;

: COS ( degrees -- cosine )
  3.14159 * 180 / COS ;

: DISTANCE ( x1 y1 x2 y2 -- distance )
  ROT - DUP *           \ (x2-x1)^2
  -ROT - DUP * +        \ (y2-y1)^2 + (x2-x1)^2
  SQRT ;
```

## Best Practices

### Code Organization
```
\ Group related words together
\ Use meaningful names
\ Add comments for complex logic
\ Test incrementally
```

### Error Handling
```
\ Always check stack depth before operations
\ Use meaningful error messages
\ Provide recovery options
\ Test edge cases
```

### Performance
```
\ Minimize stack shuffling
\ Use efficient algorithms
\ Cache frequently used values
\ Profile before optimizing
```

## Troubleshooting

### Common Errors

#### Stack Underflow
```
\ Error: Trying to DROP from empty stack
\ Solution: Check stack depth first
DEPTH 0 > IF DROP THEN
```

#### Division by Zero
```
\ Error: Division by zero
\ Solution: Check divisor before division
DUP 0 <> IF / ELSE DROP 0 THEN
```

#### Memory Access Errors
```
\ Error: Invalid memory address
\ Solution: Validate addresses before access
DUP 0 >= OVER 0xFFFF <= AND IF ! ELSE DROP THEN
```

### Debug Commands
```
WORDS     \ List all defined words
.S        \ Show stack contents
DEPTH     \ Show stack depth
RESET     \ Reset interpreter state
```

## Advanced Topics

### Metaprogramming
```
\ Create words dynamically
: MAKE-WORD ( n "name" -- )
  :                    \ Start definition
  LITERAL              \ Compile n as literal
  ." Value: " . CR ;   \ End definition

5 MAKE-WORD FIVE
FIVE                  \ Prints: Value: 5
```

### Cross-Compilation
```
\ FORTH can compile to NOVA-16 assembly
\ Use the compiler for better performance
python forth_compiler.py program.forth
```

### Multi-tasking (Future)
```
\ Cooperative multi-tasking support
TASK WORKER
: WORKER-LOOP PROCESS-DATA AGAIN ;

WORKER ACTIVATE
```

## Resources

### Built-in Help
```
WORDS     \ List all available words
HELP      \ Show help for specific word
INFO      \ Show system information
```

### Documentation
- `ARCHITECTURE.md` - Technical architecture details
- `CORE_WORDS.md` - Complete word reference
- `IMPLEMENTATION_GUIDE.md` - Technical implementation details
- `TESTING_FRAMEWORK.md` - Testing and validation

### Community Resources
- NOVA-16 GitHub repository
- FORTH programming forums
- Stack-based programming communities

## Conclusion

FORTH on NOVA-16 provides a powerful, efficient programming environment that leverages the full capabilities of the NOVA-16 hardware. From simple calculations to complex applications with graphics, sound, and input handling, FORTH offers both simplicity and sophistication.

The stack-based paradigm takes time to master but provides elegant solutions to complex problems. Start with simple programs, gradually explore advanced features, and enjoy the efficiency and expressiveness of FORTH programming on the NOVA-16 system.

Happy FORTH programming! 🚀</content>
<parameter name="filePath">c:\Code\Nova\forth\USER_GUIDE.md