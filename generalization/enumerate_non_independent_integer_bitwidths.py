#!/usr/bin/env python3

from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import time
from typing import TYPE_CHECKING, Any

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALIVE2_PATH = os.path.join(REPO_ROOT, "third_party", "alive2", "build", "alive-tv")

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from generalization.llvm_ir_to_alive_opt import (
    convert_functions_to_opt,
    convert_functions_to_opt_narrow,
    extract_functions,
    run_alive_tv,
    verification_passed,
)
from generalization.utils import preprocess_llm_response

if TYPE_CHECKING:
    from google import genai


INT_TYPE_TOKEN_PATTERN = re.compile(r"(?<![A-Za-z0-9_%.@])i(\d+)\b")
BITWIDTH_DEF_PATTERN = re.compile(
    r"(^\s*%bitwidth[^\s=]*\s*=\s*add\s+i\d+\s+)(\d+)(\s*,\s*0\s*$)",
    re.MULTILINE,
)
JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)
DEFAULT_MAX_ISSUE_SECONDS = 2 * 60 * 60


def load_json(path: pathlib.Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: pathlib.Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=path.suffix,
        prefix=f"{path.stem}.tmp_",
        dir=path.parent,
        delete=False,
        encoding="utf-8",
    ) as tmp_file:
        tmp_file.write(json.dumps(data, ensure_ascii=False, indent=2))
        tmp_path = pathlib.Path(tmp_file.name)

    tmp_path.replace(path)


def format_progress_bar(completed: int, total: int, width: int = 24) -> str:
    if total <= 0:
        return "[" + ("-" * width) + "]"

    filled = min(width, int(width * completed / total))
    return "[" + ("#" * filled) + ("." * (width - filled)) + "]"


def format_assignment_summary(assignment: dict[str, int]) -> str:
    parts = [f"{var}={value}" for var, value in sorted(assignment.items())]
    return "{" + ", ".join(parts) + "}"


