define i1 @src(i32 %arg2, i32 %arg3, ptr %arg0, ptr %arg1) {
  %v0 = add nsw i32 %arg3, %arg2
  %v1 = sext i32 %v0 to i64
  %v2 = getelementptr inbounds double, ptr %arg1, i64 %v1
  %v3 = load double, ptr %v2, align 8
  %v4 = fcmp oge double %v3, 0.000000e+00
  %v5 = fneg double %v3
  %v6 = select i1 %v4, double %v3, double %v5
  %v7 = load double, ptr %arg0, align 8
  %v8 = fcmp oge double %v7, 0.000000e+00
  %v9 = fneg double %v7
  %v10 = select i1 %v8, double %v7, double %v9
  %v11 = fadd double %v6, %v10
  %v12 = fcmp oeq double %v11, 0.000000e+00
  ret i1 %v12
}

define i1 @tgt(i32 %arg3, i32 %arg2, ptr %arg0, ptr %arg1) {
  %v0 = add nsw i32 %arg3, %arg2
  %v1 = sext i32 %v0 to i64
  %v2 = getelementptr inbounds double, ptr %arg1, i64 %v1
  %v3 = load double, ptr %v2, align 8
  %v7 = load double, ptr %arg0, align 8
  %cmp1 = fcmp oeq double %v3, 0.000000e+00
  %cmp2 = fcmp oeq double %v7, 0.000000e+00
  %res = and i1 %cmp1, %cmp2
  ret i1 %res
}