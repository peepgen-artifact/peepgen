define i32 @src(i32 %arg0) {
  %v0 = trunc nuw nsw i32 %arg0 to i8
  %v1 = mul nuw i8 %v0, 24
  %v2 = add i8 %v1, -24
  %v3 = sdiv exact i8 %v2, 24
  %v4 = sext i8 %v3 to i32
  ret i32 %v4
}

define i32 @tgt(i32 %arg0) {
  %v0 = trunc nuw nsw i32 %arg0 to i8
  %v1 = add i8 %v0, -1
  %v2 = sext i8 %v1 to i32
  ret i32 %v2
}