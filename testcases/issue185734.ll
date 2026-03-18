define i1 @src(float %arg0, float %arg1) {
  %v0 = fcmp ogt float %arg1, 1.000000e+00
  %v1 = select i1 %v0, float 1.000000e+00, float %arg1
  %v2 = fcmp ogt float %v1, 0.000000e+00
  %v3 = select i1 %v2, float %v1, float 0.000000e+00
  %v4 = fcmp ogt float %arg0, 1.000000e+00
  %v5 = select i1 %v4, float 1.000000e+00, float %arg0
  %v6 = fcmp ogt float %v5, 0.000000e+00
  %v7 = select i1 %v6, float %v5, float 0.000000e+00
  %v8 = fcmp oeq float %v3, 1.000000e+00
  %v9 = fcmp oeq float %v7, 1.000000e+00
  %v10 = and i1 %v8, %v9
  ret i1 %v10
}

define i1 @tgt(float %arg0, float %arg1) {
  %cmp0 = fcmp oge float %arg0, 1.000000e+00
  %cmp1 = fcmp oge float %arg1, 1.000000e+00
  %result = and i1 %cmp0, %cmp1
  ret i1 %result
}