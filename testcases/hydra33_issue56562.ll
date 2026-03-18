define i64 @src(i64 noundef %x) {
  %n0 = tail call { i64, i1 } @llvm.umul.with.overflow.i64(i64 %x, i64 5)
  %1 = extractvalue { i64, i1 } %n0, 1
  %2 = extractvalue { i64, i1 } %n0, 0
  %_8.i = icmp ugt i64 %2, 9223372036854775807
  %3 = or i1 %1, %_8.i
  %.0.i = select i1 %3, i64 -1, i64 %2
  ret i64 %.0.i
}

define i64 @tgt(i64 noundef %x) {
  %is_bigger = icmp ugt i64 %x, 1844674407370955161
  %product = mul nuw nsw i64 %x, 5
  %r = select i1 %is_bigger, i64 -1, i64 %product
  ret i64 %r
}

