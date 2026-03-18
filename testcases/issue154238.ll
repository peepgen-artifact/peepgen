define double @src(double %arg0, float %arg1) {
  %v2 = fadd float %arg1, 0.000000e+00
  %v3 = call noundef float @llvm.fabs.f32(float %v2)
  %v4 = fpext float %v3 to double
  %v5 = fcmp olt double %arg0, %v4
  %v6 = select i1 %v5, double %v4, double %arg0
  ret double %v6
}

define double @tgt(double %arg0, float %arg1) {
  %v2 = call noundef float @llvm.fabs.f32(float %arg1)
  %v3 = fpext float %v2 to double
  %v4 = fcmp olt double %arg0, %v3
  %v5 = select i1 %v4, double %v3, double %arg0
  ret double %v5
}