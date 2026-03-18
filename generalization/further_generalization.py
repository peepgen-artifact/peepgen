from generalization.utils import preprocess_llm_response, extract_alive2_function_bodies
import re
from llm_query import llm_query_for_elimination_with_precon, llm_query_weaken_precondition
from utils import preprocess_llm_response, strip_comment, build_ir, add_arg, extract_operands_and_types, extract_args_from_header, parse_args_list
from verification import verify_and_profile
from verification_analysis import check_verification_success
import json
import os
from compare_precondition import compare_generalization
from generalization_comparison_result import GeneralizationComparisonResult

RE_TYPE = re.compile(r'\b(i\d+|float|double|half|void|ptr|byte|label|metadata|x86_fp80|i\d+\*|[a-zA-Z_][a-zA-Z0-9_<>\.\*\[\]]*)\b')


# to be further tested in ../test_cleanup.py
def cleanup_unused_instructions(ir_code_to_be_cleaned):
    def _collect_used_vars(lines):
        used = set()
        for line in lines:
            for v in re.findall(r'(%[-a-zA-Z$._0-9]+)', line):
                used.add(v)
        return used

    def _format_args(arg_list):
        parts = []
        for name, ty in arg_list:
            if ty:
                parts.append(f"{ty} {name}")
            else:
                parts.append(f"{name}")
        return ', '.join(parts)

    def _prune_header(header, unused_vars):
        prefix, args_str, suffix = extract_args_from_header(header)
        if prefix is None:
            return header, False
        parsed = parse_args_list(args_str or '')
        kept = []
        removed_any = False
        for name, ty in parsed:
            if name.startswith('%') and name in unused_vars:
                removed_any = True
                continue
            kept.append((name, ty))
        new_args = _format_args(kept)
        return f"{prefix}({new_args}){suffix}", removed_any

    def _clean_body_lines(lines):
        safe_opcodes = {
                'add', 'fadd', 'sub', 'fsub', 'mul', 'fmul', 'udiv', 'sdiv', 'fdiv', 'urem', 'srem', 'frem',
                'shl', 'lshr', 'ashr', 'and', 'or', 'xor', 'extractelement', 'insertelement', 'shufflevector',
                'extractvalue', 'insertvalue', 'getelementptr', 'trunc', 'zext', 'sext', 'fptrunc', 'fpext',
                'fptoui', 'fptosi', 'uitofp', 'sitofp', 'ptrtoint', 'inttoptr', 'bitcast', 'addrspacecast',
                'icmp', 'fcmp', 'phi', 'select', 'freeze', 'alloca', 'div'
        }
        # Regex for finding defined variable: %name = ...
        def_pattern = re.compile(r'^\s*(%[-a-zA-Z$._0-9]+)\s*=\s*')

        current_lines = list(lines)

        while True:
            changed = False
            usage_counts = {}
            definitions = {}

            for i, line in enumerate(current_lines):
                m = def_pattern.match(line)
                rhs = line
                if m:
                    defined_var = m.group(1)
                    definitions[defined_var] = i
                    parts = line.split('=', 1)
                    if len(parts) > 1:
                        rhs = parts[1]

                usages = re.findall(r'(%[-a-zA-Z$._0-9]+)', rhs)
                for u in usages:
                    usage_counts[u] = usage_counts.get(u, 0) + 1

            indices_to_remove = []
            for var, line_idx in definitions.items():
                if usage_counts.get(var, 0) == 0:
                    line = current_lines[line_idx]
                    parts = line.split('=', 1)
                    if len(parts) > 1:
                        opcode_part = parts[1].strip()
                        opcode = opcode_part.split()[0] if opcode_part else ""

                        if opcode in safe_opcodes:
                            indices_to_remove.append(line_idx)
                        elif opcode == 'load':
                            # Remove unused non-volatile loads
                            if 'volatile' not in opcode_part:
                                indices_to_remove.append(line_idx)
                        elif opcode == 'call':
                            # Heuristic: remove calls to common pure intrinsics if unused
                            if any(x in opcode_part for x in ['@llvm.ctpop', '@llvm.ctlz', '@llvm.cttz', '@llvm.abs', '@llvm.min', '@llvm.max']):
                                indices_to_remove.append(line_idx)

            if indices_to_remove:
                indices_to_remove.sort(reverse=True)
                for idx in indices_to_remove:
                    del current_lines[idx]
                changed = True

            if not changed:
                break
        return current_lines

    bodies, headers = extract_alive2_function_bodies(ir_code_to_be_cleaned)
    src_header = headers.get('src', '')
    tgt_header = headers.get('tgt', '')
    src_body = bodies.get('src', [])
    tgt_body = bodies.get('tgt', [])

    if not src_header or not tgt_header:
        # Fallback if parsing fails
        return False, ir_code_to_be_cleaned, ir_code_to_be_cleaned, None, None, None

    new_src_body = _clean_body_lines(src_body)
    new_tgt_body = _clean_body_lines(tgt_body)

    cleaned_ir = build_ir(src_header, new_src_body, tgt_header, new_tgt_body)

    # Try pruning unused parameters from both headers (only if unused in both src and tgt bodies)
    src_used = _collect_used_vars(new_src_body)
    tgt_used = _collect_used_vars(new_tgt_body)

    s_prefix, s_args, s_suffix = extract_args_from_header(src_header)
    t_prefix, t_args, t_suffix = extract_args_from_header(tgt_header)
    if s_prefix is not None and t_prefix is not None:
        src_params = {name for name, _ in parse_args_list(s_args or '') if name.startswith('%')}
        tgt_params = {name for name, _ in parse_args_list(t_args or '') if name.startswith('%')}
        unused_src = {p for p in src_params if p not in src_used}
        unused_tgt = {p for p in tgt_params if p not in tgt_used}
        unused_both = unused_src & unused_tgt
    else:
        unused_both = set()

    if unused_both:
        pruned_src_header, _ = _prune_header(src_header, unused_both)
        pruned_tgt_header, _ = _prune_header(tgt_header, unused_both)
        pruned_ir = build_ir(pruned_src_header, new_src_body, pruned_tgt_header, new_tgt_body)
        result, err, perf = verify_and_profile(pruned_ir)
        if check_verification_success(result, err, perf):
            return True, pruned_ir, ir_code_to_be_cleaned, result, err, perf

    # Fallback: return cleaned bodies with original headers
    result, err, perf = verify_and_profile(cleaned_ir)
    if check_verification_success(result, err, perf):
        return True, cleaned_ir, ir_code_to_be_cleaned, result, err, perf
    return False, cleaned_ir, ir_code_to_be_cleaned, result, err, perf


