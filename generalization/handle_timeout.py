from datetime import datetime

from generalization.utils import extract_alive2_function_bodies, extract_alive2_cte
import re
from verification_types import VerificationResult
from verification import verify_and_profile

INT_LITERAL_PATTERN = re.compile(r'(?<![A-Za-z0-9_%.])-?\d+\b')
# Match integer type tokens only (e.g. i32, i128), not SSA names like %i2.
INT_TYPE_TOKEN_PATTERN = re.compile(r'(?<![A-Za-z0-9_%.@])i(\d+)\b')


def signed_min(bitwidth):
    return -(2 ** (bitwidth - 1))


def signed_max(bitwidth):
    return 2 ** (bitwidth - 1) - 1


def unsigned_max(bitwidth):
    return 2 ** bitwidth - 1


def to_unsigned(constant, bitwidth):
    return constant & unsigned_max(bitwidth)


def to_signed(unsigned_value, bitwidth):
    if bitwidth <= 0:
        return unsigned_value
    sign_bit = 1 << (bitwidth - 1)
    if unsigned_value >= sign_bit:
        return unsigned_value - (1 << bitwidth)
    return unsigned_value


def count_trailing_zeros(value, bitwidth):
    if value == 0:
        return bitwidth
    return (value & -value).bit_length() - 1


def is_low_ones_mask(unsigned_value):
    # Pattern: 0...001...11 (including 0 and all-ones).
    return (unsigned_value & (unsigned_value + 1)) == 0


def get_scaled_extreme_constant(constant, old_bitwidth):
    """
    If constant is an extreme value of old_bitwidth, map it to the
    corresponding extreme value of half bitwidth. Otherwise return None.
    """
    if old_bitwidth <= 1 or old_bitwidth % 2 != 0:
        return None

    new_bitwidth = old_bitwidth // 2
    if constant == signed_min(old_bitwidth):
        return signed_min(new_bitwidth)
    if constant == signed_max(old_bitwidth):
        return signed_max(new_bitwidth)
    if constant == unsigned_max(old_bitwidth):
        return unsigned_max(new_bitwidth)
    return None


def get_scaled_mask_constant(constant, old_bitwidth):
    """
    Scale contiguous edge masks by half bitwidth.
    Supported mask shapes (in old bitwidth):
      - high ones + low zeros:  1...10...0  (e.g. 0xFF000000, 0xFFFF0000)
      - high zeros + low ones:  0...01...1  (e.g. 0x0000FFFF, 0x0FFFFFFF)
    """
    if old_bitwidth <= 1 or old_bitwidth % 2 != 0:
        return None

    new_bitwidth = old_bitwidth // 2
    old_unsigned = to_unsigned(constant, old_bitwidth)

    # Low-ones form: 0...001...11
    if is_low_ones_mask(old_unsigned):
        old_low_ones = old_unsigned.bit_length()  # 0 for zero
        if old_low_ones % 2 == 0:
            new_low_ones = old_low_ones // 2
            new_unsigned = (1 << new_low_ones) - 1 if new_low_ones > 0 else 0
            return to_signed(new_unsigned, new_bitwidth) if constant < 0 else new_unsigned

    # High-ones form: 1...110...00
    low_zeros = count_trailing_zeros(old_unsigned, old_bitwidth)
    high_ones = old_bitwidth - low_zeros
    if old_unsigned != 0 and (old_unsigned >> low_zeros) == ((1 << high_ones) - 1):
        if high_ones % 2 == 0 and low_zeros % 2 == 0:
            new_high_ones = high_ones // 2
            new_low_zeros = low_zeros // 2
            new_unsigned = ((1 << new_high_ones) - 1) << new_low_zeros
            return to_signed(new_unsigned, new_bitwidth) if constant < 0 else new_unsigned

    return None


def get_scaled_extreme_or_mask_constant(constant, old_bitwidth):
    new_const = get_scaled_extreme_constant(constant, old_bitwidth)
    if new_const is not None:
        return new_const
    return get_scaled_mask_constant(constant, old_bitwidth)


def replace_nth_integer_literals(line, replacement_map):
    """
    Replace integer literals by occurrence index.
    replacement_map: {literal_index: new_value}
    """
    if not replacement_map:
        return line, False

    matches = list(INT_LITERAL_PATTERN.finditer(line))
    if not matches:
        return line, False

    line_chars = list(line)
    changed = False
    for idx in sorted(replacement_map.keys(), reverse=True):
        if idx >= len(matches):
            continue
        m = matches[idx]
        new_value = str(replacement_map[idx])
        old_value = line[m.start():m.end()]
        if old_value == new_value:
            continue
        line_chars[m.start():m.end()] = list(new_value)
        changed = True

    return ''.join(line_chars), changed


