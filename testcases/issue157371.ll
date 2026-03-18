define i1 @src(ptr %arg0) {
  %v0 = load double, ptr %arg0, align 8
  %v1 = fcmp nsz olt double %v0, 1.000000e-02
  %v2 = fcmp nsz olt double %v0, 1.990000e+00
  %v3 = or i1 %v1, %v2
  ret i1 %v3
}

define i1 @tgt(ptr %arg0) {
  %v0 = load double, ptr %arg0, align 8
  %v1 = fcmp nsz olt double %v0, 1.990000e+00
  ret i1 %v1
}