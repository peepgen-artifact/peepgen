define i32 @src(i32 %v0, i32 %v1) {
  %v2 = sub i32 32, %v1
  %v3 = shl i32 -1, %v2
  %v4 = and i32 %v0, %v3
  %v5 = sub i32 32, %v1
  %v6 = ashr i32 %v4, %v5
  ret i32 %v6
}

define i32 @tgt(i32 %v0, i32 %v1) {
  %v2 = sub i32 32, %v1
  %v3 = ashr i32 %v0, %v2
  ret i32 %v3
}
