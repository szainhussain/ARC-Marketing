from flask import jsonify
from flask_login import login_required, current_user

from app.api.v1 import api_v1


@api_v1.route("/me", methods=["GET"])
@login_required
def me():
    return (
        jsonify(
            {
                "user": current_user.to_public_dict(),
                "memberships": [m.to_public_dict() for m in current_user.memberships],
            }
        ),
        200,
    )
