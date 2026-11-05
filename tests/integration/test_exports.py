import io

from app.extensions import db
from app.services.deliverable_service import create_deliverable_with_first_version
from tests.conftest import complete_profile, create_campaign, create_org, register_and_login

CALENDAR = {"posts": [
    {"date": "2026-11-10", "channel": "instagram", "caption": "Meet Trail 30", "asset_brief": "Pack on a ridge at dawn"},
    {"date": "2026-11-12", "channel": "linkedin", "caption": "=HYPERLINK(\"x\")", "asset_brief": "Founder photo"},
], "notes": ["Post at 6pm local time"]}


def _png(color=(10, 37, 64)):
    from PIL import Image

    out = io.BytesIO()
    Image.new("RGB", (120, 40), color).save(out, format="PNG")
    return out.getvalue()


def _setup(app, client, email="owner@example.com"):
    register_and_login(client, email=email)
    org = create_org(client)
    complete_profile(client, org["id"])
    camp = create_campaign(client, org["id"])
    with app.app_context():
        d = create_deliverable_with_first_version(organization_id=org["id"], campaign_id=camp["id"], workflow_run_id=None,
                                                  deliverable_type="social_calendar", content=CALENDAR)
        db.session.commit()
        did = d.id
    return org, did


def test_brand_kit_validation_and_logo(app, client, tmp_path):
    app.config["UPLOAD_DIR"] = str(tmp_path)
    org, _ = _setup(app, client)
    base = f"/api/v1/organizations/{org['id']}"
    bad = client.patch(f"{base}/business-profile", json={"brand_colors": "#123, purple"})
    assert bad.status_code == 400 and bad.get_json()["error"]["details"][0]["field"] == "brand_colors"
    ok = client.patch(f"{base}/business-profile", json={"brand_colors": "0a2540, #635bff", "brand_persona": "A trail guide",
                                                       "brand_fonts": "Inter, Fraunces"}).get_json()["business_profile"]
    assert ok["brand_colors"] == "#0A2540,#635BFF" and ok["brand_persona"] == "A trail guide"
    up = client.post(f"{base}/documents", data={"file": (io.BytesIO(_png()), "logo.png", "image/png")},
                     content_type="multipart/form-data").get_json()["document"]
    txt = client.post(f"{base}/documents", data={"file": (io.BytesIO(b"hello world"), "notes.txt", "text/plain")},
                      content_type="multipart/form-data").get_json()["document"]
    assert client.patch(f"{base}/business-profile", json={"logo_document_id": txt["id"]}).status_code == 400
    assert client.patch(f"{base}/business-profile", json={"logo_document_id": up["id"]}).status_code == 200


def test_exports_open_in_their_apps_with_brand(app, client, tmp_path):
    app.config["UPLOAD_DIR"] = str(tmp_path)
    org, did = _setup(app, client)
    base = f"/api/v1/organizations/{org['id']}"
    logo = client.post(f"{base}/documents", data={"file": (io.BytesIO(_png()), "logo.png", "image/png")},
                       content_type="multipart/form-data").get_json()["document"]
    client.patch(f"{base}/business-profile", json={"brand_colors": "#0A2540,#635BFF", "logo_document_id": logo["id"]})

    x = client.get(f"{base}/deliverables/{did}/export?format=xlsx")
    assert x.status_code == 200 and "attachment" in x.headers["Content-Disposition"] and x.headers["Content-Disposition"].endswith('.xlsx"')
    from openpyxl import load_workbook

    wb = load_workbook(io.BytesIO(x.data))
    ws = wb.active
    values = [c.value for row in ws.iter_rows() for c in row if c.value]
    assert "Meet Trail 30" in values
    assert "'=HYPERLINK(\"x\")" in values  # formula neutralised
    fills = {c.fill.fgColor.rgb for row in ws.iter_rows() for c in row if c.fill and c.fill.fill_type == "solid"}
    assert any(str(f).endswith("0A2540") for f in fills)
    assert ws._images  # logo embedded

    p = client.get(f"{base}/deliverables/{did}/export?format=pptx")
    from pptx import Presentation

    prs = Presentation(io.BytesIO(p.data))
    texts = [sh.text_frame.text for s in prs.slides for sh in s.shapes if sh.has_text_frame]
    tables = [sh for s in prs.slides for sh in s.shapes if sh.has_table]
    assert len(prs.slides) >= 3 and any("Social calendar" in t for t in texts) and tables

    pdf = client.get(f"{base}/deliverables/{did}/export?format=pdf")
    assert pdf.status_code == 200 and pdf.data[:5] == b"%PDF-" and pdf.mimetype == "application/pdf"

    assert client.get(f"{base}/deliverables/{did}/export?format=docx").status_code == 400

    rep = client.get(f"{base}/reports/monthly/export?month=2026-11&format=pptx")
    assert rep.status_code == 200 and len(Presentation(io.BytesIO(rep.data)).slides) >= 2
    assert client.get(f"{base}/reports/monthly/export?month=2026-11&format=pdf").data[:5] == b"%PDF-"


def test_exports_are_tenant_scoped(app, client):
    org, did = _setup(app, client)
    client.post("/api/v1/auth/logout")
    register_and_login(client, email="intruder@example.com")
    create_org(client, name="Other")
    base = f"/api/v1/organizations/{org['id']}"
    assert client.get(f"{base}/deliverables/{did}/export?format=xlsx").status_code in (403, 404)
    assert client.get(f"{base}/reports/monthly/export?month=2026-11&format=pdf").status_code in (403, 404)
