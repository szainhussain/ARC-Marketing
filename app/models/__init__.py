"""Import every model so Alembic autogenerate and db.create_all() see them."""

from app.models.user import User  # noqa: F401
from app.models.organization import Organization  # noqa: F401
from app.models.membership import Membership  # noqa: F401
from app.models.business_profile import BusinessProfile  # noqa: F401
from app.models.document import Document  # noqa: F401
from app.models.campaign import Campaign  # noqa: F401
from app.models.task import Task, TaskDependency  # noqa: F401
from app.models.platform import (  # noqa: F401
    ActionPolicy,
    CalendarEntry,
    ContactEnquiry,
    Invitation,
    KnowledgeEntry,
    Notification,
    PasswordResetToken,
    Plan,
    Subscription,
)
from app.models.agent_execution import AgentExecution, AgentSetting  # noqa: F401
from app.models.workflow_run import WorkflowRun  # noqa: F401
from app.models.deliverable import Deliverable, DeliverableVersion  # noqa: F401
from app.models.approval import Approval  # noqa: F401
from app.models.external_action import ExternalAction  # noqa: F401
from app.models.integration import Integration  # noqa: F401
from app.models.usage_record import UsageRecord  # noqa: F401
from app.models.audit_event import AuditEvent  # noqa: F401
from app.models.billing import BillingEvent, WebhookDelivery, WebhookEndpoint  # noqa: F401
from app.models.collaboration import DeliverableComment, ReviewLink  # noqa: F401
from app.models.results import CampaignResult  # noqa: F401
from app.models.media import GeneratedImage  # noqa: F401
