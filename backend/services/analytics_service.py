"""
Analytics Service — Educational Data Mining & Learning Analytics
  - Class-wide error distribution
  - Student performance trends
  - At-risk student prediction
  - Learning bottleneck detection
  - Personalised recommendation data prep
"""

from collections import Counter
from sqlalchemy import func, desc
from models import (
    db, User, Lab, Submission, ErrorLog,
    PerformanceSnapshot, WriteUp, Program, Role
)


# ─────────────────────────────────────────────
#  STUDENT ANALYTICS
# ─────────────────────────────────────────────

def get_student_summary(student_id: int) -> dict:
    """Full analytics summary for a single student."""
    submissions = Submission.query.filter_by(student_id=student_id).all()
    error_logs   = ErrorLog.query.filter_by(student_id=student_id).all()

    total_subs   = len(submissions)
    if total_subs == 0:
        return _empty_student_summary(student_id)

    avg_score = sum(s.total_score for s in submissions) / total_subs
    compile_ok = sum(1 for s in submissions if s.compilation_score and s.compilation_score > 0)
    compile_rate = round(compile_ok / total_subs * 100, 1)

    # Score trend (last 10 submissions)
    recent = sorted(submissions, key=lambda s: s.submitted_at)[-10:]
    score_trend = [{"label": f"S{i+1}", "score": s.total_score} for i, s in enumerate(recent)]

    # Error analysis
    error_types  = Counter(e.error_type or "unknown" for e in error_logs)
    common_errors = [{"type": t, "count": c} for t, c in error_types.most_common(5)]

    # Lab-wise breakdown
    from models import Program as Prog
    lab_map: dict[int, list] = {}
    for sub in submissions:
        prog = Prog.query.get(sub.program_id)
        if prog:
            lab_map.setdefault(prog.lab_id, []).append(sub.total_score)
    lab_scores = [
        {"lab_id": lid, "avg": round(sum(scores)/len(scores), 2), "count": len(scores)}
        for lid, scores in lab_map.items()
    ]

    # Latest risk level
    latest_snap = (PerformanceSnapshot.query
                   .filter_by(student_id=student_id)
                   .order_by(desc(PerformanceSnapshot.snapshot_date))
                   .first())
    risk_level = latest_snap.risk_level if latest_snap else _compute_risk(avg_score, len(error_logs))

    return {
        "student_id": student_id,
        "total_submissions": total_subs,
        "avg_score": round(avg_score, 2),
        "compile_success_rate": compile_rate,
        "total_errors": len(error_logs),
        "score_trend": score_trend,
        "common_errors": common_errors,
        "lab_scores": lab_scores,
        "risk_level": risk_level,
        "ai_assist_count": len(error_logs),
    }


def _empty_student_summary(student_id: int) -> dict:
    return {
        "student_id": student_id, "total_submissions": 0,
        "avg_score": 0, "compile_success_rate": 0,
        "total_errors": 0, "score_trend": [],
        "common_errors": [], "lab_scores": [],
        "risk_level": "low", "ai_assist_count": 0,
    }


def _compute_risk(avg_score: float, error_count: int) -> str:
    if avg_score < 40 or (error_count > 10 and avg_score < 60):
        return "high"
    if avg_score < 65 or error_count > 6:
        return "medium"
    return "low"


def get_writeup_results(writeup_id: int) -> dict:
    """
    Aggregate results for a write-up assessment.
    Returns summary stats + per-student breakdown.
    """
    submissions = Submission.query.filter_by(writeup_id=writeup_id).all()
    if not submissions:
        return {"count": 0, "average": 0, "highest": 0, "lowest": 0, "results": []}

    scores = [s.total_score for s in submissions if s.total_score is not None]
    return {
        "count": len(submissions),
        "average": round(sum(scores) / len(scores), 2) if scores else 0,
        "highest": round(max(scores), 2) if scores else 0,
        "lowest": round(min(scores), 2) if scores else 0,
        "pass_rate": round(sum(1 for s in scores if s > 0) / len(scores) * 100, 1) if scores else 0,
        "results": [s.to_dict() for s in submissions],
    }

# ─────────────────────────────────────────────
#  FACULTY / CLASS ANALYTICS
# ─────────────────────────────────────────────

