define double @src(i1 %arg0, i32 %arg1, i32 %arg2) {
  %v0 = icmp samesign ult i32 %arg2, 2
  %v1 = uitofp nneg i32 %arg2 to double
  %v2 = select i1 %v0, double 1.000000e+00, double %v1
  %v3 = uitofp nneg i32 %arg1 to double
  %v4 = select i1 %arg0, double %v3, double %v2
  ret double %v4
}

define double @tgt(i1 %arg0, i32 %arg1, i32 %arg2) {
  %conv_arg1 = uitofp nneg i32 %arg1 to double
  %conv_arg2 = uitofp nneg i32 %arg2 to double
  %max_val = call double @llvm.maxnum.v2f64(double %conv_arg2, double 1.0)
  %result = select i1 %arg0, double %conv_arg1, double %max_val
  ret double %result
}