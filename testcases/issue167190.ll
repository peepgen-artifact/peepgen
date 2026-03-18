define i16 @src(i16 %arg0, i16 %arg1) {
  %v0 = add nsw i16 %arg1, %arg0
  %v1 = mul nsw i16 %arg0, 8697
  %v2 = mul nsw i16 %v0, 6436
  %v3 = sub nsw i16 %v1, %v2
  ret i16 %v3
}

define i16 @tgt(i16 %arg0, i16 %arg1) {
  %v0 = mul nsw i16 %arg0, 2261
  %v1 = mul nsw i16 %arg1, 6436
  %v2 = sub nsw i16 %v0, %v1
  ret i16 %v2
}