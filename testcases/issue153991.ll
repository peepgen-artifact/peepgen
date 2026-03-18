define i1 @src(float %v1) {
 %v2 = fmul float %v1, 5.000000e-01
  %v3 = fcmp olt float %v2, 8.000000e+00
  ret i1 %v3
}

define i1 @tgt(float %v1) {
  %v2 = fcmp olt float %v1, 1.600000e+01
  ret i1 %v2
}