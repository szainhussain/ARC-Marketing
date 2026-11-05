from urllib.parse import urlencode

from flask import current_app, jsonify, redirect, request
from flask_login import current_user, login_required

from app.api.v1 import api_v1
from app.models.integration import Integration
from app.services import publishing_service
from app.services.authorization_service import get_membership_or_403
from app.services.errors import AppError, ValidationError


@api_v1.route("/organizations/<organization_id>/integrations", methods=["GET"])
@login_required
def list_integrations_route(organization_id):
    get_membership_or_403(organization_id)
    integrations = Integration.query.filter_by(organization_id=organization_id).all()
    return jsonify({
        "integrations": [i.to_dict() for i in integrations],
        "wordpress": publishing_service.connection_status(organization_id),
        "note": "Live publishing is available for WordPress.com. Everything else is handed off after approval.",
    }), 200


@api_v1.route("/organizations/<organization_id>/integrations/wordpress/connect", methods=["POST"])
@login_required
def wordpress_connect_route(organization_id):
    membership = get_membership_or_403(organization_id)
    return jsonify({"authorize_url": publishing_service.start_connect(membership)}), 200


@api_v1.route("/integrations/wordpress/callback", methods=["GET"])
@login_required
def wordpress_callback_route():
    """WordPress.com redirects the browser here. The signed state names the
    workspace; the service checks it belongs to this user and session."""
    origin = current_app.config.get("FRONTEND_ORIGIN", "").rstrip("/")
    if request.args.get("error"):
        return redirect(f"{origin}/app/integrations?" + urlencode({"wordpress": "cancelled"}))
    try:
        publishing_service.complete_connect(current_user, request.args.get("code", ""), request.args.get("state", ""))
    except AppError as exc:
        return redirect(f"{origin}/app/integrations?" + urlencode({"wordpress": "error", "message": exc.message[:200]}))
    return redirect(f"{origin}/app/integrations?wordpress=connected")


@api_v1.route("/organizations/<organization_id>/integrations/wordpress", methods=["DELETE"])
@login_required
def wordpress_disconnect_route(organization_id):
    membership = get_membership_or_403(organization_id)
    publishing_service.disconnect(membership)
    return jsonify({"wordpress": publishing_service.connection_status(organization_id)}), 200


@api_v1.route("/organizations/<organization_id>/approvals/<approval_id>/publish/wordpress", methods=["POST"])
@login_required
def wordpress_publish_route(organization_id, approval_id):
    membership = get_membership_or_403(organization_id)
    payload = request.get_json(silent=True) or {}
    key = request.headers.get("Idempotency-Key") or payload.get("idempotency_key")
    if not key:
        raise ValidationError("Please correct the highlighted fields.", details=[{"field": "idempotency_key", "issue": "Required"}])
    action = publishing_service.request_publish(membership, approval_id, payload.get("article_index", 0), key,
                                                mode=payload.get("mode", "publish"))
    return jsonify({"external_action": action.to_dict()}), 202


@api_v1.route("/organizations/<organization_id>/deliverables/<deliverable_id>/publications", methods=["GET"])
@login_required
def deliverable_publications_route(organization_id, deliverable_id):
    get_membership_or_403(organization_id)
    return jsonify({"publications": publishing_service.list_publications(organization_id, deliverable_id)}), 200


@api_v1.route("/organizations/<organization_id>/external-actions/<action_id>/unpublish", methods=["POST"])
@login_required
def wordpress_unpublish_route(organization_id, action_id):
    membership = get_membership_or_403(organization_id)
    return jsonify({"external_action": publishing_service.unpublish(membership, action_id).to_dict()}), 200
