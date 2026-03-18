define i8 @src(i8 %v0, i8 %v1) {
  %v2 = mul nsw i8 2, %v0
  %v3 = mul nsw i8 %v1, %v2
  %v5 = sdiv exact i8 %v3, %v2
  ret i8 %v5
}

define i8 @tgt(i8 %v0, i8 %v1) {
  ret i8 %v1
}
