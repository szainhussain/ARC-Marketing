from flask import jsonify, request
from flask_login import login_required

from app.api.v1 import api_v1
from app.extensions import csrf, db, limiter
from app.services import outreach_service as svc
from app.services.authorization_service import get_membership_or_403


def _body() -> dict:
    return request.get_json(silent=True) or {}


@api_v1.route("/organizations/<organization_id>/outreach", methods=["GET"])
@login_required
def outreach_overview_route(organization_id):
    get_membership_or_403(organization_id)
    return jsonify({"sender": svc.sender_status(organization_id), "lists": svc.list_lists(organization_id),
                    "batches": svc.list_batches(organization_id)}), 200


@api_v1.route("/organizations/<organization_id>/outreach/sender", methods=["PUT", "POST"])
@login_required
def outreach_sender_route(organization_id):
    m = get_membership_or_403(organization_id)
    return jsonify({"sender": svc.connect_sender(m, _body())}), 200


@api_v1.route("/organizations/<organization_id>/outreach/sender", methods=["DELETE"])
@login_required
def outreach_sender_delete_route(organization_id):
    m = get_membership_or_403(organization_id)
    return jsonify({"sender": svc.disconnect_sender(m)}), 200


@api_v1.route("/organizations/<organization_id>/outreach/lists", methods=["POST"])
@login_required
def outreach_list_create_route(organization_id):
    m = get_membership_or_403(organization_id)
    return jsonify(svc.create_list(m, _body())), 201


@api_v1.route("/organizations/<organization_id>/outreach/lists/<list_id>/contacts", methods=["GET"])
@login_required
def outreach_contacts_route(organization_id, list_id):
    get_membership_or_403(organization_id)
    return jsonify({"contacts": svc.list_contacts(organization_id, list_id)}), 200


@api_v1.route("/organizations/<organization_id>/outreach/suppressions", methods=["GET"])
@login_required
def outreach_suppressions_route(organization_id):
    get_membership_or_403(organization_id)
    return jsonify({"suppressions": svc.list_suppressions(organization_id)}), 200


@api_v1.route("/organizations/<organization_id>/outreach/suppressions", methods=["POST"])
@login_required
def outreach_suppress_route(organization_id):
    m = get_membership_or_403(organization_id)
    svc.suppress(organization_id, _body().get("email"), "manual", actor=m.user_id)
    db.session.commit()
    return jsonify({"suppressions": svc.list_suppressions(organization_id)}), 201


@api_v1.route("/organizations/<organization_id>/outreach/batches", methods=["POST"])
@login_required
def outreach_batch_create_route(organization_id):
    m = get_membership_or_403(organization_id)
    return jsonify({"batch": svc.create_batch(m, _body())}), 201


@api_v1.route("/organizations/<organization_id>/outreach/batches/<batch_id>", methods=["PATCH"])
@login_required
def outreach_batch_update_route(organization_id, batch_id):
    m = get_membership_or_403(organization_id)
    return jsonify({"batch": svc.update_batch(m, batch_id, _body())}), 200


@api_v1.route("/organizations/<organization_id>/outreach/batches/<batch_id>/preview", methods=["GET"])
@login_required
def outreach_batch_preview_route(organization_id, batch_id):
    get_membership_or_403(organization_id)
    return jsonify({"preview": svc.preview(organization_id, batch_id)}), 200


@api_v1.route("/organizations/<organization_id>/outreach/batches/<batch_id>/<action>", methods=["POST"])
@login_required
def outreach_batch_action_route(organization_id, batch_id, action):
    m = get_membership_or_403(organization_id)
    if action == "request-approval":
        return jsonify({"batch": svc.request_approval(m, batch_id)}), 200
    if action == "approve":
        return jsonify({"batch": svc.approve_batch(m, batch_id)}), 200
    return jsonify({"batch": svc.set_state(m, batch_id, action)}), 200


# Public: the unsubscribe link in every email (page POSTs here) and the
# RFC 8058 one-click endpoint mail apps call directly. The token is random
# and stored only as a hash.
@api_v1.route("/outreach/unsubscribe/<token>", methods=["POST"])
@csrf.exempt
@limiter.limit("60 per hour")
def outreach_unsubscribe_route(token):
    return jsonify(svc.unsubscribe(token)), 200
