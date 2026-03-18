define i64 @src(i64 %v0) {
  %v1 = sub nuw i64 71, %v0
  %v2 = and i64 -8, %v1
  %v3 = sub i64 64, %v2
  ret i64 %v3
}

define i64 @tgt(i64 %v0) {
  %v1 = and i64 120, %v0
  ret i64 %v1
}
