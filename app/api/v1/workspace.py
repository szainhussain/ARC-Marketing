"""Workspace administration and collaboration API: settings, team,
invitations, billing/plan, action policies, agent budgets, notifications,
knowledge library, content calendar, content index, approval revoke,
run start approval, integration catalog. Every route begins with
get_membership_or_403; state changes add a role check."""

import hashlib
import json
import secrets
from datetime import date, timedelta

from flask import current_app, jsonify, request
from flask_login import current_user, login_required, login_user

from app.agents.registry import get_agent
from app.api.v1 import api_v1
from app.extensions import db
from app.integrations.catalog import AVAILABLE, CATALOG
from app.models.agent_execution import AgentSetting
from app.models.base import utcnow
from app.models.campaign import Campaign
from app.models.deliverable import Deliverable
from app.models.integration import Integration
from app.models.membership import (
    OPERATOR_ROLES,
    ROLE_LABELS,
    ROLE_OWNER,
    VALID_ROLES,
    WORKSPACE_ADMIN_ROLES,
    Membership,
)
from app.models.organization import Organization
from app.models.platform import (
    CALENDAR_STATUSES,
    KNOWLEDGE_KINDS,
    CalendarEntry,
    Invitation,
    KnowledgeEntry,
    Notification,
)
from app.models.user import User
from app.services.approval_service import revoke_approval
from app.services.audit_service import record_audit_event
from app.services.authorization_service import get_membership_or_403, require_role
from app.services.errors import Conflict, NotFound, PermissionDenied, ValidationError
from app.services.platform_service import (
    change_plan,
    check_entitlement,
    get_subscription,
    list_policies,
    public_plans,
    set_policy,
    usage_against_entitlements,
)
from app.workflows.engine import approve_run_start


def _payload() -> dict:
    return request.get_json(silent=True) or {}


def _invalid(field: str, issue: str):
    return ValidationError("Please correct the highlighted fields.", details=[{"field": field, "issue": issue}])


def _paginate(query, default=50, maximum=200):
    try:
        limit = max(1, min(int(request.args.get("limit", default)), maximum))
        offset = max(0, int(request.args.get("offset", 0)))
    except ValueError:
        raise _invalid("limit", "Must be a number")
    total = query.order_by(None).count()
    return query.limit(limit).offset(offset).all(), {"total": total, "limit": limit, "offset": offset}


# ---- Workspace settings ----------------------------------------------------

def _workspace_dict(org: Organization, membership: Membership) -> dict:
    return {
        **org.to_public_dict(),
        "timezone": org.timezone,
        "max_concurrent_tasks": org.max_concurrent_tasks,
        "default_run_budget_usd": org.default_run_budget_usd,
        "platform_default_run_budget_usd": current_app.config.get("AI_WORKFLOW_BUDGET_USD", 1.0),
        "automation_paused": org.automation_paused,
        "kill_switch_enabled": org.kill_switch_enabled,
        "accent_color": org.accent_color,
        "brand_accent": _brand_accent(org.id),
        "your_role": membership.role,
        "your_role_label": ROLE_LABELS.get(membership.role, membership.role),
    }


def _brand_accent(organization_id: str) -> str | None:
    """The Brand Kit's primary colour, offered as the workspace's app accent."""
    from app.models.business_profile import BusinessProfile
    from app.services.business_profile_service import brand_palette

    palette = brand_palette(BusinessProfile.query.filter_by(organization_id=organization_id).first())
    return palette[0] if palette else None


@api_v1.route("/organizations/<organization_id>", methods=["GET"])
@login_required
def get_workspace_route(organization_id):
    membership = get_membership_or_403(organization_id)
    org = db.session.get(Organization, organization_id)
    return jsonify({"workspace": _workspace_dict(org, membership)}), 200


