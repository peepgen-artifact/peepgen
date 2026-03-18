define i1 @src(i64 %arg0) {
  %v0 = sdiv exact i64 %arg0, 12
  %v1 = icmp ugt i64 %v0, 12
  ret i1 %v1
}

define i1 @tgt(i64 %arg0) {
  %v0 = icmp ugt i64 %arg0, 144
  ret i1 %v0
}