from app.extensions import db
from app.models.task import STATUS_CANCELLED as TASK_CANCELLED
from app.models.task import STATUS_COMPLETED as TASK_COMPLETED
from app.models.task import STATUS_FAILED as TASK_FAILED
from app.models.workflow_run import RUN_TRANSITIONS
from app.models.workflow_run import STATUS_CANCELLED as RUN_CANCELLED
from app.models.workflow_run import WorkflowRun
from app.services.audit_service import record_audit_event
from app.services.errors import NotFound
from app.workflows.state_machine import apply_transition


def get_run_or_404(organization_id: str, run_id: str) -> WorkflowRun:
    run = WorkflowRun.query.filter_by(id=run_id, organization_id=organization_id).first()
    if run is None:
        raise NotFound("Workflow run not found.")
    return run


def cancel_run(organization_id: str, run_id: str, user_id: str) -> WorkflowRun:
    run = get_run_or_404(organization_id, run_id)
    apply_transition(run, RUN_CANCELLED, RUN_TRANSITIONS)
    for task in run.tasks:
        if task.status not in (TASK_COMPLETED, TASK_FAILED):
            task.status = TASK_CANCELLED
    db.session.flush()
    record_audit_event(
        organization_id, "workflow.cancelled", actor_user_id=user_id,
        target_type="workflow_run", target_id=run.id,
    )
    db.session.commit()
    return run
