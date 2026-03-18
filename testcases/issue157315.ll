define i1 @src(i32 %arg0, i32 %arg1) {
  %v0 = add i32 %arg1, -60
  %v1 = add i32 %v0, %arg0
  %v2 = tail call i32 @llvm.smax.i32(i32 %v1, i32 -155)
  %v3 = tail call i32 @llvm.smin.i32(i32 %v2, i32 100)
  %v4 = icmp eq i32 %v1, %v3
  ret i1 %v4
}


define i1 @tgt(i32 %arg0, i32 %arg1) {
  %sum = add i32 %arg0, 95
  %1 = add i32 %sum, %arg1
  %result = icmp ult i32 %1, 256
  ret i1 %result
}