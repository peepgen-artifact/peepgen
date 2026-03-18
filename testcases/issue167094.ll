define float @src(float %arg0) {
  %v0 = fcmp nsz ogt float %arg0, -3.200000e+04
  %v1 = select nsz i1 %v0, float %arg0, float -3.200000e+04
  %v2 = fcmp nsz ogt float %v1, 3.200000e+04
  %v3 = select nsz i1 %v2, float 3.200000e+04, float %v1
  ret float %v3
}

define float @tgt(float %arg0) {
  %v1 = call float @llvm.maxnum.f32(float %arg0, float -3.200000e+04)
  %v3 = call float @llvm.minnum.f32(float %v1, float 3.200000e+04)
  ret float %v3
}