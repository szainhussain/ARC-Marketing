from flask import jsonify, request
from flask_login import login_required, login_user, logout_user
from flask_wtf.csrf import generate_csrf

from app.api.v1 import api_v1
from app.extensions import csrf, db
from app.models.user import User
from app.services.errors import Conflict, ValidationError


@api_v1.route("/auth/csrf-token", methods=["GET"])
@csrf.exempt
def csrf_token():
    return jsonify({"csrf_token": generate_csrf()}), 200


@api_v1.route("/auth/register", methods=["POST"])
def register():
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    full_name = (payload.get("full_name") or "").strip()

    errors = []
    if not email or "@" not in email:
        errors.append({"field": "email", "issue": "A valid email is required"})
    if len(password) < 8:
        errors.append({"field": "password", "issue": "Must be at least 8 characters"})
    if not full_name:
        errors.append({"field": "full_name", "issue": "Required"})
    if errors:
        raise ValidationError("Please correct the highlighted fields.", details=errors)

    if User.query.filter_by(email=email).first() is not None:
        raise Conflict("An account with this email already exists.")

    user = User(email=email, full_name=full_name)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    login_user(user)
    return jsonify({"user": user.to_public_dict()}), 201


@api_v1.route("/auth/login", methods=["POST"])
def login():
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""

    user = User.query.filter_by(email=email).first()
    # Deliberately generic message for both "no such user" and "wrong
    # password" to avoid account enumeration.
    if user is None or not user.check_password(password) or not user.is_active_account:
        from app.services.errors import AuthenticationError

        raise AuthenticationError("Invalid email or password.")

    login_user(user)
    return jsonify({"user": user.to_public_dict()}), 200


@api_v1.route("/auth/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"status": "ok"}), 200
