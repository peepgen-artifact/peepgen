import re

RE_VAR = re.compile(r'(%[-a-zA-Z$._0-9]+)')
BINARY_OPS = {
    'add', 'sub', 'mul', 'udiv', 'sdiv', 'urem', 'srem',
    'and', 'or', 'xor', 'shl', 'lshr', 'ashr',
    'fadd', 'fsub', 'fmul', 'fdiv'
}

def indent(lines):
    return ["  " + line.strip() for line in lines]

def add_arg(header, arg_type, arg_name):
    if ')' not in header:
        return header
    idx = header.rfind(')')
    prefix = header[:idx]
    suffix = header[idx:]
    if prefix.strip().endswith('('):
        return f"{prefix}{arg_type} {arg_name}{suffix}"
    else:
        return f"{prefix}, {arg_type} {arg_name}{suffix}"

def strip_comment(line):
    # remove trailing comments starting with ';'
    return line.split(';', 1)[0].strip()

def remove_comments(text):
    lines = text.splitlines()
    cleaned_lines = [strip_comment(line) for line in lines]
    # remove empty lines after stripping comments/whitespace
    non_empty = [ln for ln in cleaned_lines if ln]
    return '\n'.join(non_empty)

def extract_alive2_cte(err):
    """
    Extract counterexample from Alive2 error output.
    """
    lines = err.strip().split('\n')
    in_example = False
    example_lines = []
    for line in lines:
        if line.startswith('Transformation doesn\'t verify!'):
            in_example = True
        if in_example:
            example_lines.append(line)
    return '\n'.join(example_lines)

def extract_alive2_function_bodies(ir_code):
    body = {'src': [], 'tgt': []}
    header = {'src': "", 'tgt': ""}
    current_func = None


    for line in ir_code.split('\n'):
        line = line.strip()

        if not line:
            continue

        if line.startswith('define') and '@src' in line:
            current_func = 'src'
            header['src'] = line
            continue
        elif line.startswith('define') and '@tgt' in line:
            current_func = 'tgt'
            header['tgt'] = line
            continue

        if line == '}':
            current_func = None
            continue

        if current_func:
            body[current_func].append(line)

    return body, header

def preprocess_llm_response(llm_response):
    if "```" in llm_response:
        matches = re.findall(r"```(?:\w+)?\n(.*?)```", llm_response, re.DOTALL)
        if matches:
            llm_response = matches[0]
        elif llm_response.strip().startswith("```"):
            lines = llm_response.splitlines()
            if len(lines) >= 2:
                lines = lines[1:-1]
            llm_response = '\n'.join(lines)
    llm_response = remove_comments(llm_response)

    match = re.search(r"^define\s+", llm_response, re.MULTILINE)
    if match:
        preamble = llm_response[:match.start()]
        declare_lines = [ln for ln in preamble.splitlines() if re.match(r"^\s*declare\b", ln)]
        llm_response = '\n'.join(declare_lines + [llm_response[match.start():]])
    # Remove lines that are only control markers (allowing surrounding whitespace)
    lines = llm_response.splitlines()
    filtered_lines = [ln for ln in lines if ln.strip() not in {'entry:', '=>'}]
    return '\n'.join(filtered_lines)

def extract_args_from_header(header):
        # find the first parenthesis pair and return args string and surrounding parts
    try:
        l = header.index('(')
        r = header.index(')', l)
    except ValueError:
        return None, None, None
    prefix = header[:l]
    args_str = header[l+1:r].strip()
    # suffix should exclude the closing paren; keep the text after ')'
    suffix = header[r+1:]
    return prefix, args_str, suffix

def parse_args_list(args_str):
    """Parse comma-separated args like 'i32 %a, i8* %p' -> [('%a','i32'), ('%p','i8*')]"""
    args = []
    if not args_str.strip():
        return args
    parts = []
    depth_paren = 0
    depth_angle = 0
    depth_brace = 0
    cur = ''
    for ch in args_str:
        if ch == '(': depth_paren += 1
        elif ch == ')': depth_paren -= 1
        elif ch == '<': depth_angle += 1
        elif ch == '>': depth_angle -= 1
        elif ch == '{': depth_brace += 1
        elif ch == '}': depth_brace -= 1

        if ch == ',' and depth_paren == 0 and depth_angle == 0 and depth_brace == 0:
            parts.append(cur.strip())
            cur = ''
        else:
            cur += ch
    if cur.strip():
        parts.append(cur.strip())

    for p in parts:
        # Try to find %var
        vm = RE_VAR.search(p)
        if vm:
            var_name = vm.group(1)
            # Find var_name in p. We assume type is everything before var_name.
            # But be careful about "getelementptr ... %var" where type is earlier.
            # However, for simple args "type %var", this works.
            # For "type constant", we ignore.

            # We search for the LAST occurrence of var_name to be safe?
            # Usually %var is at the end of the type-value pair.
            idx = p.rfind(var_name)
            if idx != -1:
                ty = p[:idx].strip()
                if not ty:
                    args.append((var_name, None))
                else:
                    args.append((var_name, ty))
            else:
                args.append((var_name, None))
        else:
            # No variable found, might be a constant (e.g. "i32 1", "1", "true", "null")
            p = p.strip()
            if p:
                tokens = p.split()
                if len(tokens) >= 2:
                    # Assume last token is value, rest is type
                    val = tokens[-1]
                    ty = ' '.join(tokens[:-1])
                    args.append((val, ty))
                else:
                    # Just one token, assume it's the value
                    args.append((p, None))
    return args

