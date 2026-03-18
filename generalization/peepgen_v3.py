from google import genai
import os
import pathlib
import subprocess
import sys
from datetime import datetime
import json
import re
from llm_query import (
    llm_query_generalize,
    llm_query_with_err,
    llm_query_with_counterexample,
    llm_query_undefined_behavior,
    llm_query_performance_improvement,
)
from further_generalization import further_generalization
from verification_analysis import analyze_verification_result
from verification_types import VerificationResult, reset_verification_state
from generalization.utils import preprocess_llm_response
from verification import verify_and_profile
from generalization.first_generalization import first_generalization

def load_testcases(testcases_folder):
    testcases_input_foler = testcases_folder
    testcases_dict = {}
    for filename in os.listdir(testcases_input_foler):
        file_path = os.path.join(testcases_input_foler, filename)
        with open(file_path, "r", encoding="utf-8") as f:
            data = f.read()
            testcases_dict[filename] = data
    return testcases_dict

# def split_bitwidth_variants(bitwidth_response):
#     """
#     Split LLM bitwidth response by required section header format:
#     ### <TYPE>
#     """
#     section_pat = re.compile(r"(?m)^\s*###\s*([^\n]+?)\s*$")
#     matches = list(section_pat.finditer(bitwidth_response or ""))
#     if not matches:
#         raw = (bitwidth_response or "").strip()
#         return [{"type": "unknown", "raw_section": raw}] if raw else []

#     variants = []
#     for idx, m in enumerate(matches):
#         variant_type = m.group(1).strip()
#         start = m.end()
#         end = matches[idx + 1].start() if idx + 1 < len(matches) else len(bitwidth_response)
#         section_text = bitwidth_response[start:end].strip()
#         variants.append(
#             {
#                 "type": variant_type,
#                 "raw_section": section_text,
#             }
#         )
#     return variants

# def normalize_variant_ir(section_text):

#     normalized = preprocess_llm_response(section_text or "").strip()
#     if not normalized:
#         return None, "empty_section_after_preprocess"
#     if normalized.lower() == "fail":
#         return None, "llm_returned_fail"

#     return normalized, None

def bitwidth_generalization(processed_file):
    if not processed_file:
        print("Skipping bitwidth generalization: empty processed file path.")
        return None

    processed_path = pathlib.Path(processed_file).expanduser().resolve()
    if not processed_path.exists():
        print(f"Skipping bitwidth generalization: processed file not found: {processed_path}")
        return None

    repo_root = pathlib.Path(__file__).resolve().parents[1]
    generalization_dir = repo_root / "generalization"
    llvm_ir_to_alive_opt_script = generalization_dir / "llvm_ir_to_alive_opt.py"
    enumerate_bitwidths_script = (
        generalization_dir / "enumerate_non_independent_integer_bitwidths.py"
    )
    python_executable = sys.executable or "python3"

    auto_bitwidth_path = processed_path.with_name(
        f"{processed_path.stem}.auto_bitwidth.json"
    )
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    enumerated_output_path = auto_bitwidth_path.with_name(
        f"{auto_bitwidth_path.stem}.llm_integer_bitwidth_enumeration.{timestamp}.json"
    )

    commands = [
        (
            "auto bitwidth analysis",
            [
                python_executable,
                str(llvm_ir_to_alive_opt_script),
                "--json-input",
                str(processed_path),
                "--json-output",
                str(auto_bitwidth_path),
            ],
        ),
        (
            "non-independent integer bitwidth enumeration",
            [
                python_executable,
                str(enumerate_bitwidths_script),
                "--json-input",
                str(auto_bitwidth_path),
                "--json-output",
                str(enumerated_output_path),
            ],
        ),
    ]

    for step_name, cmd in commands:
        print(f"Running {step_name}: {' '.join(cmd)}")
        try:
            subprocess.run(
                cmd,
                check=True,
                cwd=repo_root,
            )
        except subprocess.CalledProcessError as exc:
            print(
                f"Bitwidth generalization step failed ({step_name}), exit code: {exc.returncode}"
            )
            return None

    print(f"Bitwidth generalization output: {enumerated_output_path}")
    return str(enumerated_output_path)

