define i32 @src(i32 %arg0, i32 %arg1) {
  %v0 = sub nsw i32 0, %arg1
  %v1 = call i32 @llvm.smax.i32(i32 %arg0, i32 %v0)
  %v2 = add nuw nsw i32 %v1, %arg1
  ret i32 %v2
}


define i32 @tgt(i32 %arg0, i32 %arg1) {
  %v0 = add i32 %arg0, %arg1
  %v1 = call i32 @llvm.smax.i32(i32 %v0, i32 0)
  ret i32 %v1
}