def operator_mutation_shift_mul_div(ir_code):
    """
    Attempts to generalize bitwise operators to arithmetic operators with a new input variable.
    Specifically:
    1. shl %x, C  -> mul %x, %factor
    2. lshr %x, C -> udiv %x, %factor
    3. ashr %x, C -> sdiv %x, %factor

    Where %factor is a NEW input argument added to the function signature.
    This generalizes the operation from "shift by constant" to "multiply/divide by arbitrary value".
    """
    perf_recession_count = 0
    current_ir = ir_code
    mutation_success = False
    # Regex to find shift instructions with constant or variable shift amounts
    shift_pattern = re.compile(r'^\s*(%[-a-zA-Z$._0-9]+)\s*=\s*(shl|lshr|ashr)\s+(i\d+)\s+(%?[-a-zA-Z$._0-9]+)\s*,\s*(%[-a-zA-Z$._0-9]+|\d+)\s*')

    while True:
        bodies, headers = extract_alive2_function_bodies(current_ir)
        src_header = headers.get('src', '')
        tgt_header = headers.get('tgt', '')
        src_body = bodies.get('src', [])
        tgt_body = bodies.get('tgt', [])

        if not src_header or not tgt_header:
            break

        # Collect all shift candidates from both src and tgt in this pass
        candidates = []  # list of dicts: {func, idx, lhs, opcode, ty, op1, shift}
        for func_name, body in (('src', src_body), ('tgt', tgt_body)):
            for idx, line in enumerate(body):
                m = shift_pattern.match(line)
                if not m:
                    continue
                candidates.append({
                    'func': func_name,
                    'idx': idx,
                    'lhs': m.group(1),
                    'opcode': m.group(2),
                    'ty': m.group(3),
                    'op1': m.group(4),
                    'shift': m.group(5),
                })

        if not candidates:
            break
        # Build ordered list of distinct (opcode, shift) pairs (preserve first-seen order)
        # Treat different opcodes separately even if the shift amount is identical.
        seen_keys = []
        seen_set = set()
        for c in candidates:
            key = (c['opcode'], c['shift'])
            if key not in seen_set:
                seen_set.add(key)
                seen_keys.append(key)

        # Process shifts one-by-one: for each distinct shift amount, replace all occurrences
        # with a new argument (or reuse if possible), then verify immediately.
        applied_any = False
        for opcode, shift_amt_str in seen_keys:
            # determine arg name for this opcode+shift pair
            suffix = shift_amt_str.replace('%', '')
            base_name = f"%factor_{opcode}_{suffix}"
            new_arg_name = base_name

            # find a type for this shift (use first candidate with this opcode+shift)
            ty = None
            for c in candidates:
                if c['shift'] == shift_amt_str and c['opcode'] == opcode:
                    ty = c['ty']
                    break
            if not ty:
                continue

            # decide reuse or find unique name
            reuse = False
            type_sig = f"{ty} {new_arg_name}"
            if type_sig in src_header and type_sig in tgt_header:
                reuse = True
            else:
                if (new_arg_name in src_header) or (new_arg_name in tgt_header):
                    counter = 1
                    while True:
                        cand_name = f"{base_name}_new{counter if counter > 1 else ''}"
                        if (cand_name not in src_header) and (cand_name not in tgt_header):
                            new_arg_name = cand_name
                            break
                        if f"{ty} {cand_name}" in src_header and f"{ty} {cand_name}" in tgt_header:
                            new_arg_name = cand_name
                            reuse = True
                            break
                        counter += 1

            # Build candidate bodies by replacing only this shift amount occurrences
            new_src_body = list(src_body)
            new_tgt_body = list(tgt_body)
            for c in candidates:
                if c['shift'] != shift_amt_str or c['opcode'] != opcode:
                    continue
                new_opcode = 'mul' if c['opcode'] == 'shl' else ('udiv' if c['opcode'] == 'lshr' else 'sdiv')
                new_line = f"  {c['lhs']} = {new_opcode} {c['ty']} {c['op1']}, {new_arg_name}"
                if c['func'] == 'src':
                    new_src_body[c['idx']] = new_line
                else:
                    new_tgt_body[c['idx']] = new_line

            # Update headers: add arg if not reused
            new_src_header = src_header
            new_tgt_header = tgt_header
            if not reuse:
                new_src_header = add_arg(new_src_header, ty, new_arg_name)
                new_tgt_header = add_arg(new_tgt_header, ty, new_arg_name)

            # Build candidate IR and verify immediately
            candidate_ir = build_ir(new_src_header, new_src_body, new_tgt_header, new_tgt_body)
            res, err, perf = verify_and_profile(candidate_ir)

            winner = perf.get('winner', 'error')
            if winner != 'tgt':
                perf_recession_count += 1

            if check_verification_success(res, err, perf):

                # accept change and restart outer loop to recompute candidates
                current_ir = candidate_ir
                mutation_success = True
                applied_any = True
                break
            # else: try next distinct shift amount

        if not applied_any:
            # no per-shift replacement succeeded in this pass
            break
        # else restart scanning with updated current_ir

    return current_ir, mutation_success, perf_recession_count



