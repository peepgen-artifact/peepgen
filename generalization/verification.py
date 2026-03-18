"""
Combined verification wrapper that runs Alive2 verification and optional
performance profiling (via `llc` + `llvm-mca`). This centralizes calls so
other modules can import `verify_and_profile` and get both correctness and
performance info in one place.

Exports:
- verify_with_alive2(ir_code): returns (result, err)
- profile_ir(ir_code, metric, ...): returns performance dict (from performance_verification)
- verify_and_profile(ir_code, metric=..., ...): returns {'alive2':(result,err),'perf':perf_dict}

CLI: run the combined verification/profile for a file or the embedded example.
"""

from typing import Optional, Tuple, Dict, Any
from alive2_verification import alive2_verify
from generalization.performance_verification import compare_ir_performance


def verify_with_alive2(ir_code: str) -> Tuple[str, str]:
	"""Run Alive2 on the provided IR. Returns (result_stdout, stderr).
	The function wraps `alive2_verify` so callers don't need to manage temp files.
	"""
	result, err = alive2_verify(ir_code)
	return result, err


def profile_ir(ir_code: str, metric: str = 'uops', llc_cmd: Optional[str] = None, llvm_mca_cmd: Optional[str] = None, mcpu: Optional[str] = None, keep_files: bool = False) -> Dict[str, Any]:
	"""Profile `ir_code` using `llc`+`llvm-mca`. Returns the dict produced by compare_ir_performance.
	"""
	perf = compare_ir_performance(ir_code, metric=metric, llc_cmd=llc_cmd, llvm_mca_cmd=llvm_mca_cmd, mcpu=mcpu, keep_files=keep_files)
	return perf


def verify_and_profile(ir_code: str, metric: str = 'uops', llc_cmd: Optional[str] = None, llvm_mca_cmd: Optional[str] = None, mcpu: Optional[str] = None, keep_files: bool = False) -> Dict[str, Any]:
	"""Run Alive2 verification and then (optionally) profile with llvm-mca.

	Returns a dict with keys:
	  - 'alive2': {'result': <stdout>, 'err': <stderr>}
	  - 'perf': <perf_dict>  (as returned by compare_ir_performance)
	"""
	result, err = verify_with_alive2(ir_code)
	perf = None
	try:
		perf = profile_ir(ir_code, metric=metric, llc_cmd=llc_cmd, llvm_mca_cmd=llvm_mca_cmd, mcpu=mcpu, keep_files=keep_files)
	except Exception as e:
		perf = {'error': str(e)}

	return result, err, perf


if __name__ == '__main__':
	import argparse
	parser = argparse.ArgumentParser(description='Run Alive2 verification and optional performance profiling')
	parser.add_argument('--infile', '-i', help='Input file containing src/tgt alive2 IR', required=False)
	parser.add_argument('--metric', choices=['cycles', 'uops'], default='uops')
	parser.add_argument('--llc', default=None)
	parser.add_argument('--llvm-mca', dest='llvm_mca', default=None)
	parser.add_argument('--mcpu', default=None)
	parser.add_argument('--keep', action='store_true', help='Keep temporary files from profile step')

	args = parser.parse_args()

	if args.infile:
		with open(args.infile, 'r') as f:
			ir = f.read()
	else:
		# simple embedded example (same as performance_verification example)
		ir = '''; embedded example: src uses sdiv, tgt uses ashr

define i32 @src(i32 %x) {
  ; src: signed divide by 8 (uses idiv-like instruction, expensive)
  %div = sdiv i32 %x, 8
  ret i32 %div
}

define i32 @tgt(i32 %x) {
  ; tgt: arithmetic right shift by 3 (equivalent to divide by 8 for signed integers)
  %shr = ashr i32 %x, 3
  ret i32 %shr
}
'''

	result, err, perf = verify_and_profile(ir, metric=args.metric, llc_cmd=args.llc, llvm_mca_cmd=args.llvm_mca, mcpu=args.mcpu, keep_files=args.keep)
	print('Alive2 result:')
	print(result)
	print('Alive2 stderr:')
	print(err)
	print('Performance:')
	print(perf)

