define i1 @src(ptr %arg0, ptr %arg1) {
  %v0 = load i64, ptr %arg1, align 8
  %v1 = shl nsw i64 %v0, 5
  %v2 = getelementptr inbounds i8, ptr %arg0, i64 -8
  %v3 = load i64, ptr %v2, align 8
  %v4 = shl nsw i64 %v3, 5
  %v5 = add nsw i64 %v4, 32
  %v6 = icmp eq i64 %v1, %v5
  ret i1 %v6
}

define i1 @tgt(ptr %arg0, ptr %arg1) {
  %v0 = load i64, ptr %arg1, align 8
  %v2 = getelementptr inbounds i8, ptr %arg0, i64 -8
  %v3 = load i64, ptr %v2, align 8
  %v7 = add nsw i64 %v3, 1
  %v6 = icmp eq i64 %v0, %v7
  ret i1 %v6
}