def eliminate_node(ir_code):
    original_ir_code = ir_code
    perf_recession_count = 0

    def make_pattern(var):
        return r'(?<![A-Za-z0-9$_\.\-])' + re.escape(var) + r'(?![A-Za-z0-9$_\.\-])'

    current_ir = ir_code
    eliminate_node_success = False

    while True:
        src_changed = False
        tgt_changed = False

        bodies, headers = extract_alive2_function_bodies(current_ir)
        src_header = headers.get('src', '')
        tgt_header = headers.get('tgt', '')
        src_body = bodies.get('src', [])
        tgt_body = bodies.get('tgt', [])

        if not src_header or not tgt_header:
            break

        # Try synchronized elimination first
        tgt_map = {}
        for idx, line in enumerate(tgt_body):
            key = strip_comment(line)
            if key.startswith('ret') or "=" not in key:
                continue
            tgt_map.setdefault(key, []).append(idx)

        for i in range(len(src_body) - 1, -1, -1):
            line = src_body[i]
            key = strip_comment(line)
            if key.startswith('ret') or "=" not in key:
                continue

            if key in tgt_map.keys():
                operands_and_types_list = extract_operands_and_types(line)
                op_var_lhs = line.split('=')[0].strip()
                operands_and_types_list.append( (op_var_lhs, None) )  # also consider LHS variable

                for op, ty in operands_and_types_list:
                    if not op or not op.startswith('%'):
                        continue
                    # If this operand is already present in either function header, skip it
                    if re.search(make_pattern(op), src_header) and re.search(make_pattern(op), tgt_header):
                        continue

                    new_name = '%newvar_' + op.split('%')[-1]
                    pat = make_pattern(op)

                    new_src_body = []
                    src_replaced = False
                    for s_line in src_body:
                        if s_line.strip().startswith('ret'):
                            new_src_body.append(s_line)
                            continue
                        is_def = False
                        if '=' in s_line:
                            lhs = s_line.split('=')[0].strip()
                            if lhs == op:
                                is_def = True
                        if not is_def:
                            if ty is None:
                                m = re.search(r'([a-zA-Z0-9_<>\.\*\[\]]+)\s+' + re.escape(op), s_line)
                                if m:
                                    ty = m.group(1)

                            new_line = re.sub(pat, new_name, s_line)
                            if new_line != s_line:
                                src_replaced = True
                            new_src_body.append(new_line)
                        else:
                            new_src_body.append(s_line)

                    new_tgt_body = []
                    tgt_replaced = False
                    for t_line in tgt_body:
                        if t_line.strip().startswith('ret'):
                            new_tgt_body.append(t_line)
                            continue
                        is_def = False
                        if '=' in t_line:
                            lhs = t_line.split('=')[0].strip()
                            if lhs == op:
                                is_def = True
                        if not is_def:
                            new_line = re.sub(pat, new_name, t_line)
                            if new_line != t_line:
                                tgt_replaced = True
                            new_tgt_body.append(new_line)
                        else:
                            new_tgt_body.append(t_line)

                    if not (src_replaced or tgt_replaced):
                        continue

                    if ty is None:
                        continue
                    new_src_header = add_arg(src_header, ty, new_name)
                    new_tgt_header = add_arg(tgt_header, ty, new_name)

                    test_ir = build_ir(new_src_header, new_src_body, new_tgt_header, new_tgt_body)
                    res, err, perf = verify_and_profile(test_ir)

                    winner = perf.get('winner', 'error')
                    if winner != 'tgt':
                        perf_recession_count += 1
                        # print("**********performance regression detected**********\n")
                        # print(test_ir)
                    if check_verification_success(res, err, perf):
                        current_ir = test_ir
                        src_changed = True
                        tgt_changed = True
                        eliminate_node_success = True
                        break
            if src_changed:
                break

        if src_changed:
            continue

        for i in range(len(src_body) - 1, -1, -1):
            line = src_body[i]
            if line.strip().startswith('ret') or "=" not in line:
                continue
            operands_and_types_list = extract_operands_and_types(line)
            op_var_lhs = line.split('=')[0].strip()
            operands_and_types_list.append( (op_var_lhs, None) )

            for op, ty in operands_and_types_list:
                if not op or not op.startswith('%'):
                    continue
                # If this operand is already present in either function header, skip it
                if re.search(make_pattern(op), src_header) and re.search(make_pattern(op), tgt_header):
                    continue
                new_name = '%newvar_' + op.split('%')[-1]
                pat = make_pattern(op)

                new_src_body = []
                src_replaced = False
                for s_line in src_body:
                    if s_line.strip().startswith('ret'):
                        new_src_body.append(s_line)
                        continue
                    is_def = False
                    if '=' in s_line:
                        lhs = s_line.split('=')[0].strip()
                        if lhs == op:
                            is_def = True
                    if not is_def:
                        new_line = re.sub(pat, new_name, s_line)
                        if new_line != s_line:
                            src_replaced = True
                        new_src_body.append(new_line)
                    else:
                        new_src_body.append(s_line)

                if not src_replaced:
                    continue

                new_tgt_body = tgt_body
                new_src_header = add_arg(src_header, ty, new_name)
                new_tgt_header = tgt_header

                test_ir = build_ir(new_src_header, new_src_body, new_tgt_header, new_tgt_body)
                res, err, perf = verify_and_profile(test_ir)

                winner = perf.get('winner', 'error')
                if winner != 'tgt':
                    perf_recession_count += 1
                    # print("**********performance regression detected**********\n")
                    # print(test_ir)

                if check_verification_success(res, err, perf):
                    current_ir = test_ir
                    src_changed = True
                    eliminate_node_success = True
                    break
            if src_changed:
                break

        if src_changed:
            continue

        for i in range(len(tgt_body) - 1, -1, -1):
            line = tgt_body[i]
            if line.strip().startswith('ret') or "=" not in line:
                continue
            operands_and_types_list = extract_operands_and_types(line)
            op_var_lhs = line.split('=')[0].strip()
            operands_and_types_list.append( (op_var_lhs, None) )

            for op, ty in operands_and_types_list:
                if not op or not op.startswith('%'):
                    continue
                # If this operand is already present in either function header, skip it
                if re.search(make_pattern(op), src_header) and re.search(make_pattern(op), tgt_header):
                    continue
                new_name = '%newvar_' + op.split('%')[-1]
                pat = make_pattern(op)

                new_tgt_body = []
                tgt_replaced = False
                for t_line in tgt_body:
                    if t_line.strip().startswith('ret'):
                        new_tgt_body.append(t_line)
                        continue
                    is_def = False
                    if '=' in t_line:
                        lhs = t_line.split('=')[0].strip()
                        if lhs == op:
                            is_def = True
                    if not is_def:
                        new_line = re.sub(pat, new_name, t_line)
                        if new_line != t_line:
                            tgt_replaced = True
                        new_tgt_body.append(new_line)
                    else:
                        new_tgt_body.append(t_line)

                if not tgt_replaced:
                    continue

                new_src_body = src_body
                new_tgt_header = add_arg(tgt_header, ty, new_name)
                new_src_header = src_header

                test_ir = build_ir(new_src_header, new_src_body, new_tgt_header, new_tgt_body)
                res, err, perf = verify_and_profile(test_ir)

                winner = perf.get('winner', 'error')
                if winner != 'tgt':
                    perf_recession_count += 1
                    # print("**********performance regression detected**********\n")
                    # print(test_ir)


                if check_verification_success(res, err, perf):
                    current_ir = test_ir
                    tgt_changed = True
                    eliminate_node_success = True
                    break

        if not src_changed and not tgt_changed:
            break

    return current_ir, original_ir_code, eliminate_node_success, perf_recession_count

