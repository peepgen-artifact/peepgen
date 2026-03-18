define i1 @src(i64 %arg0, ptr %arg1) {
  %v0 = getelementptr double, ptr %arg1, i64 %arg0
  %v1 = mul nuw nsw i64 %arg0, 24
  %v2 = getelementptr i8, ptr %v0, i64 %v1
  %v3 = load double, ptr %v2, align 8
  %v4 = call noundef double @llvm.fabs.f64(double %v3)
  %v5 = fcmp ogt double %v4, 0x10000000000000
  ret i1 %v5
}

define i1 @tgt(i64 %arg0, ptr %arg1) {
  %scaled_idx = mul nuw nsw i64 %arg0, 4
  %v0_opt = getelementptr double, ptr %arg1, i64 %scaled_idx
  %v3 = load double, ptr %v0_opt, align 8
  %v4 = call noundef double @llvm.fabs.f64(double %v3)
  %v5 = fcmp ogt double %v4, 0x10000000000000
  ret i1 %v5
}