@api_v1.route("/organizations/<organization_id>", methods=["PATCH"])
@login_required
def update_workspace_route(organization_id):
    membership = get_membership_or_403(organization_id)
    require_role(membership, WORKSPACE_ADMIN_ROLES)
    org = db.session.get(Organization, organization_id)
    p = _payload()
    if "name" in p:
        if not str(p["name"]).strip():
            raise _invalid("name", "Required")
        org.name = str(p["name"]).strip()[:255]
    if "timezone" in p:
        org.timezone = str(p["timezone"])[:64] or "UTC"
    if "accent_color" in p:
        from app.models.organization import ACCENT_CHOICES

        value = p["accent_color"]
        if value in (None, "", "arc"):
            org.accent_color = None
        elif value in ACCENT_CHOICES:
            org.accent_color = value
        else:
            raise _invalid("accent_color", f"Choose one of: {', '.join(ACCENT_CHOICES)}")
    if "max_concurrent_tasks" in p:
        try:
            value = int(p["max_concurrent_tasks"])
        except (TypeError, ValueError):
            raise _invalid("max_concurrent_tasks", "Must be a whole number")
        if not 1 <= value <= 12:
            raise _invalid("max_concurrent_tasks", "Must be between 1 and 12")
        org.max_concurrent_tasks = value
    if "default_run_budget_usd" in p:
        value = p["default_run_budget_usd"]
        if value in (None, ""):
            org.default_run_budget_usd = None
        else:
            try:
                value = float(value)
            except (TypeError, ValueError):
                raise _invalid("default_run_budget_usd", "Must be a number")
            if not 0.05 <= value <= 100:
                raise _invalid("default_run_budget_usd", "Must be between 0.05 and 100")
            org.default_run_budget_usd = value
    record_audit_event(organization_id, "workspace.updated", actor_user_id=current_user.id,
                       target_type="organization", target_id=organization_id)
    db.session.commit()
    return jsonify({"workspace": _workspace_dict(org, membership)}), 200


# ---- Team & invitations ---------------------------------------------------

@api_v1.route("/organizations/<organization_id>/members", methods=["GET"])
@login_required
def list_members_route(organization_id):
    membership = get_membership_or_403(organization_id)
    members = Membership.query.filter_by(organization_id=organization_id).all()
    invites = []
    if membership.role in WORKSPACE_ADMIN_ROLES:
        invites = [
            i.to_dict() for i in Invitation.query.filter(
                Invitation.organization_id == organization_id,
                Invitation.accepted_at.is_(None), Invitation.revoked_at.is_(None),
            ).order_by(Invitation.created_at.desc())
        ]
    return jsonify({
        "members": [{
            "membership_id": m.id, "user_id": m.user_id, "full_name": m.user.full_name,
            "email": m.user.email, "role": m.role, "role_label": ROLE_LABELS.get(m.role, m.role),
            "joined_at": m.created_at.isoformat() if m.created_at else None,
        } for m in members],
        "invitations": invites,
        "roles": [{"role": r, "label": ROLE_LABELS[r]} for r in VALID_ROLES],
    }), 200


@api_v1.route("/organizations/<organization_id>/members/<membership_id>", methods=["PATCH"])
@login_required
def update_member_route(organization_id, membership_id):
    me = get_membership_or_403(organization_id)
    require_role(me, WORKSPACE_ADMIN_ROLES)
    target = Membership.query.filter_by(id=membership_id, organization_id=organization_id).first()
    if target is None:
        raise NotFound("Member not found.")
    role = _payload().get("role")
    if role not in VALID_ROLES:
        raise _invalid("role", "Unknown role")
    if (role == ROLE_OWNER or target.role == ROLE_OWNER) and me.role != ROLE_OWNER:
        raise PermissionDenied("Only an owner can grant or change the owner role.")
    if target.role == ROLE_OWNER and role != ROLE_OWNER:
        owners = Membership.query.filter_by(organization_id=organization_id, role=ROLE_OWNER).count()
        if owners <= 1:
            raise Conflict("A workspace needs at least one owner.")
    target.role = role
    record_audit_event(organization_id, "member.role_changed", actor_user_id=current_user.id,
                       target_type="membership", target_id=target.id, metadata={"role": role})
    db.session.commit()
    return jsonify({"status": "ok"}), 200