def generalize_optimization(testcases_dict, model, prev_processed_path, client, all_outputs_folder, output_folder):

    dirs_created = False
    # list to record processed testcases metadata
    processed_testcases = []
    processed_filenames = set()
    # If prev_processed_path is falsy (None/empty), skip loading previous data.
    if prev_processed_path and os.path.exists(prev_processed_path):
        try:
            with open(prev_processed_path, "r", encoding="utf-8") as pf:
                data = json.load(pf)
                if isinstance(data, list):
                    processed_testcases.extend(data)
                    for e in data:
                        fn = e.get("filename")
                        if fn:
                            performance_success_true = e.get("final_performance_success")
                            if performance_success_true is True:
                                processed_filenames.add(fn)
        except Exception as e:
            print(f"Warning: failed to read previous processed file {prev_processed_path}: {e}")

    def ensure_dirs():
        nonlocal dirs_created
        if not dirs_created:
            os.makedirs(all_outputs_folder, exist_ok=True)
            os.makedirs(output_folder, exist_ok=True)
            dirs_created = True

    def write_alive2_stdout_stderr(output_file, result, err):
        ensure_dirs()
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("=== STDOUT ===\n")
            f.write(result)
            f.write("\n=== STDERR ===\n")
            f.write(err)

    def write_perf_output(output_file, src, tgt, winner, metric):
        ensure_dirs()
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("=== Winner ===\n")
            f.write(str(winner))
            f.write("\n=== PERFORMANCE METRICS ===\n")
            f.write(str(metric))
            f.write("\n=== Source Code Performance ===\n")
            f.write(str(src))
            f.write("\n=== target Code Performance ===\n")
            f.write(str(tgt))

    def run_furgen_and_bitwidth(ir_code, filename, attempt, trigger_reason):
        ensure_dirs()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_output_file = f"{output_folder}/{filename}_{model}_#{attempt}attempt_{timestamp}_furgen_ablation.json"
        txt_output_file = f"{output_folder}/{filename}_{model}_#{attempt}attempt_{timestamp}_alive2_furgen.txt"
        bitwidth_output_file = f"{output_folder}/{filename}_{model}_#{attempt}attempt_{timestamp}_bitwidth_generalization.txt"

        with open(json_output_file, "w", encoding="utf-8") as f:
            json.dump({}, f)
        with open(txt_output_file, "w", encoding="utf-8") as f:
            f.write(f"Ablation Study for {filename}\n")
            f.write(f"Trigger: {trigger_reason}\n\n")

        furgen_results = further_generalization(ir_code, client, model, json_output_file, txt_output_file)
        furgen_output_code = furgen_results.get("final_output_code", ir_code)

        # bitwidth_prompt, bitwidth_response = llm_query_bitwidth_generalization(client, furgen_output_code, model)
        # bitwidth_variants = split_bitwidth_variants(bitwidth_response)
        # bitwidth_variant_results = []
        # success_bitwidth_types = []
        # failed_bitwidth_types = []

        # for idx, variant in enumerate(bitwidth_variants, start=1):
        #     variant_type = variant.get("type", "unknown")
        #     raw_section = variant.get("raw_section", "")
        #     normalized_ir, parse_error = normalize_variant_ir(raw_section)

        #     variant_entry = {
        #         "index": idx,
        #         "type": variant_type,
        #         "parse_error": parse_error,
        #         "alive2_result": None,
        #         "alive2_err": None,
        #         "perf": None,
        #         "perf_winner": None,
        #         "alive2_verified": False,
        #         "perf_tgt_better": False,
        #         "verification_success": False,
        #     }

        #     if parse_error is None and normalized_ir is not None:
        #         result, err, perf = verify_and_profile(normalized_ir)
        #         winner = perf.get("winner") if isinstance(perf, dict) else None
        #         alive2_verified = (
        #             not err
        #             and "Transformation seems to be correct!" in result
        #             and "WARNING: Source function is always UB." not in result
        #         )

        #         verification_success = None
        #         if alive2_verified and winner == "tgt":
        #             verification_success = True
        #             success_bitwidth_types.append(variant_type)
        #         else:
        #             verification_success = False
        #             failed_bitwidth_types.append(variant_type)

        #         variant_entry.update(
        #             {
        #                 "alive2_result": result,
        #                 "alive2_err": err,
        #                 "perf": perf,
        #                 "perf_winner": winner,
        #                 "alive2_verified": alive2_verified,
        #                 "perf_tgt_better": winner == "tgt",
        #                 "verification_success": verification_success,
        #             }
        #         )

        #     bitwidth_variant_results.append(
        #         {
        #             "meta": variant_entry,
        #             "raw_section": raw_section,
        #             "normalized_ir": normalized_ir,
        #         }
        #     )


        # bitwidth_independent = len(success_bitwidth_types) > 0 and len(failed_bitwidth_types) == 0
        # bitwidth_summary = {
        #     "bitwidth_independent": bitwidth_independent,
        #     "success_bitwidth_types": success_bitwidth_types,
        #     "failed_bitwidth_types": failed_bitwidth_types,
        #     "total_variant_count": len(bitwidth_variants),
        # }

        # with open(bitwidth_output_file, "w", encoding="utf-8") as f:
        #     f.write(f"Trigger: {trigger_reason}\n\n")
        #     f.write(f"bitwidth_independent: {bitwidth_independent}\n")
        #     f.write(f"total_variant_count: {len(bitwidth_variants)}\n")
        #     f.write(f"success_bitwidth_types: {success_bitwidth_types}\n")
        #     f.write(f"failed_bitwidth_types: {failed_bitwidth_types}\n\n")
        #     f.write(bitwidth_prompt)
        #     f.write("\n\n=== bitwidth_response ===\n")
        #     f.write(bitwidth_response)
        #     f.write("\n\n=== bitwidth_split_and_verification ===\n")
        #     f.write(f"parsed_variant_count: {len(bitwidth_variants)}\n")
        #     for variant in bitwidth_variant_results:
        #         meta = variant["meta"]
        #         f.write("\n----------------------------------------\n")
        #         f.write(f"variant_index: {meta['index']}\n")
        #         f.write(f"variant_type: {meta['type']}\n")
        #         f.write(f"parse_error: {meta['parse_error']}\n")
        #         f.write(f"alive2_verified: {meta['alive2_verified']}\n")
        #         f.write(f"perf_tgt_better: {meta['perf_tgt_better']}\n")
        #         f.write(f"perf_winner: {meta['perf_winner']}\n")
        #         f.write(f"verification_success: {meta['verification_success']}\n")
        #         f.write("\n=== raw_section ===\n")
        #         f.write(variant["raw_section"] or "")
        #         f.write("\n\n=== normalized_ir ===\n")
        #         f.write(variant["normalized_ir"] or "")
        #         f.write("\n\n=== alive2_result ===\n")
        #         f.write(meta["alive2_result"] or "")
        #         f.write("\n\n=== alive2_err ===\n")
        #         f.write(meta["alive2_err"] or "")
        #         f.write("\n\n=== perf ===\n")
        #         f.write(json.dumps(meta["perf"], ensure_ascii=False, indent=2, default=str))
        #         f.write("\n")

        # return furgen_results, furgen_output_code, bitwidth_summary
        return furgen_results, furgen_output_code

    for filename, testcase in testcases_dict.items():
        raw_name = filename.split('.')[0]
        if raw_name in processed_filenames:
            print(f"Skipping already-processed testcase: {raw_name}")
            continue
        filename = raw_name
        attempt = 0
        max_attempt = 3

        last_err = None

        verification_result = reset_verification_state('init')
        verification_perf_succ = None

        initial_prompt = None
        prompt = None
        last_pre_processed = None
        cte = None
        final_result = None
        first_successful_result = None
        first_successful_attempt = None
        furgen_executed = False
        # bitwidth_executed = False
        furgen_trigger_reason = None
        # bitwidth_independent = False
        # bitwidth_success_types = []
        # bitwidth_failed_types = []
        # bitwidth_total_variant_count = 0

        while attempt < max_attempt:
            attempt += 1
            prompt = None
            print(f"=========Processing {filename}, Attempt {attempt}=========")

            if verification_result == VerificationResult.VERIFIED_SUCCESS:
                if verification_perf_succ:
                    furgen_input = last_pre_processed if last_pre_processed is not None else first_successful_result
                    if furgen_input is not None:
                        furgen_trigger_reason = "in_loop_after_alive2_and_mca_success"
                        # _, furgen_output_code, bitwidth_summary = run_furgen_and_bitwidth(
                        #     furgen_input, filename, attempt, furgen_trigger_reason
                        # )
                        _, furgen_output_code = run_furgen_and_bitwidth(
                            furgen_input, filename, attempt, furgen_trigger_reason
                        )
                        furgen_executed = True
                        # bitwidth_executed = True
                        # bitwidth_independent = bitwidth_summary.get("bitwidth_independent", False)
                        # bitwidth_success_types = bitwidth_summary.get("success_bitwidth_types", [])
                        # bitwidth_failed_types = bitwidth_summary.get("failed_bitwidth_types", [])
                        # bitwidth_total_variant_count = bitwidth_summary.get("total_variant_count", 0)
                        final_result = furgen_output_code
                    else:
                        print(f"Warning: no valid IR found for further_generalization in {filename}.")
                    # continue
                    break

                else:
                    prompt, response = llm_query_performance_improvement(client, last_pre_processed, model, perf, initial_prompt)

            if verification_result in [VerificationResult.VERIFIED_UNEXPECTED, VerificationResult.VERIFIED_INIT,  VerificationResult.WRONG_INPUT]:

                # Pre-cleaning: Eliminate unused/redundant nodes before LLM generalization
                print(f"First generalization for {filename}...")

                initial_prompt, response, should_continue, new_ver_res = first_generalization(
                    testcase, filename, client, model, output_folder, attempt
                )

                if not should_continue:
                    verification_result = new_ver_res
                    break


            elif verification_result == VerificationResult.UNDEFINED_BEHAVIOR:
                prompt, response = llm_query_undefined_behavior(client, last_pre_processed, model, initial_prompt)

            elif verification_result == VerificationResult.VERIFIED_WRONG:
                prompt, response = llm_query_with_counterexample(client, last_pre_processed, initial_prompt, cte, model)

            elif verification_result == VerificationResult.VERIFIED_ERROR:
                prompt, response = llm_query_with_err(client, last_pre_processed, initial_prompt, last_err, model)

            else:
                initial_prompt, response = llm_query_generalize(client, testcase, model)

            pre_processed_response = preprocess_llm_response(response)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"{output_folder}/{filename}_{model}_#{attempt}attempt_{timestamp}_context.txt"
            ensure_dirs()
            with open(output_file, "w", encoding="utf-8") as f:
                if prompt:
                    f.write(f"====== #{attempt} prompt ======\n")
                    f.write(prompt)
                else:
                    f.write(f"========= #{attempt} initial_prompt ======\n")
                    f.write(initial_prompt)
                f.write(f"====== #{attempt} pre_processed_response ======\n")
                f.write(pre_processed_response)

            result, err, perf = verify_and_profile(pre_processed_response)
            ver_res, ver_perf_succ, new_last_pp, new_cte, new_err = analyze_verification_result(
                result, err, perf, filename, output_folder, model, attempt,
                pre_processed_response, write_alive2_stdout_stderr, write_perf_output,
            )

            verification_result = ver_res
            verification_perf_succ = ver_perf_succ

            if new_last_pp is not None:
                last_pre_processed = new_last_pp

            if new_cte is not None:
                cte = new_cte

            if new_err is not None:
                last_err = new_err

            if verification_result == VerificationResult.VERIFIED_SUCCESS and verification_perf_succ:
                if first_successful_result is None:
                    first_successful_result = pre_processed_response
                    first_successful_attempt = attempt

        if (
            not furgen_executed
            and attempt >= max_attempt
            and first_successful_result is not None
        ):
            furgen_trigger_reason = "post_max_attempt_fallback_first_success"
            # _, furgen_output_code, bitwidth_summary = run_furgen_and_bitwidth(
            _, furgen_output_code = run_furgen_and_bitwidth(
                first_successful_result,
                filename,
                first_successful_attempt if first_successful_attempt is not None else attempt,
                furgen_trigger_reason,
            )
            furgen_executed = True
            # bitwidth_executed = True
            # bitwidth_independent = bitwidth_summary.get("bitwidth_independent", False)
            # bitwidth_success_types = bitwidth_summary.get("success_bitwidth_types", [])
            # bitwidth_failed_types = bitwidth_summary.get("failed_bitwidth_types", [])
            # bitwidth_total_variant_count = bitwidth_summary.get("total_variant_count", 0)
            final_result = furgen_output_code

        try:
            entry = {
                "filename": filename,
                "model": model,
                "attempts": attempt,
                "final_verification_result": str(verification_result),
                "final_performance_success": verification_perf_succ,
                # "bitwidth_independent": bitwidth_independent,
                "furgen_executed": furgen_executed,
                # "bitwidth_generalization_executed": bitwidth_executed,
                # "bitwidth_total_variant_count": bitwidth_total_variant_count,
                # "bitwidth_success_types": bitwidth_success_types,
                # "bitwidth_failed_types": bitwidth_failed_types,
                "furgen_trigger_reason": furgen_trigger_reason,
                "final_result_without_bitwidth_generalization": final_result,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            processed_testcases.append(entry)
            # write progress to file after each testcase so we can resume/inspect
            ensure_dirs()
            processed_file = f"{output_folder}/processed_testcases.json"
            with open(processed_file, "w", encoding="utf-8") as pf:
                json.dump(processed_testcases, pf, indent=2)
        except Exception as e:
            print(f"Warning: failed to write processed_testcases file: {e}")

    bitwidth_generalization(processed_file)

def main():
    model = "gemini-3-pro-preview"
    testcases = "../testcases/test1"


    testcases_folders = [
        testcases
    ]

    all_testcases_dict = {}

    for folder in testcases_folders:
        if os.path.exists(folder):
            folder_dict = load_testcases(folder)

            all_testcases_dict.update(folder_dict)
        else:
            print(f"Warning: Folder not found: {folder}")

    with open("../config/gemini_config.json", "r") as f:
        config = json.load(f)
    client = genai.Client(api_key=config["GEMINI_API_KEY"])
    all_outputs_folder = f"outputs_folder"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_folder = f"{all_outputs_folder}/generalized_optimization_outputs_{timestamp}"

    prev_processed_path = None
    generalize_optimization(all_testcases_dict, model, prev_processed_path, client, all_outputs_folder, output_folder)

if __name__ == "__main__":
    main()
