define i32 @src(i64 %arg0, i64 %arg1) {
  %v0 = icmp eq i64 %arg1, %arg0
  %v1 = insertelement <4 x i1> poison, i1 %v0, i64 0
  %v2 = shufflevector <4 x i1> %v1, <4 x i1> poison, <4 x i32> zeroinitializer
  %v3 = bitcast <4 x i1> %v2 to i4
  %v4 = zext i4 %v3 to i32
  ret i32 %v4
}

define i32 @tgt(i64 %arg0, i64 %arg1) {
  %v0 = icmp eq i64 %arg1, %arg0
  %v_i32 = zext i1 %v0 to i32
  %result = mul i32 %v_i32, 15
  ret i32 %result
}