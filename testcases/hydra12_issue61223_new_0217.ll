define i32 @src(i32 %v0) {
  %bit = and i32 %v0, 1
  %cond = icmp ne i32 %bit, 0
  call void @llvm.assume(i1 %cond)
  %v1 = add i32 -1, %v0
  %v2 = lshr i32 %v1, 1
  ret i32 %v2
}

define i32 @tgt(i32 %v0) {
  %bit = and i32 %v0, 1
  %cond = icmp ne i32 %bit, 0
  call void @llvm.assume(i1 %cond)
  %v1 = lshr i32 %v0, 1
  ret i32 %v1
}