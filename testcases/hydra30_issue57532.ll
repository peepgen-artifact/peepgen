define i1 @src(i32 %v0) {
  %v1 = xor i32 -1, %v0
  %v2 = icmp slt i32 %v0, %v1
  ret i1 %v2
}

define i1 @tgt(i32 %v0) {
  %v1 = icmp slt i32 %v0, 0
  ret i1 %v1
}
