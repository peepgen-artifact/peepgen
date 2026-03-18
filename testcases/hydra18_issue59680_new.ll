define i1 @src(i32 %v0) {
  %v1 = and i32 -65536, %v0
  %v2 = icmp eq i32 287440896, %v1
  %v3 = and i32 -256, %v0
  %v4 = icmp eq i32 287453952, %v3
  %v5 = or i1 %v2, %v4
  ret i1 %v5
}

define i1 @tgt(i32 %v0) {
  %v1 = and i32 -65536, %v0
  %v2 = icmp eq i32 287440896, %v1
  ret i1 %v2
}
