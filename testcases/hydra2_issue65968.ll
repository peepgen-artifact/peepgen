define i1 @src(i32 %v0, i32 %v1) {
  %v2 = and i32 -2147483648, %v0
  %v3 = xor i32 -2147483648, %v2
  %v4 = xor i32 -1, %v1
  %v5 = and i32 -2147483648, %v4
  %v6 = xor i32 -2147483648, %v5
  %v7 = icmp eq i32 %v3, %v6
  ret i1 %v7
}

define i1 @tgt(i32 %v0, i32 %v1) {
  %v2 = xor i32 %v0, %v1
  %v3 = icmp slt i32 %v2, 0
  ret i1 %v3
}
