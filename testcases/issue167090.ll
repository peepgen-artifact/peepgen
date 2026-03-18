define i32 @src(i32 %i16arg0) {
  %v0 = tail call i32 @llvm.umin.i32(i32 %i16arg0, i32 16)
  %v1 = add nuw nsw i32 %v0, 16
  %v2 = tail call i32 @llvm.umin.i32(i32 %i16arg0, i32 %v1)
  %v3 = add nuw nsw i32 %v2, 16
  %v4 = tail call i32 @llvm.umin.i32(i32 %i16arg0, i32 %v3)
  ret i32 %v4
}

define i32 @tgt(i32 %i16arg0) {
  %v0 = tail call i32 @llvm.umin.i32(i32 %i16arg0, i32 48)
  ret i32 %v0
}