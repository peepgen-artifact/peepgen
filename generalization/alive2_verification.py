import tempfile
import subprocess
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALIVE2_PATH = os.path.join(REPO_ROOT, "third_party", "alive2", "build", "alive-tv")

def alive2_verify(generalized_optimization, smt_to=50000):
    if not os.path.isfile(ALIVE2_PATH):
        raise FileNotFoundError(f"alive-tv not found: {ALIVE2_PATH}")
    # Create a temporary file with the LLVM IR content
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ll', delete=False) as temp_file:
        temp_file.write(generalized_optimization)
        temp_file_path = temp_file.name

    try:
        command = f"{ALIVE2_PATH} --smt-to={smt_to} {temp_file_path}"
        # command = f"{ALIVE2_PATH} {temp_file_path}"
        proc = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            text=True,
        )
        result = proc.stdout
        err = proc.stderr
    finally:
        # Clean up the temporary file
        os.unlink(temp_file_path)

    return result, err