def build_arg_list(src_args_str, tgt_args_str):
        # parse args using existing helper; parse_args_list returns list of (op, ty)
    src_parsed = parse_args_list(src_args_str or '')
    tgt_parsed = parse_args_list(tgt_args_str or '')

        # Build ordered union: keep src order, then append tgt args whose name not seen
    ordered = []
    seen = set()
    for op, ty in src_parsed:
        name = op.strip()
        if name in seen:
            continue
        seen.add(name)
        ordered.append((name, ty))
    for op, ty in tgt_parsed:
        name = op.strip()
        if name in seen:
            continue
        seen.add(name)
        ordered.append((name, ty))
        # Format: keep 'type name' when type is present, otherwise just name
    parts = []
    for name, ty in ordered:
        if ty:
            parts.append(f"{ty} {name}")
        else:
            parts.append(f"{name}")
    return ', '.join(parts)

def build_ir(src_header, src_body, tgt_header, tgt_body, build_split_ir = False):
    # Ensure src/tgt headers have the same parameter list (union of both args)

    s_prefix, s_args, s_suffix = extract_args_from_header(src_header)
    t_prefix, t_args, t_suffix = extract_args_from_header(tgt_header)

    if s_prefix is not None and t_prefix is not None:
        unified_args = build_arg_list(s_args, t_args)
        new_src_header = f"{s_prefix}({unified_args}){s_suffix}"
        new_tgt_header = f"{t_prefix}({unified_args}){t_suffix}"
    else:
        # fallback: leave headers unchanged
        new_src_header = src_header
        new_tgt_header = tgt_header

    if build_split_ir:
        return f"{new_src_header}\n" + "\n".join(indent(src_body)) + "\n}\n", f"{new_tgt_header}\n" + "\n".join(indent(tgt_body)) + "\n}\n"

    else:
        return f"{new_src_header}\n" + "\n".join(indent(src_body)) + "\n}\n\n" + \
            f"{new_tgt_header}\n" + "\n".join(indent(tgt_body)) + "\n}\n"

def extract_operands_and_types(line):
    """
    Parse one LLVM IR instruction line and return a list of (operand, type) pairs found on the RHS.
    Heuristic-based; covers many common instructions.
    """
    line = strip_comment(line)
    if not line:
        return []

    # split off assignment if present
    if '=' in line:
        lhs, rhs = line.split('=', 1)
        rhs = rhs.strip()
    else:
        rhs = line.strip()

    # get opcode (first token)
    m_op = re.match(r'^([a-zA-Z][a-zA-Z0-9_.]*)\b', rhs)
    if not m_op:
        # fallback: return all %vars
        return [(v, None) for v in RE_VAR.findall(rhs)]

    opcode = m_op.group(1)
    rest = rhs[len(opcode):].strip()

    # Handle specific instructions

    # call
    if opcode == 'call':
        # Match pattern: call [ret_ty] <func_name>(<args>)
        # We use a regex that captures the function name (starting with @ or %) and the args inside ().
        # This handles simple return types. Complex return types are matched by (.+?) non-greedily.
        m = re.match(r'^call\s+(.+?)\s+(@[-a-zA-Z0-9_.\$]+|%[-a-zA-Z0-9_.\$]+)\s*\((.*)\)', rhs)
        if m:
            # args_str is everything inside the parentheses.
            # Note: (.*) is greedy, so it matches until the last closing paren.
            # This is usually correct unless there are attributes after the call that contain parens.
            args_str = m.group(3)

            # If the greedy match captured too much (e.g. nested parens in attributes?),
            # we might need to be smarter. But for standard IR, the args list is the main parenthesized group.
            # However, if the function name itself wasn't matched correctly, we might have issues.

            return parse_args_list(args_str)

        # Fallback for other call forms (e.g. inline asm, bitcast constant expr)
        # Just try to parse the whole rest as args list, though it might be messy.
        return parse_args_list(rest)

    if opcode in ('icmp', 'fcmp'):
        # remove predicate
        tokens = rest.split(maxsplit=1)
        if len(tokens) > 1:
            rest = tokens[1]
        ret_args_list = parse_args_list(rest)
        # Propagate type from first operand to others if missing
        if len(ret_args_list) >= 2:
            op1, ty1 = ret_args_list[0]
            if ty1:
                for i in range(1, len(ret_args_list)):
                    op, ty = ret_args_list[i]
                    if ty is None:
                        ret_args_list[i] = (op, ty1)
        return ret_args_list


    # Binary ops: remove flags
    if opcode in BINARY_OPS:
        # Flags: nsw, nuw, exact, fast-math
        flags = {'nsw', 'nuw', 'exact', 'fast', 'nnan', 'ninf', 'nsz', 'arcp', 'contract', 'afn', 'reassoc'}
        tokens = rest.split()
        while tokens and tokens[0] in flags:
            tokens.pop(0)
        rest = ' '.join(tokens)

        parsed = parse_args_list(rest)
        # Propagate type from first operand to second if missing
        if len(parsed) >= 2:
            op1, ty1 = parsed[0]
            op2, ty2 = parsed[1]
            if ty1 and not ty2:
                parsed[1] = (op2, ty1)
        return parsed

    # icmp/fcmp


    # getelementptr
    if opcode in ('getelementptr', 'gep'):
        # remove inbounds
        if rest.startswith('inbounds '):
            rest = rest[9:].strip()
        return parse_args_list(rest)

    # Generic handling for others (load, store, select, etc.)
    return parse_args_list(rest)


