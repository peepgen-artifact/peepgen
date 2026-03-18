define i1 @src(double %arg0) {
  %v0 = fptrunc double %arg0 to float
  %v1 = fcmp uno float %v0, 0.000000e+00
  ret i1 %v1
}

define i1 @tgt(double %arg0) {
  %v1 = fcmp uno double %arg0, 0.000000e+00
  ret i1 %v1
}