@api_v1.route("/organizations/<organization_id>/members/<membership_id>", methods=["DELETE"])
@login_required
def remove_member_route(organization_id, membership_id):
    me = get_membership_or_403(organization_id)
    require_role(me, WORKSPACE_ADMIN_ROLES)
    target = Membership.query.filter_by(id=membership_id, organization_id=organization_id).first()
    if target is None:
        raise NotFound("Member not found.")
    if target.role == ROLE_OWNER:
        if me.role != ROLE_OWNER:
            raise PermissionDenied("Only an owner can remove an owner.")
        if Membership.query.filter_by(organization_id=organization_id, role=ROLE_OWNER).count() <= 1:
            raise Conflict("A workspace needs at least one owner.")
    db.session.delete(target)
    record_audit_event(organization_id, "member.removed", actor_user_id=current_user.id,
                       target_type="membership", target_id=membership_id)
    db.session.commit()
    return jsonify({"status": "ok"}), 200


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@api_v1.route("/organizations/<organization_id>/invitations", methods=["POST"])
@login_required
def create_invitation_route(organization_id):
    me = get_membership_or_403(organization_id)
    require_role(me, WORKSPACE_ADMIN_ROLES)
    p = _payload()
    email = (p.get("email") or "").strip().lower()
    role = p.get("role") or "viewer"
    if "@" not in email:
        raise _invalid("email", "A valid email is required")
    if role not in VALID_ROLES or (role == ROLE_OWNER and me.role != ROLE_OWNER):
        raise _invalid("role", "Not an assignable role")
    existing_user = User.query.filter_by(email=email).first()
    if existing_user and Membership.query.filter_by(organization_id=organization_id,
                                                    user_id=existing_user.id).first():
        raise Conflict("That person is already a member.")
    check_entitlement(organization_id, "seats")
    token = secrets.token_urlsafe(32)
    invite = Invitation(
        organization_id=organization_id, email=email, role=role, token_hash=_hash(token),
        invited_by_user_id=current_user.id,
        expires_at=utcnow() + timedelta(days=current_app.config.get("INVITATION_TTL_DAYS", 7)),
    )
    db.session.add(invite)
    record_audit_event(organization_id, "invitation.created", actor_user_id=current_user.id,
                       target_type="invitation", metadata={"role": role})
    db.session.commit()
    # No email provider is configured, so the admin shares this link
    # themselves. It's shown once; only its hash is stored.
    link = f"{current_app.config['FRONTEND_ORIGIN']}/accept-invite?token={token}"
    return jsonify({"invitation": invite.to_dict(), "invite_link": link,
                    "delivery": "manual, share this link; email sending is not configured"}), 201


@api_v1.route("/organizations/<organization_id>/invitations/<invitation_id>", methods=["DELETE"])
@login_required
def revoke_invitation_route(organization_id, invitation_id):
    me = get_membership_or_403(organization_id)
    require_role(me, WORKSPACE_ADMIN_ROLES)
    invite = Invitation.query.filter_by(id=invitation_id, organization_id=organization_id).first()
    if invite is None:
        raise NotFound("Invitation not found.")
    invite.revoked_at = utcnow()
    db.session.commit()
    return jsonify({"status": "ok"}), 200


@api_v1.route("/invitations/accept", methods=["POST"])
@login_required
def accept_invitation_route():
    invite = Invitation.query.filter_by(token_hash=_hash(_payload().get("token") or "")).first()
    now = utcnow()
    expires = invite.expires_at if invite else None
    if expires is not None and expires.tzinfo is None:
        from datetime import timezone

        expires = expires.replace(tzinfo=timezone.utc)
    if invite is None or invite.revoked_at or invite.accepted_at or expires < now:
        raise ValidationError("This invitation is invalid, expired or already used.")
    if invite.email != current_user.email.lower():
        raise PermissionDenied("This invitation was sent to a different email address.")
    if not Membership.query.filter_by(organization_id=invite.organization_id, user_id=current_user.id).first():
        db.session.add(Membership(organization_id=invite.organization_id, user_id=current_user.id, role=invite.role))
    invite.accepted_at = now
    record_audit_event(invite.organization_id, "invitation.accepted", actor_user_id=current_user.id,
                       target_type="invitation", target_id=invite.id)
    db.session.commit()
    login_user(current_user._get_current_object())
    return jsonify({"organization_id": invite.organization_id}), 200


# ---- Billing ---------------------------------------------------------------

@api_v1.route("/organizations/<organization_id>/billing", methods=["GET"])
@login_required
def billing_route(organization_id):
    get_membership_or_403(organization_id)
    sub = get_subscription(organization_id)
    db.session.commit()
    return jsonify({
        "subscription": sub.to_dict(),
        "usage": usage_against_entitlements(organization_id),
        "plans": [p.to_dict() for p in public_plans()],
        "payments": {"connected": False,
                     "note": "No payment processor is connected. Plan changes adjust limits only; nothing is charged."},
    }), 200


