define i32 @src(i32 %v0) {
  %v1 = lshr i32 %v0, 15
  %v2 = xor i32 -1, %v1
  %v3 = icmp eq i32 0, %v0
  %v4 = zext i1 %v3 to i32
  %v5 = and i32 %v2, %v4
  ret i32 %v5
}

define i32 @tgt(i32 %v0) {
  %v1 = icmp eq i32 0, %v0
  %v2 = zext i1 %v1 to i32
  ret i32 %v2
}
