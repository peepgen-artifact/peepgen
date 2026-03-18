define i32 @src(i1 %v0) {
  %v1 = xor i1 true, %v0
  %v2 = sext i1 %v1 to i32
  %v3 = add i32 1, %v2
  %v4 = select i1 %v0, i32 64, i32 %v3
  ret i32 %v4
}

define i32 @tgt(i1 %v0) {
  %v1 = select i1 %v0, i32 64, i32 0
  ret i32 %v1
}
