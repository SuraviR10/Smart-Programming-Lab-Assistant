"""Assessment routes — write-ups, submissions, grading, monitoring."""

from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from models import db, WriteUp, Submission, Program, Lab, User, Role, WriteUpStatus, SubmissionStatus, Notification
from services.assessment_service import grade_submission
from services.analytics_service import build_performance_snapshot, get_writeup_results

assessment_bp = Blueprint("assessment", __name__, url_prefix="/api/assessment")


def _faculty_or_admin():
    claims = get_jwt()
    if claims.get("role") not in (Role.FACULTY, Role.ADMIN):
        return jsonify({"error": "Faculty or Admin access required."}), 403
    return None


# ── WRITE-UPS ─────────────────────────────────

@assessment_bp.post("/writeups")
@jwt_required()
def create_writeup():
    err = _faculty_or_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    required = ["title", "lab_id", "program_id", "duration_minutes", "total_marks"]
    missing = [f for f in required if data.get(f) is None]
    if missing:
        return jsonify({"error": f"Missing: {', '.join(missing)}"}), 400

    Lab.query.get_or_404(data["lab_id"])
    Program.query.get_or_404(data["program_id"])

    wu = WriteUp()
    wu.title = data["title"].strip()
    wu.lab_id = data["lab_id"]
    wu.program_id = data["program_id"]
    wu.duration_minutes = int(data["duration_minutes"])
    wu.total_marks = float(data["total_marks"])
    wu.enable_monitoring = data.get("enable_monitoring", True)
    wu.auto_submit = data.get("auto_submit", True)
    wu.status = WriteUpStatus.DRAFT

    if data.get("start_time"):
        wu.start_time = datetime.fromisoformat(data["start_time"])
    if data.get("end_time"):
        wu.end_time = datetime.fromisoformat(data["end_time"])

    db.session.add(wu)
    db.session.commit()
    return jsonify({"message": "Write-Up created.", "writeup": wu.to_dict()}), 201


@assessment_bp.get("/writeups")
@jwt_required()
def list_writeups():
    claims = get_jwt()
    uid = int(get_jwt_identity())
    lab_id = request.args.get("lab_id", type=int)

    if claims.get("role") in (Role.FACULTY, Role.ADMIN):
        query = WriteUp.query
        if lab_id:
            query = query.filter_by(lab_id=lab_id)
    else:
        # Student: only live or completed write-ups from enrolled labs
        user = User.query.get_or_404(uid)
        enrolled_lab_ids = [l.id for l in user.labs_enrolled.all()]
        query = WriteUp.query.filter(
            WriteUp.lab_id.in_(enrolled_lab_ids),
            WriteUp.status.in_([WriteUpStatus.LIVE, WriteUpStatus.COMPLETED, WriteUpStatus.SCHEDULED]),
        )
        if lab_id:
            query = query.filter_by(lab_id=lab_id)

    writeups = query.order_by(WriteUp.created_at.desc()).all()
    return jsonify({"writeups": [wu.to_dict() for wu in writeups]}), 200


@assessment_bp.patch("/writeups/<int:wu_id>")
@jwt_required()
def update_writeup(wu_id: int):
    err = _faculty_or_admin()
    if err:
        return err
    wu = WriteUp.query.get_or_404(wu_id)
    data = request.get_json(silent=True) or {}

    for field in ["title", "duration_minutes", "total_marks", "enable_monitoring", "auto_submit"]:
        if field in data:
            setattr(wu, field, data[field])

    if data.get("status") and data["status"] in vars(WriteUpStatus).values():
        wu.status = data["status"]
    if data.get("start_time"):
        wu.start_time = datetime.fromisoformat(data["start_time"])
    if data.get("end_time"):
        wu.end_time = datetime.fromisoformat(data["end_time"])

    db.session.commit()
    return jsonify({"writeup": wu.to_dict()}), 200


@assessment_bp.post("/writeups/<int:wu_id>/publish")
@jwt_required()
def publish_writeup(wu_id: int):
    err = _faculty_or_admin()
    if err:
        return err
    wu = WriteUp.query.get_or_404(wu_id)
    wu.status = WriteUpStatus.LIVE
    db.session.commit()
    return jsonify({"message": "Write-Up is now live.", "writeup": wu.to_dict()}), 200


# ── SUBMISSIONS ───────────────────────────────

