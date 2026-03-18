define i1 @src(i32 %arg0, i32 %arg1) {
  %1 = ashr i32 %arg0, 31
  %2 = lshr i32 %1, 1
  %3 = xor i32 %2, %arg0
  %4 = ashr i32 %arg1, 31
  %5 = lshr i32 %4, 1
  %6 = xor i32 %5, %arg1
  %7 = icmp eq i32 %3, %6
  ret i1 %7
}
define i1 @tgt(i32 %arg0, i32 %arg1) {
  %1 = icmp eq i32 %arg0, %arg1
  ret i1 %1
}