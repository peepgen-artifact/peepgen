define i32 @src(i32 %v0) {
  %v1 = shl i32 2, %v0
  %v2 = and i32 14, %v1
  %v3 = icmp ne i32 0, %v2
  %v4 = zext i1 %v3 to i32
  ret i32 %v4
}

define i32 @tgt(i32 %v0) {
  %v1 = icmp ult i32 %v0, 3
  %v2 = zext i1 %v1 to i32
  ret i32 %v2
}
