"""
Assessment Service — automated grading engine
  - Runs all test cases for a submission
  - Calculates compilation / output / logic scores
  - Calls AI for logic-based evaluation
  - Produces final grade with detailed feedback
"""

from datetime import datetime, timezone
from models import db, Submission, TestCase, TestResult, PerformanceSnapshot, SubmissionStatus
from services.compiler_service import run_test_case, compile_only
from services.ai_service import evaluate_code_logic


# Marks distribution (percentages of total_marks)
COMPILATION_WEIGHT = 0.30   # 30%
OUTPUT_WEIGHT      = 0.40   # 40%
LOGIC_WEIGHT       = 0.30   # 30%


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

        tr = TestResult(
            submission_id=submission.id,
            test_case_id=tc.id,
            passed=passed,
            actual_output=tc_result.get("actual_output", ""),
            expected_output=tc_result.get("expected_output", ""),
            marks_awarded=marks_awarded,
            execution_time_ms=tc_result.get("execution_time_ms"),
        )
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


def get_writeup_results(writeup_id: int) -> dict:
    """
    Aggregate results for a write-up assessment.
    Returns summary stats + per-student breakdown.
    """
    submissions = Submission.query.filter_by(writeup_id=writeup_id).all()
    if not submissions:
        return {"count": 0, "average": 0, "highest": 0, "lowest": 0, "results": []}

    scores = [s.total_score for s in submissions]
    return {
        "count": len(submissions),
        "average": round(sum(scores) / len(scores), 2),
        "highest": round(max(scores), 2),
        "lowest": round(min(scores), 2),
        "pass_rate": round(sum(1 for s in scores if s > 0) / len(scores) * 100, 1),
        "results": [s.to_dict() for s in submissions],
    }


def build_performance_snapshot(student_id: int, lab_id: int | None = None) -> PerformanceSnapshot:
    """
    Compute and persist a performance snapshot for a student.
    Called periodically or after each assessment.
    """
    from models import ErrorLog
    from sqlalchemy import func

    query = Submission.query.filter_by(student_id=student_id)
    if lab_id:
        # Filter by lab via program → lab join
        from models import Program
        lab_program_ids = [p.id for p in Program.query.filter_by(lab_id=lab_id).all()]
        query = query.filter(Submission.program_id.in_(lab_program_ids))

    submissions = query.all()
    if not submissions:
        snap = PerformanceSnapshot(student_id=student_id, lab_id=lab_id)
        db.session.add(snap)
        db.session.commit()
        return snap

    total = len(submissions)
    compiled = sum(1 for s in submissions if s.compilation_score and s.compilation_score > 0)
    avg_score = sum(s.total_score for s in submissions) / total
    compile_rate = compiled / total if total else 0

    # Most common error type
    error_counts: dict[str, int] = {}
    for el in ErrorLog.query.filter_by(student_id=student_id).all():
        t = el.error_type or "unknown"
        error_counts[t] = error_counts.get(t, 0) + 1
    common_error = max(error_counts, key=error_counts.get) if error_counts else None
    total_errors = sum(error_counts.values())

    # AI assist count (number of error logs)
    ai_assists = ErrorLog.query.filter_by(student_id=student_id).count()

    # Risk level heuristic
    if avg_score < 40 or (total_errors > 10 and avg_score < 60):
        risk = "high"
    elif avg_score < 65 or total_errors > 6:
        risk = "medium"
    else:
        risk = "low"

    snap = PerformanceSnapshot(
        student_id=student_id,
        lab_id=lab_id,
        avg_score=round(avg_score, 2),
        total_submissions=total,
        compile_success_rate=round(compile_rate, 3),
        common_error_type=common_error,
        error_count=total_errors,
        ai_assist_count=ai_assists,
        risk_level=risk,
    )
    db.session.add(snap)
    db.session.commit()
    return snap
