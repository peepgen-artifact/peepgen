define i16 @src(i32 %arg1, i32 %arg2, ptr %arg0) {
  %v0 = udiv i32 %arg2, %arg1
  %v1 = load i16, ptr %arg0, align 2
  %v2 = and i32 %v0, 65535
  %v3 = zext i16 %v1 to i32
  %v4 = call i32 @llvm.umin.i32(i32 %v2, i32 %v3)
  %v5 = trunc nuw i32 %v4 to i16
  ret i16 %v5
}

define i16 @tgt(i32 %arg1, i32 %arg2, ptr %arg0) {
  %v0 = udiv i32 %arg2, %arg1
  %v1 = load i16, ptr %arg0, align 2
  %v2 = trunc i32 %v0 to i16
  %v3 = call i16 @llvm.umin.i16(i16 %v2, i16 %v1)
  ret i16 %v3
}