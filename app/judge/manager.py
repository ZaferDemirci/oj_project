from app.judge.executor import run_single_testcase
from app.judge.comparator import compare_outputs
from app.utils.sanitize import truncate_text
from typing import List, Dict, Any

# Result constants
RESULT_AC = "AC"
RESULT_WA = "WA"
RESULT_RE = "RE"
RESULT_TLE = "TLE"
RESULT_SE = "SE"


async def judge_submission(
    source_code: str,
    test_cases: List[Dict[str, Any]],
    time_limit: float,
) -> Dict[str, Any]:
    """
    Run all test cases and produce the final structured result.

    Args:
        source_code: The Python source code to test.
        test_cases: List of dicts, each with:
            - case_id: str
            - input: str
            - output: str (expected output)
            - score: int
            - is_hidden: bool
        time_limit: Time limit in seconds per test case.

    Returns:
        Structured result dict as required by the assignment:
        {
            "result": "AC" | "WA" | "RE" | "TLE" | "SE",
            "score": int,
            "total_time": float,
            "cases": [
                {
                    "case_id": str,
                    "result": "AC" | "WA" | "RE" | "TLE" | "SE",
                    "score": int,
                    "time_used": float,
                    "exit_code": int,
                    "stdout": str,
                    "stderr": str,
                    "input_data": str,
                    "expected_output": str,
                    "is_hidden": bool,
                }
            ]
        }
    """
    if not source_code or not source_code.strip():
        return {
            "result": "SE",
            "score": 0,
            "total_time": 0.0,
            "cases": [],
            "error": "Source code is empty",
        }

    if not test_cases:
        return {
            "result": "SE",
            "score": 0,
            "total_time": 0.0,
            "cases": [],
            "error": "No test cases provided",
        }

    case_results = []
    total_score = 0
    total_time = 0.0
    final_result = RESULT_AC  # Start optimistic

    for test_case in test_cases:
        case_id = test_case.get("case_id", "unknown")
        expected_output = test_case.get("output", "")
        case_score = test_case.get("score", 0)

        # Run the test case
        exec_result = await run_single_testcase(
            source_code=source_code,
            test_input=test_case.get("input", ""),
            time_limit=time_limit,
        )

        # Determine case result
        case_result = None
        case_stdout = exec_result.get("stdout", "")
        case_stderr = exec_result.get("stderr", "")
        exit_code = exec_result.get("exit_code", -1)
        time_used = exec_result.get("time_used", 0.0)
        timed_out = exec_result.get("timed_out", False)
        judge_error = exec_result.get("error")

        # Check for judge error (SE)
        if judge_error:
            case_result = RESULT_SE
            final_result = RESULT_SE

        # Check for timeout (TLE)
        elif timed_out:
            case_result = RESULT_TLE
            if final_result != RESULT_SE:
                final_result = RESULT_TLE

        # Check for runtime error (RE) - exit code != 0 OR stderr contains errors (also if stdout cannot be decoded properly, it's treated as RE by the executor.)
        elif exit_code != 0:
            case_result = RESULT_RE
            if final_result not in [RESULT_SE, RESULT_TLE]:
                final_result = RESULT_RE

        # Check for wrong answer (WA) output mismatch
        elif not compare_outputs(case_stdout, expected_output):
            case_result = RESULT_WA
            if final_result not in [RESULT_SE, RESULT_TLE, RESULT_RE]:
                final_result = RESULT_WA

        # AC
        else:
            case_result = RESULT_AC
            total_score += case_score

        # Case result dict with truncation and missing fields
        case_result_dict = {
            "case_id": case_id,
            "result": case_result,
            "score": case_score if case_result == RESULT_AC else 0,
            "time_used": time_used,
            "exit_code": exit_code,
            # Truncate stdout and stderr BEFORE persisting
            "stdout": truncate_text(case_stdout),
            "stderr": truncate_text(case_stderr),
            # Add missing input and expected output truncated
            "input_data": truncate_text(test_case.get("input", "")),
            "expected_output": truncate_text(expected_output),
            "is_hidden": test_case.get("is_hidden", False),
        }
        case_results.append(case_result_dict)
        total_time += time_used

        # If SE, TLE, or RE stop early
        if case_result in [RESULT_SE, RESULT_TLE, RESULT_RE]:
            break

    # Determine final result based on the worst case
    if all(cr.get("result") == RESULT_AC for cr in case_results):
        final_result = RESULT_AC

    # Final output
    output = {
        "result": final_result,
        "score": total_score,
        "total_time": total_time,
        "cases": case_results,
    }

    # If there is a top‑level error truncate
    if "error" in output and output["error"]:
        output["error"] = truncate_text(output["error"])

    return output