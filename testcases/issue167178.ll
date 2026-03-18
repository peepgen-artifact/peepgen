define i1 @src(i32 %arg0) {
  %v0 = lshr i32 %arg0, 9
  %v1 = add nuw i32 %v0, %arg0
  %v2 = icmp ult i32 %v1, 256
  ret i1 %v2
}

define i1 @tgt(i32 %arg0) {
  %v2 = icmp ult i32 %arg0, 256
  ret i1 %v2
}