define i1 @src(i1 %v0, i1 %v1) {
  %not_v1 = xor i1 %v1, true
  %cond_val = select i1 %v0, i1 %not_v1, i1 false
  %precondition = icmp eq i1 %cond_val, false
  call void @llvm.assume(i1 %precondition)
  %v2 = xor i1 true, %v0
  %v3 = select i1 %v2, i1 %v1, i1 false
  ret i1 %v3
}

define i1 @tgt(i1 %v0, i1 %v1) {
  %not_v1 = xor i1 %v1, true
  %cond_val = select i1 %v0, i1 %not_v1, i1 false
  %precondition = icmp eq i1 %cond_val, false
  call void @llvm.assume(i1 %precondition)
  %v2 = xor i1 %v0, %v1
  ret i1 %v2
}