def eliminate_node_with_precon_llm(ir_code, client, model):
    if not client or not model:
        return ir_code, ir_code, None, False, None, None, None

    prompt, response_text = llm_query_for_elimination_with_precon(client, ir_code, model)

    if "Fail" in response_text:
        return ir_code, ir_code, prompt, False, None, None, None

    processed_code = preprocess_llm_response(response_text)

    if not processed_code:
        return None, ir_code, prompt, False, None, None, None

    res, err, perf = verify_and_profile(processed_code)

    if check_verification_success(res, err, perf):
        if processed_code.strip() == ir_code.strip():
             return processed_code, ir_code, prompt, False, res, err, perf

        return processed_code, ir_code, prompt, True, res, err, perf
    else:
        return processed_code, ir_code, prompt, False, res, err, perf

def remove_precon(ir_code):
    original_ir_code = ir_code
    perf_recession_count = 0
    current_ir = ir_code
    removed_precon_count = 0

    while True:
        original_function, header = extract_alive2_function_bodies(current_ir)

        src_header = header['src']
        tgt_header = header['tgt']
        src_function_body = original_function['src']
        tgt_function_body = original_function['tgt']

        src_assumes = [l for l in src_function_body if "call void @llvm.assume" in l]
        tgt_assumes = [l for l in tgt_function_body if "call void @llvm.assume" in l]

        candidates = []
        for s_line in src_assumes:
            for t_line in tgt_assumes:
                if s_line.strip() == t_line.strip():
                    candidates.append((s_line, t_line))
                    break

        change_made = False
        for src_rem, tgt_rem in candidates:
            new_src_body = src_function_body.copy()
            new_tgt_body = tgt_function_body.copy()

            if src_rem in new_src_body:
                new_src_body.remove(src_rem)
            if tgt_rem in new_tgt_body:
                new_tgt_body.remove(tgt_rem)

            test_ir = build_ir(src_header, new_src_body, tgt_header, new_tgt_body)
            result, err, perf = verify_and_profile(test_ir)

            winner = perf.get('winner', 'error')
            if winner != 'tgt':
                perf_recession_count += 1

            if check_verification_success(result, err, perf):
                current_ir = test_ir
                change_made = True
                removed_precon_count += 1
                break

        if not change_made:
            one_sided_changed = False
            tgt_assumes_stripped = set(t.strip() for t in tgt_assumes)

            # Try removing a single assume from src, ONLY if it's not in tgt
            for s_line in src_assumes:
                if s_line.strip() in tgt_assumes_stripped:
                    continue

                new_src_body = src_function_body.copy()
                if s_line in new_src_body:
                    new_src_body.remove(s_line)
                else:
                    continue

                test_ir = build_ir(src_header, new_src_body, tgt_header, tgt_function_body)
                result, err, perf = verify_and_profile(test_ir)

                winner = perf.get('winner', 'error')
                if winner != 'tgt':
                    perf_recession_count += 1

                if check_verification_success(result, err, perf):
                    current_ir = test_ir
                    one_sided_changed = True
                    removed_precon_count += 1
                    break

            if one_sided_changed:
                continue

            break

    return current_ir, original_ir_code, removed_precon_count, perf_recession_count

