define i32 @src(i32 %arg0) {
  %v0 = and i32 %arg0, 1
  %v1 = icmp eq i32 %v0, 0
  %v2 = or disjoint i32 %arg0, 1
  %v3 = add nsw i32 %arg0, -1
  %v4 = select i1 %v1, i32 %v2, i32 %v3
  %v5 = srem i32 %v4, 6
  ret i32 %v5
}

define i32 @tgt(i32 %arg0) {
  %v4_opt = xor i32 %arg0, 1
  %v5_opt = srem i32 %v4_opt, 6
  ret i32 %v5_opt
}