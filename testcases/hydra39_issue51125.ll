define i8 @src(i8 %v0, i8 %v1) {
  %v2 = sdiv i8 %v0, %v1
  %v3 = add nsw i8 1, %v2
  %v4 = mul nsw i8 %v1, %v3
  %v5 = sub nsw i8 %v4, %v0
  ret i8 %v5
}

define i8 @tgt(i8 %v0, i8 %v1) {
  %v2 = srem i8 %v0, %v1
  %v3 = sub i8 %v1, %v2
  ret i8 %v3
}