@api_v1.route("/organizations/<organization_id>/billing/plan", methods=["POST"])
@login_required
def change_plan_route(organization_id):
    me = get_membership_or_403(organization_id)
    require_role(me, (ROLE_OWNER,))
    sub = change_plan(organization_id, _payload().get("plan_code"))
    record_audit_event(organization_id, "billing.plan_changed", actor_user_id=current_user.id,
                       target_type="subscription", target_id=sub.id, metadata={"plan": sub.plan.code})
    db.session.commit()
    return jsonify({"subscription": sub.to_dict()}), 200


# ---- Automation policies & budgets ----------------------------------------

@api_v1.route("/organizations/<organization_id>/policies", methods=["GET"])
@login_required
def list_policies_route(organization_id):
    get_membership_or_403(organization_id)
    return jsonify({"policies": list_policies(organization_id)}), 200


@api_v1.route("/organizations/<organization_id>/policies/<action_type>", methods=["PATCH"])
@login_required
def set_policy_route(organization_id, action_type):
    me = get_membership_or_403(organization_id)
    require_role(me, WORKSPACE_ADMIN_ROLES)
    mode = _payload().get("mode")
    set_policy(organization_id, action_type, mode, current_user.id)
    record_audit_event(organization_id, "policy.changed", actor_user_id=current_user.id,
                       target_type="action_policy", metadata={"action_type": action_type, "mode": mode})
    db.session.commit()
    return jsonify({"policies": list_policies(organization_id)}), 200


@api_v1.route("/organizations/<organization_id>/agents/<agent_id>/settings", methods=["PATCH"])
@login_required
def agent_settings_route(organization_id, agent_id):
    me = get_membership_or_403(organization_id)
    require_role(me, WORKSPACE_ADMIN_ROLES)
    if get_agent(agent_id) is None:
        raise NotFound("Agent not found.")
    setting = AgentSetting.query.filter_by(organization_id=organization_id, agent_id=agent_id).first()
    if setting is None:
        setting = AgentSetting(organization_id=organization_id, agent_id=agent_id)
        db.session.add(setting)
    value = _payload().get("monthly_budget_usd")
    if value in (None, ""):
        setting.monthly_budget_usd = None
    else:
        try:
            value = float(value)
        except (TypeError, ValueError):
            raise _invalid("monthly_budget_usd", "Must be a number")
        if value < 0:
            raise _invalid("monthly_budget_usd", "Must not be negative")
        setting.monthly_budget_usd = value
    record_audit_event(organization_id, "agent.budget_changed", actor_user_id=current_user.id,
                       target_type="agent", target_id=agent_id)
    db.session.commit()
    return jsonify({"settings": setting.to_dict()}), 200


# ---- Notifications ---------------------------------------------------------

def _notification_query(organization_id):
    return Notification.query.filter(
        Notification.organization_id == organization_id,
        (Notification.user_id.is_(None)) | (Notification.user_id == current_user.id),
    )


@api_v1.route("/organizations/<organization_id>/notifications", methods=["GET"])
@login_required
def list_notifications_route(organization_id):
    get_membership_or_403(organization_id)
    query = _notification_query(organization_id)
    if request.args.get("unread") == "1":
        query = query.filter(Notification.read_at.is_(None))
    rows, page = _paginate(query.order_by(Notification.created_at.desc()), default=30)
    unread = _notification_query(organization_id).filter(Notification.read_at.is_(None)).count()
    return jsonify({"notifications": [n.to_dict() for n in rows], "unread_count": unread, "page": page}), 200


@api_v1.route("/organizations/<organization_id>/notifications/read", methods=["POST"])
@login_required
def mark_notifications_read_route(organization_id):
    get_membership_or_403(organization_id)
    ids = _payload().get("ids")
    query = _notification_query(organization_id).filter(Notification.read_at.is_(None))
    if ids:
        query = query.filter(Notification.id.in_(ids))
    for n in query.all():
        n.read_at = utcnow()
    db.session.commit()
    return jsonify({"status": "ok"}), 200


# ---- Knowledge library -----------------------------------------------------

