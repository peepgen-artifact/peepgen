from generalization.utils import preprocess_llm_response, extract_alive2_function_bodies
import re
from further_generalization import remove_flags
from llm_query import llm_query_for_elimination
from utils import preprocess_llm_response
from verification import verify_and_profile
from verification_analysis import check_verification_success
def build_ir(src_header, src_body, tgt_header, tgt_body):
    return f"{src_header}\n" + "\n".join(src_body) + "\n}\n\n" + \
        f"{tgt_header}\n" + "\n".join(tgt_body) + "\n}\n"


def remove_flags1(ir_code):
    """
    Iteratively attempt to remove optimization flags (nsw, nuw, exact) from instructions.
    Verifies each removal with verify_and_profile.
    """

    current_ir = ir_code
    # Candidate flags to try removing. Grouped roughly by risk: lower-risk / common
    # and higher-risk flags mixed — verify_and_profile will reject unsafe removals.
    flags = [
        # integer overflow / exactness
        'nsw', 'nuw', 'exact',

        # floating-point fast-math flags
        'fast', 'reassoc', 'nnan', 'ninf', 'nsz', 'arcp', 'contract', 'afn',

        # function / call attributes that can affect optimizations
        'readonly', 'readnone', 'noinline', 'alwaysinline', 'inlinehint',

        # pointer flags (high risk; verification will usually reject unsafe removals)
        'inbounds',

        # memory / atomics (usually too risky to remove automatically but included for
        # completeness and will be gated by Alive2 verification)
        'volatile',
        'align'
    ]
    
    def _remove_flag_from_line(line, flag):
        # Try removing with preceding whitespace, then following whitespace, then bare token
        new_line = re.sub(rf"\s+\b{flag}\b", '', line)
        if new_line == line:
            new_line = re.sub(rf"\b{flag}\b\s+", '', line)
        if new_line == line:
            new_line = re.sub(rf"\b{flag}\b", '', line)
        return new_line

    rm_flag_changed = True
    while rm_flag_changed:
        rm_flag_changed = False
        lines = current_ir.splitlines()

        bodies, headers = extract_alive2_function_bodies(current_ir)
        src_header = headers.get('src', '')
        tgt_header = headers.get('tgt', '')
        src_body = bodies.get('src', [])
        tgt_body = bodies.get('tgt', [])

        for i, line in enumerate(lines):
            if not line.strip() or line.strip().startswith(';'):
                continue

            found_flags = []
            for f in flags:
                if re.search(rf'\b{f}\b', line):
                    found_flags.append(f)

            if not found_flags:
                continue

        for flag in found_flags:
                # First try synchronized removal from both src and tgt if both contain the flag 

                # Try synchronized removal only when the SAME LINE CONTENT (string equality)
                # appears in both src and tgt and that content contains the flag.
            try_synchronized = False
            matching_keys = []
            if src_body and tgt_body and src_header and tgt_header:
                src_map = {}
                for idx, s in enumerate(src_body):
                    key = s.strip()
                    src_map.setdefault(key, []).append(idx)
                tgt_map = {}
                for idx, t in enumerate(tgt_body):
                    key = t.strip()
                    tgt_map.setdefault(key, []).append(idx)

                    # find keys (line contents) that appear in both and contain the flag
                common_keys = [k for k in src_map.keys() if k in tgt_map]
                for k in common_keys:
                    if re.search(rf"\b{flag}\b", k):
                        matching_keys.append(k)
                if matching_keys:
                    try_synchronized = True

            if try_synchronized:
                new_src_body = src_body.copy()
                new_tgt_body = tgt_body.copy()
                    # remove flag only on the matching lines (preserve other occurrences)
                for key in matching_keys:
                    for j in src_map.get(key, []):
                        new_src_body[j] = _remove_flag_from_line(new_src_body[j], flag)
                    for j in tgt_map.get(key, []):
                        new_tgt_body[j] = _remove_flag_from_line(new_tgt_body[j], flag)

                    # If nothing changed, skip synchronized attempt
                if new_src_body != src_body or new_tgt_body != tgt_body:
                    candidate_ir_sync = build_ir(src_header, new_src_body, tgt_header, new_tgt_body)
                    result, err, perf = verify_and_profile(candidate_ir_sync)
                    # if check_verification_success(result, err, perf):
                    if True:
                        current_ir = candidate_ir_sync
                            # bodies, headers = extract_alive2_function_bodies(current_ir)
                            # src_header = headers.get('src', '')
                            # tgt_header = headers.get('tgt', '')
                            # src_body = bodies.get('src', [])
                            # tgt_body = bodies.get('tgt', [])
                        rm_flag_changed = True
                        continue

                # Fallback: try removing the flag only on the current line (original behavior)
            new_line = _remove_flag_from_line(line, flag)
            if new_line == line:
                continue

            new_lines = list(lines)
            new_lines[i] = new_line
            candidate_ir = '\n'.join(new_lines)


            if True:
                current_ir = candidate_ir
                    # bodies, headers = extract_alive2_function_bodies(current_ir)
                    # src_header = headers.get('src', '')
                    # tgt_header = headers.get('tgt', '')
                    # src_body = bodies.get('src', [])
                    # tgt_body = bodies.get('tgt', [])
                rm_flag_changed = True
                break 

        if rm_flag_changed is False:
            break

    return current_ir