def shrink_extreme_constants(original_line, scaled_line):
    """
    Keep semantic intent for selected constants when their carrier
    bitwidth is scaled down by half:
      - signed/unsigned extrema
      - contiguous edge masks (high-ones/low-ones)
    """
    changed = False

    # Case 1: typed constants in forms like "i32 -2147483648".
    typed_const_pattern = re.compile(r'\bi(\d+)\s+(-?\d+)\b')
    for m in typed_const_pattern.finditer(original_line):
        old_bw = int(m.group(1))
        old_const = int(m.group(2))
        new_const = get_scaled_extreme_or_mask_constant(old_const, old_bw)
        if new_const is None:
            continue

        new_bw = old_bw // 2
        # Replace one corresponding occurrence after bitwidth shrinking.
        pattern = re.compile(rf'\bi{new_bw}\s+{re.escape(str(old_const))}\b')
        scaled_line, replaced = pattern.subn(f'i{new_bw} {new_const}', scaled_line, count=1)
        if replaced:
            changed = True

    # Case 2: untyped constants tied to the instruction integer bitwidth,
    # e.g. "icmp ne i32 %x, -2147483648".
    line = original_line.strip()
    if not line or any(x in line for x in ['half', 'float', 'double', 'bfloat']):
        return scaled_line, changed

    if '=' in line:
        instruction_part = line.split('=', 1)[1].strip()
        instruction_op = instruction_part.split()[0]
    else:
        instruction_op = "call"

    if instruction_op in ['trunc', 'zext', 'sext', 'select', 'call']:
        return scaled_line, changed

    bitwidths = [int(bw) for bw in INT_TYPE_TOKEN_PATTERN.findall(original_line)]
    if not bitwidths:
        return scaled_line, changed
    old_bw = bitwidths[0]

    if old_bw <= 1 or old_bw % 2 != 0:
        return scaled_line, changed

    original_literals = [int(m.group(0)) for m in INT_LITERAL_PATTERN.finditer(original_line)]
    scaled_matches = list(INT_LITERAL_PATTERN.finditer(scaled_line))
    if not original_literals or len(original_literals) != len(scaled_matches):
        return scaled_line, changed

    replacement_map = {}
    for idx, old_const in enumerate(original_literals):
        new_const = get_scaled_extreme_or_mask_constant(old_const, old_bw)
        if new_const is None:
            continue

        current_const = int(scaled_matches[idx].group(0))
        if current_const == old_const:
            replacement_map[idx] = new_const

    scaled_line, literal_changed = replace_nth_integer_literals(scaled_line, replacement_map)
    return scaled_line, (changed or literal_changed)


def can_fit(constant, bitwidth):
    """check if a constant can fit in the given bitwidth (signed)"""
    if constant < 0:
        if bitwidth <= 0:
            return False
        min_val = -(2 ** (bitwidth - 1))
        max_val = 2 ** (bitwidth - 1) - 1
        return min_val <= constant <= max_val
    else:
        if bitwidth <= 0:
            return False
        min_val = 0
        max_val = unsigned_max(bitwidth)
        return min_val <= constant <= max_val

def validate_line_constants(line):
    """validate if constants in a line of IR code can fit in their corresponding bitwidths"""
    line = line.strip()
    instruction_part = ""
    if not line:
        return True

    if any(x in line for x in ['half', 'float', 'double', 'bfloat']):
        return True

    parts = [part.strip(',') for part in line.split()]
    constants = [int(p) for p in parts if p.lstrip('-').isdigit()]
    if not constants:
        return True

    bitwidths = [int(bw) for bw in INT_TYPE_TOKEN_PATTERN.findall(line)]
    if not bitwidths:
        return True

    if '=' in line:
        instruction_part = line.split('=', 1)[1].strip()
        instruction_op = instruction_part.split()[0]
    else:
        instruction_op = "call"

    if instruction_op in ['trunc', 'zext', 'sext']:
        validation_bitwidth = bitwidths[0]  # source type


    elif instruction_op == 'select':

        instruction_pairs = instruction_part.split(',')
        if len(instruction_pairs) == 3:
            for pair in instruction_pairs[1:]:
                if len(pair.split()) != 2:
                    return False
                pair_1, pair_2 = pair.split()
                bitwidth_number = pair_1[1:]

                if pair_2.lstrip('-').isdigit() and bitwidth_number.isdigit():
                    constant = int(pair_2)
                    if not can_fit(constant, int(bitwidth_number)):
                        return False

        else:
            return False

    elif instruction_op == "call":
        if line.count('(') != 1 or line.count(')') != 1:
            return True
        match = re.search(r'\((.*?)\)', line)

        parameters = match.group(1)
        param_list = [param.strip() for param in parameters.split(',')]
        for pair in param_list:
            if len(pair.split()) != 2:
                return False
            pair_1, pair_2 = pair.split()
            bitwidth_number = pair_1[1:]

            if pair_2.lstrip('-').isdigit() and bitwidth_number.isdigit():
                constant = int(pair_2)
                if not can_fit(constant, int(bitwidth_number)):
                    return False

    else:                                         # ordinary instruction
        validation_bitwidth = bitwidths[0]
        for constant in constants:
            if not can_fit(constant, validation_bitwidth):
                return False

    return True

