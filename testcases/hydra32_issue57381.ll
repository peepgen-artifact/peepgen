define i32 @src(i16 %v0) {
  %v1 = lshr i16 %v0, 15
  %v2 = zext i16 %v1 to i32
  %v3 = sub nsw i32 0, %v2
  %v4 = sext i16 %v0 to i32
  %v5 = sub nsw i32 1000, %v4
  %v6 = and i32 %v3, %v5
  ret i32 %v6
}

define i32 @tgt(i16 %v0) {
  %v1 = icmp slt i16 %v0, 0
  %v2 = sext i16 %v0 to i32
  %v3 = sub nsw i32 1000, %v2
  %v4 = select i1 %v1, i32 %v3, i32 0
  ret i32 %v4
}