def format_duration(seconds: float) -> str:
    rounded = max(0, int(round(seconds)))
    minutes, secs = divmod(rounded, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h{minutes:02d}m{secs:02d}s"
    if minutes:
        return f"{minutes}m{secs:02d}s"
    return f"{secs}s"


def normalize_command_output(output: str | bytes | None) -> str | None:
    if output is None:
        return None
    if isinstance(output, bytes):
        output = output.decode("utf-8", errors="replace")
    normalized = output.strip()
    return normalized or None


def summarize_verification_status(verification: dict[str, Any]) -> str:
    if verification.get("skipped_due_to_prior_timeout", False):
        return "skipped_timeout"
    if verification.get("issue_timeout_reached", False):
        return "issue_timeout"
    if verification["verified"]:
        return "verified"
    if verification["timed_out"]:
        return "timed_out"
    return "failed"


def iter_distinct_non_i1_integer_widths(ir: str) -> list[int]:
    widths: list[int] = []
    seen: set[int] = set()
    for match in INT_TYPE_TOKEN_PATTERN.finditer(ir):
        width = int(match.group(1))
        if width <= 1 or width in seen:
            continue
        seen.add(width)
        widths.append(width)
    return widths


def build_width_variable_map(ir: str) -> dict[int, str]:
    widths = sorted(iter_distinct_non_i1_integer_widths(ir))
    return {width: f"W{index}" for index, width in enumerate(widths, start=1)}


def build_placeholder_template(ir: str, width_var_map: dict[int, str]) -> str:
    def replace_bitwidth_constant(match: re.Match[str]) -> str:
        width = int(match.group(2))
        var = width_var_map.get(width)
        if var is None:
            return match.group(0)
        return f"{match.group(1)}__CONST_{var}__{match.group(3)}"

    templated = BITWIDTH_DEF_PATTERN.sub(replace_bitwidth_constant, ir)

    def replace_type(match: re.Match[str]) -> str:
        width = int(match.group(1))
        if width <= 1:
            return match.group(0)
        var = width_var_map.get(width)
        if var is None:
            return match.group(0)
        return f"__TYPE_{var}__"

    return INT_TYPE_TOKEN_PATTERN.sub(replace_type, templated)


def instantiate_template(template: str, assignment: dict[str, int]) -> str:
    instantiated = template
    for var, width in assignment.items():
        instantiated = instantiated.replace(f"__TYPE_{var}__", f"i{width}")
        instantiated = instantiated.replace(f"__CONST_{var}__", str(width))
    return instantiated


def build_symbolic_alive_opt(
    ir: str,
    src_name: str,
    tgt_name: str,
    transform_name: str,
) -> tuple[str | None, str | None]:
    try:
        functions = extract_functions(ir)
        return (
            convert_functions_to_opt(functions, src_name, tgt_name, transform_name),
            None,
        )
    except Exception as exc:
        return None, str(exc)


def build_symbolic_alive_opt_narrow(
    ir: str,
    src_name: str,
    tgt_name: str,
    transform_name: str,
) -> tuple[str | None, str | None]:
    try:
        functions = extract_functions(ir)
        return (
            convert_functions_to_opt_narrow(
                functions, src_name, tgt_name, transform_name
            ),
            None,
        )
    except Exception as exc:
        return None, str(exc)


def normalize_llm_json_response(text: str) -> dict[str, Any]:
    cleaned = (text or "").strip()
    if not cleaned:
        raise ValueError("empty_llm_response")

    cleaned = preprocess_llm_response(cleaned).strip()
    match = JSON_OBJECT_RE.search(cleaned)
    if not match:
        raise ValueError("llm_response_does_not_contain_json")

    parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("llm_response_json_is_not_object")
    return parsed


def normalize_assignments(
    parsed: dict[str, Any],
    width_var_map: dict[int, str],
) -> tuple[list[dict[str, int]], list[str]]:
    expected_vars = list(width_var_map.values())
    raw_assignments = parsed.get("assignments_le_64", [])
    warnings: list[str] = []
    normalized: list[dict[str, int]] = []
    seen: set[tuple[tuple[str, int], ...]] = set()

    if not isinstance(raw_assignments, list):
        warnings.append("assignments_le_64_is_not_a_list")
        return normalized, warnings

    for index, entry in enumerate(raw_assignments, start=1):
        if not isinstance(entry, dict):
            warnings.append(f"assignment_{index}_is_not_object")
            continue

        assignment: dict[str, int] = {}
        invalid = False
        for var in expected_vars:
            value = entry.get(var)
            if not isinstance(value, int):
                warnings.append(f"assignment_{index}_missing_or_invalid_{var}")
                invalid = True
                break
            if value <= 1 or value > 64:
                warnings.append(f"assignment_{index}_{var}_out_of_range")
                invalid = True
                break
            assignment[var] = value

        if invalid:
            continue

        key = tuple(sorted(assignment.items()))
        if key in seen:
            continue
        seen.add(key)
        normalized.append(assignment)

    normalized.sort(key=lambda item: tuple(item[var] for var in expected_vars))
    return normalized, warnings


def verify_assignment(
    ir: str,
    alive_tv_bin: pathlib.Path,
    timeout_seconds: float | None = None,
) -> dict[str, Any]:
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".ll", prefix="alive_enum_", delete=False
    ) as tmp_file:
        tmp_file.write(ir)
        tmp_path = pathlib.Path(tmp_file.name)

    try:
        try:
            result = run_alive_tv(
                alive_tv_bin,
                tmp_path,
                timeout_seconds=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            return {
                "verified": False,
                "stdout": normalize_command_output(exc.stdout),
                "stderr": normalize_command_output(exc.stderr),
                "timed_out": True,
                "issue_timeout_reached": True,
                "timeout_reason": (
                    "Stopped this issue after exhausting its remaining wall-clock "
                    "budget."
                ),
            }
    finally:
        tmp_path.unlink(missing_ok=True)

    passed = verification_passed(result)
    combined_output = "\n".join(
        part for part in [result.stdout.strip(), result.stderr.strip()] if part
    )
    timed_out = "ERROR: Timeout" in combined_output or "timeout" in combined_output.lower()
    return {
        "verified": passed,
        "stdout": result.stdout.strip() or None,
        "stderr": result.stderr.strip() or None,
        "timed_out": timed_out,
    }


def build_skipped_timeout_result(
    assignment: dict[str, int],
    timed_out_var: str,
    timed_out_value: int,
) -> dict[str, Any]:
    return {
        "verified": False,
        "stdout": None,
        "stderr": None,
        "timed_out": True,
        "skipped_due_to_prior_timeout": True,
        "timeout_cutoff": {
            "variable": timed_out_var,
            "value": timed_out_value,
        },
        "timeout_reason": (
            f"Skipped because prior {timed_out_var}={timed_out_value} timed out, "
            f"so larger {timed_out_var} values were marked timeout without re-running Alive2."
        ),
    }


def load_gemini_client(config_path: pathlib.Path | None) -> "genai.Client":
    try:
        from google import genai
    except ImportError as exc:
        raise ImportError(
            "google.genai is not installed; install the dependency before using Gemini-backed mode"
        ) from exc

    api_key = (os.environ.get("GEMINI_API_KEY") or "").strip()
    if not api_key and config_path is not None and config_path.exists():
        config = load_json(config_path)
        if isinstance(config, dict):
            api_key = str(config.get("GEMINI_API_KEY") or "").strip()

    if not api_key:
        raise ValueError(
            "missing Gemini API key; set GEMINI_API_KEY or provide --config with GEMINI_API_KEY"
        )

    return genai.Client(api_key=api_key)


def llm_query_valid_integer_bitwidths(
    client: "genai.Client",
    model: str,
    ir: str,
    symbolic_alive_opt: str | None,
    placeholder_template: str,
    width_var_map: dict[int, str],
) -> tuple[str, str]:
    width_descriptions = [
        {
            "variable": var,
            "original_width": width,
            "meaning": f"All original i{width} integer type tokens in the LLVM IR.",
        }
        for width, var in width_var_map.items()
    ]

    prompt = f"""You are analyzing an integer-typed LLVM IR optimization that is NOT fully bitwidth-independent.

Task:
1. Infer width relations under which the optimization is valid.
2. Enumerate all concrete assignments with width <= 64 that you judge likely valid.
3. Be conservative: only include assignments if you believe the optimization should verify.

Notes:
- Width variables refer to the following original width families:
{json.dumps(width_descriptions, ensure_ascii=False, indent=2)}
- The placeholder template replaces integer type tokens with markers like __TYPE_W1__ and matching bitwidth-definition constants with __CONST_W1__.
- If the rule appears valid for infinitely many widths, still only enumerate concrete assignments up to 64.
- Do not invent new width variables.
- Every listed assignment must include every width variable exactly once.
- Widths must be integers in [2, 64].

Original LLVM IR:
{ir}

Bitwidth-erased Alive representation:
{symbolic_alive_opt or "UNAVAILABLE"}

Instantiation template:
{placeholder_template}

Output strict JSON only:
{{
  "summary": "short summary",
  "rule": "natural-language width condition",
  "assignments_le_64": [
    {{"W1": 8, "W2": 16}}
  ]
}}
"""

    response = client.models.generate_content(model=model, contents=prompt)
    return prompt, response.text or ""


def filter_target_entries(data: Any, ir_field: str) -> list[dict[str, Any]]:
    if not isinstance(data, list):
        raise ValueError("input JSON must be a list")

    filtered: list[dict[str, Any]] = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        if entry.get(ir_field) is None:
            continue
        if entry.get("auto_bitwidth_status") != "not-independent":
            continue
        if entry.get("auto_bitwidth_kind") != "integer":
            continue
        filtered.append(entry)
    return filtered


def enrich_entry(
    entry: dict[str, Any],
    ir_field: str,
    src_name: str,
    tgt_name: str,
    alive_tv_bin: pathlib.Path,
    client: "genai.Client | None",
    model: str,
    dry_run: bool,
    issue_index: int | None = None,
    issue_total: int | None = None,
    max_issue_seconds: float = DEFAULT_MAX_ISSUE_SECONDS,
) -> dict[str, Any]:
    result = dict(entry)
    ir = str(entry[ir_field])
    filename = str(entry.get("filename") or "unknown_case")
    transform_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", filename)
    if issue_index is not None and issue_total is not None:
        issue_label = f"[{issue_index}/{issue_total}] {filename}"
    else:
        issue_label = filename
    issue_start_time = time.monotonic()

    width_var_map = build_width_variable_map(ir)
    placeholder_template = build_placeholder_template(ir, width_var_map)
    symbolic_alive_opt, symbolic_alive_opt_error = build_symbolic_alive_opt(
        ir, src_name, tgt_name, transform_name
    )
    narrow_alive_opt, narrow_alive_opt_error = build_symbolic_alive_opt_narrow(
        ir, src_name, tgt_name, transform_name
    )

    result["llm_integer_bitwidth_width_variables"] = [
        {"original_width": width, "variable": var}
        for width, var in width_var_map.items()
    ]
    result["llm_integer_bitwidth_placeholder_template"] = placeholder_template
    result["llm_integer_bitwidth_symbolic_alive_opt"] = symbolic_alive_opt
    result["llm_integer_bitwidth_symbolic_alive_opt_error"] = symbolic_alive_opt_error
    result["llm_integer_bitwidth_narrow_alive_opt"] = narrow_alive_opt
    result["llm_integer_bitwidth_narrow_alive_opt_error"] = narrow_alive_opt_error

    if dry_run:
        result["llm_integer_bitwidth_prompt"] = None
        result["llm_integer_bitwidth_raw_response"] = None
        result["llm_integer_bitwidth_parsed"] = None
        result["llm_integer_bitwidth_assignment_warnings"] = ["dry_run"]
        result["llm_integer_bitwidth_candidate_assignments_le_64"] = []
        result["llm_integer_bitwidth_verified_assignments"] = []
        result["llm_integer_bitwidth_failed_assignments"] = []
        result["llm_integer_bitwidth_assignments_total"] = 0
        result["llm_integer_bitwidth_assignments_completed"] = 0
        result["llm_integer_bitwidth_issue_timeout_seconds"] = max_issue_seconds
        result["llm_integer_bitwidth_issue_timeout_reached"] = False
        result["llm_integer_bitwidth_issue_timeout_unprocessed_assignments"] = []
        return result

    if client is None:
        raise ValueError("Gemini client is required unless --dry-run is used")

    prompt, raw_response = llm_query_valid_integer_bitwidths(
        client=client,
        model=model,
        ir=ir,
        symbolic_alive_opt=symbolic_alive_opt,
        placeholder_template=placeholder_template,
        width_var_map=width_var_map,
    )

    assignment_warnings: list[str] = []
    try:
        parsed = normalize_llm_json_response(raw_response)
        assignments, assignment_warnings = normalize_assignments(
            parsed, width_var_map
        )
    except Exception as exc:
        parsed = {
            "summary": None,
            "rule": None,
            "assignments_le_64": [],
            "parse_error": str(exc),
        }
        assignments = []

    verified_assignments: list[dict[str, Any]] = []
    failed_assignments: list[dict[str, Any]] = []
    single_width_var = list(width_var_map.values())[0] if len(width_var_map) == 1 else None
    timeout_cutoff_value: int | None = None
    total_assignments = len(assignments)
    issue_timeout_reached = False
    issue_timeout_unprocessed_assignments: list[dict[str, int]] = []
    print(
        f"{issue_label} assignments {format_progress_bar(0, total_assignments)} "
        f"0/{total_assignments} completed; remaining {total_assignments}; "
        f"budget {format_duration(max_issue_seconds)}",
        file=sys.stderr,
    )

    for assignment_index, assignment in enumerate(assignments, start=1):
        elapsed_before_assignment = time.monotonic() - issue_start_time
        remaining_issue_seconds = max_issue_seconds - elapsed_before_assignment
        if remaining_issue_seconds <= 0:
            issue_timeout_reached = True
            issue_timeout_unprocessed_assignments = assignments[assignment_index - 1 :]
            completed_so_far = len(verified_assignments) + len(failed_assignments)
            print(
                f"{issue_label} assignments "
                f"{format_progress_bar(completed_so_far, total_assignments)} "
                f"{completed_so_far}/{total_assignments} completed; "
                f"issue budget exhausted after {format_duration(elapsed_before_assignment)}; "
                f"moving to next issue with "
                f"{len(issue_timeout_unprocessed_assignments)} assignments unprocessed",
                file=sys.stderr,
            )
            break

        completed_before = assignment_index - 1
        remaining_after_current = total_assignments - assignment_index
        print(
            f"{issue_label} assignments "
            f"{format_progress_bar(completed_before, total_assignments)} "
            f"{completed_before}/{total_assignments} completed; "
            f"running {assignment_index}/{total_assignments} "
            f"{format_assignment_summary(assignment)}; "
            f"remaining after current {remaining_after_current}",
            file=sys.stderr,
        )
        instantiated_ir = instantiate_template(placeholder_template, assignment)
        if (
            single_width_var is not None
            and timeout_cutoff_value is not None
            and assignment[single_width_var] > timeout_cutoff_value
        ):
            verification = build_skipped_timeout_result(
                assignment=assignment,
                timed_out_var=single_width_var,
                timed_out_value=timeout_cutoff_value,
            )
        else:
            verification = verify_assignment(
                instantiated_ir,
                alive_tv_bin,
                timeout_seconds=remaining_issue_seconds,
            )
            if (
                single_width_var is not None
                and verification["timed_out"]
                and not verification.get("issue_timeout_reached", False)
                and timeout_cutoff_value is None
            ):
                timeout_cutoff_value = assignment[single_width_var]

        payload = {
            "assignment": assignment,
            "instantiated_ir": instantiated_ir,
            "verified": verification["verified"],
            "stdout": verification["stdout"],
            "stderr": verification["stderr"],
            "timed_out": verification["timed_out"],
            "issue_timeout_reached": verification.get("issue_timeout_reached", False),
            "skipped_due_to_prior_timeout": verification.get(
                "skipped_due_to_prior_timeout", False
            ),
            "timeout_cutoff": verification.get("timeout_cutoff"),
            "timeout_reason": verification.get("timeout_reason"),
        }
        if verification["verified"]:
            verified_assignments.append(payload)
        else:
            failed_assignments.append(payload)

        completed_after = assignment_index
        remaining = total_assignments - completed_after
        elapsed = time.monotonic() - issue_start_time
        eta = (elapsed / completed_after) * remaining if completed_after else 0.0
        print(
            f"{issue_label} assignments "
            f"{format_progress_bar(completed_after, total_assignments)} "
            f"{completed_after}/{total_assignments} completed; "
            f"last={format_assignment_summary(assignment)} "
            f"status={summarize_verification_status(verification)}; "
            f"remaining {remaining}; eta~{format_duration(eta)}",
            file=sys.stderr,
        )

        if verification.get("issue_timeout_reached", False):
            issue_timeout_reached = True
            issue_timeout_unprocessed_assignments = assignments[assignment_index:]
            print(
                f"{issue_label} assignments "
                f"{format_progress_bar(completed_after, total_assignments)} "
                f"{completed_after}/{total_assignments} completed; "
                f"issue budget exhausted while running "
                f"{format_assignment_summary(assignment)}; moving to next issue with "
                f"{len(issue_timeout_unprocessed_assignments)} assignments unprocessed",
                file=sys.stderr,
            )
            break

    result["llm_integer_bitwidth_prompt"] = prompt
    result["llm_integer_bitwidth_raw_response"] = raw_response
    result["llm_integer_bitwidth_parsed"] = parsed
    result["llm_integer_bitwidth_assignment_warnings"] = assignment_warnings
    result["llm_integer_bitwidth_candidate_assignments_le_64"] = assignments
    result["llm_integer_bitwidth_verified_assignments"] = verified_assignments
    result["llm_integer_bitwidth_failed_assignments"] = failed_assignments
    result["llm_integer_bitwidth_assignments_total"] = total_assignments
    result["llm_integer_bitwidth_assignments_completed"] = (
        len(verified_assignments) + len(failed_assignments)
    )
    result["llm_integer_bitwidth_issue_timeout_seconds"] = max_issue_seconds
    result["llm_integer_bitwidth_issue_timeout_reached"] = issue_timeout_reached
    result["llm_integer_bitwidth_issue_timeout_unprocessed_assignments"] = (
        issue_timeout_unprocessed_assignments
    )
    return result


def default_config_path() -> pathlib.Path:
    return pathlib.Path(REPO_ROOT) / "config" / "gemini_config.json"


def default_output_path(json_input: pathlib.Path) -> pathlib.Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return json_input.with_name(
        f"{json_input.stem}.llm_integer_bitwidth_enumeration.{timestamp}.json"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Filter non-independent integer testcase entries, ask Gemini for valid "
            "bitwidth assignments up to 64, verify them, and write enriched JSON."
        )
    )
    parser.add_argument("--json-input", type=pathlib.Path, required=True)
    parser.add_argument("--json-output", type=pathlib.Path, default=None)
    parser.add_argument(
        "--json-ir-field",
        default="final_result_without_bitwidth_generalization",
    )
    parser.add_argument("--src-name", default="src")
    parser.add_argument("--tgt-name", default="tgt")
    parser.add_argument(
        "--alive-tv-bin",
        type=pathlib.Path,
        default=pathlib.Path(ALIVE2_PATH),
    )
    parser.add_argument("--model", default="gemini-2.5-pro")
    parser.add_argument("--config", type=pathlib.Path, default=default_config_path())
    parser.add_argument(
        "--skip",
        type=int,
        default=0,
        help="skip the first N filtered items before processing",
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--max-issue-seconds",
        type=float,
        default=DEFAULT_MAX_ISSUE_SECONDS,
        help=(
            "maximum wall-clock time to spend on one issue before skipping the "
            "remaining assignments and moving to the next issue"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="skip Gemini calls and Alive2 verification; still emit filtered entries and symbolic templates",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.skip < 0:
        raise ValueError("--skip must be non-negative")
    if args.limit is not None and args.limit < 0:
        raise ValueError("--limit must be non-negative")
    if args.max_issue_seconds <= 0:
        raise ValueError("--max-issue-seconds must be positive")

    input_data = load_json(args.json_input)
    filtered = filter_target_entries(input_data, args.json_ir_field)
    if args.skip:
        filtered = filtered[args.skip :]
    if args.limit is not None:
        filtered = filtered[: args.limit]

    client = None
    if not args.dry_run:
        client = load_gemini_client(args.config)

    output_path = args.json_output
    if output_path is None:
        output_path = default_output_path(args.json_input)

    enriched: list[dict[str, Any]] = []
    for index, entry in enumerate(filtered, start=1):
        filename = entry.get("filename") or f"case_{index}"
        print(
            f"[{index}/{len(filtered)}] processing {filename}",
            file=sys.stderr,
        )
        enriched.append(
            enrich_entry(
                entry=entry,
                ir_field=args.json_ir_field,
                src_name=args.src_name,
                tgt_name=args.tgt_name,
                alive_tv_bin=args.alive_tv_bin,
                client=client,
                model=args.model,
                dry_run=args.dry_run,
                issue_index=index,
                issue_total=len(filtered),
                max_issue_seconds=args.max_issue_seconds,
            )
        )
        save_json(output_path, enriched)
        print(
            f"[{index}/{len(filtered)}] checkpointed {len(enriched)} entries to {output_path}",
            file=sys.stderr,
        )

    save_json(output_path, enriched)
    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
