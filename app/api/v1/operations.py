"""Marketing Operations Center API: agents, task queue, approvals inbox,
activity feed, and workspace-level automation controls.

Every route starts with get_membership_or_403; state-changing routes add a
role check. Nothing here can trigger an external marketing action."""

from datetime import timedelta

from flask import jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import func

from app.agents.registry import agents_in_department_order, get_agent
from app.api.v1 import api_v1
from app.extensions import db
from app.models.agent_execution import EXEC_FAILED, EXEC_SUCCEEDED, AgentExecution, AgentSetting
from app.models.approval import DECISION_PENDING, Approval
from app.models.audit_event import AuditEvent
from app.models.base import utcnow
from app.models.campaign import Campaign
from app.models.deliverable import Deliverable
from app.models.membership import (
    APPROVAL_CAPABLE_ROLES,
    ROLE_ADMIN,
    ROLE_OWNER,
)
from app.models.organization import Organization
from app.models.task import STATUS_RUNNING, TERMINAL_TASK_STATUSES, Task
from app.models.workflow_run import WorkflowRun
from app.services.authorization_service import get_membership_or_403, require_role
from app.services.errors import NotFound, ValidationError
from app.workflows.engine import cancel_task, retry_task, set_agent_paused

WORKSPACE_ADMIN_ROLES = (ROLE_OWNER, ROLE_ADMIN)


def _settings_by_agent(organization_id: str) -> dict[str, AgentSetting]:
    return {s.agent_id: s for s in AgentSetting.query.filter_by(organization_id=organization_id)}


def _agent_stats(organization_id: str) -> dict[str, dict]:
    since = utcnow() - timedelta(days=30)
    rows = (
        db.session.query(
            AgentExecution.agent_id,
            AgentExecution.status,
            func.count(AgentExecution.id),
            func.coalesce(func.sum(AgentExecution.estimated_cost_usd), 0.0),
        )
        .filter(AgentExecution.organization_id == organization_id, AgentExecution.started_at >= since)
        .group_by(AgentExecution.agent_id, AgentExecution.status)
        .all()
    )
    stats: dict[str, dict] = {}
    for agent_id, status, count, cost in rows:
        s = stats.setdefault(agent_id, {"succeeded": 0, "failed": 0, "running": 0, "estimated_cost_usd": 0.0})
        s[status] = s.get(status, 0) + count
        s["estimated_cost_usd"] += float(cost or 0)
    active = (
        db.session.query(Task.agent_id, func.count(Task.id))
        .filter(Task.organization_id == organization_id, Task.status.notin_(TERMINAL_TASK_STATUSES))
        .group_by(Task.agent_id)
        .all()
    )
    for agent_id, count in active:
        stats.setdefault(agent_id, {"succeeded": 0, "failed": 0, "running": 0, "estimated_cost_usd": 0.0})
        stats[agent_id]["open_tasks"] = count
    return stats


def _agent_status(agent_id: str, setting, org: Organization, running_ids: set[str]) -> str:
    if org.automation_paused:
        return "workspace_paused"
    if setting and setting.is_paused:
        return "paused"
    return "working" if agent_id in running_ids else "idle"


def _running_agent_ids(organization_id: str) -> set[str]:
    return {
        row[0]
        for row in db.session.query(Task.agent_id)
        .filter(Task.organization_id == organization_id, Task.status == STATUS_RUNNING)
        .distinct()
    }


@api_v1.route("/organizations/<organization_id>/agents", methods=["GET"])
@login_required
def list_agents_route(organization_id):
    get_membership_or_403(organization_id)
    org = db.session.get(Organization, organization_id)
    settings = _settings_by_agent(organization_id)
    stats = _agent_stats(organization_id)
    running = _running_agent_ids(organization_id)
    agents = []
    for spec in agents_in_department_order():
        data = spec.to_public_dict()
        data["settings"] = settings[spec.agent_id].to_dict() if spec.agent_id in settings else {
            "agent_id": spec.agent_id, "is_paused": False, "monthly_budget_usd": None,
        }
        data["status"] = _agent_status(spec.agent_id, settings.get(spec.agent_id), org, running)
        data["stats_30d"] = stats.get(spec.agent_id, {"succeeded": 0, "failed": 0, "running": 0,
                                                       "estimated_cost_usd": 0.0})
        agents.append(data)
    return jsonify({"agents": agents}), 200


