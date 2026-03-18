define i1 @src(i32 %arg0) {
  %v0 = add nsw i32 %arg0, -1
  %v1 = sitofp i32 %v0 to float
  %v2 = fsub float 1.000000e+00, %v1
  %v3 = fcmp olt float %v2, 1.000000e+00
  ret i1 %v3
}

define i1 @tgt(i32 %arg0) {
  %res = icmp sgt i32 %arg0, 1
  ret i1 %res
}