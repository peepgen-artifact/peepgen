define i1 @src(i32 %arg0) {
  %v0 = icmp slt i32 %arg0, 1
  %v1 = select i1 %v0, i32 -1, i32 1
  %v2 = sub nsw i32 %arg0, %v1
  %v3 = icmp eq i32 %v2, 0
  ret i1 %v3
}

define i1 @tgt(i32 %arg0) {
  %v0 = icmp eq i32 %arg0, -1
  %v1 = icmp eq i32 %arg0, 1
  %v2 = or i1 %v0, %v1
  ret i1 %v2
}