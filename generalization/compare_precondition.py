import re
from generalization.utils import build_arg_list, extract_alive2_function_bodies, build_ir, analyze_constant_generalization,extract_args_from_header, parse_args_list
from generalization.verification import verify_and_profile
from generalization_comparison_result import GeneralizationComparisonResult

def compare_generalization(original_ir, new_ir):
    success1 = None
    success2 = None
    bodies_old, headers_old = extract_alive2_function_bodies(original_ir)
    bodies_new, headers_new = extract_alive2_function_bodies(new_ir)

    src_header_old = headers_old.get('src', '')
    src_body_old = bodies_old.get('src', [])

    src_header_new = headers_new.get('tgt', '')
    src_body_new = bodies_new.get('tgt', [])

    if not src_header_old or not src_header_new or not src_body_old or not src_body_new:
        return False

    ir_narrow_to_wide = original_ir + new_ir
    res1, err1, _ = verify_and_profile(ir_narrow_to_wide)
    if err1:
        return GeneralizationComparisonResult.GenError

    if not err1 and "Transformation seems to be correct!" in res1 and "WARNING: Source function is always UB." not in res1:
        success1 = True
    else:
        success1 = False

    if not success1:
        return GeneralizationComparisonResult.GenFail

    ir_wide_to_narrow = new_ir.replace("@tgt", "@src") + original_ir.replace("@src", "@tgt")
    res2, err2, _ = verify_and_profile(ir_wide_to_narrow)

    if err2:
        return GeneralizationComparisonResult.GenError

    if "Transformation seems to be correct!" not in res2:
        return GeneralizationComparisonResult.GenSucc
    else:
        return GeneralizationComparisonResult.GenEqual