@api_v1.route("/organizations/<organization_id>/knowledge", methods=["GET"])
@login_required
def list_knowledge_route(organization_id):
    get_membership_or_403(organization_id)
    query = KnowledgeEntry.query.filter_by(organization_id=organization_id)
    status = request.args.get("status")
    if status:
        query = query.filter_by(status=status)
    else:
        query = query.filter(KnowledgeEntry.status != "archived")
    q = (request.args.get("q") or "").strip()
    if q:
        like = f"%{q}%"
        query = query.filter(KnowledgeEntry.title.ilike(like) | KnowledgeEntry.body.ilike(like))
    rows, page = _paginate(query.order_by(KnowledgeEntry.updated_at.desc()))
    return jsonify({"entries": [r.to_dict() for r in rows], "page": page, "kinds": list(KNOWLEDGE_KINDS)}), 200


def _validate_knowledge(p: dict, partial=False) -> dict:
    data = {}
    for field, maxlen in (("title", 255), ("body", 20000), ("source_url", 1000)):
        if field in p:
            data[field] = (p.get(field) or "").strip()[:maxlen]
    if not partial and not data.get("title"):
        raise _invalid("title", "Required")
    if not partial and not data.get("body"):
        raise _invalid("body", "Required")
    if data.get("source_url") and not data["source_url"].startswith(("http://", "https://")):
        raise _invalid("source_url", "Must start with http:// or https://")
    if "kind" in p:
        if p["kind"] not in KNOWLEDGE_KINDS:
            raise _invalid("kind", "Unknown kind")
        data["kind"] = p["kind"]
    return data


@api_v1.route("/organizations/<organization_id>/knowledge", methods=["POST"])
@login_required
def create_knowledge_route(organization_id):
    me = get_membership_or_403(organization_id)
    require_role(me, OPERATOR_ROLES + ("contributor",))
    check_entitlement(organization_id, "knowledge_entries")
    data = _validate_knowledge(_payload())
    entry = KnowledgeEntry(organization_id=organization_id, created_by_user_id=current_user.id,
                           approved_by_user_id=current_user.id, status="approved", **data)
    db.session.add(entry)
    db.session.flush()
    record_audit_event(organization_id, "knowledge.created", actor_user_id=current_user.id,
                       target_type="knowledge_entry", target_id=entry.id)
    db.session.commit()
    return jsonify({"entry": entry.to_dict()}), 201


def _knowledge_or_404(organization_id, entry_id):
    entry = KnowledgeEntry.query.filter_by(id=entry_id, organization_id=organization_id).first()
    if entry is None:
        raise NotFound("Knowledge entry not found.")
    return entry


@api_v1.route("/organizations/<organization_id>/knowledge/<entry_id>", methods=["PATCH"])
@login_required
def update_knowledge_route(organization_id, entry_id):
    me = get_membership_or_403(organization_id)
    require_role(me, OPERATOR_ROLES + ("contributor",))
    entry = _knowledge_or_404(organization_id, entry_id)
    p = _payload()
    data = _validate_knowledge(p, partial=True)
    if data:
        for k, v in data.items():
            setattr(entry, k, v)
        entry.version += 1
    if "status" in p:
        if p["status"] not in ("approved", "archived"):
            raise _invalid("status", "Must be approved or archived")
        if p["status"] == "approved":
            require_role(me, OPERATOR_ROLES + ("approver",))
            entry.approved_by_user_id = current_user.id
        entry.status = p["status"]
    record_audit_event(organization_id, "knowledge.updated", actor_user_id=current_user.id,
                       target_type="knowledge_entry", target_id=entry.id,
                       metadata={"status": entry.status, "version": entry.version})
    db.session.commit()
    return jsonify({"entry": entry.to_dict()}), 200


# ---- Content calendar ------------------------------------------------------

def _parse_date(value, field):
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        raise _invalid(field, "Use YYYY-MM-DD")


@api_v1.route("/organizations/<organization_id>/calendar", methods=["GET"])
@login_required
def list_calendar_route(organization_id):
    get_membership_or_403(organization_id)
    start = _parse_date(request.args.get("from") or date.today().replace(day=1).isoformat(), "from")
    end = _parse_date(request.args.get("to") or (start + timedelta(days=62)).isoformat(), "to")
    rows = (
        CalendarEntry.query.filter(
            CalendarEntry.organization_id == organization_id,
            CalendarEntry.scheduled_date >= start, CalendarEntry.scheduled_date <= end,
        ).order_by(CalendarEntry.scheduled_date).all()
    )
    names = {c.id: c.name for c in Campaign.query.filter_by(organization_id=organization_id)}
    return jsonify({"entries": [{**r.to_dict(), "campaign_name": names.get(r.campaign_id)} for r in rows],
                    "statuses": list(CALENDAR_STATUSES)}), 200