def validate_bitwidths(ir_code):
    function_body, _ = extract_alive2_function_bodies(ir_code)
    src_function_body = function_body['src']
    tgt_function_body = function_body['tgt']
    for line in src_function_body:
        if not validate_line_constants(line):
            return False

    for line in tgt_function_body:
        if not validate_line_constants(line):
            return False

    return True

def shrink_bitwidths_by_half(ir_code):
    changed = False
    def replace_bitwidth(match):
        nonlocal changed
        bitwidth = int(match.group(1))
        if bitwidth > 1:
            if bitwidth % 2 == 0:
                new_bitwidth = bitwidth // 2
                changed = True
                return f'i{new_bitwidth}'
            else:
                return match.group(0)
        else:
            return match.group(0)

    # scaled_code = INT_TYPE_TOKEN_PATTERN.sub(replace_bitwidth, ir_code)
    lines = ir_code.splitlines()
    new_lines = []
    for line in lines:

        if 'getelementptr' in line:
            m_gep = re.search(r'getelementptr\s+(?:inbounds\s+)?(i\d+|float|double|half)', line)
            if m_gep:
                gep_type_str = m_gep.group(1)

                placeholder = f"__GEP_TYPE_PLACEHOLDER__"
                line_masked = line.replace(gep_type_str, placeholder, 1)

                line_shrunk = INT_TYPE_TOKEN_PATTERN.sub(replace_bitwidth, line_masked)
                line_with_constants, line_constant_changed = shrink_extreme_constants(line, line_shrunk)
                line_final = line_with_constants.replace(placeholder, gep_type_str)
                if line_constant_changed:
                    changed = True
                new_lines.append(line_final)
            else:
                line_shrunk = INT_TYPE_TOKEN_PATTERN.sub(replace_bitwidth, line)
                line_final, line_constant_changed = shrink_extreme_constants(line, line_shrunk)
                if line_constant_changed:
                    changed = True
                new_lines.append(line_final)
        else:
            line_shrunk = INT_TYPE_TOKEN_PATTERN.sub(replace_bitwidth, line)
            line_final, line_constant_changed = shrink_extreme_constants(line, line_shrunk)
            if line_constant_changed:
                changed = True
            new_lines.append(line_final)

    scaled_code = '\n'.join(new_lines)


    bitwidth_def_pattern = re.compile(r'(^\s*%bitwidth[^\s=]*\s*=\s*)add\s+i(\d+)\s+(\d+)\s*,\s*0', re.MULTILINE)
    def replace_bitwidth_def(m):
        nonlocal changed
        prefix = m.group(1)
        bitwidth_val = m.group(2)
        const = int(m.group(3))
        if const > 1 and const % 2 == 0:
            new_const = const // 2
            changed = True
            return f'{prefix}add i{bitwidth_val} {new_const}, 0'
        return m.group(0)

    scaled_code = bitwidth_def_pattern.sub(replace_bitwidth_def, scaled_code)

    def replace_float_type(match):
        nonlocal changed
        ftype = match.group(0)
        if ftype == 'double':
            changed = True
            return 'float'
        elif ftype == 'float':
            changed = True
            return 'half'
        return ftype

    scaled_code = re.sub(r'\b(double|float)\b', replace_float_type, scaled_code)

    return scaled_code, changed


def shrink_and_validate(original_ir_code):

    has_int_to_shrink = False
    for match in INT_TYPE_TOKEN_PATTERN.finditer(original_ir_code):
        bitwidth = int(match.group(1))
        if bitwidth > 1 and bitwidth % 2 == 0:
            has_int_to_shrink = True
            break

    has_float_to_shrink = bool(re.search(r'\b(double|float)\b', original_ir_code))

    if not has_int_to_shrink and not has_float_to_shrink:
        return original_ir_code, False

    ir_code, changed = shrink_bitwidths_by_half(original_ir_code)

    if changed:
        if (validate_bitwidths(ir_code)):
            return ir_code, True
        else:
            return original_ir_code, False
    else:
        return original_ir_code, False