@api_v1.route("/organizations/<organization_id>/agents/<agent_id>", methods=["GET"])
@login_required
def get_agent_route(organization_id, agent_id):
    get_membership_or_403(organization_id)
    spec = get_agent(agent_id)
    if spec is None:
        raise NotFound("Agent not found.")
    org = db.session.get(Organization, organization_id)
    setting = AgentSetting.query.filter_by(organization_id=organization_id, agent_id=agent_id).first()
    executions = (
        AgentExecution.query.filter_by(organization_id=organization_id, agent_id=agent_id)
        .order_by(AgentExecution.started_at.desc())
        .limit(25)
        .all()
    )
    tasks = (
        Task.query.filter(
            Task.organization_id == organization_id,
            Task.agent_id == agent_id,
            Task.status.notin_(TERMINAL_TASK_STATUSES),
        )
        .order_by(Task.created_at.desc())
        .limit(25)
        .all()
    )
    data = spec.to_public_dict()
    data["settings"] = setting.to_dict() if setting else {
        "agent_id": agent_id, "is_paused": False, "monthly_budget_usd": None,
    }
    data["status"] = _agent_status(agent_id, setting, org, _running_agent_ids(organization_id))
    data["stats_30d"] = _agent_stats(organization_id).get(
        agent_id, {"succeeded": 0, "failed": 0, "running": 0, "estimated_cost_usd": 0.0}
    )
    return jsonify({
        "agent": data,
        "recent_executions": [e.to_dict() for e in executions],
        "open_tasks": [t.to_dict() for t in tasks],
    }), 200


def _set_paused(organization_id, agent_id, paused):
    membership = get_membership_or_403(organization_id)
    require_role(membership, APPROVAL_CAPABLE_ROLES)
    setting = set_agent_paused(organization_id, agent_id, paused, current_user.id)
    return jsonify({"settings": setting.to_dict()}), 200


@api_v1.route("/organizations/<organization_id>/agents/<agent_id>/pause", methods=["POST"])
@login_required
def pause_agent_route(organization_id, agent_id):
    return _set_paused(organization_id, agent_id, True)


@api_v1.route("/organizations/<organization_id>/agents/<agent_id>/resume", methods=["POST"])
@login_required
def resume_agent_route(organization_id, agent_id):
    return _set_paused(organization_id, agent_id, False)


@api_v1.route("/organizations/<organization_id>/tasks", methods=["GET"])
@login_required
def list_tasks_route(organization_id):
    get_membership_or_403(organization_id)
    query = Task.query.filter(Task.organization_id == organization_id)
    status = request.args.get("status")
    if status == "open":
        query = query.filter(Task.status.notin_(TERMINAL_TASK_STATUSES))
    elif status:
        query = query.filter(Task.status == status)
    if request.args.get("agent_id"):
        query = query.filter(Task.agent_id == request.args["agent_id"])
    if request.args.get("run_id"):
        query = query.filter(Task.workflow_run_id == request.args["run_id"])
    tasks = query.order_by(Task.created_at.desc(), Task.sequence_index).limit(200).all()
    campaign_names = {
        c.id: c.name
        for c in Campaign.query.filter(Campaign.organization_id == organization_id,
                                       Campaign.id.in_({t.campaign_id for t in tasks}))
    }
    payload = []
    for t in tasks:
        item = t.to_dict()
        item["campaign_name"] = campaign_names.get(t.campaign_id)
        payload.append(item)
    return jsonify({"tasks": payload}), 200


@api_v1.route("/organizations/<organization_id>/tasks/<task_id>/retry", methods=["POST"])
@login_required
def retry_task_route(organization_id, task_id):
    membership = get_membership_or_403(organization_id)
    require_role(membership, APPROVAL_CAPABLE_ROLES)
    task = retry_task(organization_id, task_id, current_user.id)
    return jsonify({"task": task.to_dict()}), 200


@api_v1.route("/organizations/<organization_id>/tasks/<task_id>/cancel", methods=["POST"])
@login_required
def cancel_task_route(organization_id, task_id):
    membership = get_membership_or_403(organization_id)
    require_role(membership, APPROVAL_CAPABLE_ROLES)
    task = cancel_task(organization_id, task_id, current_user.id)
    return jsonify({"task": task.to_dict()}), 200


@api_v1.route("/organizations/<organization_id>/tasks/<task_id>/executions", methods=["GET"])
@login_required
def task_executions_route(organization_id, task_id):
    get_membership_or_403(organization_id)
    executions = (
        AgentExecution.query.filter_by(organization_id=organization_id, task_id=task_id)
        .order_by(AgentExecution.attempt_number)
        .all()
    )
    return jsonify({"executions": [e.to_dict() for e in executions]}), 200


