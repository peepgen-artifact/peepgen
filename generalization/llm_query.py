def llm_query_generalize(client, original_optimization, model):
    prompts = f"""Generalize the following LLVM IR peephole optimization and output it in Alive2 verifiable LHS/RHS format.
LLVM IR to optimize:
"{original_optimization}"

Primary goal:
Produce a real generalization: the resulting rule must be valid for a strictly broader set of inputs, not merely a renaming or a symbolic name that is subsequently fixed to a literal, nor creating a same optimization only with different bitwidth.

Requirements:
Generalize this optimization to make it applicable to a wider range of types (integers or floating point) and constants. Ensure the generalization is correct.Important: Preserve the Data Type Category.
- If the original optimization uses Integer types, your generalization MUST use Integer types.
- If the original optimization uses Floating Point types (float, double, etc.), your generalization MUST use Floating Point types. Do NOT convert it to Integers.
Symbolic Constants: Try to use symbolic constants (e.g., C1, C2) to replace every fixed value in the precondition/LHS/RHS as much as possible.
Output Format: Strictly output the code directly in Alive2's define type @src(...) {{ret type %lhs}} and define type @tgt(...) {{ret type %rhs}} format. (type can be i32, float, etc.).
Make it definitely able to run in alive2 directly.
- For Integers: Do not include iX or iN. Select a specific bitwidth (e.g., i32, i64). Default is i32.
- For Floating Point: Use standard types like half, float, double.
You are encouraged to use appropriate operators and attributes:
sext, zext, cttz, ctlz, ctpop, nsw, nuw, exact, nnan, ninf, nsz, etc.
If a numeric constant represents the bitwidth of a variable, you MUST bind that bitwidth to the specific variable. Represent each binding as an add i32 <N>, 0 assignment and use that %bitwidth_... name everywhere the bitwidth is referenced.
- If you want to use a bitwidth-related constant (e.g., 32) and you believe this constant represents the bitwidth of a variable C1, please represent this constant as %bitwidth_C1 = add i32 32, 0.
- If a bitwidth-related constant represents the bitwidth of multiple variables (for example %C1 and %C2), bind it using a combined name joining variable identifiers with underscores: %bitwidth_C1_C2 = add i32 32, 0.
Always define these %bitwidth_* bindings in both @src and @tgt (either as an extra input argument or as an initial assignment inside each function) and then use the %bitwidth_* symbol in any expressions or preconditions that depend on the bitwidth.
Do not directly let %bitwidth_C1 = i32 32 since it is not acceptable in alive2.
Do not directly let %bitwidth = add i32 32, 0. since the the variable name %bitwidth does not indicate which variable it is referring to.
Explicitly output all necessary preconditions within the Alive2 code.
If precondition is required, please put the precondtion into the @src and @tgt function respectively by using something like call void @llvm.assume() to make it act as a precondtion correctly.
Do not include any explanation or reasoning process, just output the code in the format of plain text.
"""

    resp = client.models.generate_content(
        model=model,      #  "gemini-1.5-pro" / "gemini-2.5-flash"
        contents=prompts
    )
    return prompts, resp.text

def llm_query_with_err(client, pre_processed_response, initial_prompt, error_message, model):
    prompts = f"""Based on the initial optimization request: "{initial_prompt}",
alive2 failed to verify the equivalence of the IR code:
"{pre_processed_response}"
Please output a correct optimized function based on the error message: "{error_message}".
Do not include any explanation or reasoning process, just output the code in the format of plain text.
Output Format: Strictly output the code directly in Alive2's define type @src(...) {{ret type %lhs}} and define type @tgt(...) {{ret type %rhs}} format (type can be i32, float, etc.).
"""

    resp = client.models.generate_content(
        model=model,      #  "gemini-1.5-pro" / "gemini-2.5-flash"
        contents=prompts
    )
    return prompts, resp.text

def llm_query_with_counterexample(client, pre_processed_response, initial_prompt, counterexample, model):
    prompts = f"""Based on the initial optimization request: "{initial_prompt}",
alive2 failed to verify the equivalence of the IR code:
"{pre_processed_response}"
Please output a correct optimized function based on the counterexample: "{counterexample}".
Do not include any explanation or reasoning process, just output the code in the format of plain text.
Output Format: Strictly output the code directly in Alive2's define type @src(...) {{ret type %lhs}} and define type @tgt(...) {{ret type %rhs}} format (type can be i32, float, etc.).
"""
    resp = client.models.generate_content(
        model=model,
        contents=prompts
    )
    return prompts, resp.text


