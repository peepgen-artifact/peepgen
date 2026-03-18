define i1 @src(i8 %v0) {
  %v1 = zext i8 %v0 to i32
  %v2 = sub nuw i8 -1, %v0
  %v3 = zext i8 %v2 to i32
  %v4 = add nuw nsw i32 %v1, %v3
  %v5 = icmp ult i32 %v4, 256
  ret i1 %v5
}

define i1 @tgt(i8 %v0) {
  ret i1 true
}
