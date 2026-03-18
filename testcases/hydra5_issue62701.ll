define i1 @src(i64 %v0) {
  %v1 = icmp ult i64 4, %v0
  %v2 = add i64 -4, %v0
  %v3 = select i1 %v1, i64 %v2, i64 %v0
  %v4 = icmp ult i64 4, %v3
  ret i1 %v4
}

define i1 @tgt(i64 %v0) {
  %v1 = icmp ult i64 8, %v0
  ret i1 %v1
}
