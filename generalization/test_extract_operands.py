import re
import json

BINARY_OPS = {
    'add', 'sub', 'mul', 'udiv', 'sdiv', 'urem', 'srem',
    'and', 'or', 'xor', 'shl', 'lshr', 'ashr',
    'icmp', 'fcmp',
    'fadd', 'fsub', 'fmul', 'fdiv'
}

def generate_variants_by_renaming_operands(line, operands):

    variants = []

    def make_pattern(var):
        return r'(?<![A-Za-z0-9$_\.\-])' + re.escape(var) + r'(?![A-Za-z0-9$_\.\-])'

    for i, (op, ty) in enumerate(operands):

        if not op or not op.startswith('%'):
            continue
        new_name = op + '_new'
        pat = make_pattern(op)
        new_line = re.sub(pat, new_name, line)
        line = new_line
        variants.append((i, op, new_name, new_line))
    return variants

RE_VAR = re.compile(r'(%[-a-zA-Z$._0-9]+)')
RE_TYPE = re.compile(r'\b(i\d+|float|double|half|void|ptr|byte|label|metadata|x86_fp80|i\d+\*|[a-zA-Z_][a-zA-Z0-9_<>\.\*\[\]]*)\b')

def _strip_comment(line):
    # remove trailing comments starting with ';'
    return line.split(';', 1)[0].strip()

def parse_args_list(args_str):
    """Parse comma-separated args like 'i32 %a, i8* %p' -> [('%a','i32'), ('%p','i8*')]"""
    args = []
    if not args_str.strip():
        return args
    parts = []
    depth = 0
    cur = ''
    for ch in args_str:
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        if ch == ',' and depth == 0:
            parts.append(cur.strip())
            cur = ''
        else:
            cur += ch
    if cur.strip():
        parts.append(cur.strip())
    for p in parts:
        # p might be "i32 %a" or "i32 42" or "i8* getelementptr(...)", etc.
        m = re.match(r'^\s*([^\s]+)\s+(.+)$', p)
        if m:
            ty = m.group(1).strip()
            op = m.group(2).strip()
            args.append((op, ty))
        else:
            # fallback: look for %var
            vm = RE_VAR.search(p)
            if vm:
                args.append((vm.group(1), None))
            else:
                args.append((p, None))
    return args

