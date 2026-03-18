define float @src(float %arg0) {
  %v0 = fcmp nsz ogt float %arg0, 0.000000e+00
  %v1 = select nsz i1 %v0, float %arg0, float 0.000000e+00
  %v2 = fcmp nsz ogt float %v1, 0x3FE96C8000000000
  %v3 = select nsz i1 %v2, float 0x3FE96C8000000000, float %v1
  ret float %v3
}

define float @tgt(float %arg0) {
  %v0 = call float @llvm.maxnum.f32(float %arg0, float 0.000000e+00)
  %v1 = call float @llvm.minnum.f32(float %v0, float 0x3FE96C8000000000)
  ret float %v1
}