def get_lab_analytics(lab_id: int) -> dict:
    """Comprehensive analytics for a single lab."""
    lab = Lab.query.get_or_404(lab_id)
    students = lab.students.all()
    student_ids = [s.id for s in students]

    if not student_ids:
        return {"lab_id": lab_id, "student_count": 0}

    programs = Program.query.filter_by(lab_id=lab_id).all()
    program_ids = [p.id for p in programs]

    submissions = (Submission.query
                   .filter(Submission.program_id.in_(program_ids))
                   .filter(Submission.student_id.in_(student_ids))
                   .all())

    error_logs = (ErrorLog.query
                  .filter(ErrorLog.student_id.in_(student_ids))
                  .all())

    # Class average per program
    prog_scores: dict[int, list] = {p.id: [] for p in programs}
    for sub in submissions:
        if sub.program_id in prog_scores:
            prog_scores[sub.program_id].append(sub.total_score)

    program_stats = []
    for prog in programs:
        scores = prog_scores.get(prog.id, [])
        program_stats.append({
            "program_id": prog.id,
            "title": prog.title,
            "avg_score": round(sum(scores)/len(scores), 2) if scores else 0,
            "submission_count": len(scores),
            "pass_rate": round(sum(1 for s in scores if s > 0)/len(scores)*100, 1) if scores else 0,
        })

    # Error distribution
    error_dist = Counter(e.error_type or "unknown" for e in error_logs)
    error_distribution = [{"type": t, "count": c} for t, c in error_dist.most_common(8)]

    # At-risk students
    at_risk = _identify_at_risk_students(student_ids, program_ids)

    # Class performance timeline (per write-up)
    writeups = WriteUp.query.filter_by(lab_id=lab_id).order_by(WriteUp.start_time).all()
    wu_timeline = []
    for wu in writeups:
        wu_subs = [s for s in submissions if s.writeup_id == wu.id]
        if wu_subs:
            wu_avg = sum(s.total_score for s in wu_subs) / len(wu_subs)
            wu_timeline.append({"writeup": wu.title, "avg": round(wu_avg, 2), "count": len(wu_subs)})

    return {
        "lab_id": lab_id,
        "lab_name": lab.name,
        "student_count": len(students),
        "total_submissions": len(submissions),
        "class_avg": round(sum(s.total_score for s in submissions)/len(submissions), 2) if submissions else 0,
        "compile_success_rate": round(
            sum(1 for s in submissions if s.compilation_score and s.compilation_score > 0) / len(submissions) * 100, 1
        ) if submissions else 0,
        "program_stats": program_stats,
        "error_distribution": error_distribution,
        "at_risk_students": at_risk,
        "performance_timeline": wu_timeline,
    }


def _identify_at_risk_students(student_ids: list, program_ids: list) -> list:
    """Identify students who may need additional support."""
    at_risk = []
    for sid in student_ids:
        subs = Submission.query.filter(
            Submission.student_id == sid,
            Submission.program_id.in_(program_ids)
        ).all()
        if not subs:
            continue
        avg = sum(s.total_score for s in subs) / len(subs)
        errors = ErrorLog.query.filter_by(student_id=sid).count()
        risk = _compute_risk(avg, errors)
        if risk in ("medium", "high"):
            user = User.query.get(sid)
            at_risk.append({
                "student_id": sid,
                "name": user.name if user else "Unknown",
                "avg_score": round(avg, 2),
                "error_count": errors,
                "risk_level": risk,
            })
    return sorted(at_risk, key=lambda x: (x["risk_level"] == "high", -x["error_count"]), reverse=True)


def get_faculty_dashboard_data(faculty_id: int) -> dict:
    """Aggregate data for faculty dashboard."""
    labs = Lab.query.filter_by(faculty_id=faculty_id, is_active=True).all()
    lab_ids = [l.id for l in labs]

    total_students = 0
    for lab in labs:
        total_students += lab.students.count()

    all_program_ids = [
        p.id for lid in lab_ids
        for p in Program.query.filter_by(lab_id=lid).all()
    ]

    recent_submissions = (Submission.query
                          .filter(Submission.program_id.in_(all_program_ids))
                          .order_by(desc(Submission.submitted_at))
                          .limit(20).all())

    active_writeups = (WriteUp.query
                       .filter(WriteUp.lab_id.in_(lab_ids), WriteUp.status == "live")
                       .all())

    return {
        "total_labs": len(labs),
        "total_students": total_students,
        "recent_submissions": [s.to_dict() for s in recent_submissions],
        "active_writeups": [wu.to_dict() for wu in active_writeups],
        "labs": [l.to_dict() for l in labs],
    }


