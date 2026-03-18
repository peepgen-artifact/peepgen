define i1 @src(i64 %arg0) {
  %1 = lshr i64 %arg0, 32
  %2 = trunc nuw i64 %1 to i32
  %3 = xor i32 %2, 55296
  %4 = add i32 %3, -1114112
  %5 = icmp ult i32 %4, -1112064
  %6 = icmp eq i64 %1, 1114112
  %7 = or i1 %6, %5
  ret i1 %7
}

define i1 @tgt(i64 %arg0) {
  %1 = lshr i64 %arg0, 32
  %2 = trunc nuw i64 %1 to i32
  %3 = xor i32 %2, 55296
  %4 = add i32 %3, -1114112
  %5 = icmp ult i32 %4, -1112064
  ret i1 %5
}