from app.models.campaign import Campaign
from app.models.usage_record import UsageRecord
from app.models.workflow_run import STATUS_COMPLETED, WorkflowRun


def workflow_summary(organization_id: str) -> dict:
    total_campaigns = Campaign.query.filter_by(organization_id=organization_id).count()
    total_runs = WorkflowRun.query.filter_by(organization_id=organization_id).count()
    completed_runs = WorkflowRun.query.filter_by(
        organization_id=organization_id, status=STATUS_COMPLETED
    ).count()
    usage_rows = UsageRecord.query.filter_by(organization_id=organization_id).all()
    total_estimated_cost = round(sum(r.estimated_cost_usd for r in usage_rows), 6)

    return {
        "total_campaigns": total_campaigns,
        "total_workflow_runs": total_runs,
        "completed_workflow_runs": completed_runs,
        "estimated_ai_cost_usd": total_estimated_cost,
        "cost_basis": "estimate",
        "note": (
            "Figures reflect completed activity recorded by this workspace; "
            "they are not a guarantee of marketing outcomes."
        ),
    }


def usage_by_period(organization_id: str) -> list[dict]:
    rows = (
        UsageRecord.query.filter_by(organization_id=organization_id)
        .order_by(UsageRecord.created_at.desc())
        .limit(200)
        .all()
    )
    return [r.to_dict() for r in rows]
