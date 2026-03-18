from handle_timeout import handle_timeout
from datetime import datetime
test = """
define i32 @src(i32 %arg0, i16 %C_cmp, i16 %C_repl_low, i32 %C_repl_high) {
  %Mask = add i32 4294901760, 0
  %trunc = trunc i32 %arg0 to i16
  %cmp = icmp eq i16 %trunc, %C_cmp
  %high_bits = and i32 %arg0, %Mask
  %sel_low = select i1 %cmp, i16 %C_repl_low, i16 %trunc
  %sel_high = select i1 %cmp, i32 %C_repl_high, i32 %high_bits
  %ext_low = zext i16 %sel_low to i32
  %res = or disjoint i32 %sel_high, %ext_low
  ret i32 %res
}

define i32 @tgt(i32 %arg0, i16 %C_cmp, i16 %C_repl_low, i32 %C_repl_high) {
  %trunc = trunc i32 %arg0 to i16
  %cmp = icmp eq i16 %trunc, %C_cmp
  %repl_low_zext = zext i16 %C_repl_low to i32
  %full_repl = or i32 %C_repl_high, %repl_low_zext
  %res = select i1 %cmp, i32 %full_repl, i32 %arg0
  ret i32 %res
}
"""
output_folder = ""
filename = "test_file"
model = "test_model"
attempt = 1
verification_result, updated_last_pre_processed, updated_cte, timeout_feedback_err = handle_timeout(
            test, output_folder, filename, model, attempt, scale_down_attempt=1, max_attempts=10
        )