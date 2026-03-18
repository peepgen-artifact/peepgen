define i1 @src(ptr %lpo_arg0) {
  %v0 = getelementptr inbounds nuw i8, ptr %lpo_arg0, i64 16
  %v1 = load i64, ptr %v0, align 8
  %v2 = trunc i64 %v1 to i32
  %v3 = icmp eq i32 %v2, 0
  %v4 = icmp ult i64 %v1, 4294967296
  %v5 = and i1 %v4, %v3
  ret i1 %v5
}

define i1 @tgt(ptr %lpo_arg0) {
  %v0 = getelementptr inbounds nuw i8, ptr %lpo_arg0, i64 16
  %v1 = load i64, ptr %v0, align 8
  %v2 = icmp eq i64 %v1, 0
  ret i1 %v2
}