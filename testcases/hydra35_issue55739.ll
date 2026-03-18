define i1 @src(i32 %v0) {
  %v1 = shl i32 2, %v0
  %v2 = and i32 16, %v1
  %v3 = icmp ne i32 0, %v2
  ret i1 %v3
}

define i1 @tgt(i32 %v0) {
  %v1 = icmp eq i32 3, %v0
  ret i1 %v1
}
