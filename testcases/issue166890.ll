define i1 @src(i64 %arg0, i64 %arg1) {
  %v0 = add nuw nsw i64 %arg1, 4095
  %v1 = add nuw nsw i64 %v0, %arg0
  %v2 = icmp samesign ult i64 %v1, 4096
  ret i1 %v2
}

define i1 @tgt(i64 %arg0, i64 %arg1) {
  %v0 = add nuw nsw i64 %arg0, %arg1
  %v1 = icmp ult i64 %v0, 1
  ret i1 %v1
}