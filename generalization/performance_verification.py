import re
import subprocess
import tempfile
import os
import shutil
from generalization.utils import extract_alive2_function_bodies

# Determine default paths for third-party tools
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
third_party_llc = os.path.join(project_root, 'third_party', 'llvm', 'bin', 'llc')
third_party_mca = os.path.join(project_root, 'third_party', 'llvm', 'bin', 'llvm-mca')

DEFAULT_LLC = third_party_llc if os.path.exists(third_party_llc) else 'llc'
DEFAULT_MCA = third_party_mca if os.path.exists(third_party_mca) else 'llvm-mca'


DEFAULT_DECLS = []


def _ensure_decls(module_text, extra_decls=None):
    """Prepend necessary declare lines if the IR references common intrinsics.
    Returns the new module text.
    """
    decls = []
    if extra_decls:
        decls.extend(extra_decls)

    if '@llvm.assume' in module_text and 'declare void @llvm.assume' not in module_text:
        decls.append('declare void @llvm.assume(i1)')

    # Dynamic intrinsic handling
    # (base_name, arg_types_template, ret_type_template)
    # T is the type derived from suffix
    patterns = [
        ('llvm.ctpop', ['T'], 'T'),
        ('llvm.ctlz', ['T', 'i1'], 'T'),
        ('llvm.cttz', ['T', 'i1'], 'T'),
        ('llvm.abs', ['T', 'i1'], 'T'),
        ('llvm.smin', ['T', 'T'], 'T'),
        ('llvm.smax', ['T', 'T'], 'T'),
        ('llvm.umin', ['T', 'T'], 'T'),
        ('llvm.umax', ['T', 'T'], 'T'),
        ('llvm.fshl', ['T', 'T', 'T'], 'T'),
        ('llvm.fshr', ['T', 'T', 'T'], 'T'),
        ('llvm.bswap', ['T'], 'T'),
        ('llvm.bitreverse', ['T'], 'T'),
        ('llvm.uadd.sat', ['T', 'T'], 'T'),
        ('llvm.sadd.sat', ['T', 'T'], 'T'),
        ('llvm.usub.sat', ['T', 'T'], 'T'),
        ('llvm.ssub.sat', ['T', 'T'], 'T'),
    ]

    def get_llvm_type(suffix):
        # i32, i64, i128, etc.
        if re.match(r'^i\d+$', suffix): return suffix
        # v4i32 -> <4 x i32>, v2float -> <2 x float>
        m = re.match(r'^v(\d+)(i\d+|float|double|half)$', suffix)
        if m: return f"<{m.group(1)} x {m.group(2)}>"
        return None

    for base, args_tmpl, ret_tmpl in patterns:
        # Find all usages: @llvm.base.suffix
        # Use regex escape for base just in case
        regex = r'@' + re.escape(base) + r'\.([a-zA-Z0-9_]+)'
        matches = set(re.findall(regex, module_text))

        for suffix in matches:
            T = get_llvm_type(suffix)
            if not T: continue

            # Construct args
            args_str = ', '.join([T if a == 'T' else a for a in args_tmpl])
            ret_str = T if ret_tmpl == 'T' else ret_tmpl

            decl_line = f"declare {ret_str} @{base}.{suffix}({args_str})"

            if decl_line not in module_text and decl_line not in decls:
                decls.append(decl_line)

    if not decls:
        return module_text

    prefix = '\n'.join(decls) + '\n\n'
    return prefix + module_text


def _build_module_from_parts(header, body_lines):
    # header is like 'define i32 @src(i32 %x) {', but extract_alive2 returns header without '{'
    # ensure header ends up as 'define ... {'
    hdr = header.strip()
    if not hdr.endswith('{'):
        # If header already contains a trailing '{' in some variants, keep it
        hdr = hdr
    lines = [hdr]
    lines.extend(body_lines)
    lines.append('}')
    return '\n'.join(lines) + '\n'


