define i1 @src(double %arg2, ptr %arg0, ptr %arg1) {
  %v0 = fcmp ult double %arg2, 0.000000e+00
  %v1 = load double, ptr %arg1, align 8
  %v2 = fcmp ult double %v1, 0.000000e+00
  %v3 = select i1 %v2, double -1.000000e+00, double 1.000000e+00
  %v4 = fneg double %v3
  %v5 = select i1 %v0, double %v4, double %v3
  %v6 = load double, ptr %arg0, align 8
  %v7 = fcmp ult double %v6, 0.000000e+00
  %v8 = fneg double %v5
  %v9 = select i1 %v7, double %v8, double %v5
  %v10 = fcmp ult double %v9, 0.000000e+00
  ret i1 %v10
}

define i1 @tgt(double %arg2, ptr %arg0, ptr %arg1) {
  %v1 = load double, ptr %arg1, align 8
  %v6 = load double, ptr %arg0, align 8
  %v0 = fcmp ult double %arg2, 0.000000e+00
  %v2 = fcmp ult double %v1, 0.000000e+00
  %v7 = fcmp ult double %v6, 0.000000e+00
  %v3 = xor i1 %v0, %v2
  %v8 = xor i1 %v3, %v7
  ret i1 %v8
}