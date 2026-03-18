define i1 @src(i64 %0) {
  %2 = call { i64, i1 } @llvm.umul.with.overflow.i64(i64 %0, i64 168)
  %3 = extractvalue { i64, i1 } %2, 0
  %4 = extractvalue { i64, i1 } %2, 1
  %5 = icmp ugt i64 %3, -16
  %6 = or i1 %4, %5
  ret i1 %6
}

define i1 @tgt(i64 %0) {
  %2 = icmp ugt i64 %0, 109802048057794950
  ret i1 %2
}