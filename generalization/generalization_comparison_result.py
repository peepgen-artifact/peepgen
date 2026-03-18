from enum import Enum

class GeneralizationComparisonResult(Enum):
    GenSucc = "succ"
    GenEqual = "equal"
    GenFail = "fail"
    GenError = "error"