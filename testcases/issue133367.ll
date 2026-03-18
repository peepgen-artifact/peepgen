define i1 @src1(double %.11946, double %.11936) {
  %1 = fcmp oge double %.11936, 0.000000e+00
  %2 = fneg double %.11936
  %3 = select i1 %1, double %.11936, double %2
  %4 = fcmp oge double %.11946, 0.000000e+00
  %5 = fneg double %.11946
  %6 = select i1 %4, double %.11946, double %5
  %7 = fcmp olt double %3, %6
  ret i1 %7
}

define i1 @tgt1(double %.11946, double %.11936) local_unnamed_addr #0 {
  %abs11936 = tail call double @llvm.fabs.f64(double %.11936)
  %abs11946 = tail call double @llvm.fabs.f64(double %.11946)
  %cmp = fcmp olt double %abs11936, %abs11946
  ret i1 %cmp
}