@api_v1.route("/organizations/<organization_id>/calendar", methods=["POST"])
@login_required
def create_calendar_entry_route(organization_id):
    me = get_membership_or_403(organization_id)
    require_role(me, OPERATOR_ROLES + ("contributor",))
    p = _payload()
    if not (p.get("title") or "").strip():
        raise _invalid("title", "Required")
    if not (p.get("channel") or "").strip():
        raise _invalid("channel", "Required")
    campaign_id = p.get("campaign_id")
    if campaign_id and not Campaign.query.filter_by(id=campaign_id, organization_id=organization_id).first():
        raise NotFound("Campaign not found.")
    entry = CalendarEntry(
        organization_id=organization_id, campaign_id=campaign_id or None,
        scheduled_date=_parse_date(p.get("scheduled_date"), "scheduled_date"),
        channel=p["channel"].strip()[:64], title=p["title"].strip()[:255], body=p.get("body"),
        created_by_user_id=current_user.id,
    )
    db.session.add(entry)
    db.session.commit()
    return jsonify({"entry": entry.to_dict()}), 201


@api_v1.route("/organizations/<organization_id>/calendar/<entry_id>", methods=["PATCH"])
@login_required
def update_calendar_entry_route(organization_id, entry_id):
    me = get_membership_or_403(organization_id)
    require_role(me, OPERATOR_ROLES + ("contributor",))
    entry = CalendarEntry.query.filter_by(id=entry_id, organization_id=organization_id).first()
    if entry is None:
        raise NotFound("Calendar entry not found.")
    p = _payload()
    if "status" in p:
        if p["status"] not in CALENDAR_STATUSES:
            raise _invalid("status", "Unknown status")
        entry.status = p["status"]
        if p["status"] == "published_confirmed":
            record_audit_event(organization_id, "calendar.publication_confirmed_by_user",
                               actor_user_id=current_user.id, target_type="calendar_entry", target_id=entry.id)
    if "scheduled_date" in p:
        entry.scheduled_date = _parse_date(p["scheduled_date"], "scheduled_date")
    for field in ("title", "channel", "body"):
        if field in p and p[field] is not None:
            setattr(entry, field, str(p[field]))
    db.session.commit()
    return jsonify({"entry": entry.to_dict()}), 200


@api_v1.route("/organizations/<organization_id>/calendar/<entry_id>", methods=["DELETE"])
@login_required
def delete_calendar_entry_route(organization_id, entry_id):
    me = get_membership_or_403(organization_id)
    require_role(me, OPERATOR_ROLES + ("contributor",))
    entry = CalendarEntry.query.filter_by(id=entry_id, organization_id=organization_id).first()
    if entry is None:
        raise NotFound("Calendar entry not found.")
    db.session.delete(entry)
    db.session.commit()
    return jsonify({"status": "ok"}), 200


@api_v1.route("/organizations/<organization_id>/calendar/from-deliverable", methods=["POST"])
@login_required
def calendar_from_deliverable_route(organization_id):
    """Turn a Social Media agent's calendar into dated entries. Posts are
    spread one per day from start_date in the agent's order; the agent's
    own 'day' label is kept in the body for reference."""

    me = get_membership_or_403(organization_id)
    require_role(me, OPERATOR_ROLES + ("contributor",))
    p = _payload()
    deliverable = Deliverable.query.filter_by(id=p.get("deliverable_id"), organization_id=organization_id).first()
    if deliverable is None or deliverable.deliverable_type != "social_calendar" or not deliverable.current_version:
        raise _invalid("deliverable_id", "Must be a social calendar deliverable")
    if CalendarEntry.query.filter_by(organization_id=organization_id, deliverable_id=deliverable.id).first():
        raise Conflict("This social calendar is already on the content calendar.")
    start = _parse_date(p.get("start_date"), "start_date")
    content = json.loads(deliverable.current_version.content_json)
    created = []
    for index, post in enumerate((content.get("calendar_entries") or [])[:60]):
        caption = str(post.get("caption") or "").strip()
        if not caption:
            continue
        tags = " ".join(post.get("hashtags") or [])
        body = "\n\n".join(x for x in (caption, tags, f"CTA: {post['cta']}" if post.get("cta") else "",
                                       f"Agent's slot: {post.get('day')}") if x)
        entry = CalendarEntry(
            organization_id=organization_id, campaign_id=deliverable.campaign_id, deliverable_id=deliverable.id,
            scheduled_date=start + timedelta(days=index), channel=str(post.get("channel") or "social")[:64],
            title=caption[:120], body=body, created_by_user_id=current_user.id,
        )
        db.session.add(entry)
        created.append(entry)
    record_audit_event(organization_id, "calendar.imported", actor_user_id=current_user.id,
                       target_type="deliverable", target_id=deliverable.id, metadata={"entries": len(created)})
    db.session.commit()
    return jsonify({"created": len(created)}), 201


