"""Request and list on-brand generated images for a deliverable."""

from flask import jsonify, request
from flask_login import current_user, login_required

from app.api.v1 import api_v1
from app.extensions import limiter
from app.models.membership import OPERATOR_ROLES
from app.services.authorization_service import get_membership_or_403, require_role
from app.services.media_service import list_images, request_image


@api_v1.route("/organizations/<organization_id>/deliverables/<deliverable_id>/images", methods=["GET"])
@login_required
def list_images_route(organization_id, deliverable_id):
    get_membership_or_403(organization_id)
    return jsonify({"images": list_images(organization_id, deliverable_id)}), 200


@api_v1.route("/organizations/<organization_id>/deliverables/<deliverable_id>/images", methods=["POST"])
@login_required
@limiter.limit("60 per hour")
def request_image_route(organization_id, deliverable_id):
    me = get_membership_or_403(organization_id)
    require_role(me, OPERATOR_ROLES + ("contributor",))
    p = request.get_json(silent=True) or {}
    job = request_image(organization_id, current_user.id, deliverable_id, p.get("item_index"),
                        note=p.get("note") or "", aspect_ratio=p.get("aspect_ratio"))
    # Queued only; the worker generates it (no model call in a web request).
    return jsonify({"image": job.to_dict()}), 202