def _write_temp_file(contents, suffix='.ll'):
    fd, path = tempfile.mkstemp(suffix=suffix, text=True)
    os.close(fd)
    with open(path, 'w') as f:
        f.write(contents)
    return path


def _run_llc(llc_cmd, input_ll, output_s, mcpu=None, triple=None):
    cmd = [llc_cmd, '-O3', '-filetype=asm', input_ll, '-o', output_s]
    if mcpu:
        cmd.extend(['-mcpu', mcpu])
    if triple:
        cmd.extend(['-mtriple', triple])
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return res.returncode, res.stdout, res.stderr


def _run_llvm_mca(llvm_mca_cmd, asm_file, mcpu=None):
    # Use -mcpu if provided
    cmd = [llvm_mca_cmd, asm_file]
    if mcpu:
        cmd = [llvm_mca_cmd, '-mcpu=' + mcpu, asm_file]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return res.returncode, res.stdout, res.stderr


def _parse_mca_output(output):
    # Try to find Total Cycles and Total uOps
    cycles = None
    uops = None
    m = re.search(r'Total Cycles:\s*([0-9]+(?:\.[0-9]+)?)', output)
    if m:
        cycles = float(m.group(1))
    m2 = re.search(r'Total uOps:\s*([0-9]+(?:\.[0-9]+)?)', output)
    if m2:
        uops = float(m2.group(1))
    # sometimes wording may differ; try alternate searches
    if cycles is None:
        m = re.search(r'Total Cycles\s*[:]?\s*([0-9]+(?:\.[0-9]+)?)', output)
        if m:
            cycles = float(m.group(1))
    if uops is None:
        m = re.search(r'Total uOps?\s*[:]?\s*([0-9]+(?:\.[0-9]+)?)', output)
        if m:
            uops = float(m.group(1))

    return {'cycles': cycles, 'uops': uops, 'raw': output}


def compare_ir_performance(ir_code, metric='uops', llc_cmd=None, llvm_mca_cmd=None, mcpu=None, triple=None, keep_files=False, extra_decls=None):
    """
    Split an Alive2-style IR into `@src` and `@tgt`, compile both with `llc` and run
    `llvm-mca`. Returns a dict:
      { 'src': {cycles,uops,raw}, 'tgt': {...}, 'winner': 'src'|'tgt'|'tie'|'unknown' }

    metric: 'cycles' or 'uops'
    """
    if llc_cmd is None:
        llc_cmd = DEFAULT_LLC
    if llvm_mca_cmd is None:
        llvm_mca_cmd = DEFAULT_MCA

    bodies, headers = extract_alive2_function_bodies(ir_code)
    src_header = headers.get('src', '')
    tgt_header = headers.get('tgt', '')
    src_body = bodies.get('src', [])
    tgt_body = bodies.get('tgt', [])

    if not src_header or not tgt_header:
        raise ValueError('IR must contain both @src and @tgt definitions')

    src_module = _build_module_from_parts(src_header, src_body)
    tgt_module = _build_module_from_parts(tgt_header, tgt_body)

    # Ensure common declarations
    src_module = _ensure_decls(src_module, extra_decls)
    tgt_module = _ensure_decls(tgt_module, extra_decls)

    tmpdir = tempfile.mkdtemp(prefix='perf_verify_')
    try:
        src_ll = os.path.join(tmpdir, 'src.ll')
        tgt_ll = os.path.join(tmpdir, 'tgt.ll')
        with open(src_ll, 'w') as f:
            f.write(src_module)
        with open(tgt_ll, 'w') as f:
            f.write(tgt_module)

        src_s = os.path.join(tmpdir, 'src.s')
        tgt_s = os.path.join(tmpdir, 'tgt.s')

        rc, out, err = _run_llc(llc_cmd, src_ll, src_s, mcpu=mcpu, triple=triple)
        if rc != 0:
            raise RuntimeError(f'llc failed for src: rc={rc}\nstdout:\n{out}\nstderr:\n{err}')

        rc, out, err = _run_llc(llc_cmd, tgt_ll, tgt_s, mcpu=mcpu, triple=triple)
        if rc != 0:
            raise RuntimeError(f'llc failed for tgt: rc={rc}\nstdout:\n{out}\nstderr:\n{err}')

        rc, out_src, err_src = _run_llvm_mca(llvm_mca_cmd, src_s, mcpu=mcpu)
        if rc != 0:
            # llvm-mca can exit non-zero but still print useful output; continue
            pass
        src_metrics = _parse_mca_output(out_src + '\n' + err_src)

        rc, out_tgt, err_tgt = _run_llvm_mca(llvm_mca_cmd, tgt_s, mcpu=mcpu)
        if rc != 0:
            pass
        tgt_metrics = _parse_mca_output(out_tgt + '\n' + err_tgt)

        s_val = src_metrics.get(metric)
        t_val = tgt_metrics.get(metric)
        if s_val is None or t_val is None:
            winner = 'unknown'
        else:
            if abs(s_val - t_val) < 1e-9:
                # winner = 'tie'
                winner = 'tgt'
            elif metric == 'cycles':
                winner = 'src' if s_val < t_val else 'tgt'
            elif metric == 'uops':  # uops smaller is better
                winner = 'src' if s_val < t_val else 'tgt'
            else:
                winner = 'unknown'

        result = {
            'src': src_metrics,
            'tgt': tgt_metrics,
            'winner': winner,
            'metric': metric,
            'tmpdir': tmpdir if keep_files else None,
        }

        if not keep_files:
            # cleanup
            try:
                shutil.rmtree(tmpdir)
            except Exception:
                pass

        return result
    except Exception:
        # if any error, remove tmpdir and re-raise
        try:
            shutil.rmtree(tmpdir)
        except Exception:
            pass
        raise


