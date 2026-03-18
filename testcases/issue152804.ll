define i32 @src(i32 %0) {
  %v0 = and i32 %0, -4
  %v1 = add i32 %v0, -1
  %v2 = and i32 %v1, -4
  %v3 = add nuw i32 %v2, 4
  ret i32 %v3
}

define i32 @tgt(i32 %0) {
  %v0 = and i32 %0, -4
  ret i32 %v0
}