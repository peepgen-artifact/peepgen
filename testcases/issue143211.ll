define i1 @src(i8 %0, i8 %1) {
  %3 = sub nsw i8 %1, %0
  %4 = add nsw i8 %1, %0
  %5 = icmp sgt i8 %3, %4
  ret i1 %5
}

define i1 @tgt(i8 %0, i8 %1) {
  %3 = icmp slt i8 %0, 0
  ret i1 %3
}