import os
from datetime import datetime
from generalization.utils import extract_alive2_function_bodies, remove_comments
from verification import verify_and_profile
from verification_analysis import check_verification_success
from further_generalization import eliminate_node, cleanup_unused_instructions
from llm_query import llm_query_generalize
from verification_types import VerificationResult

def first_generalization(testcase, filename, client, model, output_folder, attempt):
    """
    Performs pre-cleaning on the testcase and logs the result.

    Returns:
        (initial_prompt, response, should_continue, verification_result)

        - initial_prompt: The prompt generated for the LLM (or None if skipped)
        - response: The response from the LLM (or None if skipped)
        - should_continue: Boolean, True if the loop should continue processing this testcase, False if we should skip/break (e.g. wrong input)
        - verification_result: The new VerificationResult state if we are skipping, else None.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"{output_folder}/{filename}_{model}_#{attempt}attempt_{timestamp}_preprocess.txt"

    # Helper to log to file
    def log(msg):
        with open(log_filename, "a", encoding="utf-8") as f:
            f.write(msg + "\n")

    # Ensure output folder exists
    os.makedirs(output_folder, exist_ok=True)

    # Initialize log file
    with open(log_filename, "w", encoding="utf-8") as f:
        f.write(f"Preprocessing log for {filename}\n\n")

    log("=== Original Testcase (Before remove_comments) ===")
    log(testcase)

    testcase = remove_comments(testcase)

    log("\n=== Testcase (After remove_comments) ===")
    log(testcase)

    body, header = extract_alive2_function_bodies(testcase)
    if not body['src'] or not body['tgt'] or not header['src'] or not header['tgt']:
        log("Not LLVM IR structure. Skipping preprocessing.")

        initial_prompt, response = llm_query_generalize(client, testcase, model)
        return initial_prompt, response, True, VerificationResult.VERIFIED_INIT

    result, err, perf = verify_and_profile(testcase)
    if check_verification_success(result, err, perf):
        log("Initial verification successful. Proceeding with elimination.")


        eliminated_ir, pre_eliminated_ir, eliminated_succ, perf_recession_count = eliminate_node(testcase)

        log(f"Eliminate Node Success: {eliminated_succ}")

        if eliminated_succ:
            input_for_cleanup = eliminated_ir
        else:
            input_for_cleanup = pre_eliminated_ir

        log("\n=== After Eliminate Node (eliminated_ir) ===\n")
        log(input_for_cleanup)

        log("\n=== Before Cleanup Unused Instructions ===\n")
        log(input_for_cleanup)

        pre_cleanup_success, input_for_llm, input_for_llm_original, first_time_result, first_time_err, first_time_perf = cleanup_unused_instructions(input_for_cleanup)

        log(f"\nCleanup Success: \n{pre_cleanup_success}")

        if pre_cleanup_success:
            final_input = input_for_llm
            log("\n Preprocessing Result (Cleaned IR):\n")
            log(final_input)
        else:
            final_input = input_for_llm_original
            log("\n Preprocessing Result (Original/Eliminated IR - No Cleanup):\n")
            log(final_input)

        initial_prompt, response = llm_query_generalize(client, final_input, model)
        return initial_prompt, response, True, VerificationResult.VERIFIED_INIT

    else:

        # Log the skip reason and details directly to the preprocess log
        log(f"\nSkipped {filename}")
        log("\nThis testcase is likely not a valid optimization pair.")
        log("\n=== Original Testcase ===\n")
        log(testcase)
        log("\n=== Verification Result ===\n")
        log(result)
        log("\n=== Verification Error Output ===\n")
        log(err)
        log("\n=== Performance Result ===")
        log(str(perf))

        return None, None, False, VerificationResult.WRONG_INPUT
