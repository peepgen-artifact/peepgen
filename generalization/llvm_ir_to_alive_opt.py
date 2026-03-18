#!/usr/bin/env python3

"""Convert a subset of LLVM IR src/tgt functions into Alive .opt syntax.

The script also supports a JSON batch mode for processed testcase files that
contain a `final_result_without_bitwidth_generalization` field.
"""

from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
from typing import Any

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALIVE2_PATH = os.path.join(REPO_ROOT, "third_party", "alive2", "build", "alive-tv")
ALIVE_PATH = os.path.join(REPO_ROOT, "third_party", "alive2", "build", "alive")


DEFINE_RE = re.compile(
    r"^\s*define\s+(?P<ret>\S+)\s+@(?P<name>[^(]+)\((?P<args>[^)]*)\)\s*\{\s*$"
)
ASSUME_RE = re.compile(
    r"^call\s+void\s+@llvm\.assume\s*\(\s*i1\s+(?P<cond>.+?)\s*\)\s*$"
)
RET_RE = re.compile(r"^ret\s+(?P<ty>\S+)\s+(?P<val>.+?)\s*$")
ICMP_RE = re.compile(
    r"^(?P<lhs>%[-a-zA-Z$._0-9]+)\s*=\s*icmp\s+"
    r"(?P<pred>[a-z]+)\s+(?P<ty>\S+)\s+(?P<a>[^,]+),\s*(?P<b>.+?)\s*$"
)
FCMP_RE = re.compile(
    r"^(?P<lhs>%[-a-zA-Z$._0-9]+)\s*=\s*fcmp"
    r"(?P<flags>(?:\s+[A-Za-z]+)*)\s+"
    r"(?P<pred>[a-z]+)\s+(?P<ty>\S+)\s+(?P<a>[^,]+),\s*(?P<b>.+?)\s*$"
)
BINOP_RE = re.compile(
    r"^(?P<lhs>%[-a-zA-Z$._0-9]+)\s*=\s*(?P<op>"
    r"add|sub|mul|sdiv|udiv|srem|urem|shl|lshr|ashr|and|or|xor"
    r")(?P<flags>(?:\s+(?:nsw|nuw|exact))*)\s+"
    r"(?P<ty>\S+)\s+(?P<a>[^,]+),\s*(?P<b>.+?)\s*$"
)
FP_BINOP_RE = re.compile(
    r"^(?P<lhs>%[-a-zA-Z$._0-9]+)\s*=\s*(?P<op>fadd|fsub|fmul|fdiv|frem)"
    r"(?P<flags>(?:\s+[A-Za-z]+)*)\s+"
    r"(?P<ty>\S+)\s+(?P<a>[^,]+),\s*(?P<b>.+?)\s*$"
)
FNEG_RE = re.compile(
    r"^(?P<lhs>%[-a-zA-Z$._0-9]+)\s*=\s*fneg"
    r"(?P<flags>(?:\s+[A-Za-z]+)*)\s+"
    r"(?P<ty>\S+)\s+(?P<val>.+?)\s*$"
)
SELECT_RE = re.compile(
    r"^(?P<lhs>%[-a-zA-Z$._0-9]+)\s*=\s*select"
    r"(?P<flags>(?:\s+[A-Za-z]+)*)\s+"
    r"(?P<cond_ty>\S+)\s+(?P<cond>[^,]+),\s*"
    r"(?P<ty_a>\S+)\s+(?P<a>[^,]+),\s*"
    r"(?P<ty_b>\S+)\s+(?P<b>.+?)\s*$"
)
CAST_RE = re.compile(
    r"^(?P<lhs>%[-a-zA-Z$._0-9]+)\s*=\s*(?P<op>"
    r"zext|sext|trunc|bitcast|ptrtoint|inttoptr|sitofp|uitofp|fptosi|fptoui|fpext|fptrunc"
    r")(?P<flags>(?:\s+[A-Za-z]+)*)\s+"
    r"(?P<src_ty>\S+)\s+(?P<val>.+?)\s+to\s+(?P<dst_ty>\S+)\s*$"
)
FREEZE_RE = re.compile(
    r"^(?P<lhs>%[-a-zA-Z$._0-9]+)\s*=\s*freeze\s+(?P<ty>\S+)\s+(?P<val>.+?)\s*$"
)

