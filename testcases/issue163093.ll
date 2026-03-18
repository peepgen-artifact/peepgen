define i1 @src(i64 %arg0, ptr %arg1) {
  %v0 = getelementptr inbounds nuw i8, ptr %arg1, i64 72
  %v1 = load i64, ptr %v0, align 8
  %v2 = getelementptr inbounds nuw i8, ptr %arg1, i64 64
  %v3 = load i64, ptr %v2, align 8
  %v4 = sub i64 %v1, %v3
  %v5 = icmp slt i64 %v1, 0
  %v6 = select i1 %v5, i64 0, i64 %v4
  %v7 = sub i64 %v3, %arg0
  %v8 = add i64 %v7, %v6
  %v9 = icmp eq i64 %v8, 0
  ret i1 %v9
}

define i1 @tgt(i64 %arg0, ptr %arg1) {
  %v0 = getelementptr inbounds nuw i8, ptr %arg1, i64 72
  %v1 = load i64, ptr %v0, align 8
  %v2 = getelementptr inbounds nuw i8, ptr %arg1, i64 64
  %v3 = load i64, ptr %v2, align 8
  %v4 = icmp slt i64 %v1, 0
  %v5 = select i1 %v4, i64 %v3, i64 %v1
  %v6 = sub i64 %v5, %arg0
  %v7 = icmp eq i64 %v6, 0
  ret i1 %v7
}