def llm_query_undefined_behavior(client, pre_processed_response, model, initial_prompt):
    prompts = f"""Based on the initial optimization request: "{initial_prompt}"
The generalized IR below has undefined behavior in the source function:
"{pre_processed_response}"
Please modify the optimization to eliminate the undefined behavior while ensuring the optimization remains valid.
Make sure the optimization is correct and can be directly verified by Alive2.
Do not include any explanation or reasoning process, just output the code in the format of plain text.
Output Format: Strictly output the code directly in Alive2's define type @src(...) {{ret type %lhs}} and define type @tgt(...) {{ret type %rhs}} format (type can be i32, float, etc.).
"""
    resp = client.models.generate_content(
        model=model,      #  "gemini-1.5-pro" / "gemini-2.5-flash"
        contents=prompts
    )
    return prompts, resp.text

def llm_query_performance_improvement(client, ir_code, model, perf, initial_prompt):

    metric = perf.get("metric", "uops")
    src = perf.get("src", {}) if isinstance(perf, dict) else {}
    tgt = perf.get("tgt", {}) if isinstance(perf, dict) else {}

    src_metric = src.get(metric)
    tgt_metric = tgt.get(metric)

    prompts = f"""Task: improve target performance specifically for {metric} (lower is better) while preserving Alive2 correctness; success criterion: tgt_{metric} < src_{metric}

Initial optimization request:
{initial_prompt}

Current verified IR:
{ir_code}

Current llvm-mca summary:
- metric: {metric}
- src_{metric}: {src_metric}
- tgt_{metric}: {tgt_metric}

Please modify this generalized optimization to make sure that the target function shows superior performance than the source in the performance metric "{metric}".
Do not include any explanation or reasoning process, just output the code in the format of plain text.
Prefer reducing target instruction count and avoiding slow NaN-handling paths.
Output Format:
Strictly output the code directly in Alive2's format:
define type @src(...) {{ret type %lhs}}
define type @tgt(...) {{ret type %rhs}}
(type can be i32, float, etc.)
"""

    resp = client.models.generate_content(
        model=model,      #  "gemini-1.5-pro" / "gemini-2.5-flash"
        contents=prompts
    )
    return prompts, resp.text


def llm_query_for_elimination_with_precon(client, ir_code, model):
        prompts = f"""
You are an expert in LLVM IR optimization and Alive2 verification.
Your task is to perform "Structural Generalization via Property Extraction" on the given LLVM IR.

Definitions:
1. **Structural Decoupling**: The process of replacing a specific instruction sequence (Construction) that produces a value with a generic input argument constrained by declarative properties (preconditions using `llvm.assume`).
2. **Goal**: To make the optimization valid for ANY input satisfying the mathematical properties, not just those produced by the specific instructions in the original code.

Context:
We have an optimization that is valid for the current specific input structure. We suspect the optimization holds not because of *how* the value is computed (e.g., via `zext`), but because of the *properties* of the value (e.g., its range is [0, 255]).
Previous attempts to make the input completely free (unconstrained) failed, so we need to find the *minimal set of properties* required to maintain validity.

Input IR:
{ir_code}

Example:
# Original:
define i32 @src(i8 %input) {{
  %val = zext i8 %input to i32
  %res = and i32 %val, 255
  ret i32 %res
}}
define i32 @tgt(i8 %input) {{
  %val = zext i8 %input to i32
  ret i32 %val
}}

# Explanation:
# The original optimization removes `and %val, 255` because `%val` comes from `zext i8` (Construction), so its high bits are strictly zero.
# We want to generalize this to ANY value fitting in [0, 255], regardless of source (Property).
# We eliminate the `zext` instruction and replace `%val` with a generic input constrained to be <= 255.

# Generalized (Structure Decoupled):
define i32 @src(i32 %val) {{
  %is_bounded = icmp ule i32 %val, 255
  call void @llvm.assume(i1 %is_bounded)
  %res = and i32 %val, 255
  ret i32 %res
}}
define i32 @tgt(i32 %val) {{
  ret i32 %val
}}

Instructions:
ONLY generalize instructions that impose **Value Properties** (e.g., Range, Known Bits, Alignment) which could inevitably come from multiple diverse sources (Polymorphic Provenance).
- GOOD: Generalize `zext` (Range), `and` (Known Bits), `shl` (Alignment), `urem` (Upper Bound), etc. These properties allow the optimization to apply to values from Loads, Arguments, etc.
- BAD: Do NOT generalize core **Computational Logic** (e.g., replacing `add %x, 1` with `assume(%y == %x + 1)`). This is meaningless because it simply moves the complexity to the constraint without allowing new matching scenarios.

Steps:
1. Identify a computed value (from `zext`, `and`, `shl`, `or`, `urem`, etc.) that implies a useful **Value Property** (Range, Known Bits, Alignment).
2. Verify that this property is generic (e.g., "value is small") and not just the instruction's definition (e.g., "value is x+1").
3. Eliminate the instruction producing that value and replace it with a new input argument.
4. Add an `llvm.assume` precondition to the new argument that mathematically captures the property.
   - e.g., Replace `zext i8` with `assume(x <= 255)`
5. If NO such useful structural decoupling is possible, strictly output "Fail".

Strictly output the code directly in Alive2's define type @src(...) {{ret type %lhs}} and define type @tgt(...) {{ret type %rhs}} format (type can be i32, float, etc.) or a single word "Fail" representing failure.
"""
        resp = client.models.generate_content(
            model=model,
            contents=prompts
        )
        return prompts, resp.text