SAFE_INTEGER_LITERALS = {0, 1, -1}
FLOAT_TYPES = ("half", "float", "double")
FLOAT_SUFFIXES = {"half": "f16", "float": "f32", "double": "f64"}
FLOAT_INT_BITS = {"half": 16, "float": 32, "double": 64}
FLOAT_SIGN_CLEAR_MASK = {
    "half": 32767,
    "float": 2147483647,
    "double": 9223372036854775807,
}
FLOAT_INTRINSIC_RE = re.compile(
    r"@llvm\.(?P<name>fabs|maxnum|minnum|maximum|minimum)\.f(?:16|32|64)\b"
)
INT_LITERAL_RE = re.compile(r"(?<![%@A-Za-z0-9_.])-?\d+(?![A-Za-z0-9_.])")
FLOAT_LITERAL_RE = re.compile(
    r"(?<![%@A-Za-z0-9_.])-?(?:\d+\.\d*|\d*\.\d+)(?:[eE][+-]?\d+)?(?![A-Za-z0-9_.])"
)
SHORTCUT_BLOCKED_CAST_RE = re.compile(r"\b(?:trunc|zext|sext)\b")


def strip_comment(line: str) -> str:
    if ";" in line:
        line = line.split(";", 1)[0]
    return line.strip()


def symbolize_type(ty: str) -> str:
    # Leave i1 concrete. For wider integer types, omit the type so Alive uses
    # a symbolic integer type and enumerates legal typings.
    if re.fullmatch(r"i[1-9][0-9]*", ty) and ty != "i1":
        return ""
    return ty


def format_type(ty: str) -> str:
    ty = symbolize_type(ty)
    return f"{ty} " if ty else ""


def format_typed_operand(ty: str, operand: str) -> str:
    ty = symbolize_type(ty)
    if ty:
        return f"{ty} {operand}"
    return operand


def split_top_level(text: str, delimiter: str = ",") -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    depth_paren = 0
    depth_square = 0
    depth_curly = 0

    for ch in text:
        if ch == "(":
            depth_paren += 1
        elif ch == ")":
            depth_paren = max(depth_paren - 1, 0)
        elif ch == "[":
            depth_square += 1
        elif ch == "]":
            depth_square = max(depth_square - 1, 0)
        elif ch == "{":
            depth_curly += 1
        elif ch == "}":
            depth_curly = max(depth_curly - 1, 0)

        if ch == delimiter and not (depth_paren or depth_square or depth_curly):
            parts.append("".join(current).strip())
            current = []
            continue

        current.append(ch)

    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return parts


def parse_typed_operand(text: str) -> tuple[str, str]:
    text = text.strip()
    if " " not in text:
        raise ValueError(f"expected typed operand, got: {text}")
    ty, operand = text.split(None, 1)
    return ty, operand.strip()


def parse_extractvalue(line: str) -> str | None:
    marker = " = extractvalue "
    if marker not in line:
        return None

    lhs, rest = line.split(marker, 1)
    if "," not in rest:
        raise ValueError(f"unsupported extractvalue LLVM IR line: {line}")

    before_idx, idx = rest.rsplit(",", 1)
    agg = before_idx.split()[-1]
    return f"{lhs.strip()} = extractvalue {agg}, {idx.strip()}"


def parse_call(line: str) -> dict[str, str] | None:
    m = re.match(
        r"^(?:(?P<lhs>%[-a-zA-Z$._0-9]+)\s*=\s*)?"
        r"(?:(?:tail|musttail|notail)\s+)?call\s+(?P<body>.+?)\s*$",
        line,
    )
    if not m:
        return None

    body = m.group("body")
    at_pos = body.find("@")
    if at_pos < 0:
        raise ValueError(f"unsupported indirect call: {line}")

    before_at = body[:at_pos].strip()
    after_at = body[at_pos + 1 :]
    open_paren = after_at.find("(")
    close_paren = after_at.rfind(")")
    if open_paren < 0 or close_paren < open_paren:
        raise ValueError(f"malformed call syntax: {line}")

    callee = after_at[:open_paren].strip()
    args = after_at[open_paren + 1 : close_paren].strip()
    ret = before_at.split()[-1] if before_at else ""
    return {
        "lhs": m.group("lhs") or "",
        "ret": ret,
        "callee": callee,
        "args": args,
    }


