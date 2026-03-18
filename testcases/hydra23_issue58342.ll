define i1 @src(i8 %v0) {
  %v1 = icmp ult i8 %v0, 2
  %v2 = sub i8 %v0, 2
  %v3 = select i1 %v1, i8 0, i8 %v2
  %v4 = icmp eq i8 5, %v3
  ret i1 %v4
}

define i1 @tgt(i8 %v0) {
  %v1 = icmp eq i8 7, %v0
  ret i1 %v1
}
