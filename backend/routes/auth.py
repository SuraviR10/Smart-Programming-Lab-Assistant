"""Auth routes — register, login, logout, profile, change password."""

from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity, get_jwt
)
from models import db, User, Role

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

# Simple in-memory token blocklist for logout
_blocklist: set[str] = set()


def is_token_revoked(jwt_payload: dict) -> bool:
    return jwt_payload.get("jti") in _blocklist


# ── REGISTER ─────────────────────────────────
@auth_bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    required = ["name", "email", "password", "role"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    role = data["role"].lower()
    if role not in (Role.ADMIN, Role.FACULTY, Role.STUDENT):
        return jsonify({"error": "Invalid role. Must be admin, faculty, or student."}), 400

    if User.query.filter_by(email=data["email"].lower().strip()).first():
        return jsonify({"error": "An account with this email already exists."}), 409

    user = User(
        name=data["name"].strip(),
        email=data["email"].lower().strip(),
        role=role,
        department=data.get("department"),
        semester=data.get("semester"),
        section=data.get("section"),
        academic_year=data.get("academic_year"),
    )
    if role == Role.STUDENT:
        user.roll_number = data.get("roll_number")

    user.set_password(data["password"])
    db.session.add(user)
    db.session.commit()

    token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})
    return jsonify({"message": "Account created successfully.", "token": token, "user": user.to_dict()}), 201


# ── LOGIN ─────────────────────────────────────
@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").lower().strip()
    password = data.get("password") or ""
    role_hint = (data.get("role") or "").lower()

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid email or password."}), 401

    if not user.is_active:
        return jsonify({"error": "Your account has been deactivated. Contact the administrator."}), 403

    if role_hint and user.role != role_hint:
        return jsonify({"error": f"This account is registered as '{user.role}', not '{role_hint}'."}), 403

    user.last_login = datetime.now(timezone.utc)
    db.session.commit()

    token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})
    return jsonify({
        "message": "Login successful.",
        "token": token,
        "user": user.to_dict(),
        "redirect": _redirect_for_role(user.role),
    }), 200


def _redirect_for_role(role: str) -> str:
    return {"admin": "/admin-dashboard.html", "faculty": "/faculty-dashboard.html"}.get(role, "/student-dashboard.html")


# ── LOGOUT ────────────────────────────────────
@auth_bp.post("/logout")
@jwt_required()
def logout():
    jti = get_jwt().get("jti")
    if jti:
        _blocklist.add(jti)
    return jsonify({"message": "Logged out successfully."}), 200


# ── PROFILE ───────────────────────────────────
@auth_bp.get("/profile")
@jwt_required()
def profile():
    uid = int(get_jwt_identity())
    user = User.query.get_or_404(uid)
    return jsonify({"user": user.to_dict()}), 200


@auth_bp.patch("/profile")
@jwt_required()
def update_profile():
    uid = int(get_jwt_identity())
    user = User.query.get_or_404(uid)
    data = request.get_json(silent=True) or {}

    allowed = ["name", "department", "semester", "section", "academic_year"]
    for field in allowed:
        if field in data:
            setattr(user, field, data[field])

    db.session.commit()
    return jsonify({"message": "Profile updated.", "user": user.to_dict()}), 200


# ── CHANGE PASSWORD ───────────────────────────
@auth_bp.post("/change-password")
@jwt_required()
def change_password():
    uid = int(get_jwt_identity())
    user = User.query.get_or_404(uid)
    data = request.get_json(silent=True) or {}

    current = data.get("current_password", "")
    new_pw  = data.get("new_password", "")

    if not user.check_password(current):
        return jsonify({"error": "Current password is incorrect."}), 400
    if len(new_pw) < 6:
        return jsonify({"error": "New password must be at least 6 characters."}), 400

    user.set_password(new_pw)
    db.session.commit()
    return jsonify({"message": "Password changed successfully."}), 200