def convert_intrinsic_call(line: str) -> str:
    call = parse_call(line)
    if call is None:
        raise ValueError(f"unsupported call in function body: {line}")

    lhs = call["lhs"]
    callee = call["callee"]
    args = split_top_level(call["args"])

    if callee == "llvm.assume":
        if len(args) != 1:
            raise ValueError(f"unsupported assume call: {line}")
        ty, cond = parse_typed_operand(args[0])
        if ty != "i1":
            raise ValueError(f"llvm.assume expects i1 condition: {line}")
        return f"assume({cond})"

    if not lhs:
        raise ValueError(f"unsupported void/non-SSA call in function body: {line}")

    unary_intrinsics = {
        "llvm.ctpop.": "ctpop",
        "llvm.fabs.": "fabs",
    }
    binary_intrinsics = {
        "llvm.smin.": "smin",
        "llvm.smax.": "smax",
        "llvm.umin.": "umin",
        "llvm.umax.": "umax",
        "llvm.maxnum.": "fmax",
        "llvm.minnum.": "fmin",
        "llvm.maximum.": "fmaximum",
        "llvm.minimum.": "fminimum",
    }
    binary_with_bool_intrinsics = {
        "llvm.ctlz.": "ctlz",
        "llvm.cttz.": "cttz",
    }
    overflow_intrinsics = {
        "llvm.sadd.with.overflow.": "sadd_overflow",
        "llvm.uadd.with.overflow.": "uadd_overflow",
        "llvm.ssub.with.overflow.": "ssub_overflow",
        "llvm.usub.with.overflow.": "usub_overflow",
        "llvm.smul.with.overflow.": "smul_overflow",
        "llvm.umul.with.overflow.": "umul_overflow",
    }

    for prefix, op in unary_intrinsics.items():
        if callee.startswith(prefix):
            if len(args) != 1:
                raise ValueError(f"unexpected arg count for {callee}: {line}")
            ty, val = parse_typed_operand(args[0])
            return f"{lhs} = {op} {format_typed_operand(ty, val)}".rstrip()

    for prefix, op in binary_intrinsics.items():
        if callee.startswith(prefix):
            if len(args) != 2:
                raise ValueError(f"unexpected arg count for {callee}: {line}")
            ty0, val0 = parse_typed_operand(args[0])
            ty1, val1 = parse_typed_operand(args[1])
            return (
                f"{lhs} = {op} {format_typed_operand(ty0, val0)}, "
                f"{format_typed_operand(ty1, val1)}"
            ).rstrip()

    for prefix, op in binary_with_bool_intrinsics.items():
        if callee.startswith(prefix):
            if len(args) != 2:
                raise ValueError(f"unexpected arg count for {callee}: {line}")
            ty0, val0 = parse_typed_operand(args[0])
            ty1, val1 = parse_typed_operand(args[1])
            return (
                f"{lhs} = {op} {format_typed_operand(ty0, val0)}, "
                f"{format_typed_operand(ty1, val1)}"
            ).rstrip()

    for prefix, op in overflow_intrinsics.items():
        if callee.startswith(prefix):
            if len(args) != 2:
                raise ValueError(f"unexpected arg count for {callee}: {line}")
            ty0, val0 = parse_typed_operand(args[0])
            ty1, val1 = parse_typed_operand(args[1])
            return (
                f"{lhs} = {op} {format_typed_operand(ty0, val0)}, "
                f"{format_typed_operand(ty1, val1)}"
            ).rstrip()

    raise ValueError(f"unsupported call in function body: {line}")