def weaken_precon_llm(ir_code, client, model):
    current_ir = ir_code
    ir_code_changed = False

    # placeholders for consistent 6-value return
    weaken_precon_prompt = None
    result = None
    err = None
    perf = None

    if not client or not model:
        return current_ir, weaken_precon_prompt, ir_code_changed, result, err, perf

    original_function, header = extract_alive2_function_bodies(current_ir)
    src_body = original_function.get('src', [])
    tgt_body = original_function.get('tgt', [])

    src_assumes = [l.strip() for l in src_body if "call void @llvm.assume" in l]
    tgt_assumes = [l.strip() for l in tgt_body if "call void @llvm.assume" in l]

    union = []
    seen = set()
    for a in src_assumes + tgt_assumes:
        if a not in seen:
            union.append(a)
            seen.add(a)

    if not union:
        return current_ir, weaken_precon_prompt, ir_code_changed, result, err, perf

    assume_text = "\n".join(union)
    try:
        weaken_precon_prompt, llm_response = llm_query_weaken_precondition(client, current_ir, assume_text, model)
        processed_response = preprocess_llm_response(llm_response)

        result, err, perf = verify_and_profile(processed_response)
        if check_verification_success(result, err, perf):
            if processed_response.strip() != current_ir.strip():
                current_ir = processed_response
                ir_code_changed = True

    except Exception as e:
        print(f"Error during precondition relaxation: {e}")

    return current_ir, weaken_precon_prompt, ir_code_changed, result, err, perf

def remove_flags(ir_code):
    perf_recession_count = 0
    removed_flags_count = 0
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
    ]

    def _remove_flag_from_line(line, flag):
        if flag == 'align':
            # Handle align with argument: ", align N" or " align N"
            # Try removing with preceding comma first
            new_line = re.sub(r",\s*align\s+\d+", '', line)
            if new_line == line:
                new_line = re.sub(r"\s+align\s+\d+", '', line)
            return new_line

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

                    common_keys = [k for k in src_map.keys() if k in tgt_map]
                    for k in common_keys:
                        if re.search(rf"\b{flag}\b", k):
                            matching_keys.append(k)
                    if matching_keys:
                        try_synchronized = True

                if try_synchronized:
                    new_src_body = src_body.copy()
                    new_tgt_body = tgt_body.copy()
                    for key in matching_keys:
                        for j in src_map.get(key, []):
                            new_src_body[j] = _remove_flag_from_line(new_src_body[j], flag)
                        for j in tgt_map.get(key, []):
                            new_tgt_body[j] = _remove_flag_from_line(new_tgt_body[j], flag)

                    if new_src_body != src_body or new_tgt_body != tgt_body:
                        candidate_ir_sync = build_ir(src_header, new_src_body, tgt_header, new_tgt_body)
                        result, err, perf = verify_and_profile(candidate_ir_sync)

                        winner = perf.get('winner', 'error')
                        if winner != 'tgt':
                            perf_recession_count += 1

                        if check_verification_success(result, err, perf):
                            current_ir = candidate_ir_sync
                            bodies, headers = extract_alive2_function_bodies(current_ir)
                            src_header = headers.get('src', '')
                            tgt_header = headers.get('tgt', '')
                            src_body = bodies.get('src', [])
                            tgt_body = bodies.get('tgt', [])
                            rm_flag_changed = True
                            removed_flags_count += 1
                            break

                # Fallback: try removing the flag only on the current line
                new_line = _remove_flag_from_line(line, flag)
                if new_line == line:
                    continue

                new_lines = list(lines)
                new_lines[i] = new_line
                candidate_ir = '\n'.join(new_lines)

                result, err, perf = verify_and_profile(candidate_ir)

                winner = perf.get('winner', 'error')
                if winner != 'tgt':
                    perf_recession_count += 1

                if check_verification_success(result, err, perf):
                    current_ir = candidate_ir
                    bodies, headers = extract_alive2_function_bodies(current_ir)
                    src_header = headers.get('src', '')
                    tgt_header = headers.get('tgt', '')
                    src_body = bodies.get('src', [])
                    tgt_body = bodies.get('tgt', [])
                    rm_flag_changed = True
                    removed_flags_count += 1
                    break

            if rm_flag_changed:
                # restart scanning from the top when a change was applied
                break

    return current_ir, removed_flags_count, perf_recession_count




