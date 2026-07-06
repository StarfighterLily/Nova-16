; NoBASIC to LLVM IR
; Source: <unknown>
target triple = "x86_64-pc-windows-msvc"


define i16 @_func_add(i16 %a, i16 %b) {
  entry:
  %l_a = alloca i16
  store i16 %a, i16* %l_a
  %l_b = alloca i16
  store i16 %b, i16* %l_b
  %t_0 = load i16, i16* %l_a
  %t_1 = load i16, i16* %l_b
  %t_2 = add i16 %t_0, %t_1
  ret i16 %t_2
  ret i16 0
}

define i32 @main() {
  entry:
  ret i32 0
}