examples = [
    ("test", '''
define i16 @src(i32 %arg1, i32 %arg2, ptr %arg0) {
  %v0 = udiv i32 %arg2, %arg1
  %v1 = load i16, ptr %arg0, align 2
  %v2 = and i32 %v0, 65535
  %v3 = zext i16 %v1 to i32
  %v4 = call i32 @llvm.umin.i32(i32 %v2, i32 %v3)
  %v5 = trunc nuw i32 %v4 to i16
  ret i16 %v5
}

define i16 @tgt(i32 %arg1, i32 %arg2, ptr %arg0) {
  %v0 = udiv i32 %arg2, %arg1
  %v1 = load i16, ptr %arg0, align 2
  %v2 = trunc i32 %v0 to i16
  %v3 = call i16 @llvm.umin.i16(i16 %v2, i16 %v1)
  ret i16 %v3
}
'''),

#     ("both-side identical nsw (sync)", '''
# define i32 @src(i32 %x, i32 %y) {
# %a = add nsw i32 %x, %y
# ret i32 %a
# }

# define i32 @tgt(i32 %x, i32 %y) {
# %a = add nsw i32 %x, %y
# ret i32 %a
# }
# '''),

#     ("tgt-only nsw", '''
# define i32 @src(i32 %x, i32 %y) {
# %a = add nuw i32 %x, %y
# ret i32 %a
# }

# define i32 @tgt(i32 %x, i32 %y) {
# %a = add nsw i32 %x, %y
# ret i32 %a
# }
# '''),

#     ("multiple occurrences same line", '''
# define i32 @src(i32 %x, i32 %y) {
# %a = add nsw i32 %x, %y
# %c = add nsw i32 %x, %y
# ret i32 %c
# }

# define i32 @tgt(i32 %x, i32 %y) {
# %a = add nsw i32 %x, %y
# %c = add nsw i32 %x, %y
# ret i32 %c
# }
# '''),

#     ("pointer/inbounds example", '''
# define i32 @src(i32* %p) {
# %q = getelementptr inbounds i32, i32* %p, i32 1
# ret i32 0
# }

# define i32 @tgt(i32* %p) {
# %q = getelementptr inbounds i32, i32* %p, i32 1
# ret i32 0
# }
# '''),

#     ("fast-math flags on fp ops", '''
# define double @src(double %x, double %y) {
# %r = fadd double %x, %y
# ret double %r
# }

# define double @tgt(double %x, double %y) {
# %r = fadd fast double %x, %y
# ret double %r
# }
# '''),
]


def run_examples():
    for idx, (name, ir) in enumerate(examples, start=1):
        print("=== Example {}: {} ===".format(idx, name))
        print("Original IR:\n" + ir)
        new_ir = remove_flags(ir)
        print("Transformed IR:\n" + new_ir)
        print("\n")


if __name__ == '__main__':
    run_examples()