def extract_operands_and_types(line):
    """
    Parse one LLVM IR instruction line and return a list of (operand, type) pairs found on the RHS.
    Heuristic-based; covers many common instructions.
    """
    line = _strip_comment(line)
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

    # Binary ops like "add i32 %a, %b"
    if opcode in BINARY_OPS:
        # pattern: opcode <type> <op1>, <op2> (op2 usually without type)
        m = re.match(rf'^{opcode}\s+([^\s,]+)\s+([^,]+),\s*(.+)$', rhs)
        if m:
            ty = m.group(1).strip()
            op1 = m.group(2).strip()
            op2 = m.group(3).strip()
            return [(op1, ty), (op2, ty)]
        # fallback: find %vars
        return [(v, None) for v in RE_VAR.findall(rhs)]

    # load: "load i32, i32* %ptr"
    if opcode == 'load':
        m = re.match(r'^load\s+([^\s,]+)\s*,\s*([^\s,]+)\s+(.+)$', rhs)
        if m:
            loaded_ty = m.group(1).strip()
            ptr = m.group(3).strip()
            return [(ptr, loaded_ty)]
        return [(v, None) for v in RE_VAR.findall(rhs)]

    # store: "store i32 %val, i32* %ptr"
    if opcode == 'store':
        m = re.match(r'^store\s+([^\s,]+)\s+([^,]+),\s*([^\s,]+)\s+(.+)$', rhs)
        if m:
            val_ty = m.group(1).strip()
            val = m.group(2).strip()
            ptr = m.group(4).strip()
            return [(val, val_ty), (ptr, None)]
        return [(v, None) for v in RE_VAR.findall(rhs)]

    # call: "call i32 @foo(i32 %a, i8* %p)"
    if opcode == 'call':
        m = re.match(r'^call\s+([^\s@\(]+)\s+(@?[-a-zA-Z0-9_.\$]+)\s*\((.*)\)', rhs)
        if m:
            ret_ty = m.group(1).strip()
            args_str = m.group(3)
            args = parse_args_list(args_str)
            return args
        # alternate form: call void @llvm.assume(i1 %cond)
        m2 = re.match(r'^call\s+(.+?)\((.*)\)', rhs)
        if m2:
            args_str = m2.group(2)
            return parse_args_list(args_str)
        return [(v, None) for v in RE_VAR.findall(rhs)]

    # getelementptr: "getelementptr inbounds <ty>, <ty>* %ptr, i32 0, i32 %idx"
    if opcode == 'getelementptr' or opcode == 'gep':
        # find first %var after the comma sequence
        vars_found = RE_VAR.findall(rhs)
        if vars_found:
            # return pointer operand and try to infer element type (first type token)
            mty = RE_TYPE.search(rhs)
            ty = mty.group(1) if mty else None
            return [(vars_found[0], ty)]
        return []

    # phi: "phi i32 [ %a, %bb1 ], [ %b, %bb2 ]"
    if opcode == 'phi':
        # find all entries like [ %a, %bb ]
        entries = re.findall(r'\[\s*([^,]+)\s*,\s*([^\]]+)\]', rhs)
        results = []
        # type token before entries
        mty = re.match(r'phi\s+([^\s]+)\s+', rhs)
        ty = mty.group(1) if mty else None
        for val,bb in entries:
            val = val.strip()
            results.append((val, ty))
        return results

    # select: "select i1 %cond, i32 %a, i32 %b"
    if opcode == 'select':
        # More robust parsing: split into cond, true-val, false-val parts
        m = re.match(r'^select\s+([^,]+),\s*([^,]+),\s*(.+)$', rhs)
        if m:
            cond_part = m.group(1).strip()
            true_part = m.group(2).strip()
            false_part = m.group(3).strip()
            results = []
            # cond: usually like 'i1 %c' -> ( %c, i1 )
            mm = re.match(r'^([^\s]+)\s+(.+)$', cond_part)
            if mm:
                cond_ty = mm.group(1).strip()
                cond_op = mm.group(2).strip()
                vm = RE_VAR.search(cond_op)
                results.append((vm.group(1) if vm else cond_op, cond_ty))
            else:
                vm = RE_VAR.search(cond_part)
                results.append((vm.group(1) if vm else cond_part, None))

            # true value
            mm = re.match(r'^([^\s]+)\s+(.+)$', true_part)
            if mm:
                t_ty = mm.group(1).strip()
                t_op = mm.group(2).strip()
                vm = RE_VAR.search(t_op)
                results.append((vm.group(1) if vm else t_op, t_ty))
            else:
                vm = RE_VAR.search(true_part)
                results.append((vm.group(1) if vm else true_part, None))

            # false value
            mm = re.match(r'^([^\s]+)\s+(.+)$', false_part)
            if mm:
                f_ty = mm.group(1).strip()
                f_op = mm.group(2).strip()
                vm = RE_VAR.search(f_op)
                results.append((vm.group(1) if vm else f_op, f_ty))
            else:
                vm = RE_VAR.search(false_part)
                results.append((vm.group(1) if vm else false_part, None))

            return results

    # fallback: return all %vars; attempt to guess type by searching left tokens
    vars_found = RE_VAR.findall(rhs)
    results = []
    for v in vars_found:
        pat = re.compile(r'([^\s,]+)\s+' + re.escape(v))
        mm = pat.search(rhs)
        if mm:
            maybe_ty = mm.group(1)
            if re.match(r'^(i\d+|float|double|[a-zA-Z_].*|\w+\*)$', maybe_ty):
                results.append((v, maybe_ty))
                continue
        results.append((v, None))
    return results


def _print_result(line, res):
    print('\nIN:  ' + line)
    print('OUT:')
    print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    sample_lines = [
        '%res = sub i32 %a, %b',
        '%x = zext i8 %y to i32',
        '  %v = load i32, i32* %ptr ; load example',
        'store i32 %val, i32* %p',
        'call void @llvm.assume(i1 %cond)',
        'call i32 @foo(i32 %a, i8* %p)',
        '%gep = getelementptr inbounds %struct.My, %struct.My* %ptr, i32 0, i32 %idx',
        '%p = phi i32 [ %a, %bb1 ], [ %b, %bb2 ]',
        '%s = select i1 %c, i32 %a, i32 %b',
        '%m = mul i32 %val, 0',
    ]

    for l in sample_lines:
        r = extract_operands_and_types(l)
        variants = generate_variants_by_renaming_operands(l, r)
        print("original:", l)
        for idx, orig, newname, new_line in variants:
            print(f"replace #{idx} operand {orig} -> {newname} :")
            print("  ", new_line)
        print()
        # _print_result(l, r)
        # print(r)
