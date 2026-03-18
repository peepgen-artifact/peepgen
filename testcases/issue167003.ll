define i32 @src(i32 %arg1, ptr %arg0) {
  %v0 = sub nsw i32 0, %arg1
  %v1 = load i32, ptr %arg0, align 8
  %v2 = sub nsw i32 %v1, %arg1
  %v3 = tail call i32 @llvm.smin.i32(i32 %v0, i32 %v2)
  %v4 = add nsw i32 %v3, %arg1
  ret i32 %v4
}

define i32 @tgt(i32 %arg1, ptr %arg0) {
  %v1 = load i32, ptr %arg0, align 8
  %v3 = tail call i32 @llvm.smin.i32(i32 %v1, i32 0)
  ret i32 %v3
}