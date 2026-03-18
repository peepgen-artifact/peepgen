from generalization.compare_precondition import compare_initial_generalization

# ir_A = """
# define i1 @src(i64 %arg0) {
#   %v0 = sdiv exact i64 %arg0, 12
#   %v1 = icmp ugt i64 %v0, 12
#   ret i1 %v1
# }

# define i1 @tgt(i64 %arg0) {
#   %v0 = icmp ugt i64 %arg0, 144
#   ret i1 %v0
# }
# """

# ir_B = """
# define i1 @src(i32 %x, i32 %C1, i32 %C2) {
# %c1_is_positive = icmp sgt i32 %C1, 0
# call void @llvm.assume(i1 %c1_is_positive)
# %mul_with_overflow = call {i32, i1} @llvm.smul.with.overflow.i32(i32 %C1, i32 %C2)
# %overflow_bit = extractvalue {i32, i1} %mul_with_overflow, 1
# %no_overflow = icmp eq i1 %overflow_bit, false
# call void @llvm.assume(i1 %no_overflow)
# %v0 = sdiv exact i32 %x, %C1
# %v1 = icmp ugt i32 %v0, %C2
# ret i1 %v1
# }
# define i1 @tgt(i32 %x, i32 %C1, i32 %C2) {
# %c1_is_positive = icmp sgt i32 %C1, 0
# call void @llvm.assume(i1 %c1_is_positive)
# %mul_with_overflow = call {i32, i1} @llvm.smul.with.overflow.i32(i32 %C1, i32 %C2)
# %product = extractvalue {i32, i1} %mul_with_overflow, 0
# %overflow_bit = extractvalue {i32, i1} %mul_with_overflow, 1
# %no_overflow = icmp eq i1 %overflow_bit, false
# call void @llvm.assume(i1 %no_overflow)
# %v0 = icmp ugt i32 %x, %product
# ret i1 %v0
# }
# """

# ir_A = """
# define i1 @src(float %lpo_arg0) {
#   %v0 = fcmp ogt float %lpo_arg0, 1.000000e+00
#   %v1 = select i1 %v0, float 1.000000e+00, float %lpo_arg0
#   %v2 = fcmp ogt float %v1, 0.000000e+00
#   %v3 = select i1 %v2, float %v1, float 0.000000e+00
#   %v4 = fcmp oeq float %v3, 1.000000e+00
#   ret i1 %v4
# }

# define i1 @tgt(float %lpo_arg0) {
#   %v = fcmp oge float %lpo_arg0, 1.000000e+00
#   ret i1 %v
# }
# """

# ir_B = """
# define i1 @src(float %x, float %C_high, float %C_low) {
# %pre = fcmp ogt float %C_high, %C_low
# call void @llvm.assume(i1 %pre)
# %v0 = fcmp ogt float %x, %C_high
# %v1 = select i1 %v0, float %C_high, float %x
# %v2 = fcmp ogt float %v1, %C_low
# %v3 = select i1 %v2, float %v1, float %C_low
# %v4 = fcmp oeq float %v3, %C_high
# ret i1 %v4
# }
# define i1 @tgt(float %x, float %C_high, float %C_low) {
# %pre = fcmp ogt float %C_high, %C_low
# call void @llvm.assume(i1 %pre)
# %v = fcmp oge float %x, %C_high
# ret i1 %v
# }
# """


# ir_A = """
# define i1 @src(<2 x float> %lpo_arg0) {
#   %v0 = extractelement <2 x float> %lpo_arg0, i64 0
#   %v1 = fmul float %v0, 2.000000e+00
#   %v2 = extractelement <2 x float> %lpo_arg0, i64 1
#   %v3 = fmul float %v2, 2.000000e+00
#   %v4 = fadd float %v1, -1.000000e+00
#   %v5 = fadd float %v3, -1.000000e+00
#   %v6 = fcmp oeq float %v4, 0.000000e+00
#   %v7 = fcmp oeq float %v5, 0.000000e+00
#   %v8 = select i1 %v6, i1 %v7, i1 false
#   ret i1 %v8
# }

# define i1 @tgt(<2 x float> %lpo_arg0) {
#   %v0 = extractelement <2 x float> %lpo_arg0, i64 0
#   %v6 = fcmp oeq float %v0, 5.000000e-01
#   %v2 = extractelement <2 x float> %lpo_arg0, i64 1
#   %v7 = fcmp oeq float %v2, 5.000000e-01
#   %v8 = select i1 %v6, i1 %v7, i1 false
#   ret i1 %v8
# }
# """

