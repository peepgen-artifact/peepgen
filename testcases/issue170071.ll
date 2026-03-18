define i64 @src(i64 %v0) {
  %v1 = tail call i64 @llvm.umax.i64(i64 %v0, i64 1)
  %v2 = add nsw i64 %v1, %v0
  %v3 = icmp ult i64 %v2, %v0
  %v4 = tail call i64 @llvm.umin.i64(i64 %v2, i64 288230376151711743)
  %v5 = select i1 %v3, i64 288230376151711743, i64 %v4
  ret i64 %v5
}

define i64 @tgt(i64 %v0) {
  %v1 = tail call i64 @llvm.umax.i64(i64 %v0, i64 1)
  %v2 = add nsw i64 %v1, %v0
  %v4 = tail call i64 @llvm.umin.i64(i64 %v2, i64 288230376151711743)
  ret i64 %v4
}
