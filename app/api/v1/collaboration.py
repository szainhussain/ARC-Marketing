"""Comments on deliverables and client review links (workspace + public sides)."""

from flask import current_app, jsonify, request
from flask_login import current_user, login_required

from app.api.v1 import api_v1
from app.extensions import csrf, limiter
from app.models.membership import OPERATOR_ROLES
from app.services.authorization_service import get_membership_or_403, require_role
from app.services.collaboration_service import (
    add_comment,
    comment_via_link,
    create_review_link,
    decide_via_link,
    list_comments,
    list_review_links,
    review_payload,
    revoke_review_link,
)


def _payload():
    return request.get_json(silent=True) or {}


@api_v1.route("/organizations/<organization_id>/deliverables/<deliverable_id>/comments", methods=["GET"])
@login_required
def list_comments_route(organization_id, deliverable_id):
    get_membership_or_403(organization_id)
    return jsonify({"comments": list_comments(organization_id, deliverable_id)}), 200


@api_v1.route("/organizations/<organization_id>/deliverables/<deliverable_id>/comments", methods=["POST"])
@login_required
def add_comment_route(organization_id, deliverable_id):
    me = get_membership_or_403(organization_id)
    require_role(me, OPERATOR_ROLES + ("approver", "contributor"))
    comment = add_comment(organization_id, deliverable_id, current_user.id, _payload().get("body"))
    return jsonify({"comment": comment.to_dict(author_name=current_user.full_name)}), 201


@api_v1.route("/organizations/<organization_id>/approvals/<approval_id>/review-links", methods=["GET"])
@login_required
def list_review_links_route(organization_id, approval_id):
    get_membership_or_403(organization_id)
    return jsonify({"review_links": list_review_links(organization_id, approval_id)}), 200


@api_v1.route("/organizations/<organization_id>/approvals/<approval_id>/review-links", methods=["POST"])
@login_required
def create_review_link_route(organization_id, approval_id):
    me = get_membership_or_403(organization_id)
    p = _payload()
    link, token = create_review_link(organization_id, approval_id, me, p.get("label"), p.get("days"))
    # The raw token is shown once; only its hash is stored.
    url = f"{current_app.config['FRONTEND_ORIGIN']}/review/{token}"
    return jsonify({"review_link": link.to_dict(), "url": url}), 201


@api_v1.route("/organizations/<organization_id>/review-links/<link_id>", methods=["DELETE"])
@login_required
def revoke_review_link_route(organization_id, link_id):
    me = get_membership_or_403(organization_id)
    return jsonify({"review_link": revoke_review_link(organization_id, link_id, me).to_dict()}), 200


# ---- Public (token is the credential; no session) ---------------------------

@api_v1.route("/public/review/<token>", methods=["GET"])
@limiter.limit("60 per hour")
def public_review_route(token):
    return jsonify(review_payload(token)), 200


@api_v1.route("/public/review/<token>/decision", methods=["POST"])
@csrf.exempt
@limiter.limit("20 per hour")
def public_review_decision_route(token):
    p = _payload()
    approval = decide_via_link(token, p.get("decision"), p.get("name"), p.get("email"), p.get("comment"))
    return jsonify({"decision": approval.decision}), 200


@api_v1.route("/public/review/<token>/comments", methods=["POST"])
@csrf.exempt
@limiter.limit("30 per hour")
def public_review_comment_route(token):
    p = _payload()
    return jsonify({"comment": comment_via_link(token, p.get("name"), p.get("body")).to_dict()}), 201
