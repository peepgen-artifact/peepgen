define i32 @src(i32 %v0) {
  %v1 = icmp eq i32 0, %v0
  %v2 = call i32 @llvm.cttz.i32(i32 %v0, i1 false)
  %v3 = shl i32 1, %v2
  %v4 = xor i32 -1, %v3
  %v5 = and i32 %v0, %v4
  %v6 = select i1 %v1, i32 0, i32 %v5
  ret i32 %v6
}

; Function Attrs: nocallback nofree nosync nounwind speculatable willreturn memory(none)
declare i32 @llvm.cttz.i32(i32, i1 immarg) #0

attributes #0 = { nocallback nofree nosync nounwind speculatable willreturn memory(none) }

define i32 @tgt(i32 %v0) {
  %v1 = add i32 -1, %v0
  %v2 = and i32 %v0, %v1
  ret i32 %v2
}