def compare_initial_generalization(opt_A_ir, opt_B_ir):
    """
    Compares two optimizations A and B, where B is a generalization of A.
    Checks if B correctly generalizes A by constraining B's generalized variables
    to match A's constants and verifying equivalence.
    """

    # 1. Extract functions
    bodies_A, headers_A = extract_alive2_function_bodies(opt_A_ir)
    bodies_B, headers_B = extract_alive2_function_bodies(opt_B_ir)

    srcA_body = bodies_A.get('src', [])
    srcB_body = bodies_B.get('src', [])
    tgtA_body = bodies_A.get('tgt', [])
    tgtB_body = bodies_B.get('tgt', [])

    srcA_header = headers_A.get('src', '')
    srcB_header = headers_B.get('src', '')
    tgtA_header = headers_A.get('tgt', '')
    tgtB_header = headers_B.get('tgt', '')

    if not (srcA_body and srcB_body and tgtA_body and tgtB_body):
        return False, False

    def process_pair(funcA_body, funcB_body, funcA_header, funcB_header):
        # Analyze generalization
        mappings, arg_map = analyze_constant_generalization(funcA_body, funcB_body)
        print(mappings)
        print("----")

        mappings, arg_map = analyze_constant_generalization(funcA_body, funcB_body)
        print(mappings)

        # Helper to extract arg types dictionary from header
        def get_header_arg_types(header):
            prefix, args_str, suffix = extract_args_from_header(header)
            parsed = parse_args_list(args_str or '')
            return {name: ty for name, ty in parsed}

        types_A = get_header_arg_types(funcA_header)
        types_B = get_header_arg_types(funcB_header)

        type_replacements = {}
        if arg_map:
            for old_arg, new_arg in arg_map.items():
                tA = types_A.get(old_arg)
                tB = types_B.get(new_arg)
                # print(f"Mapping {old_arg}({tA}) -> {new_arg}({tB})")
                if tA and tB and tA != tB:
                    type_replacements[tA] = tB

        # Rename arguments in funcA_body to match funcB_header (generalized args)
        if arg_map:
             new_funcA_body = []
             for line in funcA_body:
                 new_line = line
                 for old_arg, new_arg in arg_map.items():
                     if old_arg == new_arg: continue
                     if not old_arg.startswith('%'):
                         continue

                     esc_old = re.escape(old_arg)
                     pattern = r'(?<![-a-zA-Z$._0-9])' + esc_old + r'(?![-a-zA-Z$._0-9])'
                     new_line = re.sub(pattern, new_arg, new_line)

                 # Apply type replacements on the line
                 for old_ty, new_ty in type_replacements.items():
                     pattern_ty = r'\b' + re.escape(old_ty) + r'\b'
                     if not old_ty[-1].isalnum():
                         pattern_ty = re.escape(old_ty)
                     new_line = re.sub(pattern_ty, new_ty, new_line)

                 new_funcA_body.append(new_line)
             funcA_body = new_funcA_body

        # Helper to find type of a variable in header
        def find_arg_type(header, var_name):
            escaped_var = re.escape(var_name)
            m = re.search(r'([a-zA-Z0-9_*]+)\s+' + escaped_var + r'\b', header)
            if m:
                return m.group(1)
            return None

        # Insert generalized lines and assumptions at the beginning
        insertions = []
        inserted_vars = set()

        for i, m in enumerate(mappings):
            generalized_lines = m.get('generalized_lines', [])
            const_val = m['original']

            if not generalized_lines:
                # Direct argument mapping: 1 -> %C
                gen_var = m['generalized']

                if gen_var in inserted_vars:
                    continue
                inserted_vars.add(gen_var)

                # Find type of gen_var in B's header
                ty = find_arg_type(funcB_header, gen_var)
                if not ty:
                    ty = 'i32'
                cond_var = f"%cond_assume_{i}"


                if ty in ['float', 'double', 'half']:
                    insertions.append(f"{cond_var} = fcmp oeq {ty} {gen_var}, {const_val}")
                    insertions.append(f"call void @llvm.assume(i1 {cond_var})")
                elif ty == 'ptr':
                    insertions.append(f"{cond_var} = icmp eq {ty} {gen_var}, {const_val}")
                    insertions.append(f"call void @llvm.assume(i1 {cond_var})")
                else :
                    insertions.append(f"{cond_var} = icmp eq {ty} {gen_var}, {const_val}")
                    insertions.append(f"call void @llvm.assume(i1 {cond_var})")

            else:
                # Expression mapping: 1 -> (%w + 1)
                # Add all lines
                for l in generalized_lines:
                    if l not in insertions:
                        insertions.append(l)

                last_line = generalized_lines[-1]
                lhs_match = re.search(r'(%[-a-zA-Z$._0-9]+)\s*=', last_line)
                if lhs_match:
                    lhs_var = lhs_match.group(1)

                    # Try to extract type from the line
                    parts = last_line.split('=')[1].strip().split()
                    ty = 'i32' # Default
                    if len(parts) > 1:
                        candidate = parts[1]
                        if candidate.startswith('i') or candidate in ['float', 'double', 'half', 'ptr']:
                            ty = candidate
                            if ty.endswith(','):
                                ty = ty[:-1]

                    cond_var = f"%cond_assume_{i}"
                    insertions.append(f"{cond_var} = icmp eq {ty} {lhs_var}, {const_val}")
                    insertions.append(f"call void @llvm.assume(i1 {cond_var})")

        # Construct new body for A
        # We use B's header for A because A needs to accept the generalized arguments
        final_header_A = funcB_header

        final_body_A = insertions + funcA_body

        def indent(lines):
            return ["  " + l for l in lines]

        # ir_A = f"{final_header_A}\n" + "\n".join(indent(final_body_A)) + "\n}\n"
        # ir_B = f"{funcB_header}\n" + "\n".join(indent(funcB_body)) + "\n}\n"
        raw_ir_A = f"{final_header_A}\n" + "\n".join(indent(final_body_A)) + "\n}\n"
        raw_ir_B = f"{funcB_header}\n" + "\n".join(indent(funcB_body)) + "\n}\n"

        ir_A = re.sub(r'@[^(]+', '@src', raw_ir_A, count=1)
        ir_B = re.sub(r'@[^(]+', '@tgt', raw_ir_B, count=1)

        full_ir_A = ir_A + "\n"
        full_ir_B = ir_B + "\n"
        # print(full_ir_A)
        # print(full_ir_B)
        # print("----")
        return compare_generalization(full_ir_A, full_ir_B)

    # Compare src
    src_valid = process_pair(srcA_body, srcB_body, srcA_header, srcB_header)

    # Compare tgt
    tgt_valid = process_pair(tgtA_body, tgtB_body, tgtA_header, tgtB_header)

    return src_valid, tgt_valid
