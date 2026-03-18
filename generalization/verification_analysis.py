from generalization.utils import extract_alive2_cte
from verification_types import VerificationResult, reset_verification_state
from datetime import datetime
from handle_timeout import handle_timeout

def analyze_alive2_result(result, err, filename, output_folder, model,
                          attempt, pre_processed_response, write_callback_alive2):

    verification_result = None
    updated_last_pre_processed = None
    updated_cte = None
    updated_last_err = None

    file_type = None
    timeout_flag = False

    if not err:
        if "WARNING: Source function is always UB." in result:
            verification_result = reset_verification_state('ub')
            file_type = 'ub'


        elif "Transformation seems to be correct!" in result and "WARNING: Source function is always UB." not in result:
            verification_result = reset_verification_state('success')
            file_type = 'success'

        elif "ERROR: Timeout" in result:
            timeout_flag = True
            file_type = 'timeout'
        #     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        #     output_file = f"{output_folder}/{filename}_{model}_#{attempt}attempt_{timestamp}_timeout.txt"
        #     write_callback(output_file, result, err)
        #     verification_result, scaled_response, updated_cte = handle_timeout(pre_processed_response, output_folder, filename, model, attempt, scale_down_attempt=1, max_attempts=10)
        #     updated_last_pre_processed = scaled_response

        elif "Example" in result:
            verification_result = reset_verification_state('wrong')
            file_type = 'wrong'
            updated_cte = extract_alive2_cte(result)

        else:
            verification_result = reset_verification_state('unexpected')
            file_type = 'unexpected_succ'

    else:
        if "Could not read bitcode from" in err:
            verification_result = reset_verification_state('error')
            file_type = 'failed'
            updated_last_err = err


        else:
            verification_result = reset_verification_state('unexpected')
            file_type = 'unexpected_err'


    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"{output_folder}/{filename}_{model}_#{attempt}attempt_{timestamp}_alive2_{file_type}.txt"
    write_callback_alive2(output_file, result, err)
    updated_last_pre_processed = pre_processed_response

    if timeout_flag:
        verification_result, updated_last_pre_processed, updated_cte, timeout_feedback_err = handle_timeout(
            pre_processed_response, output_folder, filename, model, attempt, scale_down_attempt=1, max_attempts=10
        )
        if timeout_feedback_err:
            updated_last_err = timeout_feedback_err


    return verification_result, updated_last_pre_processed, updated_cte, updated_last_err

def analyze_perf_result(perf, filename, output_folder, model, attempt, write_callback_perf):

    winner = perf.get('winner', 'error')
    metric = perf.get('metric', 'error')
    src = perf.get('src', {}) or {}
    tgt = perf.get('tgt', {}) or {}
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    perf_success = False
    if winner == 'tgt':
        perf_success = True
        output_file = f"{output_folder}/{filename}_{model}_#{attempt}attempt_{timestamp}_perf_success.txt"
    elif winner == 'src':
        perf_success = False
        output_file = f"{output_folder}/{filename}_{model}_#{attempt}attempt_{timestamp}_perf_failed.txt"
    elif winner == 'tie':
        perf_success = False
        output_file = f"{output_folder}/{filename}_{model}_#{attempt}attempt_{timestamp}_perf_{winner}.txt"
    else:
        perf_success = False
        output_file = f"{output_folder}/{filename}_{model}_#{attempt}attempt_{timestamp}_perf_{winner}.txt"

    write_callback_perf(output_file, src, tgt, winner, metric)

    return perf_success


def analyze_verification_result(result, err, perf, filename, output_folder, model,
                          attempt, pre_processed_response, write_callback_alive2, write_callback_perf):

    verification_result, updated_last_pre_processed, updated_cte, updated_last_err = analyze_alive2_result(result, err, filename, output_folder, model,
                          attempt, pre_processed_response, write_callback_alive2)
    verification_perf_succ = analyze_perf_result(perf, filename, output_folder, model, attempt, write_callback_perf)
    return verification_result, verification_perf_succ, updated_last_pre_processed, updated_cte, updated_last_err

def check_verification_success(result, err, perf) -> bool:

    # # For testing purposes only
    # return True

    winner = perf.get('winner', 'error')

    if not err and "Transformation seems to be correct!" in result and "WARNING: Source function is always UB." not in result and winner == 'tgt':
        return True
    else:
        return False