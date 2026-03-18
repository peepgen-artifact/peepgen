define i64 @src(i64 %arg0, ptr %arg1) {
  %v0 = load i64, ptr %arg1, align 8
  %v1 = tail call i64 @llvm.smin.i64(i64 %arg0, i64 %v0)
  %v2 = add nuw nsw i64 %arg0, 1
  %v3 = tail call i64 @llvm.smin.i64(i64 %v2, i64 %v0)
  %v4 = sub i64 %v3, %v1
  ret i64 %v4
}

define i64 @tgt(i64 %arg0, ptr %arg1) {
  %v0 = load i64, ptr %arg1, align 8
  %v1 = icmp slt i64 %arg0, %v0
  %v3 = select i1 %v1, i64 1, i64 0
  ret i64 %v3
}