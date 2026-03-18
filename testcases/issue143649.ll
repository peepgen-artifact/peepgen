define double @src(double %arg0) {
  %2 = fcmp ord double %arg0, 0.000000e+00
  %3 = select i1 %2, double %arg0, double 0.000000e+00
  %4 = call double @llvm.fabs.f64(double %3)
  %5 = fcmp one double %4, 0x7FF0000000000000
  %6 = select i1 %5, double %3, double 0.000000e+00
  ret double %6
}

define double @tgt(double %arg0) {
  %2 = call double @llvm.fabs.f64(double %arg0)
  %3 = fcmp one double %2, 0x7FF0000000000000
  %4 = select i1 %3, double %arg0, double 0.000000e+00
  ret double %4
}