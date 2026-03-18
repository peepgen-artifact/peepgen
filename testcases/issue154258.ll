define i1 @src(i32 %v3, i32 %v4) {
  %v5 = shl i32 %v3, %v4
  %v6 = sext i32 %v5 to i64
  %v7 = add i32 %v5, 32768
  %v8 = add nsw i64 %v6, 2147516416
  %v9 = icmp samesign ult i64 %v8, 4294967296
  %v131 = icmp ult i32 %v7, 65536
  %v13 = select i1 %v9, i1 %v131, i1 false
  ret i1 %v13
}

define i1 @tgt(i32 %v3, i32 %v4) {
  %v5 = shl i32 %v3, %v4
  %v6 = add i32 %v5, 32768
  %v7 = icmp ult i32 %v6, 65536
  ret i1 %v7
}