# ─────────────────────────────────────────────
#  LEARNING BOTTLENECK DETECTION
# ─────────────────────────────────────────────

def detect_bottlenecks(lab_id: int) -> list:
    """
    Identify programs where students consistently struggle.
    Returns list of programs with high failure rates.
    """
    programs = Program.query.filter_by(lab_id=lab_id).all()
    bottlenecks = []

    for prog in programs:
        subs = Submission.query.filter_by(program_id=prog.id).all()
        if len(subs) < 3:
            continue
        fail_rate = sum(1 for s in subs if s.total_score == 0) / len(subs)
        avg_score  = sum(s.total_score for s in subs) / len(subs)
        if fail_rate > 0.4 or avg_score < 50:
            bottlenecks.append({
                "program_id": prog.id,
                "title": prog.title,
                "fail_rate": round(fail_rate * 100, 1),
                "avg_score": round(avg_score, 2),
                "submission_count": len(subs),
            })

    return sorted(bottlenecks, key=lambda x: x["fail_rate"], reverse=True)


# ─────────────────────────────────────────────
#  ADMIN ANALYTICS
# ─────────────────────────────────────────────

def get_platform_stats() -> dict:
    """System-wide statistics for admin dashboard."""
    total_users      = User.query.count()
    total_faculty    = User.query.filter_by(role=Role.FACULTY).count()
    total_students   = User.query.filter_by(role=Role.STUDENT).count()
    total_labs       = Lab.query.filter_by(is_active=True).count()
    total_subs       = Submission.query.count()
    total_errors     = ErrorLog.query.count()
    total_writeups   = WriteUp.query.count()

    compile_ok = Submission.query.filter(Submission.compilation_score > 0).count()
    compile_rate = round(compile_ok / total_subs * 100, 1) if total_subs else 0

    error_dist = (db.session.query(ErrorLog.error_type, func.count(ErrorLog.id))
                  .group_by(ErrorLog.error_type)
                  .order_by(desc(func.count(ErrorLog.id)))
                  .limit(5).all())

    return {
        "total_users": total_users,
        "total_faculty": total_faculty,
        "total_students": total_students,
        "total_labs": total_labs,
        "total_submissions": total_subs,
        "total_errors": total_errors,
        "total_writeups": total_writeups,
        "compile_success_rate": compile_rate,
        "top_error_types": [{"type": t or "unknown", "count": c} for t, c in error_dist],
    }


def build_performance_snapshot(student_id: int, lab_id: int | None = None) -> PerformanceSnapshot:
    """
    Compute and persist a performance snapshot for a student.
    Called periodically or after each assessment.
    """
    query = Submission.query.filter_by(student_id=student_id)
    if lab_id:
        # Filter by lab via program → lab join
        lab_program_ids = [p.id for p in Program.query.filter_by(lab_id=lab_id).all()]
        query = query.filter(Submission.program_id.in_(lab_program_ids))

    submissions = query.all()
    
    # Find existing snapshot or create a new one
    snap = PerformanceSnapshot.query.filter_by(student_id=student_id, lab_id=lab_id).first()
    if not snap:
        snap = PerformanceSnapshot()
        snap.student_id = student_id
        snap.lab_id = lab_id
        db.session.add(snap)

    if not submissions:
        db.session.commit()
        return snap

    total = len(submissions)
    scores = [s.total_score for s in submissions if s.total_score is not None]
    avg_score = sum(scores) / len(scores) if scores else 0
    
    compiled_subs = [s for s in submissions if s.compilation_score is not None and s.compilation_score > 0]
    compile_rate = len(compiled_subs) / total if total else 0

    # Most common error type
    error_logs = ErrorLog.query.filter_by(student_id=student_id).all()
    error_counts = Counter(e.error_type or "unknown" for e in error_logs)
    common_error = error_counts.most_common(1)[0][0] if error_counts else None
    total_errors = len(error_logs)

    # AI assist count (number of error logs)
    ai_assists = total_errors

    # Risk level heuristic
    risk = _compute_risk(avg_score, total_errors)

    # Update snapshot fields
    snap.avg_score = round(avg_score, 2)
    snap.total_submissions = total
    snap.compile_success_rate = round(compile_rate, 3)
    snap.common_error_type = common_error
    snap.error_count = total_errors
    snap.ai_assist_count = ai_assists
    snap.risk_level = risk

    db.session.commit()
    return snap
