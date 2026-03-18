define i8 @src(i8 %arg0, i8 %arg1) {
  %v0 = icmp eq i8 %arg1, -1
  %v1 = or i8 %arg0, 4
  %v2 = select i1 %v0, i8 %v1, i8 %arg0
  %v3 = or i8 %v2, 1
  ret i8 %v3
}

define i8 @tgt(i8 %arg0, i8 %arg1) {
  %v0 = icmp eq i8 %arg1, -1
  %v1 = select i1 %v0, i8 5, i8 1
  %v2 = or i8 %arg0, %v1
  ret i8 %v2
}