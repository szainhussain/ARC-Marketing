"""Builds branded exports for a workspace: loads its Brand Kit (palette,
name, logo) and renders deliverables or the monthly report."""

import io
import json
import logging
import re

from app.exports.documents import FORMATS, Brand, Document, content_to_blocks, monthly_report_to_blocks, render
from app.models.business_profile import BusinessProfile
from app.models.campaign import Campaign
from app.models.document import Document as Asset
from app.models.organization import Organization
from app.services.business_profile_service import brand_palette
from app.services.deliverable_service import get_deliverable_or_404
from app.services.errors import ValidationError

log = logging.getLogger(__name__)
MAX_LOGO_BYTES = 5 * 1024 * 1024


def _check_format(fmt: str) -> str:
    fmt = (fmt or "").lower()
    if fmt not in FORMATS:
        raise ValidationError("Please correct the highlighted fields.",
                              details=[{"field": "format", "issue": "Use xlsx, pptx or pdf"}])
    return fmt


def _logo_png(organization_id: str, profile) -> bytes | None:
    if not profile or not profile.logo_document_id:
        return None
    asset = Asset.query.filter_by(id=profile.logo_document_id, organization_id=organization_id, status="stored").first()
    if asset is None:
        return None
    try:
        from PIL import Image

        from app.storage import get_storage

        raw = get_storage().get(asset.storage_key)
        if len(raw) > MAX_LOGO_BYTES:
            return None
        img = Image.open(io.BytesIO(raw))
        img.thumbnail((800, 800))
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGBA")
        out = io.BytesIO()
        img.save(out, format="PNG")
        return out.getvalue()
    except Exception:  # noqa: BLE001 - a broken logo must not block the export
        log.warning("Could not load logo for workspace %s", organization_id, exc_info=True)
        return None


def load_brand(organization_id: str) -> Brand:
    from app.extensions import db

    org = db.session.get(Organization, organization_id)
    profile = BusinessProfile.query.filter_by(organization_id=organization_id).first()
    palette = brand_palette(profile)
    brand = Brand(name=(profile.business_name if profile and profile.business_name else (org.name if org else "")))
    if palette:
        brand.primary = palette[0]
        brand.accent = palette[1] if len(palette) > 1 else palette[0]
    brand.logo_png = _logo_png(organization_id, profile)
    return brand


def _filename(*parts: str) -> str:
    base = "-".join(p for p in parts if p)
    return re.sub(r"[^A-Za-z0-9._-]+", "-", base).strip("-").lower()[:120] or "arc-export"


def schema_order(content, schema_cls):
    """Stored content is key-sorted; put it back in the schema's declared order
    (the order the agent writes it), including nested objects in lists."""

    from marshmallow import fields as mf

    if schema_cls is None or not isinstance(content, dict):
        return content
    declared = schema_cls._declared_fields
    out = {}
    for name in list(declared) + [k for k in content if k not in declared]:
        if name not in content:
            continue
        value, field = content[name], declared.get(name)
        nested = None
        if isinstance(field, mf.List) and isinstance(field.inner, mf.Nested):
            nested = field.inner.nested
        elif isinstance(field, mf.Nested):
            nested = field.nested
        if nested is not None and not isinstance(nested, type):
            nested = type(nested)
        if nested is not None and isinstance(value, list):
            value = [schema_order(v, nested) for v in value]
        elif nested is not None:
            value = schema_order(value, nested)
        out[name] = value
    return out


def export_deliverable(organization_id: str, deliverable_id: str, fmt: str) -> tuple[bytes, str, str]:
    fmt = _check_format(fmt)
    d = get_deliverable_or_404(organization_id, deliverable_id)
    version = d.current_version
    from app.ai.schemas import SCHEMAS_BY_TASK_TYPE

    content = schema_order(json.loads(version.content_json) if version else {}, SCHEMAS_BY_TASK_TYPE.get(d.deliverable_type))
    campaign = Campaign.query.filter_by(id=d.campaign_id, organization_id=organization_id).first()
    title = d.deliverable_type.replace("_", " ").capitalize()
    subtitle = f"{campaign.name if campaign else ''} · Version {version.version_number if version else 1} · {(d.review_status or '').replace('_', ' ').capitalize()}"
    doc = Document(title=title, subtitle=subtitle, blocks=content_to_blocks(content))
    data = render(fmt, doc, load_brand(organization_id))
    return data, f"{_filename(campaign.name if campaign else '', d.deliverable_type)}.{fmt}", FORMATS[fmt]


def export_monthly_report(organization_id: str, month: str, fmt: str) -> tuple[bytes, str, str]:
    from app.services.results_service import monthly_report

    fmt = _check_format(fmt)
    report = monthly_report(organization_id, month)
    brand = load_brand(organization_id)
    doc = Document(title=f"Marketing report · {report['month']}",
                   subtitle=f"{report['workspace_name']} · {report['period']['start']} to {report['period']['end']}",
                   blocks=monthly_report_to_blocks(report))
    return render(fmt, doc, brand), f"{_filename(brand.name, 'marketing-report', report['month'])}.{fmt}", FORMATS[fmt]