@assessment_bp.post("/submit")
@jwt_required()
def submit_code():
    """Student submits code for a write-up or practice."""
    uid = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip()
    program_id = data.get("program_id")
    writeup_id = data.get("writeup_id")
    language = data.get("language", "c").lower()

    if not code:
        return jsonify({"error": "Code cannot be empty."}), 400
    if not program_id:
        return jsonify({"error": "program_id is required."}), 400

    program = Program.query.get_or_404(program_id)

    # Check write-up validity if provided
    writeup = None
    if writeup_id:
        writeup = WriteUp.query.get_or_404(writeup_id)
        if writeup.status not in (WriteUpStatus.LIVE, WriteUpStatus.COMPLETED):
            return jsonify({"error": "This write-up is not currently accepting submissions."}), 400
        # Prevent duplicate submission for same writeup
        existing = Submission.query.filter_by(student_id=uid, writeup_id=writeup_id).first()
        if existing:
            return jsonify({"error": "You have already submitted for this write-up.", "submission": existing.to_dict()}), 409

    submission = Submission()
    submission.code = code
    submission.language = language
    submission.status = SubmissionStatus.PENDING
    submission.student_id = uid
    submission.program_id = program_id
    submission.writeup_id = writeup_id
    submission.max_marks = writeup.total_marks if writeup else 10.0

    # Copy monitoring data if provided
    submission.tab_switches    = data.get("tab_switches", 0)
    submission.window_blur_count = data.get("window_blur_count", 0)

    if submission.tab_switches > 2 or submission.window_blur_count > 3:
        submission.flagged = True
        submission.flag_reason = f"Tab switches: {submission.tab_switches}, Window blur: {submission.window_blur_count}"

    db.session.add(submission)
    db.session.flush()  # get submission.id before grading

    # Auto-grade
    graded = grade_submission(submission, program, writeup)

    # Update performance snapshot asynchronously (sync for now)
    try:
        build_performance_snapshot(uid, program.lab_id)
    except Exception:
        pass  # non-critical

    return jsonify({
        "message": "Submission received and graded.",
        "submission": graded.to_dict(),
        "test_results": [tr.to_dict() for tr in graded.test_results.all()],
    }), 201


@assessment_bp.get("/submissions/<int:sub_id>")
@jwt_required()
def get_submission(sub_id: int):
    uid = int(get_jwt_identity())
    claims = get_jwt()
    sub = Submission.query.get_or_404(sub_id)

    # Students can only view their own submissions
    if claims.get("role") == Role.STUDENT and sub.student_id != uid:
        return jsonify({"error": "Access denied."}), 403

    return jsonify({
        "submission": sub.to_dict(),
        "test_results": [tr.to_dict() for tr in sub.test_results.all()],
    }), 200


@assessment_bp.get("/my-submissions")
@jwt_required()
def my_submissions():
    uid = int(get_jwt_identity())
    program_id = request.args.get("program_id", type=int)
    writeup_id = request.args.get("writeup_id", type=int)
    limit = min(request.args.get("limit", 20, type=int), 100)

    query = Submission.query.filter_by(student_id=uid)
    if program_id:
        query = query.filter_by(program_id=program_id)
    if writeup_id:
        query = query.filter_by(writeup_id=writeup_id)

    subs = query.order_by(Submission.submitted_at.desc()).limit(limit).all()
    return jsonify({"submissions": [s.to_dict() for s in subs]}), 200


# ── WRITE-UP RESULTS ──────────────────────────

@assessment_bp.get("/writeups/<int:wu_id>/results")
@jwt_required()
def writeup_results(wu_id: int):
    err = _faculty_or_admin()
    if err:
        return err
    results = get_writeup_results(wu_id)
    return jsonify(results), 200


# ── MONITORING EVENT ──────────────────────────

@assessment_bp.post("/monitor-event")
@jwt_required()
def monitor_event():
    """
    Receive a monitoring event (tab switch, window blur) from the frontend.
    Body: { writeup_id, event_type }
    """
    uid = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    writeup_id = data.get("writeup_id")
    event_type = data.get("event_type")

    if writeup_id:
        sub = Submission.query.filter_by(student_id=uid, writeup_id=writeup_id).first()
        if sub:
            if event_type == "tab_switch":
                sub.tab_switches = (sub.tab_switches or 0) + 1
            elif event_type == "window_blur":
                sub.window_blur_count = (sub.window_blur_count or 0) + 1
            if (sub.tab_switches or 0) > 2 or (sub.window_blur_count or 0) > 3:
                sub.flagged = True
                sub.flag_reason = f"Tab: {sub.tab_switches}, Blur: {sub.window_blur_count}"
            db.session.commit()

    # Notify faculty via notification
    from models import Notification, WriteUp
    wu = WriteUp.query.get(writeup_id) if writeup_id else None
    if wu and wu.lab and wu.lab.faculty_id:
        student = User.query.get(uid)
        notif = Notification()
        notif.title = f"Monitoring Alert — {student.name if student else 'Student'}"
        notif.message = f"Event: {event_type} during '{wu.title}'"
        notif.notification_type = "alert"
        notif.user_id = wu.lab.faculty_id
        db.session.add(notif)
        db.session.commit()

    return jsonify({"received": True}), 200
