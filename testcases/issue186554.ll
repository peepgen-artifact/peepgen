define i1 @src(float %arg0) {
  %v0 = tail call { float, i32 } @llvm.frexp.f32.i32(float %arg0)
  %v1 = extractvalue { float, i32 } %v0, 1
  %v2 = icmp slt i32 %v1, 24
  ret i1 %v2
}

define i1 @tgt(float %arg0) {
  %v0 = call float @llvm.fabs.f32(float %arg0)
  %v1 = fcmp olt float %v0, 8.388608e+06
  ret i1 %v1
}