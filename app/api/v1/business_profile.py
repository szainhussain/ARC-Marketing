from flask import jsonify, request
from flask_login import current_user, login_required

from app.api.v1 import api_v1
from app.extensions import limiter
from app.services.authorization_service import get_membership_or_403
from app.services.business_profile_service import get_or_create_profile, update_profile
from app.services.checklist_service import onboarding_checklist
from app.services.website_import import import_from_website


@api_v1.route("/organizations/<organization_id>/business-profile", methods=["GET"])
@login_required
def get_business_profile(organization_id):
    get_membership_or_403(organization_id)
    profile = get_or_create_profile(organization_id)
    return jsonify({"business_profile": profile.to_dict()}), 200


@api_v1.route("/organizations/<organization_id>/business-profile", methods=["PATCH"])
@login_required
def patch_business_profile(organization_id):
    get_membership_or_403(organization_id)
    payload = request.get_json(silent=True) or {}
    profile = update_profile(organization_id, current_user.id, payload)
    return jsonify({"business_profile": profile.to_dict()}), 200


@api_v1.route("/organizations/<organization_id>/onboarding-checklist", methods=["GET"])
@login_required
def onboarding_checklist_route(organization_id):
    get_membership_or_403(organization_id)
    return jsonify(onboarding_checklist(organization_id)), 200


@api_v1.route("/organizations/<organization_id>/business-profile/import-website", methods=["POST"])
@login_required
@limiter.limit("20 per hour")
def import_website_route(organization_id):
    """Suggest profile fields from the business's public homepage. Saves
    nothing: the user reviews the suggestions and saves the profile."""

    get_membership_or_403(organization_id)
    url = (request.get_json(silent=True) or {}).get("url") or ""
    return jsonify(import_from_website(url)), 200
