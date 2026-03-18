from further_generalization import operator_mutation_generalization

SAMPLES = [
    (
        "simple_shl",
        """
define i32 @src(i32 %a) {
  %x = lshr i32 %a, 20
  %y = lshr i32 %x, %a
  %z = shl i32 %y, %y
  %q = shl i32 %z, %z
  %res = add i32 %x, %x
  ret i32 %res
}

define i32 @tgt(i32 %a) {
  %x = lshr i32 20, 20
  %res = add i32 %x, %x
  ret i32 %res
}
""",
    ),
#     (
#         "no_shift",
#         """
# define i32 @src(i32 %a) {
#   %y = add i32 %a, 3
#   ret i32 %y
# }

# define i32 @tgt(i32 %a) {
#   %y = add i32 %a, 3
#   ret i32 %y
# }
# """,
#     ),
#         (
#                 "large_shift",
#                 """
# define i32 @src(i32 %a) {
#     %x = shl i32 %a, 4
#     %res = mul i32 %x, %x
#     ret i32 %res
# }

# define i32 @tgt(i32 %a) {
#     %x = shl i32 %a, 4
#     %res = mul i32 %x, %x
#     ret i32 %res
# }
# """,
#         ),
#         (
#                 "logical_rshift",
#                 """
# define i32 @src(i32 %a) {
#     %x = lshr i32 %a, 2
#     %res = udiv i32 %x, 3
#     ret i32 %res
# }

# define i32 @tgt(i32 %a) {
#     %x = lshr i32 %a, 2
#     %res = udiv i32 %x, 3
#     ret i32 %res
# }
# """,
#         ),
#         (
#                 "arith_rshift",
#                 """
# define i32 @src(i32 %a) {
#     %x = ashr i32 %a, 1
#     %res = sdiv i32 %x, 5
#     ret i32 %res
# }

# define i32 @tgt(i32 %a) {
#     %x = ashr i32 %a, 1
#     %res = sdiv i32 %x, 5
#     ret i32 %res
# }
# """,
#         ),
#         (
#                 "multiple_shifts",
#                 """
# define i32 @src(i32 %a) {
#     %x = shl i32 %a, 1
#     %y = shl i32 %x, 2
#     %res = add i32 %y, %a
#     ret i32 %res
# }

# define i32 @tgt(i32 %a) {
#     %x = shl i32 %a, 1
#     %y = shl i32 %x, 2
#     %res = add i32 %y, %a
#     ret i32 %res
# }
# """,
#         ),
#         (
#                 "multiple_same_shifts",
#                 """
# define i32 @src(i32 %a, i32 %b) {
#   %x = shl i32 %a, 1
#   %y = shl i32 %b, 1
#   %res = add i32 %x, %y
#   ret i32 %res
# }

# define i32 @tgt(i32 %a, i32 %b) {
#   %x = shl i32 %a, 1
#   %y = shl i32 %b, 1
#   %res = add i32 %x, %y
#   ret i32 %res
# }
# """,
#         ),
#     (
#         "shift_and_other_ops",
#                 """
# define i32 @src(i32 %a) {
#     %x = shl i32 %a, 3
#     %y = and i32 %x, 7
#     %res = add i32 %y, 1
#     ret i32 %res
# }

# define i32 @tgt(i32 %a) {
#     %x = shl i32 %a, 3
#     %y = and i32 %x, 7
#     %res = add i32 %y, 1
#     ret i32 %res
# }
# """,
#         ),
]


def run_samples():
    for name, ir in SAMPLES:
        print("========================================")
        print(f"Sample: {name}")
        print("--- Original IR ---")
        print(ir)
        try:
            transformed_ir, success = operator_mutation_generalization(ir)
        except Exception as e:
            print("--- Transformation raised an exception ---")
            print(str(e))
            continue

        print("--- Transformed IR ---")
        if transformed_ir is None:
            print("(None)")
        else:
            print(transformed_ir)
        print(f"Mutation success: {success}")
        print()


if __name__ == '__main__':
    run_samples()
