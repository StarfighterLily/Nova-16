; NoBASIC to LLVM IR
; Source: <unknown>
target triple = "x86_64-pc-windows-msvc"

@.str.0 = private unnamed_addr constant [33 x i8] c"Aa Bb Cc Dd Ee Ff Gg Hh Ii Jj Kk\00"
@.str.1 = private unnamed_addr constant [1 x i8] c"\00"
@.str.2 = private unnamed_addr constant [33 x i8] c"Ll Mm Nn Oo Pp Qq Rr Ss Tt Uu Vv\00"
@.str.3 = private unnamed_addr constant [1 x i8] c"\00"
@.str.4 = private unnamed_addr constant [33 x i8] c"         Ww Xx Yy Zz <3         \00"
@.str.5 = private unnamed_addr constant [1 x i8] c"\00"
@.str.6 = private unnamed_addr constant [27 x i8] c"1234567890 867-5309 420 69\00"
@.str.7 = private unnamed_addr constant [1 x i8] c"\00"
@.str.8 = private unnamed_addr constant [28 x i8] c"[]:'{}|<>?,./`~!@#$%^&*()_+\00"
@.str.9 = private unnamed_addr constant [1 x i8] c"\00"
@.str.10 = private unnamed_addr constant [9 x i8] c"Cool cat\00"
@.str.11 = private unnamed_addr constant [1 x i8] c"\00"
@.str.12 = private unnamed_addr constant [10 x i8] c"Owls hoot\00"
@.str.13 = private unnamed_addr constant [1 x i8] c"\00"
@.str.14 = private unnamed_addr constant [79 x i8] c"The quick brown fox jumped over the lazy dog as a boxing wizard jabbed deftly.\00"
@.str.15 = private unnamed_addr constant [1 x i8] c"\00"
@.str.16 = private unnamed_addr constant [104 x i8] c"'Do you know the muffin man?' he asked.\0a\0d'The muffin man?' I replied.\0a\0d'The muffin man!!' he spat back.\00"

declare void @disp(i8*)

define i32 @nobasic_main() {
  entry:
  %t_0 = getelementptr inbounds [33 x i8], [33 x i8]* @.str.0, i32 0, i32 0
  call void @disp(i8* %t_0)
  %t_1 = getelementptr inbounds [1 x i8], [1 x i8]* @.str.1, i32 0, i32 0
  call void @disp(i8* %t_1)
  %t_2 = getelementptr inbounds [33 x i8], [33 x i8]* @.str.2, i32 0, i32 0
  call void @disp(i8* %t_2)
  %t_3 = getelementptr inbounds [1 x i8], [1 x i8]* @.str.1, i32 0, i32 0
  call void @disp(i8* %t_3)
  %t_4 = getelementptr inbounds [33 x i8], [33 x i8]* @.str.4, i32 0, i32 0
  call void @disp(i8* %t_4)
  %t_5 = getelementptr inbounds [1 x i8], [1 x i8]* @.str.1, i32 0, i32 0
  call void @disp(i8* %t_5)
  %t_6 = getelementptr inbounds [27 x i8], [27 x i8]* @.str.6, i32 0, i32 0
  call void @disp(i8* %t_6)
  %t_7 = getelementptr inbounds [1 x i8], [1 x i8]* @.str.1, i32 0, i32 0
  call void @disp(i8* %t_7)
  %t_8 = getelementptr inbounds [28 x i8], [28 x i8]* @.str.8, i32 0, i32 0
  call void @disp(i8* %t_8)
  %t_9 = getelementptr inbounds [1 x i8], [1 x i8]* @.str.1, i32 0, i32 0
  call void @disp(i8* %t_9)
  %t_10 = getelementptr inbounds [9 x i8], [9 x i8]* @.str.10, i32 0, i32 0
  call void @disp(i8* %t_10)
  %t_11 = getelementptr inbounds [1 x i8], [1 x i8]* @.str.1, i32 0, i32 0
  call void @disp(i8* %t_11)
  %t_12 = getelementptr inbounds [10 x i8], [10 x i8]* @.str.12, i32 0, i32 0
  call void @disp(i8* %t_12)
  %t_13 = getelementptr inbounds [1 x i8], [1 x i8]* @.str.1, i32 0, i32 0
  call void @disp(i8* %t_13)
  %t_14 = getelementptr inbounds [79 x i8], [79 x i8]* @.str.14, i32 0, i32 0
  call void @disp(i8* %t_14)
  %t_15 = getelementptr inbounds [1 x i8], [1 x i8]* @.str.1, i32 0, i32 0
  call void @disp(i8* %t_15)
  %t_16 = getelementptr inbounds [104 x i8], [104 x i8]* @.str.16, i32 0, i32 0
  call void @disp(i8* %t_16)
  ret i32 0
}