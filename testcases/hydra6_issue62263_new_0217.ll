define i32 @src(i32 %v0, i32 %v1) {
  %v2 = xor i32 -1, %v1
  %v3 = or i32 %v0, %v2
  %v4 = icmp eq i32 0, %v3
  %v5 = select i1 %v4, i32 %v0, i32 0
  ret i32 %v5
}

define i32 @tgt(i32 %v0, i32 %v1) {
  ret i32 0
}