def extract_preconditions(function_body):
    """
    Extracts all `call void @llvm.assume(i1 %cond)` instructions and their dependency trees
    from a function body (list of strings).

    Returns a list of strings containing the relevant instructions (definitions and assumes),
    topologically sorted (dependencies before users).
    """
    # 1. Parse the function body to map defined variables to their definition lines
    # Regex to capture "%var = ..."
    def_pattern = re.compile(r'^\s*(%[-a-zA-Z$._0-9]+)\s*=\s*(.*)$')

    # Map: var_name -> (line_index, line_content, set_of_used_vars)
    definitions = {}

    # Also keep track of all lines to easily retrieve them
    lines = list(function_body)

    for idx, line in enumerate(lines):
        line = strip_comment(line).strip()
        if not line:
            continue

        match = def_pattern.match(line)
        if match:
            var_name = match.group(1)
            rhs = match.group(2)
            # Extract used variables from RHS
            used_vars = set(m.group(1) for m in RE_VAR.finditer(rhs))
            definitions[var_name] = {
                'line_idx': idx,
                'line': line,
                'used_vars': used_vars
            }

    # 2. Find all llvm.assume calls
    # Pattern: call void @llvm.assume(i1 %cond)
    assume_pattern = re.compile(r'^\s*call\s+void\s+@llvm\.assume\s*\(\s*i1\s+(%[-a-zA-Z$._0-9]+)\s*\)')

    assumes = [] # List of (line_idx, line_content, condition_var)

    for idx, line in enumerate(lines):
        line = strip_comment(line).strip()
        match = assume_pattern.match(line)
        if match:
            cond_var = match.group(1)
            assumes.append({
                'line_idx': idx,
                'line': line,
                'cond_var': cond_var
            })

    if not assumes:
        return []

    # 3. Collect dependencies for all assumes
    # We use a set of line indices to avoid duplicates
    needed_line_indices = set()

    # Queue for BFS/DFS traversal of dependencies
    # Start with the condition variables of all assumes
    worklist = []

    for asm in assumes:
        needed_line_indices.add(asm['line_idx'])
        worklist.append(asm['cond_var'])

    processed_vars = set()

    while worklist:
        var = worklist.pop(0)
        if var in processed_vars:
            continue
        processed_vars.add(var)

        if var in definitions:
            def_info = definitions[var]
            needed_line_indices.add(def_info['line_idx'])

            # Add dependencies of this variable to worklist
            for dep_var in def_info['used_vars']:
                if dep_var not in processed_vars:
                    worklist.append(dep_var)

    # 4. Construct the result list
    # Sort indices to maintain original program order (topological sort for SSA)
    sorted_indices = sorted(list(needed_line_indices))

    result_lines = [lines[idx] for idx in sorted_indices]

    return result_lines

