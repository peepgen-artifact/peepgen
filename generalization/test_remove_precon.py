import sys
import os

# Add current directory to path to allow imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generalization.further_generalization import remove_precon

def run_test(name, ir_code):
    print(f"\n=== Running Test: {name} ===")
    # print("Original IR:")
    # print(ir_code.strip())
    
    try:
        new_ir, orig_ir, count, recession = remove_precon(ir_code)
        
        print(f"Removed Count: {count}")
        if count > 0:
            print("SUCCESS: Preconditions were removed.")
            print("New IR:")
            print(new_ir.strip())
        else:
            print("NO CHANGE: Preconditions were kept.")
    except Exception as e:
        print(f"ERROR: {e}")
    print("=============================")

# Case 1: Pairwise Removal (Irrelevant Precondition)
# Both src and tgt have the same assume, but it's not needed for x+0 -> x
ir_pairwise = """
define i32 @src(i32 %x) {
  %c = icmp ugt i32 %x, 10
  call void @llvm.assume(i1 %c)
  %r = add i32 %x, 0
  ret i32 %r
}
define i32 @tgt(i32 %x) {
  %c = icmp ugt i32 %x, 10
  call void @llvm.assume(i1 %c)
  ret i32 %x
}
declare void @llvm.assume(i1)
"""

# Case 2: One-sided Removal (Irrelevant Precondition in Src, None in Tgt)
# Src has assume, Tgt does not. Optimization x|0 -> x is valid regardless.
ir_onesided = """
define i32 @src(i32 %x) {
  %c = icmp ugt i32 %x, 10
  call void @llvm.assume(i1 %c)
  %r = or i32 %x, 0
  ret i32 %r
}
define i32 @tgt(i32 %x) {
  ret i32 %x
}
declare void @llvm.assume(i1)
"""

# Case 3: Necessary Precondition (Should NOT be removed)
# zext(trunc(x)) -> x requires x < 256.
# Both have assume. Removing them makes it invalid.
ir_necessary = """
define i32 @src(i32 %x) {
  %c = icmp ult i32 %x, 256
  call void @llvm.assume(i1 %c)
  %t = trunc i32 %x to i8
  %z = zext i8 %t to i32
  ret i32 %z
}
define i32 @tgt(i32 %x) {
  %c = icmp ult i32 %x, 256
  call void @llvm.assume(i1 %c)
  ret i32 %x
}
declare void @llvm.assume(i1)
"""

# Case 4: One-sided Necessary (Should NOT be removed)
# Src has assume x < 256. Tgt has none.
# Optimization zext(trunc(x)) -> x.
# If we remove src assume, src becomes "zext(trunc(x))" which is NOT equivalent to tgt "x" for large x.
# So verification should fail and assume should be kept.
ir_onesided_necessary = """
define i32 @src(i32 %x) {
  %c = icmp ult i32 %x, 256
  call void @llvm.assume(i1 %c)
  %t = trunc i32 %x to i8
  %z = zext i8 %t to i32
  ret i32 %z
}
define i32 @tgt(i32 %x) {
  ret i32 %x
}
declare void @llvm.assume(i1)
"""

if __name__ == "__main__":
    run_test("Pairwise Removal (Should Remove)", ir_pairwise)
    run_test("One-sided Removal (Should Remove)", ir_onesided)
    run_test("Necessary Precondition Pairwise (Should Keep)", ir_necessary)
    run_test("Necessary Precondition One-sided (Should Keep)", ir_onesided_necessary)