def remove_const_llm(ir_code, client, model):
    original_ir_code = ir_code

    alive2_verified_success = False
    found_constants = set()

    # Only match lines like: "%bitwidth... = add i32 32, 0"
    # Require the (stripped) line to start with a %bitwidth... name. Use MULTILINE so ^ matches line starts.
    # bitwidth_def_pattern = re.compile(r'^\s*%bitwidth[^\s=]*\s*=\s*add\s+i\d+\s+(\d+)\s*,\s*0', re.MULTILINE)
    for line in ir_code.splitlines():
        line = line.strip()
        if not line:
            continue

        # Try to generalize all constants including those in bitwidth definition lines.

        # match = bitwidth_def_pattern.search(line)
        # if match:
        #     continue

        parts = [part.strip(',') for part in line.split()]
        for p in parts:
            if p.lstrip('-').isdigit():
                val = int(p)
                if val in (0, 1, -1): # Do not generalize these common constants
                    continue
                found_constants.add(p)
                continue

            # Floating point constants (decimal)
            # Matches: 1.23, .23, 1., 1.23e-5, 1e5
            if re.match(r'^-?(?:(?:\d+\.\d*|\.\d+)(?:[eE][-+]?\d+)?|\d+[eE][-+]?\d+)$', p):
                try:
                    val = float(p)
                    if val in (0.0, 1.0, -1.0):
                        continue
                    found_constants.add(p)
                except ValueError:
                    pass
                continue

            # Hex constants (including hex floats like 0x1.2p3 or raw hex 0x1234)
            if re.match(r'^-?0x[0-9a-fA-F]+(?:\.[0-9a-fA-F]*)?(?:[pP][-+]?\d+)?$', p):
                try:
                    val = float.fromhex(p)
                    if val in (0.0, 1.0, -1.0):
                        continue
                    found_constants.add(p)
                except ValueError:
                    pass


    if not found_constants:
        # Ensure a consistent return shape: always return a 6-tuple
        # (output_code, prompt, alive2_verified_success, llm_response, result, err)
        alive2_verified_success = False
        return None, original_ir_code, None, alive2_verified_success, None, None, None, None, found_constants

    print(f"Constants found: {found_constants}, attempting to generalize...")

    constants_str = ", ".join(sorted(list(found_constants)))

    prompt = f"""Generalize the following LLVM IR optimization by replacing concrete constants with symbolic expressions based on bitwidth or other constants.
LLVM IR:
"{ir_code}"

The following concrete constants were found in the code: {constants_str}

If you introduce symbolic constants (C1, C2...), DO NOT just bind them to some specific literal values in the source or target, because symbolic constants must represent a set of number, not just one.
If you must keep numeric literals in `@src` or `@tgt`, prefer to justify them as unavoidable; otherwise prefer symbolic parameters.

Instructions:
1. Analyze if these constants ({constants_str}) can be expressed as a function of the bitwidth (W) or other constants.
   Common patterns:
   - 0, 1
   - C1, C2 (Symbolic Constants)
   - W (Bitwidth)
   - W - 1
   - 2^W - 1 (UMAX, -1)
   - 2^(W-1) - 1 (SMAX)
   - 2^(W-1) (SMIN)
   - Powers of 2 (1 << C)
   - Relations (C2 = C1 + 1)
2. Replace the concrete constants with these symbolic expressions or new symbolic constants (C1, C2, etc.).
3. If you introduce symbolic constants, add necessary preconditions using 'call void @llvm.assume()' in alive2 code, but do NOT use assume to bind a symbolic constant to a specific numeric literal.
5. Output the fully valid Alive2 LLVM IR.
6. Do not try to generalize the bitwidth by using iX/iN/iW in the ir code as it is not acceptable in alive2.
7. Do NOT explain. Output the code directly.
"""

    try:
        resp = client.models.generate_content(
            model=model,
            contents=prompt
        )
        llm_response = resp.text
        processed_response = preprocess_llm_response(llm_response)

        result, err, perf = verify_and_profile(processed_response)
        if check_verification_success(result, err, perf):
            print("Constant generalization successful!")
            alive2_verified_success = True
            output_code = processed_response

        else:
            print("Constant generalization failed verification.")
            alive2_verified_success = False
            output_code = processed_response

        return output_code, original_ir_code, prompt, alive2_verified_success, llm_response, result, err, perf, found_constants

    except Exception as e:
        print(f"Error during constant generalization: {e}")
        alive2_verified_success = False
        safe_llm_response = locals().get('llm_response', None)
        safe_result = locals().get('result', None)
        safe_err = locals().get('err', None)
        safe_perf = locals().get('perf', None)
        output_code = None
        return output_code, original_ir_code, prompt, alive2_verified_success, safe_llm_response, safe_result, safe_err, safe_perf, found_constants

