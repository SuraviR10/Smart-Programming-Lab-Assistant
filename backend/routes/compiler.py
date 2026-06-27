"""Compiler routes — compile, run, and AI error analysis."""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, ErrorLog
from services.compiler_service import compile_and_run, compile_only
from services.ai_service import analyze_compiler_error, get_debugging_hint

compiler_bp = Blueprint("compiler", __name__, url_prefix="/api/compiler")


# ── COMPILE ONLY ─────────────────────────────
@compiler_bp.post("/compile")
@jwt_required()
def compile_code():
    """
    Compile student code and return compiler output + AI error explanation.
    Body: { code, language, program_id? }
    """
    uid = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    code = data.get("code", "").strip()
    language = data.get("language", "c").lower()
    program_id = data.get("program_id")

    if not code:
        return jsonify({"error": "No code provided."}), 400

    result = compile_only(code, language)
    response = {
        "compilation_success": result["compilation_success"],
        "compiler_output": result.get("compiler_output", ""),
        "errors": result.get("errors", []),
        "status": result.get("status"),
        "ai_analysis": None,
    }

    # If compilation failed, get AI explanation and log the error
    if not result["compilation_success"] and result.get("compiler_output"):
        raw_error = result["compiler_output"]
        ai_analysis = analyze_compiler_error(raw_error, code, language)
        response["ai_analysis"] = ai_analysis

        # Persist to error log
        error_log = ErrorLog()
        error_log.raw_error = raw_error[:2000]
        error_log.error_type = ai_analysis.get("error_type")
        error_log.error_line = ai_analysis.get("error_line")
        error_log.ai_explanation = ai_analysis.get("explanation")
        error_log.ai_hint = ai_analysis.get("hint")
        error_log.ai_tip = ai_analysis.get("tip")
        error_log.code_snippet = code[:1000]
        error_log.student_id = uid
        error_log.program_id = program_id

        db.session.add(error_log)
        db.session.commit()
        response["error_log_id"] = error_log.id

    return jsonify(response), 200


# ── COMPILE + RUN ─────────────────────────────
@compiler_bp.post("/run")
@jwt_required()
def run_code():
    """
    Compile and execute student code with provided stdin.
    Body: { code, language, stdin }
    """
    uid = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    code     = data.get("code", "").strip()
    language = data.get("language", "c").lower()
    stdin    = data.get("stdin", "")
    program_id = data.get("program_id")

    if not code:
        return jsonify({"error": "No code provided."}), 400

    result = compile_and_run(code, language, stdin_data=stdin)

    # If there was a runtime error, log it and get AI analysis
    is_runtime_error = result["compilation_success"] and result.get("status") == "Runtime Error"
    if is_runtime_error and result.get("error"):
        raw_error = result["error"]
        ai_analysis = analyze_compiler_error(raw_error, code, language, is_runtime=True)
        result["ai_analysis"] = ai_analysis

        # Persist to error log
        error_log = ErrorLog()
        error_log.raw_error = raw_error[:2000]
        error_log.error_type = ai_analysis.get("error_type", "runtime")
        error_log.error_line = ai_analysis.get("error_line")
        error_log.ai_explanation = ai_analysis.get("explanation")
        error_log.ai_hint = ai_analysis.get("hint")
        error_log.ai_tip = ai_analysis.get("tip")
        error_log.code_snippet = code[:1000]
        error_log.student_id = uid
        error_log.program_id = program_id

        db.session.add(error_log)
        db.session.commit()
        result["error_log_id"] = error_log.id

    # If compilation failed, the frontend expects the AI analysis here
    is_compile_error = not result["compilation_success"]
    if is_compile_error and result.get("compiler_output"):
        raw_error = result["compiler_output"]
        ai_analysis = analyze_compiler_error(raw_error, code, language)
        result["ai_analysis"] = ai_analysis

    return jsonify(result), 200


# ── DEBUGGING HINT ────────────────────────────
@compiler_bp.post("/debug-hint")
@jwt_required()
def debug_hint():
    """
    Get a guided debugging hint from AI without providing the solution.
    Body: { code, language, problem_description }
    """
    data = request.get_json(silent=True) or {}
    code = data.get("code", "").strip()
    language = data.get("language", "c").lower()
    problem  = data.get("problem_description", "I'm stuck on this code")

    if not code:
        return jsonify({"error": "No code provided."}), 400

    hint = get_debugging_hint(code, problem, language)
    return jsonify({"hint": hint}), 200


# ── ERROR HISTORY ─────────────────────────────
@compiler_bp.get("/errors")
@jwt_required()
def error_history():
    """Get current user's compiler error history with AI explanations."""
    uid = int(get_jwt_identity())
    program_id = request.args.get("program_id", type=int)
    limit = min(request.args.get("limit", 20, type=int), 100)

    query = ErrorLog.query.filter_by(student_id=uid)
    if program_id:
        query = query.filter_by(program_id=program_id)
    errors = query.order_by(ErrorLog.logged_at.desc()).limit(limit).all()

    return jsonify({"errors": [e.to_dict() for e in errors], "total": len(errors)}), 200


@compiler_bp.get("/errors/stats")
@jwt_required()
def error_stats():
    """Error type distribution for the current student."""
    from collections import Counter
    uid = int(get_jwt_identity())
    logs = ErrorLog.query.filter_by(student_id=uid).all()
    dist = Counter(e.error_type or "unknown" for e in logs)
    return jsonify({
        "total": len(logs),
        "distribution": [{"type": t, "count": c} for t, c in dist.most_common()],
    }), 200
