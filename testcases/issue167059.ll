define i1 @src(i16 %arg0, i16 %arg1) {
  %v0 = sub nsw i16 %arg1, %arg0
  %v1 = sub nsw i16 32, %arg0
  %v2 = call i16 @llvm.smin.i16(i16 %v1, i16 %v0)
  %v3 = icmp sgt i16 %v2, 0
  ret i1 %v3
}

define i1 @tgt(i16 %arg0, i16 %arg1) {
  %v0 = icmp slt i16 %arg0, 32
  %v1 = icmp slt i16 %arg0, %arg1
  %v2 = and i1 %v0, %v1
  ret i1 %v2
}