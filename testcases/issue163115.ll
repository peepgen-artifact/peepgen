define i32 @src(i32 %arg0) {
  %v0 = shl nsw i32 %arg0, 4
  %v1 = add nsw i32 %v0, 16
  %v2 = ashr exact i32 %v1, 1
  ret i32 %v2
}

define i32 @tgt(i32 %arg0) {
  %v0 = shl i32 %arg0, 3
  %v1 = add i32 %v0, 8
  ret i32 %v1
}