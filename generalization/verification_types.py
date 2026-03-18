from enum import Enum

class VerificationResult(Enum):

    VERIFIED_INIT = "verified_init"    #first time generalization
    VERIFIED_WRONG = "verified_wrong"  # conterexample found
    VERIFIED_ERROR = "verified_error"  # syntax error
    VERIFIED_UNEXPECTED = "verified_unexpected"
    VERIFIED_SUCCESS = "verified_success" # optimization verified in alive2
    UNDEFINED_BEHAVIOR = "undefined_behavior" #UB found
    WRONG_INPUT = "wrong_input" # the input is not an optimization

def reset_verification_state(result):
    mapping = {
        'ub': VerificationResult.UNDEFINED_BEHAVIOR,
        'success': VerificationResult.VERIFIED_SUCCESS,
        'wrong': VerificationResult.VERIFIED_WRONG,
        'error': VerificationResult.VERIFIED_ERROR,
        'unexpected': VerificationResult.VERIFIED_UNEXPECTED,
        'init': VerificationResult.VERIFIED_INIT,
        'wrong_input': VerificationResult.WRONG_INPUT
    }
    return mapping.get(result)