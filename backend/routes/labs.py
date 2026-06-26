"""Labs routes — lab CRUD, manual upload, PDF extraction, program management."""

import os
import uuid
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from werkzeug.utils import secure_filename
from models import db, Lab, LabManual, Program, TestCase, User, Role, lab_students

labs_bp = Blueprint("labs", __name__, url_prefix="/api/labs")


def _require_faculty_or_admin():
    claims = get_jwt()
    if claims.get("role") not in (Role.FACULTY, Role.ADMIN):
        return jsonify({"error": "Faculty or Admin access required."}), 403
    return None


def _allowed_file(filename: str) -> bool:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in current_app.config.get("ALLOWED_EXTENSIONS", {"pdf", "txt"})


# ── LIST / CREATE LABS ────────────────────────
@labs_bp.get("")
@jwt_required()
def list_labs():
    claims = get_jwt()
    uid = int(get_jwt_identity())
    role = claims.get("role")

    if role == Role.ADMIN:
        labs = Lab.query.filter_by(is_active=True).all()
    elif role == Role.FACULTY:
        labs = Lab.query.filter_by(faculty_id=uid, is_active=True).all()
    else:
        # Student: only enrolled labs
        user = User.query.get_or_404(uid)
        labs = user.labs_enrolled.filter_by(is_active=True).all()

    return jsonify({"labs": [l.to_dict() for l in labs]}), 200


@labs_bp.post("")
@jwt_required()
def create_lab():
    err = _require_faculty_or_admin()
    if err:
        return err

    uid = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    required = ["name", "subject", "semester", "section", "academic_year"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    lab = Lab(
        name=data["name"].strip(),
        subject=data["subject"].strip(),
        description=data.get("description", ""),
        semester=int(data["semester"]),
        section=data["section"].strip(),
        academic_year=data["academic_year"].strip(),
        faculty_id=uid,
    )
    db.session.add(lab)
    db.session.commit()
    return jsonify({"message": "Lab created.", "lab": lab.to_dict()}), 201


@labs_bp.get("/<int:lab_id>")
@jwt_required()
def get_lab(lab_id: int):
    lab = Lab.query.get_or_404(lab_id)
    return jsonify({"lab": lab.to_dict()}), 200


@labs_bp.patch("/<int:lab_id>")
@jwt_required()
def update_lab(lab_id: int):
    err = _require_faculty_or_admin()
    if err:
        return err
    lab = Lab.query.get_or_404(lab_id)
    data = request.get_json(silent=True) or {}
    for field in ["name", "subject", "description", "semester", "section", "academic_year", "is_active"]:
        if field in data:
            setattr(lab, field, data[field])
    db.session.commit()
    return jsonify({"lab": lab.to_dict()}), 200


@labs_bp.delete("/<int:lab_id>")
@jwt_required()
def delete_lab(lab_id: int):
    err = _require_faculty_or_admin()
    if err:
        return err
    lab = Lab.query.get_or_404(lab_id)
    lab.is_active = False
    db.session.commit()
    return jsonify({"message": "Lab deactivated."}), 200


# ── ENROLL / REMOVE STUDENTS ──────────────────
@labs_bp.post("/<int:lab_id>/enroll")
@jwt_required()
def enroll_student(lab_id: int):
    err = _require_faculty_or_admin()
    if err:
        return err
    lab = Lab.query.get_or_404(lab_id)
    data = request.get_json(silent=True) or {}
    student_ids = data.get("student_ids", [])
    if not student_ids:
        return jsonify({"error": "student_ids list is required."}), 400

    enrolled = []
    for sid in student_ids:
        student = User.query.filter_by(id=sid, role=Role.STUDENT).first()
        if student and student not in lab.students.all():
            lab.students.append(student)
            enrolled.append(sid)

    db.session.commit()
    return jsonify({"message": f"Enrolled {len(enrolled)} student(s).", "enrolled": enrolled}), 200


@labs_bp.delete("/<int:lab_id>/enroll/<int:student_id>")
@jwt_required()
def remove_student(lab_id: int, student_id: int):
    err = _require_faculty_or_admin()
    if err:
        return err
    lab = Lab.query.get_or_404(lab_id)
    student = User.query.get_or_404(student_id)
    if student in lab.students.all():
        lab.students.remove(student)
        db.session.commit()
    return jsonify({"message": "Student removed from lab."}), 200


# ── LAB MANUAL UPLOAD ─────────────────────────
@labs_bp.post("/<int:lab_id>/manuals")
@jwt_required()
def upload_manual(lab_id: int):
    err = _require_faculty_or_admin()
    if err:
        return err

    lab = Lab.query.get_or_404(lab_id)

    if "file" not in request.files:
        return jsonify({"error": "No file provided."}), 400

    file = request.files["file"]
    if not file.filename or not _allowed_file(file.filename):
        return jsonify({"error": "Only PDF and TXT files are allowed."}), 400

    original_name = secure_filename(file.filename)
    unique_name   = f"{uuid.uuid4().hex}_{original_name}"
    save_dir      = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, unique_name)
    file.save(save_path)

    manual = LabManual(
        filename=unique_name,
        original_name=original_name,
        file_path=save_path,
        status="processing",
        lab_id=lab_id,
    )
    db.session.add(manual)
    db.session.commit()

    # Extract programs synchronously (use Celery in production)
    programs_found = _extract_programs_from_manual(manual, lab_id)

    manual.status = "processed"
    db.session.commit()

    return jsonify({
        "message": "Manual uploaded and processed.",
        "manual": manual.to_dict(),
        "programs_extracted": programs_found,
    }), 201


