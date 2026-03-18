
import sys
import os

# Add current directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from generalization.utils import analyze_constant_generalization

def test_simple_replacement():
    src_A = [
        "%x = add i32 %a, 1",
        "ret i32 %x"
    ]
    src_B = [
        "%x = add i32 %a, %C",
        "ret i32 %x"
    ]
    
    print("Test 1: Simple Replacement")
    mappings = analyze_constant_generalization(src_A, src_B)
    print(mappings)
    assert len(mappings) == 1
    assert mappings[0]['original'] == '1'
    assert mappings[0]['generalized'] == '%C'

def test_expression_replacement():
    src_A = [
        "%x = shl i32 30, 31",
        "ret i32 %x"
    ]
    src_B = [
        "%w = call i32 @llvm.cttz.i32(i32 %C2, i1 true)",
        "%a = add i32 %b, 1",
        "%t = sub i32 %w, 1",
        "%x = shl i32 %a, %t",
        "ret i32 %x"
    ]
    
    print("\nTest 2: Expression Replacement")
    mappings = analyze_constant_generalization(src_A, src_B)
    print(mappings)
#     assert len(mappings) == 1
#     assert mappings[0]['original'] == '31'
#     # The expression string format depends on my implementation
#     # It should be (%w - 1) or sub(%w, 1)
#     assert 'sub' in mappings[0]['generalized'] or '-' in mappings[0]['generalized']

def test_nested_expression():
    # src_A = [
    #     "%a = load double, ptr %2, align 8",
    #     "%t1 = fadd double %a, 1.5",
    #     "%t2 = fmul double %t1, 2.0",
    #     "ret double %t2"
    # ]
    # src_B = [
    #     "%c1 = fadd double %w, 0.5", 
    #     "%t1 = fadd double %b, %c1", # 1.5 -> (w + 0.5)
    #     "%t2 = fmul double %t2, %k", # 2.0 -> k
    #     "ret double %t2"
    # ]
    src_A = [
  "%v0 = fcmp ogt float %lpo_arg0, 1.000000e+00",
  "%v1 = select i1 %v0, float 1.000000e+00, float %lpo_arg0",
  "%v2 = fcmp ogt float %v1, 0.000000e+00",
  "%v3 = select i1 %v2, float %v1, float 0.000000e+00",
  "%v4 = fcmp oeq float %v3, 1.000000e+00",
  "ret i1 %v4"

    ]
    src_B = [
"%v0 = fcmp ogt float %x, %C_high",
"%v1 = select i1 %v0, float %C_high, float %x",
"%v2 = fcmp ogt float %v1, %C_low",
"%v3 = select i1 %v2, float %v1, float %C_low",
"%v4 = fcmp oeq float %v3, %C_high",
"ret i1 %v4"
    ]



    
    print("\nTest 3: Nested Expression")
    mappings = analyze_constant_generalization(src_A, src_B)
    print(mappings)
    # assert len(mappings) == 2
    # # Order depends on traversal, but we expect both float originals
    # originals = sorted([m['original'] for m in mappings])
    # assert originals == ['1.5', '2.0']

# def test_structural_mismatch():
#     src_A = [
#         "%x = add i32 %a, 1",
#         "ret i32 %x"
#     ]
#     src_B = [
#         "%x = sub i32 %a, -1",
#         "ret i32 %x"
#     ]
    
#     print("\nTest 4: Structural Mismatch")
#     mappings = analyze_constant_generalization(src_A, src_B)
#     print(mappings)
#     # Should be empty because opcodes differ (add vs sub)
#     assert len(mappings) == 0

if __name__ == "__main__":
#     test_simple_replacement()
    # test_expression_replacement()
    test_nested_expression()
#     test_structural_mismatch()
#     print("\nAll tests passed!")
