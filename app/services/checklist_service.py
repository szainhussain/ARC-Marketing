"""Getting-started checklist, computed from what the workspace has really done
(no stored "checked" flags that can drift from reality)."""

from app.models.approval import Approval
from app.models.billing import WebhookEndpoint
from app.models.business_profile import BusinessProfile
from app.models.campaign import Campaign
from app.models.external_action import ExternalAction
from app.models.membership import Membership
from app.models.platform import Invitation, KnowledgeEntry
from app.models.workflow_run import WorkflowRun


def onboarding_checklist(organization_id: str) -> dict:
    profile = BusinessProfile.query.filter_by(organization_id=organization_id).first()

    def count(model, **filters):
        return model.query.filter_by(organization_id=organization_id, **filters).count()

    items = [
        {"key": "profile", "title": "Complete your business profile", "to": "/app/onboarding",
         "done": bool(profile and profile.onboarding_completed)},
        {"key": "brand_voice", "title": "Describe your brand voice", "to": "/app/brand",
         "done": bool(profile and (profile.tone_of_voice or "").strip())},
        {"key": "knowledge", "title": "Add knowledge your agents should use", "to": "/app/knowledge",
         "done": count(KnowledgeEntry) > 0},
        {"key": "campaign", "title": "Create your first campaign", "to": "/app/campaigns/new",
         "done": count(Campaign) > 0},
        {"key": "run", "title": "Run your marketing department", "to": "/app/campaigns",
         "done": count(WorkflowRun) > 0},
        {"key": "approve", "title": "Review and approve a deliverable", "to": "/app/approvals",
         "done": Approval.query.filter(Approval.organization_id == organization_id,
                                       Approval.decision != "pending").count() > 0},
        {"key": "publish", "title": "Export or send approved work", "to": "/app/content",
         "done": count(ExternalAction) > 0},
        {"key": "connect", "title": "Connect Zapier, Make or a webhook", "to": "/app/integrations",
         "done": count(WebhookEndpoint) > 0},
        {"key": "team", "title": "Invite a teammate or approver", "to": "/app/team",
         "done": count(Membership) > 1 or count(Invitation) > 0},
    ]
    done = sum(1 for i in items if i["done"])
    return {"items": items, "done": done, "total": len(items), "complete": done == len(items)}