if __name__ == '__main__':
    import argparse

    p = argparse.ArgumentParser(description='Compare src/tgt performance using llc+llvm-mca')
    p.add_argument('--infile', '-i', help='Input file containing src/tgt alive2 IR', required=False)
    p.add_argument('--metric', choices=['cycles', 'uops'], default='uops')
    p.add_argument('--llc', default=DEFAULT_LLC)
    p.add_argument('--llvm-mca', dest='llvm_mca', default=DEFAULT_MCA)
    p.add_argument('--mcpu', default=None)
    p.add_argument('--keep', action='store_true', help='Keep temporary files')

    args = p.parse_args()
    def example_ir():
        return '''; embedded example: src uses sdiv, tgt uses ashr

define i1 @src(ptr %lpo_arg0) {
  %v0 = getelementptr inbounds nuw i8, ptr %lpo_arg0, i64 16
  %v1 = load i64, ptr %v0, align 8
  %v2 = trunc i64 %v1 to i32
  %v3 = icmp eq i32 %v2, 0
  %v4 = icmp ult i64 %v1, 4294967296
  %v5 = and i1 %v4, %v3
  ret i1 %v5
}

define i1 @tgt(ptr %lpo_arg0) {
  %v0 = getelementptr inbounds nuw i8, ptr %lpo_arg0, i64 16
  %v1 = load i64, ptr %v0, align 8
  %v2 = icmp eq i64 %v1, 0
  ret i1 %v2
}
'''

    if args.infile:
        with open(args.infile, 'r') as f:
            ir = f.read()
    else:
        print('No --infile provided; using embedded src/tgt example IR')
        ir = example_ir()

    res = compare_ir_performance(ir, metric=args.metric, llc_cmd=args.llc, llvm_mca_cmd=args.llvm_mca, mcpu=args.mcpu, keep_files=args.keep)
    print('Metric:', res['metric'])
    print('Src:', res['src'])
    print('Tgt:', res['tgt'])
    print('Winner:', res['winner'])