def convert_line(line: str) -> str:
    if not line:
        return ""

    m = ASSUME_RE.match(line)
    if m:
        return f"assume({m.group('cond')})"

    m = RET_RE.match(line)
    if m:
        return f"ret {format_type(m.group('ty'))}{m.group('val')}".rstrip()

    m = ICMP_RE.match(line)
    if m:
        return (
            f"{m.group('lhs')} = icmp {m.group('pred')} "
            f"{format_typed_operand(m.group('ty'), m.group('a'))}, {m.group('b')}"
        ).rstrip()

    m = FCMP_RE.match(line)
    if m:
        op_and_flags = " ".join(
            part for part in ["fcmp", (m.group("flags") or "").strip(), m.group("pred")] if part
        )
        return (
            f"{m.group('lhs')} = {op_and_flags} "
            f"{format_typed_operand(m.group('ty'), m.group('a'))}, {m.group('b')}"
        ).rstrip()

    m = BINOP_RE.match(line)
    if m:
        op_and_flags = " ".join(
            part for part in [m.group("op"), (m.group("flags") or "").strip()] if part
        )
        return (
            f"{m.group('lhs')} = {op_and_flags} "
            f"{format_typed_operand(m.group('ty'), m.group('a'))}, {m.group('b')}"
        ).rstrip()

    m = FP_BINOP_RE.match(line)
    if m:
        op_and_flags = " ".join(
            part for part in [m.group("op"), (m.group("flags") or "").strip()] if part
        )
        return (
            f"{m.group('lhs')} = {op_and_flags} "
            f"{format_typed_operand(m.group('ty'), m.group('a'))}, {m.group('b')}"
        ).rstrip()

    m = FNEG_RE.match(line)
    if m:
        op_and_flags = " ".join(
            part for part in ["fneg", (m.group("flags") or "").strip()] if part
        )
        return (
            f"{m.group('lhs')} = {op_and_flags} "
            f"{format_typed_operand(m.group('ty'), m.group('val'))}"
        ).rstrip()

    m = SELECT_RE.match(line)
    if m:
        op_and_flags = " ".join(
            part for part in ["select", (m.group("flags") or "").strip()] if part
        )
        return (
            f"{m.group('lhs')} = {op_and_flags} "
            f"{format_typed_operand(m.group('cond_ty'), m.group('cond'))}, "
            f"{format_typed_operand(m.group('ty_a'), m.group('a'))}, "
            f"{format_typed_operand(m.group('ty_b'), m.group('b'))}"
        ).rstrip()

    m = CAST_RE.match(line)
    if m:
        src = format_typed_operand(m.group("src_ty"), m.group("val"))
        dst_ty = symbolize_type(m.group("dst_ty"))
        if dst_ty:
            return f"{m.group('lhs')} = {m.group('op')} {src} to {dst_ty}".rstrip()
        return f"{m.group('lhs')} = {m.group('op')} {src}".rstrip()

    m = FREEZE_RE.match(line)
    if m:
        return (
            f"{m.group('lhs')} = freeze "
            f"{format_typed_operand(m.group('ty'), m.group('val'))}"
        ).rstrip()

    extractvalue = parse_extractvalue(line)
    if extractvalue is not None:
        return extractvalue

    if "call " in line:
        return convert_intrinsic_call(line)

    raise ValueError(f"unsupported LLVM IR line: {line}")


def convert_line_narrow(line: str) -> str:
    if not line:
        return ""

    m = ASSUME_RE.match(line)
    if m:
        return f"assume({m.group('cond')})"

    m = RET_RE.match(line)
    if m:
        return f"ret {format_type(m.group('ty'))}{m.group('val')}".rstrip()

    m = ICMP_RE.match(line)
    if m:
        return (
            f"{m.group('lhs')} = icmp {m.group('pred')} "
            f"{format_typed_operand(m.group('ty'), m.group('a'))}, {m.group('b')}"
        ).rstrip()

    m = BINOP_RE.match(line)
    if m:
        op_and_flags = " ".join(
            part for part in [m.group("op"), (m.group("flags") or "").strip()] if part
        )
        return (
            f"{m.group('lhs')} = {op_and_flags} "
            f"{format_typed_operand(m.group('ty'), m.group('a'))}, {m.group('b')}"
        ).rstrip()

    if line.startswith("call ") or " call " in line:
        raise ValueError(f"unsupported call in function body: {line}")

    raise ValueError(f"unsupported LLVM IR line: {line}")


def extract_functions(text: str) -> dict[str, list[str]]:
    functions: dict[str, list[str]] = {}
    current_name: str | None = None
    current_body: list[str] = []

    for raw_line in text.splitlines():
        line = strip_comment(raw_line)
        if not line:
            continue

        if current_name is None:
            m = DEFINE_RE.match(line)
            if m:
                current_name = m.group("name")
                current_body = []
            continue

        if line == "}":
            functions[current_name] = current_body[:]
            current_name = None
            current_body = []
            continue

        current_body.append(line)

    return functions


