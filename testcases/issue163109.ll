define ptr @src(i8 %arg1, ptr %arg0) {
  %v0 = icmp eq i8 %arg1, 116
  %v1 = select i1 %v0, ptr %arg0, ptr null
  %v2 = getelementptr inbounds nuw i8, ptr %v1, i16 48
  %v3 = getelementptr inbounds nuw i8, ptr %arg0, i16 40
  %v4 = select i1 %v0, ptr %v2, ptr %v3
  ret ptr %v4
}

define ptr @tgt(i8 %arg1, ptr %arg0) {
  %v0 = icmp eq i8 %arg1, 116
  %v1 = select i1 %v0, i16 48, i16 40
  %v2 = getelementptr inbounds i8, ptr %arg0, i16 %v1
  ret ptr %v2
}