# ---- Content index (all deliverables) --------------------------------------

@api_v1.route("/organizations/<organization_id>/deliverables", methods=["GET"])
@login_required
def list_all_deliverables_route(organization_id):
    get_membership_or_403(organization_id)
    query = Deliverable.query.filter_by(organization_id=organization_id)
    if request.args.get("type"):
        query = query.filter(Deliverable.deliverable_type.in_(request.args["type"].split(",")))
    if request.args.get("review_status"):
        query = query.filter_by(review_status=request.args["review_status"])
    if request.args.get("campaign_id"):
        query = query.filter_by(campaign_id=request.args["campaign_id"])
    rows, page = _paginate(query.order_by(Deliverable.created_at.desc()))
    names = {c.id: c.name for c in Campaign.query.filter_by(organization_id=organization_id)}
    return jsonify({
        "deliverables": [{**d.to_dict(), "campaign_name": names.get(d.campaign_id),
                          "created_at": d.created_at.isoformat() if d.created_at else None} for d in rows],
        "page": page,
    }), 200


# ---- Approvals & runs ------------------------------------------------------

@api_v1.route("/organizations/<organization_id>/approvals/<approval_id>/revoke", methods=["POST"])
@login_required
def revoke_approval_route(organization_id, approval_id):
    membership = get_membership_or_403(organization_id)
    approval = revoke_approval(organization_id, approval_id, membership)
    return jsonify({"approval": approval.to_dict()}), 200


@api_v1.route("/organizations/<organization_id>/runs/<run_id>/approve-start", methods=["POST"])
@login_required
def approve_run_start_route(organization_id, run_id):
    membership = get_membership_or_403(organization_id)
    if not membership.can_approve_external_actions():
        raise PermissionDenied("Your role does not permit approval decisions.")
    run = approve_run_start(organization_id, run_id, current_user.id)
    return jsonify({"workflow_run": run.to_dict()}), 200


# ---- Integrations ----------------------------------------------------------

@api_v1.route("/organizations/<organization_id>/integrations/catalog", methods=["GET"])
@login_required
def integration_catalog_route(organization_id):
    get_membership_or_403(organization_id)
    disabled = {
        i.provider for i in Integration.query.filter_by(organization_id=organization_id, state="disabled")
    }
    # Only manual-export destinations have a per-workspace switch; webhook-based
    # automations are switched on by adding a webhook endpoint.
    items = [{**c, "enabled": c["key"] not in disabled if c["status"] == AVAILABLE and c["key"].startswith("manual_export:") else None}
             for c in CATALOG]
    return jsonify({"integrations": items}), 200


@api_v1.route("/organizations/<organization_id>/integrations/<path:key>", methods=["PATCH"])
@login_required
def toggle_integration_route(organization_id, key):
    me = get_membership_or_403(organization_id)
    require_role(me, WORKSPACE_ADMIN_ROLES)
    item = next((c for c in CATALOG if c["key"] == key), None)
    if item is None or item["status"] != AVAILABLE:
        raise ValidationError("Only available integrations can be enabled or disabled.")
    enabled = bool(_payload().get("enabled"))
    row = Integration.query.filter_by(organization_id=organization_id, provider=key).first()
    if row is None:
        row = Integration(organization_id=organization_id, provider=key, account_label=item["name"])
        db.session.add(row)
    row.state = "connected" if enabled else "disabled"
    record_audit_event(organization_id, f"integration.{'enabled' if enabled else 'disabled'}",
                       actor_user_id=current_user.id, target_type="integration", metadata={"key": key})
    db.session.commit()
    return jsonify({"key": key, "enabled": enabled}), 200
