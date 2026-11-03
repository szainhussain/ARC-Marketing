import uuid

from flask import current_app

from app.agents.base import StageContext
from app.agents.cmo_planner import CMOPlannerStage
from app.agents.content_creator import ContentCreatorStage
from app.agents.marketing_manager import MarketingManagerStage
from app.agents.quality_reviewer import QualityReviewerStage
from app.agents.research_analyst import ResearchAnalystStage
from app.ai.errors import (
    AIProviderError,
    AIRequestTimeout,
    BudgetExceeded,
    InvalidOutput,
    ProviderUnavailable,
    RateLimited,
)
from app.ai.provider_adapter import get_provider
from app.extensions import db
from app.models.base import utcnow
from app.models.campaign import Campaign
from app.models.deliverable import (
    TYPE_CAMPAIGN_PLAN,
    TYPE_CONTENT_PACK,
    TYPE_QA_REPORT,
    TYPE_RESEARCH_NOTES,
    TYPE_STRATEGY,
)
from app.models.organization import Organization
from app.models.task import Task
from app.models.task import STATUS_COMPLETED as TASK_COMPLETED
from app.models.task import STATUS_FAILED as TASK_FAILED
from app.models.task import STATUS_RUNNING as TASK_RUNNING
from app.models.workflow_run import WorkflowRun
from app.models.workflow_run import STATUS_COMPLETED as RUN_COMPLETED
from app.models.workflow_run import STATUS_FAILED as RUN_FAILED
from app.models.workflow_run import STATUS_NEEDS_INPUT as RUN_NEEDS_INPUT
from app.models.workflow_run import STATUS_RUNNING as RUN_RUNNING
from app.services.audit_service import record_audit_event
from app.services.deliverable_service import create_deliverable_with_first_version
from app.services.usage_service import check_monthly_workflow_limit, record_usage

# Ordered pipeline. Each stage's output becomes an upstream_output available
# to later stages, and is saved as one versioned deliverable.
PIPELINE = [
    (CMOPlannerStage(), TYPE_STRATEGY),
    (ResearchAnalystStage(), TYPE_RESEARCH_NOTES),
    (MarketingManagerStage(), TYPE_CAMPAIGN_PLAN),
    (ContentCreatorStage(), TYPE_CONTENT_PACK),
    (QualityReviewerStage(), TYPE_QA_REPORT),
]


def start_campaign_workflow(
    organization_id: str, campaign_id: str, user_id: str, idempotency_key: str
) -> WorkflowRun:
    existing = WorkflowRun.query.filter_by(
        organization_id=organization_id, idempotency_key=idempotency_key
    ).first()
    if existing:
        return existing

    organization = db.session.get(Organization, organization_id)
    check_monthly_workflow_limit(organization)

    campaign = Campaign.query.filter_by(id=campaign_id, organization_id=organization_id).first()
    if campaign is None:
        from app.services.errors import NotFound

        raise NotFound("Campaign not found.")

    profile = organization.business_profile
    profile_dict = profile.to_dict() if profile else {}
    missing_fields = profile.completeness_warnings() if profile else ["business_profile"]

    run = WorkflowRun(
        organization_id=organization_id,
        campaign_id=campaign_id,
        started_by_user_id=user_id,
        idempotency_key=idempotency_key,
    )
    db.session.add(run)
    db.session.flush()

    tasks = [
        Task(
            organization_id=organization_id,
            campaign_id=campaign_id,
            workflow_run_id=run.id,
            stage=stage.stage_name,
            sequence_index=index,
        )
        for index, (stage, _dtype) in enumerate(PIPELINE)
    ]
    db.session.add_all(tasks)
    db.session.flush()

    record_audit_event(
        organization_id, "workflow.started", actor_user_id=user_id,
        target_type="workflow_run", target_id=run.id,
    )

    if missing_fields:
        run.status = RUN_NEEDS_INPUT
        run.error_summary = (
            "Business profile is missing required fields before a campaign "
            f"workflow can run: {', '.join(missing_fields)}."
        )
        db.session.commit()
        return run

    run.status = RUN_RUNNING
    run.started_at = utcnow()
    db.session.commit()

    _run_pipeline(run, campaign, profile_dict, tasks)
    return run


def _run_pipeline(run: WorkflowRun, campaign: Campaign, profile_dict: dict, tasks: list[Task]) -> None:
    provider = get_provider(current_app.config)
    upstream_outputs: dict[str, dict] = {}
    correlation_id = str(uuid.uuid4())

    for task, (stage, deliverable_type) in zip(tasks, PIPELINE):
        task.status = TASK_RUNNING
        task.started_at = utcnow()
        task.attempt_count += 1
        db.session.flush()

        ctx = StageContext(
            organization_id=run.organization_id,
            campaign=campaign.to_dict(),
            business_profile=profile_dict,
            upstream_outputs=upstream_outputs,
            budget_usd=current_app.config.get("AI_WORKFLOW_BUDGET_USD", 1.0),
            timeout_seconds=current_app.config.get("AI_TIMEOUT_SECONDS", 60),
            correlation_id=correlation_id,
        )

        try:
            result = stage.run(provider, ctx)
        except ProviderUnavailable as exc:
            task.status = TASK_FAILED
            task.error_summary = f"capability_unavailable: {exc}"
            task.completed_at = utcnow()
            run.status = RUN_FAILED
            run.error_summary = f"Stopped at '{stage.stage_name}': capability_unavailable."
            run.completed_at = utcnow()
            db.session.commit()
            return
        except (RateLimited, AIRequestTimeout, BudgetExceeded, InvalidOutput, AIProviderError) as exc:
            task.status = TASK_FAILED
            task.error_summary = f"{type(exc).__name__}: {exc}"
            task.completed_at = utcnow()
            run.status = RUN_FAILED
            run.error_summary = f"Stopped at '{stage.stage_name}': {type(exc).__name__}."
            run.completed_at = utcnow()
            db.session.commit()
            return

        upstream_outputs[stage.stage_name] = result.data
        create_deliverable_with_first_version(
            organization_id=run.organization_id,
            campaign_id=run.campaign_id,
            workflow_run_id=run.id,
            deliverable_type=deliverable_type,
            content=result.data,
            created_by_run_id=run.id,
        )
        record_usage(
            organization_id=run.organization_id,
            workflow_run_id=run.id,
            provider=result.provider,
            model=result.model,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            estimated_cost_usd=result.estimated_cost_usd,
        )
        run.estimated_cost_usd = (run.estimated_cost_usd or 0.0) + result.estimated_cost_usd

        task.status = TASK_COMPLETED
        task.completed_at = utcnow()
        db.session.flush()

    run.status = RUN_COMPLETED
    run.completed_at = utcnow()
    record_audit_event(
        run.organization_id, "workflow.completed", target_type="workflow_run", target_id=run.id,
    )
    db.session.commit()
