define i1 @src(double %arg0) {
  %v0 = fmul double %arg0, 1.000000e+06
  %v1 = fcmp ule double %v0, 0.000000e+00
  ret i1 %v1
}

define i1 @tgt(double %arg0) {
  %v1 = fcmp ule double %arg0, 0.000000e+00
  ret i1 %v1
}