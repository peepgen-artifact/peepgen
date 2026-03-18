define i1 @src(i32 %v0, i32 %v1) {
  %v2 = lshr i32 %v0, 31
  %v3 = icmp slt i32 -1, %v1
  %v4 = zext i1 %v3 to i32
  %v5 = icmp eq i32 %v2, %v4
  ret i1 %v5
}

define i1 @tgt(i32 %v0, i32 %v1) {
  %v2 = icmp ult i32 %v0, -2147483648
  %v3 = icmp slt i32 -1, %v1
  %v4 = xor i1 %v2, %v3
  ret i1 %v4
}
; wrong input and inconsistent with the original optimization
; in github issue