def convert_functions_to_opt(
    functions: dict[str, list[str]], src_name: str, tgt_name: str, transform_name: str
) -> str:
    if src_name not in functions:
        raise ValueError(f"source function @{src_name} not found")
    if tgt_name not in functions:
        raise ValueError(f"target function @{tgt_name} not found")

    src_lines = [convert_line(line) for line in functions[src_name]]
    tgt_lines = [convert_line(line) for line in functions[tgt_name]]

    parts = [f"Name: {transform_name}"]
    parts.extend(src_lines)
    parts.append("=>")
    parts.extend(tgt_lines)
    parts.append("")
    return "\n".join(parts)


def convert_functions_to_opt_narrow(
    functions: dict[str, list[str]], src_name: str, tgt_name: str, transform_name: str
) -> str:
    if src_name not in functions:
        raise ValueError(f"source function @{src_name} not found")
    if tgt_name not in functions:
        raise ValueError(f"target function @{tgt_name} not found")

    src_lines = [convert_line_narrow(line) for line in functions[src_name]]
    tgt_lines = [convert_line_narrow(line) for line in functions[tgt_name]]

    parts = [f"Name: {transform_name}"]
    parts.extend(src_lines)
    parts.append("=>")
    parts.extend(tgt_lines)
    parts.append("")
    return "\n".join(parts)


def run_alive(
    alive_bin: pathlib.Path, opt_path: pathlib.Path, root_only: bool
) -> subprocess.CompletedProcess[str]:
    cmd = [str(alive_bin)]
    if root_only:
        cmd.append("-root-only")
    cmd.append(str(opt_path))
    return subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        check=False,
    )


def run_alive_tv(
    alive_tv_bin: pathlib.Path,
    ll_path: pathlib.Path,
    timeout_seconds: float | None = None,
) -> subprocess.CompletedProcess[str]:
    cmd = [str(alive_tv_bin), "--smt-to=50000", str(ll_path)]
    return subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout_seconds,
    )


def verification_passed(result: subprocess.CompletedProcess[str]) -> bool:
    return (
        result.returncode == 0
        and "Transformation seems to be correct!" in result.stdout
        and "WARNING: Source function is always UB." not in result.stdout
    )


def extract_integer_literals(ir: str) -> list[int]:
    return [int(m.group(0)) for m in INT_LITERAL_RE.finditer(ir)]


def has_only_safe_integer_literals(ir: str) -> tuple[bool, list[int]]:
    literals = extract_integer_literals(ir)
    unique = sorted(set(literals))
    return set(unique).issubset(SAFE_INTEGER_LITERALS), unique


def extract_normalized_numeric_constants(ir: str) -> list[int | str]:
    spans: list[tuple[int, int]] = []
    values: list[int | str] = []

    for match in FLOAT_LITERAL_RE.finditer(ir):
        token = match.group(0)
        spans.append(match.span())
        try:
            value = Decimal(token)
        except InvalidOperation:
            values.append(token)
            continue

        if value == value.to_integral_value():
            values.append(int(value))
        else:
            values.append(token)

    for match in INT_LITERAL_RE.finditer(ir):
        start, end = match.span()
        if any(start < other_end and other_start < end for other_start, other_end in spans):
            continue
        values.append(int(match.group(0)))

    return values


def shortcut_independent_result(ir: str, kind: str) -> dict[str, Any] | None:
    if SHORTCUT_BLOCKED_CAST_RE.search(ir):
        return None

    constants = extract_normalized_numeric_constants(ir)
    normalized_constants: list[int] = []
    for value in constants:
        if not isinstance(value, int):
            return None
        normalized_constants.append(value)
        if value not in SAFE_INTEGER_LITERALS:
            return None

    return {
        "status": "bitwidth independent",
        "independent": True,
        "kind": kind,
        "reason": "safe_constants_shortcut",
        "success_types": ["shortcut"],
        "failed_types": [],
        "integer_literals": sorted(set(normalized_constants)),
        "error": None,
    }


def contains_floating_point_ir(ir: str) -> bool:
    return bool(
        re.search(r"\b(?:half|float|double)\b", ir)
        or re.search(
            r"\b(?:fcmp|fadd|fsub|fmul|fdiv|frem|fneg|fpext|fptrunc|sitofp|uitofp|fptosi|fptoui)\b",
            ir,
        )
        or re.search(r"@llvm\.(?:fabs|maxnum|minnum|maximum|minimum)\.", ir)
    )


