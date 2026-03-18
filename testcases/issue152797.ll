define i1 @src(ptr %0) {
  %v0 = getelementptr inbounds nuw i8, ptr %0, i64 4
  %v1 = load i32, ptr %v0, align 4
  %v2 = zext i32 %v1 to i64
  %v3 = ptrtoint ptr %v0 to i64
  %v4 = add i64 %v2, %v3
  %v5 = and i64 %v4, 2
  %v6 = icmp eq i64 %v5, 0
  ret i1 %v6
}

define i1 @tgt(ptr %0) {
  %v0 = getelementptr inbounds nuw i8, ptr %0, i64 4
  %v1 = load i32, ptr %v0, align 4
  %v2 = and i32 %v1, 2
  %v3 = icmp eq i32 %v2, 0
  ret i1 %v3
}