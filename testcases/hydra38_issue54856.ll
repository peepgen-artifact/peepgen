define i1 @src(i32 %v0) {
  %v1 = and i32 15, %v0
  %v2 = icmp ne i32 15, %v1
  %v3 = icmp ult i32 %v0, 16
  %v4 = and i1 %v2, %v3
  ret i1 %v4
}

define i1 @tgt(i32 %v0) {
  %v1 = icmp ult i32 %v0, 15
  ret i1 %v1
}