def verify_weaken_precon(original_ir, generalized_ir):
    original_bodies, original_headers = extract_alive2_function_bodies(original_ir)
    original_src_header = original_headers.get('src', '')
    original_tgt_header = original_headers.get('tgt', '')
    original_src_body = original_bodies.get('src', [])
    original_tgt_body = original_bodies.get('tgt', [])

    generalized_bodies, generalized_headers = extract_alive2_function_bodies(generalized_ir)
    generalized_src_header = generalized_headers.get('src', '')
    generalized_tgt_header = generalized_headers.get('tgt', '')
    generalized_src_body = generalized_bodies.get('src', [])
    generalized_tgt_body = generalized_bodies.get('tgt', [])

    original_src_ir, generalized_src_ir = build_ir(original_src_header, original_src_body, generalized_src_header.replace("@src", "@tgt"), generalized_src_body, build_split_ir=True)
    original_tgt_ir, generalized_tgt_ir = build_ir(original_tgt_header.replace("@tgt", "@src"), original_tgt_body, generalized_tgt_header, generalized_tgt_body, build_split_ir=True)

    src_generalization_status = compare_generalization(original_src_ir, generalized_src_ir)
    tgt_generalization_status = compare_generalization(original_tgt_ir, generalized_tgt_ir)

    return src_generalization_status, tgt_generalization_status


