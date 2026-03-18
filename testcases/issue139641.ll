define i64 @src(i32 %arg0) {
  %1 = sub i32 0, %arg0
  %2 = and i32 %1, 63
  %3 = zext nneg i32 %2 to i64
  %4 = sub nsw i64 0, %3
  %5 = lshr i64 %4, 8
  %6 = or i64 %5, %4
  ret i64 %6
}

define i64 @tgt(i32 %arg0) {
  %1 = and i32 %arg0, 63
  %2 = icmp ne i32 %1, 0
  %3 = sext i1 %2 to i64
  ret i64 %3
}