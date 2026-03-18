import sys
import os

# Add the current directory to sys.path to ensure imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from further_generalization import generalize_bitwidth_variable
from alive2 import alive2_verify

def test_generalize_bitwidth():
    # Example IR with a bitwidth variable
    # This IR represents a simple identity or optimization where bitwidth is defined
    # We want to see if it gets replaced by %BitWidth argument
    
    # Note: For Alive2 to verify, the IR must be valid.
    # Let's construct a case where we have a bitwidth definition.
    # Usually %bitwidth = add i32 32, 0
    
    ir_code = """
define i32 @src(i32 %x) {
  %bitwidth_val = add i32 32, 0
  %bitwidth_val1 = add i32 32, 0
  %y = add i32 %bitwidth_val, %bitwidth_val1
  %res = add i32 %y, 0
  ret i32 %res 
}

define i32 @tgt(i32 %x) {
  %bitwidth_val = add i32 32, 0
  %bitwidth_val1 = add i32 32, 0
  %y = add i32 %bitwidth_val, %bitwidth_val1
  %res = add i32 %y, 0
  ret i32 %res 
}
"""
    print("Original IR:")
    print(ir_code)

    new_ir, success = generalize_bitwidth_variable(ir_code)

    # print("\nGeneralization Success:", success)
    # print("\nNew IR:")
    # print(new_ir)

    # if success:
    #     print("\nVerifying New IR with Alive2...")
    #     result, err = alive2_verify(new_ir)
    #     print("Alive2 Result:", result)
    #     if err:
    #         print("Alive2 Error:", err)
    # else:
    #     print("Generalization failed or verification failed during generalization.")

if __name__ == "__main__":
    test_generalize_bitwidth()


