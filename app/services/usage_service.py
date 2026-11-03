from datetime import datetime, timezone

from app.extensions import db
from app.models.organization import Organization
from app.models.usage_record import UsageRecord
from app.models.workflow_run import WorkflowRun
from app.services.errors import RateLimited


def check_monthly_workflow_limit(organization: Organization) -> None:
    month_start = datetime.now(timezone.utc).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    count_this_month = WorkflowRun.query.filter(
        WorkflowRun.organization_id == organization.id,
        WorkflowRun.created_at >= month_start,
    ).count()
    if count_this_month >= organization.monthly_workflow_limit:
        raise RateLimited(
            "This workspace has reached its monthly workflow limit. "
            "Contact support to increase it."
        )


def record_usage(
    organization_id: str,
    workflow_run_id: str,
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    estimated_cost_usd: float,
) -> UsageRecord:
    record = UsageRecord(
        organization_id=organization_id,
        workflow_run_id=workflow_run_id,
        provider=provider,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost_usd=estimated_cost_usd,
        is_actual=False,
    )
    db.session.add(record)
    db.session.flush()
    return record
