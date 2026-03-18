define i32 @src(i32 %v0) {
  %v1 = sub i32 %v0, 1
  %v2 = shl nsw i32 2, %v1
  ret i32 %v2
}

define i32 @tgt(i32 %v0) {
  %v1 = shl nsw i32 1, %v0
  ret i32 %v1
}
; non profitable