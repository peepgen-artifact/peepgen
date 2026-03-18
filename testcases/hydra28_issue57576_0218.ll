define i128 @src(i128 %x, i128 %y) {
  %c = shl i128 -1, 64
  %m = mul i128 %x, %c
  %a = add i128 %y, %m
  %res = shl i128 %a, 64
  ret i128 %res
}

define i128 @tgt(i128 %x, i128 %y) {
  %res = shl i128 %y, 64
  ret i128 %res
}