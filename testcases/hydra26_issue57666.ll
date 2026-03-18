define i1 @src(i1 %v0, i1 %v1) {
  %v2 = select i1 %v0, i32 4, i32 1
  %v3 = select i1 %v1, i32 4, i32 1
  %v4 = and i32 %v2, %v3
  %v5 = icmp eq i32 0, %v4
  ret i1 %v5
}

define i1 @tgt(i1 %v0, i1 %v1) {
  %v2 = xor i1 %v0, %v1
  ret i1 %v2
}