def _extract_programs_from_manual(manual: LabManual, lab_id: int) -> int:
    """
    Extract program listings from uploaded PDF using pdfplumber.
    Parses patterns like 'Program N: Title' or 'Ex. N Title'.
    """
    import re
    text = ""

    if manual.file_path.endswith(".pdf"):
        try:
            import pdfplumber
            with pdfplumber.open(manual.file_path) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        except Exception as exc:
            current_app.logger.warning("PDF extraction failed: %s", exc)
            return 0
    else:
        try:
            with open(manual.file_path, encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except Exception:
            return 0

    manual.extracted_text = text[:50000]  # store first 50k chars

    # Detect program blocks
    prog_pattern = re.compile(
        r"(?:program|exercise|ex\.?|ex\s+no\.?)\s*[#:\-]?\s*(\d+)[:\-\.]?\s*([^\n]{3,80})",
        re.IGNORECASE,
    )
    matches = prog_pattern.findall(text)
    seen_nums: set[int] = set()
    count = 0

    # Check existing program numbers in this lab
    existing_nums = {p.number for p in Program.query.filter_by(lab_id=lab_id).all()}

    for num_str, title in matches:
        num = int(num_str)
        if num in seen_nums or num in existing_nums:
            continue
        seen_nums.add(num)
        prog = Program(
            number=num,
            title=title.strip(),
            lab_id=lab_id,
            manual_id=manual.id,
        )
        db.session.add(prog)
        count += 1

    db.session.commit()
    return count


# ── PROGRAMS ──────────────────────────────────
@labs_bp.get("/<int:lab_id>/programs")
@jwt_required()
def list_programs(lab_id: int):
    Lab.query.get_or_404(lab_id)
    claims = get_jwt()
    include_solution = claims.get("role") in (Role.FACULTY, Role.ADMIN)
    programs = Program.query.filter_by(lab_id=lab_id).order_by(Program.number).all()
    return jsonify({"programs": [p.to_dict(include_solution=include_solution) for p in programs]}), 200


@labs_bp.post("/<int:lab_id>/programs")
@jwt_required()
def add_program(lab_id: int):
    err = _require_faculty_or_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    if not data.get("title"):
        return jsonify({"error": "Program title is required."}), 400

    next_num = (Program.query.filter_by(lab_id=lab_id).count() or 0) + 1
    prog = Program(
        number=data.get("number", next_num),
        title=data["title"].strip(),
        description=data.get("description"),
        objective=data.get("objective"),
        sample_input=data.get("sample_input"),
        sample_output=data.get("sample_output"),
        reference_solution=data.get("reference_solution"),
        difficulty=data.get("difficulty", "medium"),
        prerequisites=data.get("prerequisites"),
        lab_id=lab_id,
    )
    db.session.add(prog)
    db.session.commit()
    return jsonify({"message": "Program added.", "program": prog.to_dict(include_solution=True)}), 201


@labs_bp.patch("/programs/<int:program_id>")
@jwt_required()
def update_program(program_id: int):
    err = _require_faculty_or_admin()
    if err:
        return err
    prog = Program.query.get_or_404(program_id)
    data = request.get_json(silent=True) or {}
    for field in ["title", "description", "objective", "sample_input", "sample_output",
                  "reference_solution", "difficulty", "prerequisites"]:
        if field in data:
            setattr(prog, field, data[field])
    db.session.commit()
    return jsonify({"program": prog.to_dict(include_solution=True)}), 200


# ── TEST CASES ────────────────────────────────
@labs_bp.post("/programs/<int:program_id>/testcases")
@jwt_required()
def add_test_case(program_id: int):
    err = _require_faculty_or_admin()
    if err:
        return err
    prog = Program.query.get_or_404(program_id)
    data = request.get_json(silent=True) or {}
    if not data.get("expected_output"):
        return jsonify({"error": "expected_output is required."}), 400

    tc = TestCase(
        input_data=data.get("input_data", ""),
        expected_output=data["expected_output"],
        is_hidden=data.get("is_hidden", True),
        marks=float(data.get("marks", 1.0)),
        description=data.get("description"),
        program_id=program_id,
    )
    db.session.add(tc)
    db.session.commit()
    return jsonify({"test_case": tc.to_dict(reveal=True)}), 201


@labs_bp.get("/programs/<int:program_id>/testcases")
@jwt_required()
def list_test_cases(program_id: int):
    Program.query.get_or_404(program_id)
    claims = get_jwt()
    reveal = claims.get("role") in (Role.FACULTY, Role.ADMIN)
    test_cases = TestCase.query.filter_by(program_id=program_id).all()
    return jsonify({"test_cases": [tc.to_dict(reveal=reveal) for tc in test_cases]}), 200
