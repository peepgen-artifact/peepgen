define i1 @src(ptr %0) {
  %2 = getelementptr inbounds nuw i8, ptr %0, i64 48
  %3 = load double, ptr %2, align 8
  %4 = getelementptr inbounds nuw i8, ptr %0, i64 24
  %5 = load double, ptr %4, align 8
  %6 = fadd double %3, %5
  %7 = fcmp ord double %6, 0.000000e+00
  %8 = select i1 %7, double %6, double 0.000000e+00
  %9 = fcmp oeq double %8, 1.000000e+00
  ret i1 %9
}

define i1 @tgt(ptr %0) {
  %2 = getelementptr inbounds nuw i8, ptr %0, i64 48
  %3 = load double, ptr %2, align 8
  %4 = getelementptr inbounds nuw i8, ptr %0, i64 24
  %5 = load double, ptr %4, align 8
  %6 = fadd double %3, %5
  %7 = fcmp oeq double %6, 1.000000e+00
  ret i1 %7
}