@api_v1.route("/organizations/<organization_id>/approvals", methods=["GET"])
@login_required
def list_approvals_route(organization_id):
    get_membership_or_403(organization_id)
    query = Approval.query.filter_by(organization_id=organization_id)
    if request.args.get("decision", "pending") != "all":
        query = query.filter_by(decision=request.args.get("decision", DECISION_PENDING))
    approvals = query.order_by(Approval.created_at.desc()).limit(100).all()
    deliverables = {
        d.id: d
        for d in Deliverable.query.filter(
            Deliverable.organization_id == organization_id,
            Deliverable.id.in_({a.deliverable_id for a in approvals}),
        )
    }
    campaign_names = {
        c.id: c.name
        for c in Campaign.query.filter(
            Campaign.organization_id == organization_id,
            Campaign.id.in_({d.campaign_id for d in deliverables.values()}),
        )
    }
    payload = []
    for a in approvals:
        item = a.to_dict()
        d = deliverables.get(a.deliverable_id)
        item["deliverable_type"] = d.deliverable_type if d else None
        item["campaign_id"] = d.campaign_id if d else None
        item["campaign_name"] = campaign_names.get(d.campaign_id) if d else None
        item["is_current_version"] = bool(d and d.current_version_id == a.deliverable_version_id)
        payload.append(item)
    return jsonify({"approvals": payload}), 200


@api_v1.route("/organizations/<organization_id>/activity", methods=["GET"])
@login_required
def activity_feed_route(organization_id):
    get_membership_or_403(organization_id)
    limit = min(int(request.args.get("limit", 50)), 200)
    events = (
        AuditEvent.query.filter_by(organization_id=organization_id)
        .order_by(AuditEvent.created_at.desc())
        .limit(limit)
        .all()
    )
    return jsonify({"events": [e.to_dict() for e in events]}), 200


@api_v1.route("/organizations/<organization_id>/operations/summary", methods=["GET"])
@login_required
def operations_summary_route(organization_id):
    get_membership_or_403(organization_id)
    org = db.session.get(Organization, organization_id)
    task_counts = dict(
        db.session.query(Task.status, func.count(Task.id))
        .filter(Task.organization_id == organization_id)
        .group_by(Task.status)
        .all()
    )
    run_counts = dict(
        db.session.query(WorkflowRun.status, func.count(WorkflowRun.id))
        .filter(WorkflowRun.organization_id == organization_id)
        .group_by(WorkflowRun.status)
        .all()
    )
    month_start = utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    spend = (
        db.session.query(func.coalesce(func.sum(AgentExecution.estimated_cost_usd), 0.0))
        .filter(AgentExecution.organization_id == organization_id, AgentExecution.started_at >= month_start)
        .scalar()
    )
    exec_counts = dict(
        db.session.query(AgentExecution.status, func.count(AgentExecution.id))
        .filter(AgentExecution.organization_id == organization_id, AgentExecution.started_at >= month_start)
        .group_by(AgentExecution.status)
        .all()
    )
    pending_approvals = Approval.query.filter_by(
        organization_id=organization_id, decision=DECISION_PENDING
    ).count()
    latest_runs = (
        WorkflowRun.query.filter_by(organization_id=organization_id)
        .order_by(WorkflowRun.created_at.desc())
        .limit(5)
        .all()
    )
    campaign_names = {
        c.id: c.name
        for c in Campaign.query.filter(Campaign.organization_id == organization_id,
                                       Campaign.id.in_({r.campaign_id for r in latest_runs}))
    }
    runs = []
    for r in latest_runs:
        item = r.to_dict()
        item["campaign_name"] = campaign_names.get(r.campaign_id)
        runs.append(item)
    return jsonify({
        "controls": {
            "automation_paused": org.automation_paused,
            "kill_switch_enabled": org.kill_switch_enabled,
        },
        "task_counts": task_counts,
        "run_counts": run_counts,
        "pending_approvals": pending_approvals,
        "month_to_date": {
            "estimated_ai_cost_usd": round(float(spend or 0), 4),
            "cost_is_estimate": True,
            "executions_succeeded": exec_counts.get(EXEC_SUCCEEDED, 0),
            "executions_failed": exec_counts.get(EXEC_FAILED, 0),
        },
        "latest_runs": runs,
    }), 200


@api_v1.route("/organizations/<organization_id>/operations/controls", methods=["PATCH"])
@login_required
def update_controls_route(organization_id):
    membership = get_membership_or_403(organization_id)
    require_role(membership, WORKSPACE_ADMIN_ROLES)
    payload = request.get_json(silent=True) or {}
    org = db.session.get(Organization, organization_id)
    from app.services.audit_service import record_audit_event

    changed = False
    for field in ("automation_paused", "kill_switch_enabled"):
        if field in payload:
            if not isinstance(payload[field], bool):
                raise ValidationError(
                    "Please correct the highlighted fields.",
                    details=[{"field": field, "issue": "Must be true or false"}],
                )
            setattr(org, field, payload[field])
            record_audit_event(
                organization_id, f"workspace.{field}.{'on' if payload[field] else 'off'}",
                actor_user_id=current_user.id, target_type="organization", target_id=organization_id,
            )
            changed = True
    if changed:
        db.session.commit()
    return jsonify({
        "controls": {
            "automation_paused": org.automation_paused,
            "kill_switch_enabled": org.kill_switch_enabled,
        }
    }), 200