def instantiate_floating_variant(ir: str, target_fp: str) -> str:
    if target_fp not in FLOAT_TYPES:
        raise ValueError(f"unsupported floating-point target type: {target_fp}")

    target_bits = FLOAT_INT_BITS[target_fp]
    target_suffix = FLOAT_SUFFIXES[target_fp]
    target_mask = FLOAT_SIGN_CLEAR_MASK[target_fp]

    text = re.sub(r"\b(?:half|float|double)\b", target_fp, ir)
    text = FLOAT_INTRINSIC_RE.sub(
        lambda m: f"@llvm.{m.group('name')}.{target_suffix}",
        text,
    )

    rewritten_lines: list[str] = []
    tracked_int_vars: set[str] = set()

    for raw_line in text.splitlines():
        line = raw_line

        line = re.sub(
            rf"\bbitcast\s+{target_fp}\s+(.+?)\s+to\s+i\d+\b",
            rf"bitcast {target_fp} \1 to i{target_bits}",
            line,
        )
        line = re.sub(
            rf"\bbitcast\s+i\d+\s+(.+?)\s+to\s+{target_fp}\b",
            rf"bitcast i{target_bits} \1 to {target_fp}",
            line,
        )
        line = re.sub(
            r"\band\s+i(?:16|32|64)\s+(%[-a-zA-Z$._0-9]+),\s+"
            r"(?:32767|2147483647|9223372036854775807)\b",
            rf"and i{target_bits} \1, {target_mask}",
            line,
        )

        stripped = strip_comment(line)
        bitcast_to_int = re.match(
            rf"^(?P<lhs>%[-a-zA-Z$._0-9]+)\s*=\s*bitcast\s+{target_fp}\s+.+?\s+to\s+i{target_bits}\s*$",
            stripped,
        )
        if bitcast_to_int:
            tracked_int_vars.add(bitcast_to_int.group("lhs"))

        for var in tuple(tracked_int_vars):
            line = re.sub(
                rf"\bi\d+\s+{re.escape(var)}\b",
                f"i{target_bits} {var}",
                line,
            )

        if any(var in line for var in tracked_int_vars):
            line = re.sub(
                r"^(?P<lhs>%[-a-zA-Z$._0-9]+\s*=\s*"
                r"(?:add|sub|mul|sdiv|udiv|srem|urem|shl|lshr|ashr|and|or|xor)"
                r"(?:\s+(?:nsw|nuw|exact))?\s+)i\d+\b",
                rf"\g<lhs>i{target_bits}",
                line,
            )
            line = re.sub(
                r"^(?P<lhs>%[-a-zA-Z$._0-9]+\s*=\s*icmp(?:\s+[A-Za-z]+)*\s+[a-z]+\s+)i\d+\b",
                rf"\g<lhs>i{target_bits}",
                line,
            )
            line = re.sub(
                r"^(?P<lhs>%[-a-zA-Z$._0-9]+\s*=\s*select(?:\s+[A-Za-z]+)*\s+\S+\s+[^,]+,\s+)i\d+\b",
                rf"\g<lhs>i{target_bits}",
                line,
            )
            line = re.sub(
                r"(?<=,\s)i\d+\b(?=\s+[^,]+,\s*i\d+\s+)",
                f"i{target_bits}",
                line,
                count=1,
            )

            stripped = strip_comment(line)
            tracked_def = re.match(
                r"^(?P<lhs>%[-a-zA-Z$._0-9]+)\s*=\s*"
                r"(?:add|sub|mul|sdiv|udiv|srem|urem|shl|lshr|ashr|and|or|xor)"
                rf"(?:\s+(?:nsw|nuw|exact))?\s+i{target_bits}\b",
                stripped,
            )
            if tracked_def:
                tracked_int_vars.add(tracked_def.group("lhs"))

        same_conv = re.match(
            rf"^(?P<lhs>%[-a-zA-Z$._0-9]+)\s*=\s*"
            rf"(?P<op>fpext|fptrunc)\s+{target_fp}\s+(?P<val>.+?)\s+to\s+{target_fp}\s*$",
            strip_comment(line),
        )
        if same_conv:
            line = (
                f"{same_conv.group('lhs')} = select i1 true, "
                f"{target_fp} {same_conv.group('val')}, "
                f"{target_fp} {same_conv.group('val')}"
            )

        rewritten_lines.append(line)

    return "\n".join(rewritten_lines)