# ir_B = """
# define i1 @src(<2 x i32> %arg, i32 %C1, i32 %C2, i32 %C3) {
# %precond_c1_ne_0 = icmp ne i32 %C1, 0
# call void @llvm.assume(i1 %precond_c1_ne_0)
# %tmp1 = sub i32 %C3, %C2
# %rem = srem i32 %tmp1, %C1
# %precond_exact_div = icmp eq i32 %rem, 0
# call void @llvm.assume(i1 %precond_exact_div)
# %v0 = extractelement <2 x i32> %arg, i64 0
# %mul0 = mul nsw i32 %v0, %C1
# %add0 = add nsw i32 %mul0, %C2
# %cmp0 = icmp eq i32 %add0, %C3
# %v1 = extractelement <2 x i32> %arg, i64 1
# %mul1 = mul nsw i32 %v1, %C1
# %add1 = add nsw i32 %mul1, %C2
# %cmp1 = icmp eq i32 %add1, %C3
# %res = select i1 %cmp0, i1 %cmp1, i1 false
# ret i1 %res
# }
# define i1 @tgt(<2 x i32> %arg, i32 %C1, i32 %C2, i32 %C3) {
# %precond_c1_ne_0 = icmp ne i32 %C1, 0
# call void @llvm.assume(i1 %precond_c1_ne_0)
# %tmp1 = sub i32 %C3, %C2
# %rem = srem i32 %tmp1, %C1
# %precond_exact_div = icmp eq i32 %rem, 0
# call void @llvm.assume(i1 %precond_exact_div)
# %C4_num = sub i32 %C3, %C2
# %C4 = sdiv exact i32 %C4_num, %C1
# %v0 = extractelement <2 x i32> %arg, i64 0
# %cmp0 = icmp eq i32 %v0, %C4
# %v1 = extractelement <2 x i32> %arg, i64 1
# %cmp1 = icmp eq i32 %v1, %C4
# %res = select i1 %cmp0, i1 %cmp1, i1 false
# ret i1 %res
# }
# """

# ir_A = """
# define i1 @src1(ptr readonly captures(none) %0) local_unnamed_addr #0 {
# %2 = getelementptr inbounds nuw i8, ptr %0, i64 1
# %3 = load i8, ptr %2, align 1
# %4 = zext i8 %3 to i32
# %5 = shl nuw nsw i32 %4, 8
# %6 = getelementptr inbounds nuw i8, ptr %0, i64 2
# %7 = load i8, ptr %6, align 1
# %8 = zext i8 %7 to i32
# %9 = or disjoint i32 %5, %8
# %10 = icmp ne i32 %9, 256
# ret i1 %10
# }
# define i1 @tgt1(ptr readonly captures(none) %0) local_unnamed_addr #0 {
# %2 = getelementptr inbounds nuw i8, ptr %0, i64 1
# %3 = load i8, ptr %2, align 1
# %4 = getelementptr inbounds nuw i8, ptr %0, i64 2
# %5 = load i8, ptr %4, align 1
# %6 = icmp ne i8 %3, 1
# %7 = icmp ne i8 %5, 0
# %8 = or i1 %6, %7
# ret i1 %8
# }
# """

