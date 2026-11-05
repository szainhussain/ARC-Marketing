from flask import current_app, jsonify, request
from flask_login import login_required, login_user, logout_user
from flask_wtf.csrf import generate_csrf

from app.api.v1 import api_v1
from app.extensions import csrf, db, limiter
from app.models.base import utcnow
from app.models.user import User
from app.services.errors import Conflict, ValidationError


@api_v1.route("/auth/csrf-token", methods=["GET"])
@csrf.exempt
def csrf_token():
    return jsonify({"csrf_token": generate_csrf()}), 200


@api_v1.route("/auth/register", methods=["POST"])
@limiter.limit("10 per hour")
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
    if payload.get("accept_terms") is not True:
        errors.append({"field": "accept_terms", "issue": "Please accept the Terms of Service and Privacy Policy"})
    if errors:
        raise ValidationError("Please correct the highlighted fields.", details=errors)

    if User.query.filter_by(email=email).first() is not None:
        raise Conflict("An account with this email already exists.")

    user = User(email=email, full_name=full_name,
                terms_version=current_app.config["TERMS_VERSION"], terms_accepted_at=utcnow())
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    login_user(user)
    return jsonify({"user": user.to_public_dict()}), 201


@api_v1.route("/auth/login", methods=["POST"])
@limiter.limit("10 per minute")
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

    if user.mfa_enabled_at:
        from app.services.errors import AuthenticationError
        from app.services.mfa_service import verify_second_factor

        code, recovery = payload.get("mfa_code"), payload.get("recovery_code")
        if not code and not recovery:
            err = AuthenticationError("Enter the 6-digit code from your authenticator app.")
            err.code = "MFA_REQUIRED"
            raise err
        if not verify_second_factor(user, code, recovery):
            err = AuthenticationError("That code didn't work. Try the newest code, or a recovery code.")
            err.code = "MFA_INVALID"
            raise err

    login_user(user)
    return jsonify({"user": user.to_public_dict()}), 200


@api_v1.route("/auth/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"status": "ok"}), 200


def _hash_token(token: str) -> str:
    import hashlib

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _password_errors(password: str) -> list[dict]:
    if len(password or "") < 8:
        return [{"field": "password", "issue": "Must be at least 8 characters"}]
    return []


@api_v1.route("/auth/forgot-password", methods=["POST"])
@limiter.limit("5 per hour")
def forgot_password():
    """Always returns the same response so it can't be used to discover
    which emails have accounts. No email provider is configured yet, so the
    reset link is written to the server log (see docs/OPERATIONS_RUNBOOK.md)."""

    import logging
    import secrets
    from datetime import timedelta

    from flask import current_app

    from app.models.base import utcnow
    from app.models.platform import PasswordResetToken

    email = ((request.get_json(silent=True) or {}).get("email") or "").strip().lower()
    user = User.query.filter_by(email=email).first() if email else None
    if user is not None and user.is_active_account:
        token = secrets.token_urlsafe(32)
        db.session.add(PasswordResetToken(
            user_id=user.id, token_hash=_hash_token(token),
            expires_at=utcnow() + timedelta(minutes=current_app.config["PASSWORD_RESET_TTL_MINUTES"]),
        ))
        db.session.commit()
        link = f"{current_app.config['FRONTEND_ORIGIN']}/reset-password?token={token}"
        # Never log the token in production; dev-only until email is wired.
        if current_app.config.get("DEBUG") or current_app.config.get("TESTING"):
            logging.getLogger("app.auth").warning("Password reset link (dev only): %s", link)
            current_app.extensions.setdefault("last_reset_link", link)
    return jsonify({
        "status": "ok",
        "message": "If an account exists for that email, a reset link has been sent.",
    }), 200


@api_v1.route("/auth/reset-password", methods=["POST"])
@limiter.limit("10 per hour")
def reset_password():
    from app.models.base import utcnow
    from app.models.platform import PasswordResetToken

    payload = request.get_json(silent=True) or {}
    errors = _password_errors(payload.get("password"))
    if errors:
        raise ValidationError("Please correct the highlighted fields.", details=errors)
    row = PasswordResetToken.query.filter_by(token_hash=_hash_token(payload.get("token") or "")).first()
    now = utcnow()
    expires = row.expires_at if row else None
    if expires is not None and expires.tzinfo is None:
        from datetime import timezone

        expires = expires.replace(tzinfo=timezone.utc)
    if row is None or row.used_at is not None or expires < now:
        raise ValidationError("This reset link is invalid or has expired. Request a new one.")
    user = db.session.get(User, row.user_id)
    user.set_password(payload["password"])
    user.session_version = (user.session_version or 1) + 1  # sign out everywhere
    row.used_at = now
    db.session.commit()
    return jsonify({"status": "ok", "message": "Password updated. Please sign in."}), 200


@api_v1.route("/auth/change-password", methods=["POST"])
@login_required
@limiter.limit("10 per hour")
def change_password():
    from flask_login import current_user

    payload = request.get_json(silent=True) or {}
    if not current_user.check_password(payload.get("current_password") or ""):
        raise ValidationError("Please correct the highlighted fields.",
                              details=[{"field": "current_password", "issue": "Incorrect password"}])
    errors = _password_errors(payload.get("new_password"))
    if errors:
        raise ValidationError("Please correct the highlighted fields.",
                              details=[{"field": "new_password", "issue": errors[0]["issue"]}])
    current_user.set_password(payload["new_password"])
    current_user.session_version = (current_user.session_version or 1) + 1
    db.session.commit()
    login_user(current_user._get_current_object())  # keep this session, revoke all others
    return jsonify({"status": "ok"}), 200


@api_v1.route("/auth/sign-out-everywhere", methods=["POST"])
@login_required
def sign_out_everywhere():
    from flask_login import current_user

    current_user.session_version = (current_user.session_version or 1) + 1
    db.session.commit()
    logout_user()
    return jsonify({"status": "ok"}), 200


@api_v1.route("/auth/mfa", methods=["GET"])
@login_required
def mfa_status():
    from flask_login import current_user

    from app.services.mfa_service import recovery_codes_left

    return jsonify({"enabled": current_user.mfa_enabled_at is not None,
                    "recovery_codes_left": recovery_codes_left(current_user)}), 200


@api_v1.route("/auth/mfa/setup", methods=["POST"])
@login_required
@limiter.limit("10 per hour")
def mfa_setup():
    from flask_login import current_user

    from app.services.mfa_service import start_setup

    return jsonify(start_setup(current_user)), 200


@api_v1.route("/auth/mfa/enable", methods=["POST"])
@login_required
@limiter.limit("10 per hour")
def mfa_enable():
    from flask_login import current_user

    from app.services.mfa_service import confirm_setup

    codes = confirm_setup(current_user, (request.get_json(silent=True) or {}).get("code"))
    login_user(current_user._get_current_object())  # keep this session, sign out the others
    return jsonify({"enabled": True, "recovery_codes": codes}), 200


@api_v1.route("/auth/mfa/disable", methods=["POST"])
@login_required
@limiter.limit("10 per hour")
def mfa_disable():
    from flask_login import current_user

    from app.services.mfa_service import disable

    p = request.get_json(silent=True) or {}
    disable(current_user, p.get("password"), p.get("code"), p.get("recovery_code"))
    return jsonify({"enabled": False}), 200
