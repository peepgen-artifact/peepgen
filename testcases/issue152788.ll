define i64 @src(i32 %0) {
  %v0 = add nsw i32 %0, 1
  %v1 = shl nsw i32 %0, 1
  %v2 = tail call i32 @llvm.smax.i32(i32 %v1, i32 %v0)
  %v3 = tail call i32 @llvm.smax.i32(i32 %v2, i32 4)
  %v4 = zext nneg i32 %v3 to i64
  %v5 = shl nuw nsw i64 %v4, 3
  ret i64 %v5
}

define i64 @tgt(i32 %0) {
  %v1 = shl nsw i32 %0, 1
  %v2 = tail call i32 @llvm.smax.i32(i32 %v1, i32 4)
  %v3 = zext nneg i32 %v2 to i64
  %v4 = shl nuw nsw i64 %v3, 3
  ret i64 %v4
}