def handle_timeout(pre_processed_response, output_folder, filename, model, attempt, scale_down_attempt, max_attempts=10):
    """
    Handle timeout by scaling down bitwidths and re-verifying recursively.
    Returns:
      (verification_result, final_response, cte, feedback_err)
    where feedback_err is a concise message for LLM error-feedback retries.
    """
    scaled_response, changed = shrink_and_validate(pre_processed_response)

    if not changed:
        # Cannot scale down further (all bitwidths are 1), save as failed
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"{output_folder}/{filename}_{model}_#{attempt}attempt_{timestamp}_#{scale_down_attempt}scaledown_failed.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"Cannot scale down further (all bitwidths are 1). Final response:\n{scaled_response}")
        print(f"Failed: Cannot scale down further, saved to {output_file}")
        feedback_err = (
            "Alive2 timed out, and timeout recovery failed ibecause bitwidth/type scale-down could not proceed further. "
            f"scale_down_attempt={scale_down_attempt}. "
            "Please regenerate with cleaner Alive2-valid syntax and lower verification complexity."
        )
        return VerificationResult.VERIFIED_ERROR, scaled_response, None, feedback_err

    scaled_result, scaled_err, scaled_perf = verify_and_profile(scaled_response)

    if not scaled_err:
        if "Transformation seems to be correct!" in scaled_result:
            # Success after scaling
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"{output_folder}/{filename}_{model}_#{attempt}attempt_{timestamp}_#{scale_down_attempt}scaledown_success.txt"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write("=== SCALED_RESPONSE ===\n")
                f.write(scaled_response)
                f.write("=== STDOUT ===\n")
                f.write(scaled_result)
                f.write("\n=== STDERR ===\n")
                f.write(scaled_err)
            print(f"Success after scaling: Results saved to {output_file}")
            return VerificationResult.VERIFIED_SUCCESS, scaled_response, None, None

        elif "Example" in scaled_result:
            # Counterexample found after scaling
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"{output_folder}/{filename}_{model}_#{attempt}attempt_{timestamp}_#{scale_down_attempt}scaledown_counterexample.txt"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write("=== SCALED_RESPONSE ===\n")
                f.write(scaled_response)
                f.write("=== STDOUT ===\n")
                f.write(scaled_result)
                f.write("\n=== STDERR ===\n")
                f.write(scaled_err)

            cte = extract_alive2_cte(scaled_result)
            return VerificationResult.VERIFIED_WRONG, scaled_response, cte, None

        elif "ERROR: Timeout" in scaled_result:
            # Still timeout after scaling, check if can recurse
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"{output_folder}/{filename}_{model}_#{attempt}attempt_{timestamp}_#{scale_down_attempt}scaledown_timeout.txt"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write("=== SCALED_RESPONSE ===\n")
                f.write(scaled_response)
                f.write("=== STDOUT ===\n")
                f.write(scaled_result)
                f.write("\n=== STDERR ===\n")
                f.write(scaled_err)
            if scale_down_attempt + 1 < max_attempts:
                return handle_timeout(scaled_response, output_folder, filename, model, attempt, scale_down_attempt + 1, max_attempts=10)
            feedback_err = (
                "Alive2 timed out, and timeout recovery reached max scale-down attempts without success. "
                f"max_attempts={max_attempts}, last_scale_down_attempt={scale_down_attempt}. "
                "Please preserve optimization semantics while reducing solver complexity. "
            )
            return VerificationResult.VERIFIED_ERROR, scaled_response, None, feedback_err

        else:
            # Unexpected result after scaling
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"{output_folder}/{filename}_{model}_#{attempt}attempt_{timestamp}_#{scale_down_attempt}scaledown_unexpected.txt"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write("=== SCALED_RESPONSE ===\n")
                f.write(scaled_response)
                f.write("=== STDOUT ===\n")
                f.write(scaled_result)
                f.write("\n=== STDERR ===\n")
                f.write(scaled_err)
            feedback_err = (
                "Alive2 timeout recovery produced an unexpected result after scaling. "
                f"scale_down_attempt={scale_down_attempt}. "
                "Please regenerate a simpler but valid optimization."
            )
            return VerificationResult.VERIFIED_ERROR, scaled_response, None, feedback_err
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"{output_folder}/{filename}_{model}_#{attempt}attempt_{timestamp}_#{scale_down_attempt}scaledown_unexpected.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("=== SCALED_RESPONSE ===\n")
            f.write(scaled_response)
            f.write("=== STDOUT ===\n")
            f.write(scaled_result)
            f.write("\n=== STDERR ===\n")
            f.write(scaled_err)
        feedback_err = (
            "Alive2 timeout recovery failed with stderr after scaling. "
            f"scale_down_attempt={scale_down_attempt}. "
            "Please regenerate with cleaner Alive2-valid syntax and lower verification complexity."
        )
        return VerificationResult.VERIFIED_ERROR, scaled_response, None, feedback_err
