define i8 @src(i8 %0) {
  %2 = mul nsw i8 %0, 40
  %3 = add nsw i8 %2, -40
  %4 = udiv exact i8 %3, 40
  ret i8 %4
}


define i8 @tgt(i8 %0) {
  %2 = sub nsw i8 %0, 1
  ret i8 %2
}