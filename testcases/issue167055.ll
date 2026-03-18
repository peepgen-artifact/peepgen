define i1 @src(i64 %arg0) {
  %v0 = tail call i64 @llvm.umin.i64(i64 %arg0, i64 13)
  %v1 = sub nsw i64 %arg0, %v0
  %v2 = icmp slt i64 %v1, 2
  ret i1 %v2
}

define i1 @tgt(i64 %arg0) {
  %v0 = icmp slt i64 %arg0, 15
  ret i1 %v0
}