def analyze_integer_ir(
    ir: str,
    alive_bin: pathlib.Path,
    root_only: bool,
    src_name: str,
    tgt_name: str,
    transform_name: str,
) -> dict[str, Any]:
    _, literals = has_only_safe_integer_literals(ir)

    try:
        functions = extract_functions(ir)
        opt_text = convert_functions_to_opt_narrow(
            functions, src_name, tgt_name, transform_name
        )
    except Exception as exc:
        return {
            "status": "not-independent",
            "independent": False,
            "kind": "integer",
            "reason": "narrow_symbolic_width_check_unsupported",
            "success_types": [],
            "failed_types": ["symbolic"],
            "integer_literals": literals,
            "error": str(exc),
        }

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".opt", prefix="alive_symbolic_", delete=False
    ) as tmp_file:
        tmp_file.write(opt_text)
        tmp_path = pathlib.Path(tmp_file.name)

    try:
        result = run_alive(alive_bin, tmp_path, root_only)
    finally:
        tmp_path.unlink(missing_ok=True)

    passed = verification_passed(result)
    return {
        "status": "bitwidth independent" if passed else "not-independent",
        "independent": passed,
        "kind": "integer",
        "reason": (
            "narrow_symbolic_width_check"
            if passed
            else "narrow_symbolic_width_check_failed"
        ),
        "success_types": ["symbolic"] if passed else [],
        "failed_types": [] if passed else ["symbolic"],
        "integer_literals": literals,
        "error": (result.stderr or result.stdout).strip() if not passed else None,
    }


def analyze_floating_ir(ir: str, alive_tv_bin: pathlib.Path) -> dict[str, Any]:
    success_types: list[str] = []
    failed_types: list[str] = []
    failure_messages: list[str] = []

    for fp_type in FLOAT_TYPES:
        variant_ir = instantiate_floating_variant(ir, fp_type)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".ll", prefix=f"alive_fp_{fp_type}_", delete=False
        ) as tmp_file:
            tmp_file.write(variant_ir)
            tmp_path = pathlib.Path(tmp_file.name)

        try:
            result = run_alive_tv(alive_tv_bin, tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)

        if verification_passed(result):
            success_types.append(fp_type)
        else:
            failed_types.append(fp_type)
            message = (result.stderr or result.stdout).strip()
            if message:
                failure_messages.append(f"{fp_type}: {message}")

    independent = len(success_types) > 0 and len(failed_types) == 0
    return {
        "status": "bitwidth independent" if independent else "not-independent",
        "independent": independent,
        "kind": "floating_point",
        "reason": (
            "all_floating_variants_verified"
            if independent
            else "floating_variant_verification_failed"
        ),
        "success_types": success_types,
        "failed_types": failed_types,
        "integer_literals": [],
        "error": "\n\n".join(failure_messages) if failure_messages else None,
    }


def analyze_ir(
    ir: str,
    alive_bin: pathlib.Path,
    alive_tv_bin: pathlib.Path,
    root_only: bool,
    src_name: str,
    tgt_name: str,
    transform_name: str,
) -> dict[str, Any]:
    kind = "floating_point" if contains_floating_point_ir(ir) else "integer"
    shortcut = shortcut_independent_result(ir, kind)
    if shortcut is not None:
        return shortcut

    if kind == "floating_point":
        return analyze_floating_ir(ir, alive_tv_bin)
    return analyze_integer_ir(
        ir=ir,
        alive_bin=alive_bin,
        root_only=root_only,
        src_name=src_name,
        tgt_name=tgt_name,
        transform_name=transform_name,
    )