def analyze_constant_generalization(src_A_lines, src_B_lines):
    """
    Analyzes how constants in src_A are generalized in src_B using tree-based comparison.
    Returns a list of dictionaries mapping original constants to their generalized expressions in src_B.
    Each dict has: {'original': str, 'generalized': str, 'location': str}
    """

    def parse_dag(lines):
        defs = {}
        root = None
        # Regex for assignment: %var = opcode ...
        assign_re = re.compile(r'^\s*(%[-a-zA-Z$._0-9]+)\s*=\s*([a-z]+)\s+(.*)$')
        # Regex for ret: ret type %var
        ret_re = re.compile(r'^\s*ret\s+.*?([%@][-a-zA-Z$._0-9]+|[-0-9]+|true|false|null)')

        for idx, line in enumerate(lines):
            line = strip_comment(line).strip()
            if not line: continue

            # Check for return (root)
            if line.startswith('ret '):
                # ret <type> <value>
                # Use extract_operands_and_types to parse
                args = extract_operands_and_types(line)
                if args:
                    # The return value is the first operand
                    root = args[0][0]
                continue

            # Check for assignment
            m_assign = assign_re.match(line)
            if m_assign:
                var = m_assign.group(1)
                opcode = m_assign.group(2)
                rest = m_assign.group(3)
                # Reconstruct RHS for the helper
                rhs = f"{opcode} {rest}"
                args = extract_operands_and_types(rhs)
                # extract_operands_and_types returns [(val, type), ...]
                operands = [x[0] for x in args]
                defs[var] = {'op': opcode, 'args': operands, 'line': line, 'index': idx}

        return defs, root

    defs_A, root_A = parse_dag(src_A_lines)
    defs_B, root_B = parse_dag(src_B_lines)
    # print(defs_A)
    # print(defs_B)


    if not root_A or not root_B:

        return [{"error": "Could not find return value in one of the sources"}]

    mappings = []
    arg_map = {}

    op_symbols = {
        'add': '+', 'sub': '-', 'mul': '*', 'udiv': '/', 'sdiv': '/',
        'urem': '%', 'srem': '%', 'shl': '<<', 'lshr': '>>', 'ashr': '>>',
        'and': '&', 'or': '|', 'xor': '^'
    }

    def get_expr_str(var, defs):
        # Recursively build expression string for a variable in B
        if var not in defs:
            return var # It's an argument or constant

        info = defs[var]
        op = info['op']
        args = info['args']

        arg_strs = [get_expr_str(a, defs) for a in args]

        symbol = op_symbols.get(op, op)

        if len(arg_strs) == 2 and op in op_symbols:
            return f"({arg_strs[0]} {symbol} {arg_strs[1]})"
        elif len(arg_strs) == 1 and op == 'sub' and arg_strs[0] == '0':
             # Negation? sub 0, x is not unary.
             pass

        return f"{op}({', '.join(arg_strs)})"

    def get_dependency_lines(var, defs, visited_indices=None):
        """
        Recursively collect all IR lines that define 'var' and its dependencies.
        Returns a list of (index, line) tuples.
        """
        if visited_indices is None:
            visited_indices = set()

        if var not in defs:
            return [] # Argument or constant, no definition line

        info = defs[var]
        idx = info['index']

        if idx in visited_indices:
            return []

        visited_indices.add(idx)

        items = []
        # Collect dependencies
        for arg in info['args']:
            items.extend(get_dependency_lines(arg, defs, visited_indices))

        items.append((idx, info['line']))
        return items

    def compare(node_A, node_B, path):
        # node_A/B are strings (variable names or constants)

        is_const_A = not node_A.startswith('%') and not node_A.startswith('@')
        is_const_B = not node_B.startswith('%') and not node_B.startswith('@')

        if is_const_A and not is_const_B:
            # Found a generalization!
            # Reconstruct expression for node_B
            expr_B = get_expr_str(node_B, defs_B)
            # Collect dependency lines for node_B
            dep_items = get_dependency_lines(node_B, defs_B)
            # Sort by index to restore original order
            dep_items.sort(key=lambda x: x[0])
            dep_lines = [x[1] for x in dep_items]

            mappings.append({
                'original': node_A,
                'generalized': expr_B,
                'generalized_lines': dep_lines,
                'location': path
            })
            return

        if is_const_A and is_const_B:
            # Both constants. If different, record it?
            if node_A != node_B:
                 mappings.append({
                    'original': node_A,
                    'generalized': node_B, # Just a different constant
                    'location': path
                })
            return

        if not is_const_A and is_const_B:
            # Variable became constant?
            return

        # Both are variables
        if node_A not in defs_A or node_B not in defs_B:
            # One is an argument/input.
            # If they are different arguments, we might note it, but usually we care about constants.
            if node_A not in defs_A and node_B not in defs_B:
                arg_map[node_A] = node_B
            return

        # Both are defined instructions
        info_A = defs_A[node_A]
        info_B = defs_B[node_B]

        if info_A['op'] != info_B['op']:
            # Structural divergence
            return

        # Compare operands
        args_A = info_A['args']
        args_B = info_B['args']

        if len(args_A) != len(args_B):
            return

        for i, (arg_A, arg_B) in enumerate(zip(args_A, args_B)):
            compare(arg_A, arg_B, path + f" -> {info_A['op']}[{i}]")

    compare(root_A, root_B, "root")


    return mappings, arg_map
