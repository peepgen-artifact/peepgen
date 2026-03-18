define i32 @src(i3 %v0) {
  %v1 = xor i3 -1, %v0
  %v2 = zext i3 %v1 to i32
  %v3 = sext i3 %v0 to i32
  %v4 = or i32 %v2, %v3
  ret i32 %v4
}

define i32 @tgt(i3 %v0) {
  %v1 = sext i3 %v0 to i32
  %v2 = or i32 7, %v1
  ret i32 %v2
}
