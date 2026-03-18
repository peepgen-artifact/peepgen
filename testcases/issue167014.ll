define ptr @src(i32 %arg0, ptr %arg1) {
  %v0 = getelementptr inbounds nuw i8, ptr %arg1, i64 8148
  %v1 = icmp sgt i32 %arg0, 3
  %v2 = select i1 %v1, i64 55104, i64 21304
  %v3 = getelementptr i8, ptr %v0, i64 %v2
  ret ptr %v3
}

define ptr @tgt(i32 %arg0, ptr %arg1) {
  %v1 = icmp sgt i32 %arg0, 3
  %v2 = select i1 %v1, i64 63252, i64 29452
  %v3 = getelementptr i8, ptr %arg1, i64 %v2
  ret ptr %v3
}