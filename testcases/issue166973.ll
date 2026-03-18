define i1 @src(i32 %arg0) {
  %v0 = add nsw i32 %arg0, -18
  %v1 = icmp samesign ugt i32 %v0, 7
  ret i1 %v1
}

define i1 @tgt(i32 %arg0) {
  %v1 = icmp sgt i32 %arg0, 25
  ret i1 %v1
}