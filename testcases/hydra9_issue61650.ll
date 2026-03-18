define i8 @src(i8 %v0) {
  %v1 = trunc i8 %v0 to i4
  %v2 = shl i4 %v1, 2
  %v3 = zext i4 %v2 to i8
  ret i8 %v3
}

define i8 @tgt(i8 %v0) {
  %v1 = shl i8 %v0, 2
  %v2 = and i8 12, %v1
  ret i8 %v2
}
