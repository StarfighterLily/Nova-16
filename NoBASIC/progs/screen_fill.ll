; NoBASIC to LLVM IR
; Source: <unknown>
target triple = "x86_64-pc-windows-msvc"

@g_x = global i16 0
@g_y = global i16 0
@g_z = global i16 0

declare void @setlayer(i16)
declare void @pxlon(i16, i16, i16)

define i32 @main() {
  entry:
  %t_0 = add i16 0, 1
  call void @setlayer(i16 %t_0)
  %t_1 = add i16 0, 0
  %l_z = alloca i16
  %t_2 = load i16, i16* @g_z
  store i16 %t_2, i16* %l_z
  store i16 %t_1, i16* %l_z
  store i16 %t_1, i16* @g_z
  %t_3 = add i16 0, 0
  %l_y = alloca i16
  %t_4 = load i16, i16* @g_y
  store i16 %t_4, i16* %l_y
  store i16 %t_3, i16* %l_y
  %t_5 = add i16 0, 255
  %t_6 = alloca i16
  store i16 %t_5, i16* %t_6
  %t_7 = alloca i16
  store i16 1, i16* %t_7
  br label %for.cond.0

  for.cond.0:
  %t_8 = load i16, i16* %l_y
  %t_9 = load i16, i16* %t_6
  %t_10 = load i16, i16* %t_7
  %t_11 = icmp sle i16 %t_8, %t_9
  br i1 %t_11, label %for.body.1, label %for.end.2

  for.body.1:
  %t_12 = add i16 0, 0
  %l_x = alloca i16
  %t_13 = load i16, i16* @g_x
  store i16 %t_13, i16* %l_x
  store i16 %t_12, i16* %l_x
  %t_14 = add i16 0, 255
  %t_15 = alloca i16
  store i16 %t_14, i16* %t_15
  %t_16 = alloca i16
  store i16 1, i16* %t_16
  br label %for.cond.3

  for.cond.3:
  %t_17 = load i16, i16* %l_x
  %t_18 = load i16, i16* %t_15
  %t_19 = load i16, i16* %t_16
  %t_20 = icmp sle i16 %t_17, %t_18
  br i1 %t_20, label %for.body.4, label %for.end.5

  for.body.4:
  %t_21 = load i16, i16* %l_x
  %t_22 = load i16, i16* %l_y
  %t_23 = load i16, i16* %l_z
  call void @pxlon(i16 %t_21, i16 %t_22, i16 %t_23)
  %t_24 = load i16, i16* %l_z
  %t_26 = add i16 %t_24, 1
  store i16 %t_26, i16* %l_z
  %t_25 = add i16 %t_24, 0
  %t_27 = load i16, i16* %l_x
  %t_28 = load i16, i16* %t_16
  %t_29 = add i16 %t_27, %t_28
  store i16 %t_29, i16* %l_x
  br label %for.cond.3

  for.end.5:
  %t_30 = load i16, i16* %l_y
  %t_31 = load i16, i16* %t_7
  %t_32 = add i16 %t_30, %t_31
  store i16 %t_32, i16* %l_y
  br label %for.cond.0

  for.end.2:
  ret i32 0
}