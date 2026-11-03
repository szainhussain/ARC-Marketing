from flask import jsonify, request
from flask_login import current_user, login_required

from app.api.v1 import api_v1
from app.services.organization_service import create_organization_with_owner


@api_v1.route("/organizations", methods=["POST"])
@login_required
def create_organization():
    payload = request.get_json(silent=True) or {}
    organization = create_organization_with_owner(payload.get("name", ""), current_user.id)
    return jsonify({"organization": organization.to_public_dict()}), 201
