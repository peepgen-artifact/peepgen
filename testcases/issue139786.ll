define i8 @src(i8 %arg0) {
  %1 = call i8 @llvm.umax.i8(i8 %arg0, i8 1)
  %2 = shl nuw i8 %1, 1
  %3 = call i8 @llvm.umax.i8(i8 %2, i8 16)
  %4 = icmp sgt i8 %1, -1
  %5 = select i1 %4, i8 %3, i8 -1
  ret i8 %3
}

define i8 @tgt(i8 %arg0) {
  %1 = shl nuw i8 %arg0, 1
  %2 = call i8 @llvm.umax.i8(i8 %1, i8 16)
  %3 = icmp sgt i8 %2, -1
  %4 = select i1 %3, i8 %2, i8 -1
  ret i8 %2
}