def analyze_processed_testcases(
    json_input: pathlib.Path,
    json_output: pathlib.Path,
    ir_field: str,
    alive_bin: pathlib.Path,
    alive_tv_bin: pathlib.Path,
    root_only: bool,
    src_name: str,
    tgt_name: str,
) -> int:
    data = json.loads(json_input.read_text())
    if not isinstance(data, list):
        raise ValueError("processed testcase JSON must be a list")

    for index, entry in enumerate(data):
        if not isinstance(entry, dict):
            continue

        ir = entry.get(ir_field)
        if not isinstance(ir, str) or not ir.strip():
            entry["auto_bitwidth_status"] = "not-independent"
            entry["auto_bitwidth_independent"] = False
            entry["auto_bitwidth_kind"] = None
            entry["auto_bitwidth_reason"] = "missing_ir"
            entry["auto_bitwidth_success_types"] = []
            entry["auto_bitwidth_failed_types"] = []
            entry["auto_bitwidth_integer_literals"] = []
            entry["auto_bitwidth_error"] = None
            continue

        filename = entry.get("filename") or f"case_{index}"
        transform_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(filename))
        result = analyze_ir(
            ir=ir,
            alive_bin=alive_bin,
            alive_tv_bin=alive_tv_bin,
            root_only=root_only,
            src_name=src_name,
            tgt_name=tgt_name,
            transform_name=transform_name,
        )
        entry["auto_bitwidth_status"] = result["status"]
        entry["auto_bitwidth_independent"] = result["independent"]
        entry["auto_bitwidth_kind"] = result["kind"]
        entry["auto_bitwidth_reason"] = result["reason"]
        entry["auto_bitwidth_success_types"] = result["success_types"]
        entry["auto_bitwidth_failed_types"] = result["failed_types"]
        entry["auto_bitwidth_integer_literals"] = result["integer_literals"]
        entry["auto_bitwidth_error"] = result["error"]

    json_output.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"Wrote {json_output}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Convert a restricted LLVM IR src/tgt example into Alive .opt syntax, "
            "optionally run Alive2, or analyze processed testcase JSON files."
        )
    )
    parser.add_argument(
        "input",
        nargs="?",
        type=pathlib.Path,
        help="input LLVM IR file",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=pathlib.Path,
        help="output .opt path (default: <input>.opt)",
    )
    parser.add_argument("--src-name", default="src", help="source function name")
    parser.add_argument("--tgt-name", default="tgt", help="target function name")
    parser.add_argument(
        "--name",
        default=None,
        help="Alive transform name (default: <src>_to_<tgt>)",
    )
    parser.add_argument(
        "--alive-bin",
        type=pathlib.Path,
        default=pathlib.Path(
            ALIVE_PATH
        ),
        help="Alive2 Alive-language CLI binary",
    )
    parser.add_argument(
        "--alive-tv-bin",
        type=pathlib.Path,
        default=pathlib.Path(ALIVE2_PATH),
        help="Alive2 translation-validation binary",
    )
    parser.add_argument(
        "--run-alive",
        action="store_true",
        help="run Alive2 on the generated .opt file",
    )
    parser.add_argument(
        "--no-root-only",
        dest="root_only",
        action="store_false",
        help="when running Alive2, check all SSA values instead of only the root result",
    )
    parser.add_argument(
        "--json-input",
        type=pathlib.Path,
        help="processed testcase JSON file to analyze",
    )
    parser.add_argument(
        "--json-output",
        type=pathlib.Path,
        help="output JSON path for analyzed processed testcases",
    )
    parser.add_argument(
        "--json-ir-field",
        default="final_result_without_bitwidth_generalization",
        help="JSON field that contains the src/tgt LLVM IR text",
    )
    parser.set_defaults(root_only=True)
    args = parser.parse_args()

    if args.json_input is not None:
        if args.input is not None:
            parser.error("positional input cannot be used together with --json-input")
        json_output = args.json_output
        if json_output is None:
            json_output = args.json_input.with_name(
                f"{args.json_input.stem}.auto_bitwidth.json"
            )
        return analyze_processed_testcases(
            json_input=args.json_input,
            json_output=json_output,
            ir_field=args.json_ir_field,
            alive_bin=args.alive_bin,
            alive_tv_bin=args.alive_tv_bin,
            root_only=args.root_only,
            src_name=args.src_name,
            tgt_name=args.tgt_name,
        )

    if args.input is None:
        parser.error("either an input LLVM IR file or --json-input is required")

    output = args.output
    if output is None:
        output = args.input.with_suffix(".opt")

    transform_name = args.name or f"{args.src_name}_to_{args.tgt_name}"

    text = args.input.read_text()
    functions = extract_functions(text)
    opt_text = convert_functions_to_opt(
        functions, args.src_name, args.tgt_name, transform_name
    )
    output.write_text(opt_text)
    print(f"Wrote {output}")

    if not args.run_alive:
        return 0

    result = run_alive(args.alive_bin, output, args.root_only)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
