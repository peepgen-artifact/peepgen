define i16 @src(i16 %arg0, i16 %arg1) {
  %v0 = sub nsw i16 0, %arg1
  %v1 = sub nsw i16 %arg0, %arg1
  %v2 = icmp slt i16 %arg1, 1
  %v3 = tail call i16 @llvm.smin.i16(i16 %v1, i16 -1)
  %v4 = select i1 %v2, i16 %v0, i16 %v3
  %v5 = add nsw i16 %v4, %arg1
  ret i16 %v5
}

define i16 @tgt(i16 %arg0, i16 %arg1) {
  %v2 = icmp slt i16 %arg1, 1
  %v3 = sub nsw i16 %arg1, 1
  %v4 = tail call i16 @llvm.smin.i16(i16 %arg0, i16 %v3)
  %v5 = select i1 %v2, i16 0, i16 %v4
  ret i16 %v5
}