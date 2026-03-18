define i1 @src(double %arg1, ptr %arg0) {
  %v0 = fcmp oge double %arg1, 0.000000e+00
  %v1 = fneg double %arg1
  %v2 = select i1 %v0, double %arg1, double %v1
  %v3 = getelementptr inbounds nuw i8, ptr %arg0, i64 160
  %v4 = load double, ptr %v3, align 8
  %v5 = fcmp nsz olt double %v4, %v2
  ret i1 %v5
}

define i1 @tgt(double %arg1, ptr %arg0) {
  %v2_opt = call double @llvm.fabs.f64(double %arg1)
  %v3 = getelementptr inbounds nuw i8, ptr %arg0, i64 160
  %v4 = load double, ptr %v3, align 8
  %v5 = fcmp olt double %v4, %v2_opt
  ret i1 %v5
}