def further_generalization(ir_code_original, client, model, json_output_file=None, txt_output_file=None):

    results = {}

    def log_stage(stage_name, stage_data):
        results[stage_name] = stage_data

        if json_output_file:
            try:
                if os.path.exists(json_output_file):
                    with open(json_output_file, "r", encoding="utf-8") as f:
                        try:
                            current_data = json.load(f)
                        except json.JSONDecodeError:
                            current_data = {}
                else:
                    current_data = {}

                current_data[stage_name] = stage_data

                with open(json_output_file, "w", encoding="utf-8") as f:
                    json.dump(current_data, f, indent=2, default=str)
            except Exception as e:
                print(f"Error writing JSON for stage {stage_name}: {e}")

        if txt_output_file:
            try:
                with open(txt_output_file, "a", encoding="utf-8") as f:
                    f.write(f"********************************** Furgen Stage: {stage_name} **********************************\n\n")
                    if isinstance(stage_data, dict):
                        for key, value in stage_data.items():
                            f.write(f"\n=== {key} ===\n")
                            f.write(str(value) if value is not None else "None")
                    else:
                        f.write(str(stage_data))
                    f.write("\n\n")
            except Exception as e:
                print(f"Error writing TXT for stage {stage_name}: {e}")

    ir_code_eliminate_node_with_precon, orig_ir_code, eliminate_node_with_precon_prompt, eliminate_node_with_precon_llm_succ, eliminate_node_with_precon_verification_result, eliminate_node_with_precon_verification_err, eliminate_node_with_precon_perf = eliminate_node_with_precon_llm(ir_code_original, client, model)

    log_stage("eliminate_node_with_precon_llm", {
        "output_code": ir_code_eliminate_node_with_precon,
        "original_code": orig_ir_code,
        # "prompt": eliminate_node_with_precon_prompt,
        "success": eliminate_node_with_precon_llm_succ,
        "verification_result": eliminate_node_with_precon_verification_result,
        "verification_err": eliminate_node_with_precon_verification_err,
        "performance": eliminate_node_with_precon_perf
    })

    if eliminate_node_with_precon_llm_succ:

        cleanup_after_eliminating_precon_succ, ir_code_eliminated_precon_cleaned, ir_code_eliminated_precon_original, eliminate_with_precon_alive2_result, eliminate_with_precon_alive2_err, eliminate_with_precon_alive2_perf = cleanup_unused_instructions(ir_code_eliminate_node_with_precon)

        log_stage("cleanup_after_eliminating_with_precon", {
            "success": cleanup_after_eliminating_precon_succ,
            "cleaned_code": ir_code_eliminated_precon_cleaned,
            "original_code": ir_code_eliminated_precon_original,
            "verification_result": eliminate_with_precon_alive2_result,
            "verification_err": eliminate_with_precon_alive2_err,
            "performance": eliminate_with_precon_alive2_perf
        })
        ir_code_eliminated = ir_code_eliminated_precon_cleaned
    else:
        ir_code_eliminated = ir_code_original


    # output_code_rm_const_llm, input_code_rm_const_llm, rm_const_prompt, llm_furgen_rm_const_success, llm_response, rm_const_alive2_result, rm_const_alive2_err, rm_const_alive2_perf, found_constants = remove_const_llm(ir_code_eliminated, client, model)

    # log_stage("rm_const_llm", {
    #     "input_code": input_code_rm_const_llm,
    #     "output_code": output_code_rm_const_llm,
    #     # "prompt": rm_const_prompt,
    #     "success": llm_furgen_rm_const_success,
    #     "llm_response": llm_response,
    #     "verification_result": rm_const_alive2_result,
    #     "verification_err": rm_const_alive2_err,
    #     "performance": rm_const_alive2_perf,
    #     "found_constants": list(found_constants)
    # })

    # if llm_furgen_rm_const_success:
    #     ir_code_rm_precon, ir_code_rm_precon_original, removed_precon_count, remove_precon_perf_recession_count = remove_precon(output_code_rm_const_llm)
    # else:
    ir_code_rm_precon, ir_code_rm_precon_original, removed_precon_count, remove_precon_perf_recession_count = remove_precon(ir_code_eliminated)

    log_stage("remove_precon", {
        "input_code": ir_code_rm_precon_original,
        "output_code": ir_code_rm_precon,
        "removed_count": removed_precon_count,
        "performance_recession_count": remove_precon_perf_recession_count
    })

    cleanup_after_rm_precon_succ, ir_code_rm_precon_cleaned, ir_code_rm_precon_cleaned_original, rm_precon_cleaned_alive2_result, rm_precon_cleaned_alive2_err, rm_precon_cleaned_alive2_perf = cleanup_unused_instructions(ir_code_rm_precon)

    log_stage("cleanup_after_rm_precon", {
        "success": cleanup_after_rm_precon_succ,
        "cleaned_code": ir_code_rm_precon_cleaned,
        "original_code": ir_code_rm_precon_original,
        "verification_result": rm_precon_cleaned_alive2_result,
        "verification_err": rm_precon_cleaned_alive2_err,
        "performance": rm_precon_cleaned_alive2_perf
    })

    if cleanup_after_rm_precon_succ:
        ir_code_weakened_precon, weaken_precon_prompt, ir_code_changed, weaken_precon_result, weaken_precon_err, weaken_precon_perf = weaken_precon_llm(ir_code_rm_precon_cleaned, client, model)
        log_stage("weaken_precon_llm", {
            "input_code": ir_code_rm_precon_cleaned,
            "output_code": ir_code_weakened_precon,
            # "prompt": weaken_precon_prompt,
            "changed": ir_code_changed,
            "verification_result": weaken_precon_result,
            "verification_err": weaken_precon_err,
            "performance": weaken_precon_perf
        })
        src_generalization_status, tgt_generalization_status = verify_weaken_precon(ir_code_rm_precon_cleaned, ir_code_weakened_precon)
        log_stage("weaken_verified", {
            "input_code": ir_code_rm_precon_cleaned,
            "output_code": ir_code_weakened_precon,
            "src_generalization_status": src_generalization_status,
            "tgt_generalization_status": tgt_generalization_status
        })

        if (src_generalization_status == GeneralizationComparisonResult.GenSucc and tgt_generalization_status == GeneralizationComparisonResult.GenSucc) or  \
              (src_generalization_status == GeneralizationComparisonResult.GenSucc and tgt_generalization_status == GeneralizationComparisonResult.GenEqual) or \
                (src_generalization_status == GeneralizationComparisonResult.GenEqual and tgt_generalization_status == GeneralizationComparisonResult.GenSucc):
            ir_code_weakened_precon = ir_code_weakened_precon
        else:
            ir_code_weakened_precon = ir_code_rm_precon_cleaned


    else:
        ir_code_weakened_precon, weaken_precon_prompt, ir_code_changed, weaken_precon_result, weaken_precon_err, weaken_precon_perf = weaken_precon_llm(ir_code_rm_precon_cleaned_original, client, model)
        log_stage("weaken_precon_llm", {
            "input_code": ir_code_rm_precon_cleaned_original,
            "output_code": ir_code_weakened_precon,
            # "prompt": weaken_precon_prompt,
            "changed": ir_code_changed,
            "verification_result": weaken_precon_result,
            "verification_err": weaken_precon_err,
            "performance": weaken_precon_perf
        })
        src_generalization_status, tgt_generalization_status = verify_weaken_precon(ir_code_rm_precon_cleaned_original, ir_code_weakened_precon)
        log_stage("weaken_verified", {
            "input_code": ir_code_rm_precon_cleaned_original,
            "output_code": ir_code_weakened_precon,
            "src_generalization_status": src_generalization_status,
            "tgt_generalization_status": tgt_generalization_status
        })

        if (src_generalization_status == GeneralizationComparisonResult.GenSucc and tgt_generalization_status == GeneralizationComparisonResult.GenSucc) or  \
              (src_generalization_status == GeneralizationComparisonResult.GenSucc and tgt_generalization_status == GeneralizationComparisonResult.GenEqual) or \
                (src_generalization_status == GeneralizationComparisonResult.GenEqual and tgt_generalization_status == GeneralizationComparisonResult.GenSucc):
            ir_code_weakened_precon = ir_code_rm_precon_cleaned
        else:
            ir_code_weakened_precon = ir_code_rm_precon_cleaned_original


    cleanup_after_weaken_precon_succ, ir_code_weaken_precon_cleaned, ir_code_weaken_precon_original, weaken_precon_cleaned_alive2_result, weaken_precon_cleaned_alive2_err, weaken_precon_cleaned_alive2_perf = cleanup_unused_instructions(ir_code_weakened_precon)

    log_stage("cleanup_after_weaken_precon", {
        "success": cleanup_after_weaken_precon_succ,
        "cleaned_code": ir_code_weaken_precon_cleaned,
        "original_code": ir_code_weaken_precon_original,
        "verification_result": weaken_precon_cleaned_alive2_result,
        "verification_err": weaken_precon_cleaned_alive2_err,
        "performance": weaken_precon_cleaned_alive2_perf
    })

    if cleanup_after_weaken_precon_succ:
        ir_code_rm_flags, removed_flags_count, remove_flags_perf_recession_count = remove_flags(ir_code_weaken_precon_cleaned)
    else:
        ir_code_rm_flags, removed_flags_count, remove_flags_perf_recession_count = remove_flags(ir_code_weaken_precon_original)

    log_stage("remove_flags", {
        "output_code": ir_code_rm_flags,
        "removed_count": removed_flags_count,
        "performance_recession_count": remove_flags_perf_recession_count
    })

    # ir_code_mutated, mutation_success, mutation_perf_recession_count = operator_mutation_shift_mul_div(ir_code_rm_flags)

    # log_stage("operator_mutation", {
    #     "output_code": ir_code_mutated,
    #     "operator_mutation_success": mutation_success,
    #     "performance_recession_count": mutation_perf_recession_count
    # })

    # results["final_output_code"] = ir_code_mutated
    results["final_output_code"] = ir_code_rm_flags
    return results