# ir_B = """
# define i1 @src(ptr %ptr, i64 %off1, i64 %off2, i64 %C) {
# %bitwidth_load1_load2 = add i32 16, 0
# %bitwidth_or_C = add i32 64, 0
# %bw_load_as_i64 = zext i32 %bitwidth_load1_load2 to i64
# %double_bw_load_as_i64 = shl i64 %bw_load_as_i64, 1
# %C_hi_bits = lshr i64 %C, %double_bw_load_as_i64
# %is_C_small = icmp eq i64 %C_hi_bits, 0
# call void @llvm.assume(i1 %is_C_small)
# %gep1 = getelementptr i16, ptr %ptr, i64 %off1
# %load1 = load i16, ptr %gep1, align 2
# %zext1 = zext i16 %load1 to i64
# %gep2 = getelementptr i16, ptr %ptr, i64 %off2
# %load2 = load i16, ptr %gep2, align 2
# %zext2 = zext i16 %load2 to i64
# %shl = shl nsw nuw i64 %zext1, %bw_load_as_i64
# %or = or disjoint i64 %shl, %zext2
# %cmp = icmp ne i64 %or, %C
# ret i1 %cmp
# }
# define i1 @tgt(ptr %ptr, i64 %off1, i64 %off2, i64 %C) {
# %bitwidth_load1_load2 = add i32 16, 0
# %bitwidth_or_C = add i32 64, 0
# %bw_load_as_i64 = zext i32 %bitwidth_load1_load2 to i64
# %double_bw_load_as_i64 = shl i64 %bw_load_as_i64, 1
# %C_hi_bits = lshr i64 %C, %double_bw_load_as_i64
# %is_C_small = icmp eq i64 %C_hi_bits, 0
# call void @llvm.assume(i1 %is_C_small)
# %gep1 = getelementptr i16, ptr %ptr, i64 %off1
# %load1 = load i16, ptr %gep1, align 2
# %C_shifted = lshr i64 %C, %bw_load_as_i64
# %C1 = trunc i64 %C_shifted to i16
# %cmp1 = icmp ne i16 %load1, %C1
# %gep2 = getelementptr i16, ptr %ptr, i64 %off2
# %load2 = load i16, ptr %gep2, align 2
# %C2 = trunc i64 %C to i16
# %cmp2 = icmp ne i16 %load2, %C2
# %or = or i1 %cmp1, %cmp2
# ret i1 %or
# }
# """

# ir_A = """
# define i1 @src(float %v1) {
#   %v2 = fmul float %v1, 5.000000e-01
#   %v3 = fcmp olt float %v2, 8.000000e+00
#   ret i1 %v3
# }

# define i1 @tgt(float %v1) {
#   %v2 = fcmp olt float %v1, 1.600000e+01
#   ret i1 %v2
# }
# """

# ir_B = """
# define i1 @src(float %v1, float %C1, float %C2) {
# %precond = fcmp ogt float %C1, 0.0
# call void @llvm.assume(i1 %precond)
# %mul = fmul fast float %v1, %C1
# %cmp = fcmp olt float %mul, %C2
# ret i1 %cmp
# }
# define i1 @tgt(float %v1, float %C1, float %C2) {
# %precond = fcmp ogt float %C1, 0.0
# call void @llvm.assume(i1 %precond)
# %div = fdiv fast float %C2, %C1
# %cmp = fcmp olt float %v1, %div
# ret i1 %cmp
# }
# """

ir_A = """
define i1 @src(double %lpo_arg0, double %lpo_arg1) {
  %v0 = fcmp ult double %lpo_arg1, 0.000000e+00
  %v1 = select i1 %v0, double -1.000000e+00, double 1.000000e+00
  %v2 = fcmp ult double %lpo_arg0, 0.000000e+00
  %v3 = select i1 %v2, double -1.000000e+00, double 1.000000e+00
  %v4 = fcmp une double %v1, %v3
  ret i1 %v4
}

define i1 @tgt(double %lpo_arg0, double %lpo_arg1) {
  %c0 = fcmp ult double %lpo_arg0, 0.000000e+00
  %c1 = fcmp ult double %lpo_arg1, 0.000000e+00
  %res = xor i1 %c0, %c1
  ret i1 %res
}
"""

ir_B = """
define i1 @src(float %arg0, float %arg1, float %C0, float %C1, float %C2) {
%pcond = fcmp one float %C1, %C2
call void @llvm.assume(i1 %pcond)
%cmp1 = fcmp oeq float %arg1, %C0
%sel1 = select i1 %cmp1, float %C1, float %C2
%cmp0 = fcmp oeq float %arg0, %C0
%sel0 = select i1 %cmp0, float %C1, float %C2
%res = fcmp une float %sel1, %sel0
ret i1 %res
}
define i1 @tgt(float %arg0, float %arg1, float %C0, float %C1, float %C2) {
%pcond = fcmp one float %C1, %C2
call void @llvm.assume(i1 %pcond)
%cmp0 = fcmp oeq float %arg0, %C0
%cmp1 = fcmp oeq float %arg1, %C0
%res = xor i1 %cmp0, %cmp1
ret i1 %res
}
"""


try:
    res = compare_initial_generalization(ir_A, ir_B)
    print(f"Result: {res}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
