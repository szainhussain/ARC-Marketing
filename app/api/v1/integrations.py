from flask import jsonify

from flask_login import login_required

from app.api.v1 import api_v1
from app.models.integration import Integration
from app.services.authorization_service import get_membership_or_403


@api_v1.route("/organizations/<organization_id>/integrations", methods=["GET"])
@login_required
def list_integrations_route(organization_id):
    get_membership_or_403(organization_id)
    integrations = Integration.query.filter_by(organization_id=organization_id).all()
    return (
        jsonify(
            {
                "integrations": [i.to_dict() for i in integrations],
                "note": (
                    "No live publishing connectors are configured yet. "
                    "Approved content can be handed off manually."
                ),
            }
        ),
        200,
    )
