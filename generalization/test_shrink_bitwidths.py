from generalization.handle_timeout import shrink_bitwidths_by_half

def test_shrink_bitwidths():
    test_cases = [
        (
            "Basic arithmetic shrinking",
            """
            %1 = add i32 %a, %b
            %2 = sub i64 %c, %d
            """,
            """
            %1 = add i16 %a, %b
            %2 = sub i32 %c, %d
            """
        ),
        (
            "GetElementPtr protection (i8 should stay i8)",
            """
            %q = getelementptr inbounds i8, i32* %p, i32 1
            """,
            """
            %q = getelementptr inbounds i8, i16* %p, i16 1
            """
        ),
        (
            "GetElementPtr with larger type (i32 should stay i32 as base type)",
            """
            %q = getelementptr i32, i32* %p, i64 2
            """,
            """
            %q = getelementptr i32, i16* %p, i32 2
            """
        ),
        (
            "Bitwidth definition constant shrinking",
            """
            %bitwidth = add i32 32, 0
            %other = add i32 16, 0
            """,
            """
            %bitwidth = add i16 16, 0
            %other = add i16 16, 0
            """
        ),
        (
            "Float type shrinking",
            """
            %1 = fadd double %a, %b
            %2 = fmul float %c, %d
            """,
            """
            %1 = fadd float %a, %b
            %2 = fmul half %c, %d
            """
        ),
        (
            "Mixed instructions",
            """
            define i32 @src(i32* %p) {
              %q = getelementptr inbounds i8, i32* %p, i32 1
              %v = load i8, i8* %q, align 1
              %r = zext i8 %v to i32
              ret i32 %r
            }
            """,
            """
define i16 @src(i16* %p) {
%q = getelementptr inbounds i8, i16* %p, i16 1
%v = load i4, i4* %q, align 1
%r = zext i4 %v to i16
ret i16 %r
}
            """
        ),
        (
            "Odd bitwidths and i1 preservation",
            """
            %1 = add i33 %a, %b
            %2 = select i1 %cond, i64 %x, i64 %y
            """,
            """
            %1 = add i33 %a, %b
            %2 = select i1 %cond, i32 %x, i32 %y
            """
        ),
        (
            "Vector types",
            """
            %v = add <4 x i32> %a, %b
            """,
            """
            %v = add <4 x i16> %a, %b
            """
        ),
        (
            "Array types",
            """
            %a = alloca [10 x i64], align 8
            """,
            """
            %a = alloca [10 x i32], align 8
            """
        ),
        (
            "Complex GEP with struct (struct type gets shrunk because regex doesn't protect it)",
            """
            %p = getelementptr inbounds {i32, i32}, {i32, i32}* %ptr, i64 0, i32 1
            """,
            """
            %p = getelementptr inbounds {i16, i16}, {i16, i16}* %ptr, i32 0, i16 1
            """
        ),
        (
            "Function call with multiple arguments",
            """
            %call = call i32 @func(i32 %a, i64 %b)
            """,
            """
            %call = call i16 @func(i16 %a, i32 %b)
            """
        )
    ]

    print("Running shrink_bitwidths_by_half tests...\n")
    
    for name, input_ir, expected_ir in test_cases:
        print(f"Test Case: {name}")
        print("-" * 40)
        
        # Clean up indentation for comparison
        input_ir = "\n".join([l.strip() for l in input_ir.strip().splitlines()])
        expected_ir = "\n".join([l.strip() for l in expected_ir.strip().splitlines()])
        
        result_ir, changed = shrink_bitwidths_by_half(input_ir)
        
        # Normalize result for comparison
        result_ir = "\n".join([l.strip() for l in result_ir.strip().splitlines()])
        
        if result_ir == expected_ir:
            print("PASS")
        else:
            print("FAIL")
            print("Expected:")
            print(expected_ir)
            print("\nGot:")
            print(result_ir)
        print("\n")

if __name__ == "__main__":
    test_shrink_bitwidths()
