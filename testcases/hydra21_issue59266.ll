define i1 @src(i1 %v0, i32 %v1) {
  %v2 = icmp eq i32 15, %v1
  %v3 = and i1 %v0, %v2
  %v4 = icmp ne i32 0, %v1
  %v5 = or i1 %v0, %v4
  %v6 = xor i1 %v3, %v5
  %v7 = xor i1 true, %v6
  ret i1 %v7
}

define i1 @tgt(i1 %v0, i32 %v1) {
  %v2 = select i1 %v0, i32 15, i32 0
  %v3 = icmp eq i32 %v1, %v2
  ret i1 %v3
}
