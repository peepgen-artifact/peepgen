define i1 @src(i64 %arg0, ptr %arg1) {
  %v0 = load i8, ptr %arg1, align 1
  %v1 = trunc nuw nsw i64 %arg0 to i32
  %v2 = shl nuw nsw i32 1, %v1
  %v3 = trunc nuw nsw i32 %v2 to i8
  %v4 = and i8 %v0, %v3
  %v5 = shl nuw nsw i32 4, %v1
  %v6 = trunc nuw nsw i32 %v5 to i8
  %v7 = and i8 %v0, %v6
  %v8 = icmp ne i8 %v4, 0
  %v9 = icmp ne i8 %v7, 0
  %v10 = select i1 %v8, i1 true, i1 %v9
  ret i1 %v10
}

define i1 @tgt(i64 %arg0, ptr %arg1) {
  %v0 = load i8, ptr %arg1, align 1
  %v1 = trunc nuw nsw i64 %arg0 to i8
  %1 = shl i8 5, %v1
  %2 = and i8 %v0, %1
  %v8 = icmp ne i8 %2, 0
  ret i1 %v8
}