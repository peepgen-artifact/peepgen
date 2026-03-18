define i8 @src(i64 %arg0) {
  %v0 = trunc i64 %arg0 to i8
  %v1 = urem i8 %v0, 25
  %v2 = urem i8 %v1, 5
  ret i8 %v2
}

define i8 @tgt(i64 %arg0) {
  %v0 = trunc i64 %arg0 to i8
  %v2 = urem i8 %v0, 5
  ret i8 %v2
}