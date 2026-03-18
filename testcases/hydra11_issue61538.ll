define i8 @src(i8 %v0, i8 %v1) {
  %v2 = shl nsw i8 %v0, 1
  %v3 = mul nsw i8 %v1, %v2
  %v4 = or i8 1, %v3
  %v5 = icmp slt i8 %v4, 1
  %v6 = select i1 %v5, i8 %v1, i8 1
  %v7 = mul nsw i8 %v0, %v6
  ret i8 %v7
}

define i8 @tgt(i8 %v0, i8 %v1) {
  %v2 = mul nsw i8 %v0, %v1
  %v3 = icmp slt i8 %v2, 0
  %v4 = mul nsw i8 %v0, %v1
  %v5 = select i1 %v3, i8 %v4, i8 %v0
  ret i8 %v5
}
