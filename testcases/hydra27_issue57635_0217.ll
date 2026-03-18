define i1 @src(i8 %v0) {
  %cond = icmp ne i8 %v0, 0
  call void @llvm.assume(i1 %cond)
  %v1 = add i8 -1, %v0
  %v2 = icmp ult i8 %v1, 7
  ret i1 %v2
}

define i1 @tgt(i8 %v0) {
  %cond = icmp ne i8 %v0, 0
  call void @llvm.assume(i1 %cond)
  %v1 = icmp ule i8 %v0, 7
  ret i1 %v1
}