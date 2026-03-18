define i32 @src(i32 %arg0, i32 %arg1, i32 %arg2, i32 %arg3) {
  %v0 = or i32 %arg3, %arg2
  %v1 = icmp ne i32 %arg1, 0
  %v2 = or i32 %v0, %arg0
  %v3 = icmp ne i32 %v2, 0
  %v4 = select i1 %v3, i1 true, i1 %v1
  %v5 = select i1 %v4, i32 %arg0, i32 0
  ret i32 %v5
}

define i32 @tgt(i32 %arg0, i32 %arg1, i32 %arg2, i32 %arg3) {
  ret i32 %arg0
}