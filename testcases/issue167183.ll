define i32 @src(ptr %arg0) {
  %v0 = load i32, ptr %arg0, align 4
  %v1 = shl i32 %v0, 2
  %v2 = add i32 %v1, 31
  %v3 = and i32 %v2, -4
  ret i32 %v3
}


define i32 @tgt(ptr %arg0) {
  %v0 = load i32, ptr %arg0, align 4
  %v1 = shl i32 %v0, 2
  %v2 = add i32 %v1, 28
  ret i32 %v2
}