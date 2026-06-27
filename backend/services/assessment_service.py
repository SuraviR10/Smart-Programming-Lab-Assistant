"""
Assessment Service — automated grading engine
  - Runs all test cases for a submission
  - Calculates compilation / output / logic scores
  - Calls AI for logic-based evaluation
  - Produces final grade with detailed feedback
"""

from datetime import datetime, timezone
from models import db, Submission, TestCase, TestResult, PerformanceSnapshot, SubmissionStatus
from services.compiler_service import compile_and_run, compile_only
from services.ai_service import evaluate_code_logic


# Marks distribution (percentages of total_marks)
COMPILATION_WEIGHT = 0.30   # 30%
OUTPUT_WEIGHT      = 0.40   # 40%
LOGIC_WEIGHT       = 0.30   # 30%


def run_test_case(code: str, input_data: str, expected_output: str, language: str) -> dict:
    """
    A helper to run a single test case and check the output.
    This is a simplified version of compile_and_run for assessment.
    """
    result = compile_and_run(code, language, stdin_data=input_data)
    if not result["compilation_success"] or result.get("status") == "Runtime Error":
        return {
            "passed": False,
            "actual_output": result.get("error", "Compilation/Runtime Error"),
            "expected_output": expected_output,
            "execution_time_ms": result.get("execution_time_ms"),
        }

    actual_output = (result.get("run_output", "") or "").strip().replace("\r\n", "\n")
    expected_output_stripped = (expected_output or "").strip().replace("\r\n", "\n")

    return {
        "passed": actual_output == expected_output_stripped,
        "actual_output": actual_output,
        **result,
    }

def grade_submission(submission: Submission, program, writeup=None) -> Submission:
    """
    Full automated grading pipeline for a student submission.
    Mutates submission in-place and saves to DB.
    """
    max_marks = writeup.total_marks if writeup else 10.0
    submission.max_marks = max_marks
    submission.status = SubmissionStatus.COMPILING

    # ── STEP 1: Compilation check ──────────────────────────
    compile_result = compile_only(submission.code, submission.language)
    compilation_success = compile_result["compilation_success"]
    submission.compiler_output = compile_result.get("compiler_output", "")

    if compilation_success:
        compilation_score = max_marks * COMPILATION_WEIGHT
    else:
        compilation_score = 0.0
        submission.status = SubmissionStatus.FAILED
        submission.compilation_score = 0.0
        submission.output_score = 0.0
        submission.logic_score = 0.0
        submission.total_score = 0.0
        submission.graded_at = datetime.now(timezone.utc)
        db.session.commit()
        return submission

    submission.compilation_score = round(compilation_score, 2)
    submission.status = SubmissionStatus.RUNNING

    # ── STEP 2: Test case execution ────────────────────────
    test_cases = TestCase.query.filter_by(program_id=program.id).all()
    total_tc_marks = sum(tc.marks for tc in test_cases) if test_cases else 1.0
    earned_tc_marks = 0.0

    for tc in test_cases:
        tc_result = run_test_case(
            submission.code,
            tc.input_data or "",
            tc.expected_output,
            submission.language,
        )
        passed = tc_result["passed"]
        marks_awarded = tc.marks if passed else 0.0
        earned_tc_marks += marks_awarded

        tr = TestResult()
        tr.submission_id = submission.id
        tr.test_case_id = tc.id
        tr.passed = passed
        tr.actual_output = tc_result.get("actual_output", "")
        tr.expected_output = tc_result.get("expected_output", "")
        tr.marks_awarded = marks_awarded
        tr.execution_time_ms = tc_result.get("execution_time_ms")

        db.session.add(tr)

        if tc_result.get("execution_time_ms") is not None:
            submission.execution_time_ms = tc_result["execution_time_ms"]

    output_ratio = earned_tc_marks / total_tc_marks if total_tc_marks else 0
    output_score = round(max_marks * OUTPUT_WEIGHT * output_ratio, 2)
    submission.output_score = output_score

    # ── STEP 3: Logic evaluation via AI ───────────────────
    logic_score = 0.0
    ai_feedback = "Logic evaluation not available."
    if program.reference_solution:
        try:
            logic_result = evaluate_code_logic(
                submission.code,
                program.reference_solution,
                submission.language,
            )
            logic_ratio = float(logic_result.get("logic_score", 0.5))
            logic_score = round(max_marks * LOGIC_WEIGHT * logic_ratio, 2)
            ai_feedback = logic_result.get("feedback", "")
            if logic_result.get("approach"):
                ai_feedback = f"Approach: {logic_result['approach']}. {ai_feedback}"
        except Exception:
            logic_score = round(max_marks * LOGIC_WEIGHT * 0.5, 2)
            ai_feedback = "Logic partially evaluated."
    else:
        # No reference solution — award full logic marks if output is correct
        logic_score = round(max_marks * LOGIC_WEIGHT * output_ratio, 2)
        ai_feedback = "Evaluated based on test case results."

    submission.logic_score = logic_score
    submission.ai_feedback = ai_feedback

    # ── STEP 4: Final total ────────────────────────────────
    total = round(compilation_score + output_score + logic_score, 2)
    submission.total_score = min(total, max_marks)
    submission.status = SubmissionStatus.PASSED if total > 0 else SubmissionStatus.FAILED
    submission.graded_at = datetime.now(timezone.utc)

    db.session.commit()
    return submission