def llm_query_weaken_precondition(client, ir_code, assume_line, model):
    prompts = f"""The following LLVM IR optimization has a precondition (llvm.assume) that cannot be fully removed because it is necessary for correctness.
However, we want to see if it can be RELAXED (weakened) to cover more cases while still preserving correctness.

Current LLVM IR:
{ir_code}

The precondition to relax is:
{assume_line.strip()}

Instructions:
1. Analyze the precondition and the transformation.
2. Propose a WEAKER precondition that is still sufficient for the transformation to be valid.
   - Example: If "x > 10" is required, maybe "x > 0" is enough?
   - Example: If "x % 4 == 0" is required, maybe "x % 2 == 0" is enough?
3. Replace the original assume line (precondition) with the new, relaxed assume line in the IR.
4. Output the full, valid LLVM IR.
5. Make sure the generalized optimization is correct and can be verified by Alive2.
6. Do not include any explanation or reasoning process, just output the code in the format of plain text.
7. Output Format: Strictly output the code directly in Alive2's define type @src(...) {{ret type %lhs}} and define type @tgt(...) {{ret type %rhs}} format (where type can be i32, float, etc.).
"""
    resp = client.models.generate_content(
        model=model,
        contents=prompts
    )
    return prompts, resp.text


# def llm_query_bitwidth_generalization(client, original_optimization, model):
#     """
#     Ask the LLM once to produce multiple bitwidth/type variants.
#     - If the input is integer-based, output 5 variants: i4, i8, i16, i32, i64.
#     - If the input is floating-point-based, output 3 variants: half, float, double.
#     The response must be easy to split by clear section headers.
#     Returns (prompt, response_text).
#     """
#     prompts = f"""Generalize the following LLVM IR peephole optimization and output it in Alive2 verifiable LHS/RHS format.
# LLVM IR to optimize:
# "{original_optimization}"

# Task:
# Determine whether the optimization is Integer-typed or Floating-Point-typed by inspecting the IR.
# - If Integer: output exactly 5 variants using types i4, i8, i16, i32, i64.
# - If Floating-Point: output exactly 3 variants using types half, float, double.

# Output format (strict):
# For each required variant, output a section header on its own line:
# ### <TYPE>

# Then output exactly one of:
# 1) A valid Alive2 pair:
# define <type> @src(...) {{ ... }}
# define <type> @tgt(...) {{ ... }}
# Ensure the output code is complete and directly verifiable by Alive2 (use concrete types, no placeholders, no redundant symbols).

# 2) The single word:
# Fail

# Failure handling (strict):
# - If generalization fails for a specific type, that type's section must contain only `Fail`.
# - Do NOT omit any required type section.
# - Do NOT stop early if one type fails.
# - No explanations. No extra text. Only the sections.
# """
#     resp = client.models.generate_content(
#         model=model,
#         contents=prompts
#     )
#     return prompts, resp.text
