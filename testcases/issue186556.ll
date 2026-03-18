define i1 @src(float %arg1, ptr %arg0, ptr %arg2) {
  %v0 = getelementptr inbounds nuw i8, ptr %arg2, i64 4
  %v1 = load i16, ptr %v0, align 2
  %v2 = zext i16 %v1 to i64
  %v3 = getelementptr inbounds nuw float, ptr %arg0, i64 %v2
  %v4 = load float, ptr %v3, align 4
  %v5 = fmul float %arg1, %v4
  %v6 = fcmp ogt float %v5, 0.000000e+00
  %v7 = select i1 %v6, float %v5, float 0.000000e+00
  %v8 = fcmp ogt float %v7, 1.000000e+00
  ret i1 %v8
}

define i1 @tgt(float %arg1, ptr %arg0, ptr %arg2) {
  %v0 = getelementptr inbounds nuw i8, ptr %arg2, i64 4
  %v1 = load i16, ptr %v0, align 2
  %v2 = zext i16 %v1 to i64
  %v3 = getelementptr inbounds nuw float, ptr %arg0, i64 %v2
  %v4 = load float, ptr %v3, align 4
  %v5 = fmul float %arg1, %v4
  %v6 = fcmp ogt float %v5, 1.000000e+00
  ret i1 %v6
}