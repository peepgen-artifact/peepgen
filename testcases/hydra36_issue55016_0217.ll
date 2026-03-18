define i32 @src(i32 %v0) {
  %v1 = add i32 -1, %v0
  %v2 = ashr exact i32 -2, %v1
  ret i32 %v2
}

define i32 @tgt(i32 %v0) {
  %v1 = ashr i32 -3, %v0
  ret i32 %v1
}
