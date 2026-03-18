define i1 @src(i32 %arg0) {
  %1 = add i32 %arg0, 1
  %2 = lshr i32 %1, 4
  %3 = and i32 %1, 15
  %4 = icmp ne i32 %3, 0
  %5 = zext i1 %4 to i32
  %6 = add nuw nsw i32 %2, %5
  %7 = icmp eq i32 %6, 0
  ret i1 %7
}

define i1 @tgt(i32 %arg0) {
  %5 = icmp eq i32 %arg0, -1
  ret i1 %5
}