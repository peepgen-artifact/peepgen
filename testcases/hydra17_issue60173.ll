define i32 @src(i32 %v0) {
  %v1 = add i32 1, %v0
  %v2 = and i32 3, %v1
  %v3 = icmp eq i32 0, %v2
  %v4 = select i1 %v3, i32 -2, i32 1
  %v5 = add i32 %v0, %v4
  ret i32 %v5
}

define i32 @tgt(i32 %v0) {
  %v1 = add i32 1, %v0
  %v2 = and i32 3, %v1
  %v3 = icmp eq i32 0, %v2
  %v4 = add i32 -2, %v0
  %v5 = add i32 1, %v0
  %v6 = select i1 %v3, i32 %v4, i32 %v5
  ret i32 %v6
}
