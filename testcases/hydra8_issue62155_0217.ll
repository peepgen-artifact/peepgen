define i8 @src(i8 %v0) {
  %i8 = and i8 127, %v0
  %v2 = icmp eq i8 0, %i8
  %v3 = shl i8 %v0, 1
  %v4 = select i1 %v2, i8 0, i8 %v3
  ret i8 %v4
}

define i8 @tgt(i8 %v0) {
  %i8 = shl i8 %v0, 1
  ret i8 %i8
}
