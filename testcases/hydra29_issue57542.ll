define i1 @src(i8 %v0) {
  %v1 = sdiv i8 42, %v0
  %v2 = icmp eq i8 0, %v1
  ret i1 %v2
}

define i1 @tgt(i8 %v0) {
  %v1 = add i8 -43, %v0
  %v2 = icmp ult i8 %v1, -85
  ret i1 %v2
}
