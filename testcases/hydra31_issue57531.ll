define i32 @src(i32 %v0) {
  %v1 = sub i32 0, %v0
  %v2 = or i32 %v0, %v1
  %v3 = add i32 %v0, %v2
  ret i32 %v3
}

define i32 @tgt(i32 %v0) {
  %v1 = add i32 -1, %v0
  %v2 = and i32 %v0, %v1
  ret i32 %v2
}
