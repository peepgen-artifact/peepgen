define i1 @src(ptr %arg0) {
  %v0 = getelementptr inbounds nuw i8, ptr %arg0, i64 8
  %v1 = load i8, ptr %v0, align 8
  %v2 = icmp eq i8 %v1, 4
  %v3 = select i1 %v2, ptr %arg0, ptr null
  %v4 = icmp eq ptr %v3, null
  ret i1 %v4
}

define i1 @tgt(ptr %arg0) {
  %v0 = getelementptr inbounds nuw i8, ptr %arg0, i64 8
  %v1 = load i8, ptr %v0, align 8
  %v3 = icmp ne i8 %v1, 4
  ret i1 %v3
}