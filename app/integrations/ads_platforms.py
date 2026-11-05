"""Ad platform connectors for human-approved launches (D19).

Only the built-in *test* platform exists today. It never calls anything or
spends money; spend accrues on a clock so the daily cap, monitoring and kill
switch can be exercised end to end. Meta Marketing API and Google Ads API
connectors implement the same four methods once the user has API access
(Meta: ads_management via app review; Google: an approved developer token)."""

from datetime import datetime, timezone

from flask import current_app

from app.extensions import db
from app.models.ads import SandboxAdCampaign
from app.models.base import utcnow


class AdPlatformError(Exception):
    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


class SandboxAdsPlatform:
    name = "sandbox"
    label = "ARC test platform (no real money)"

    def _get(self, external_id: str) -> SandboxAdCampaign:
        c = db.session.get(SandboxAdCampaign, external_id)
        if c is None:
            raise AdPlatformError("Campaign not found on the test platform.")
        return c

    def create(self, *, name: str, daily_budget: float, idempotency_key: str) -> str:
        existing = SandboxAdCampaign.query.filter_by(idempotency_key=idempotency_key).first()
        if existing:
            return existing.id
        c = SandboxAdCampaign(idempotency_key=idempotency_key, name=name[:200], daily_budget=daily_budget,
                              status="ACTIVE", active_since=utcnow())
        db.session.add(c)
        db.session.flush()
        return c.id

    def _settle(self, c: SandboxAdCampaign) -> None:
        if c.status == "ACTIVE" and c.active_since:
            c.accrued_before = self._accrued(c)
            c.active_since = None

    def _accrued(self, c: SandboxAdCampaign) -> float:
        total = c.accrued_before or 0.0
        if c.status == "ACTIVE" and c.active_since:
            since = c.active_since if c.active_since.tzinfo else c.active_since.replace(tzinfo=timezone.utc)
            speed = float(current_app.config.get("ADS_SANDBOX_SPEED", 1.0))
            total += (utcnow() - since).total_seconds() * speed * c.daily_budget / 86400
        return total

    def pause(self, external_id: str) -> None:
        c = self._get(external_id)
        self._settle(c)
        c.status = "PAUSED"

    def resume(self, external_id: str) -> None:
        c = self._get(external_id)
        if c.status == "PAUSED":
            c.status, c.active_since = "ACTIVE", utcnow()

    def archive(self, external_id: str) -> None:
        c = self._get(external_id)
        self._settle(c)
        c.status = "ARCHIVED"

    def status(self, external_id: str) -> dict:
        """Platforms cap spend at the daily budget themselves; so does this one."""
        c = self._get(external_id)
        total = self._accrued(c)
        midnight = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        created = c.created_at if c.created_at.tzinfo else c.created_at.replace(tzinfo=timezone.utc)
        today = total if created >= midnight else min(total, c.daily_budget)
        return {"status": c.status, "spend_today": min(today, c.daily_budget), "spend_total": total}


PLATFORMS = {"sandbox": SandboxAdsPlatform}
PLANNED = {"meta": "Meta Ads (Facebook & Instagram) — needs Marketing API access", "google": "Google Ads — needs an approved developer token"}
