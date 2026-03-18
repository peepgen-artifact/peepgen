define i32 @src(i32 %v0) {
  %v1 = srem i32 %v0, 8
  %v2 = icmp slt i32 %v1, 0
  %v3 = srem i32 %v0, 8
  %v4 = add nsw i32 8, %v3
  %v5 = srem i32 %v0, 8
  %v6 = select i1 %v2, i32 %v4, i32 %v5
  ret i32 %v6
}

define i32 @tgt(i32 %v0) {
  %v1 = and i32 7, %v0
  ret i32 %v1
}
