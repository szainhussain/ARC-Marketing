"""Branded Excel / PowerPoint / PDF exports of deliverables and reports.

Content is first turned into neutral *blocks* (heading, paragraph, bullets,
table), then rendered in the client's Brand Kit: primary colour for headers,
their logo on the cover, their business name in the footer. Pure Python
(openpyxl, python-pptx, reportlab); no network, no AI calls.
"""

import io
from dataclasses import dataclass, field

FORMATS = {
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "pdf": "application/pdf",
}
DEFAULT_PRIMARY = "#1F2A44"
DEFAULT_ACCENT = "#2563EB"
MAX_CELL = 32000  # Excel's per-cell limit is 32,767 characters


@dataclass
class Brand:
    name: str = ""
    primary: str = DEFAULT_PRIMARY
    accent: str = DEFAULT_ACCENT
    logo_png: bytes | None = None


@dataclass
class Block:
    kind: str  # heading | paragraph | bullets | table
    text: str = ""
    items: list[str] = field(default_factory=list)
    columns: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)


@dataclass
class Document:
    title: str
    subtitle: str
    blocks: list[Block]


# ---- Content -> blocks ------------------------------------------------------

def humanize(key: str) -> str:
    return key.replace("_", " ").strip().capitalize()


def _text(v) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "Yes" if v else "No"
    if isinstance(v, (int, float)):
        return f"{v:,.2f}".rstrip("0").rstrip(".") if isinstance(v, float) else f"{v:,}"
    if isinstance(v, list):
        return "; ".join(_text(x) for x in v)
    if isinstance(v, dict):
        return "; ".join(f"{humanize(k)}: {_text(x)}" for k, x in v.items())
    return str(v)


def content_to_blocks(content: dict) -> list[Block]:
    """Generic walk over any deliverable schema: strings become paragraphs,
    string lists become bullets, lists of objects become tables."""

    blocks: list[Block] = []
    for key, value in (content or {}).items():
        if value in (None, "", [], {}):
            continue
        blocks.append(Block("heading", text=humanize(key)))
        if isinstance(value, list) and value and all(isinstance(x, dict) for x in value):
            cols: list[str] = []
            for row in value:
                for k in row:
                    if k not in cols:
                        cols.append(k)
            blocks.append(Block("table", columns=[humanize(c) for c in cols],
                                rows=[[_text(r.get(c)) for c in cols] for r in value]))
        elif isinstance(value, list):
            blocks.append(Block("bullets", items=[_text(x) for x in value]))
        elif isinstance(value, dict):
            blocks.append(Block("table", columns=["Item", "Detail"],
                                rows=[[humanize(k), _text(v)] for k, v in value.items()]))
        else:
            blocks.append(Block("paragraph", text=_text(value)))
    return blocks


def monthly_report_to_blocks(report: dict) -> list[Block]:
    from app.services.results_service import METRIC_FIELDS  # noqa: F401 (documents the fields used)

    t = report["results"]["totals"]
    money = lambda v: "—" if v is None else f"${v:,.2f}"  # noqa: E731
    num = lambda v: "—" if v is None else f"{v:,.0f}"  # noqa: E731
    blocks = [Block("heading", text="Results"),
              Block("table", columns=["Metric", "Value"], rows=[
                  ["Spend", money(t.get("spend"))], ["Leads", num(t.get("leads"))],
                  ["Cost per lead", money(t.get("cost_per_lead"))], ["Conversions", num(t.get("conversions"))],
                  ["Revenue", money(t.get("revenue"))],
                  ["Return on ad spend", "—" if t.get("roas") is None else f"{t['roas']:.2f}x"]])]
    if report.get("highlights"):
        blocks += [Block("heading", text="Highlights"), Block("bullets", items=report["highlights"])]
    by_campaign = report["results"].get("by_campaign") or []
    if by_campaign:
        blocks += [Block("heading", text="By campaign"), Block("table",
                   columns=["Campaign", "Spend", "Leads", "Cost / lead", "Revenue", "ROAS"],
                   rows=[[c.get("campaign_name") or "", money(c.get("spend")), num(c.get("leads")),
                          money(c.get("cost_per_lead")), money(c.get("revenue")),
                          "—" if c.get("roas") is None else f"{c['roas']:.2f}x"] for c in by_campaign])]
    a = report["activity"]
    blocks += [Block("heading", text="What your marketing department did"),
               Block("table", columns=["Activity", "Count"], rows=[
                   ["Campaign runs completed", num(a["runs_completed"])],
                   ["Deliverables produced", num(a["deliverables_created"])],
                   ["Approvals given", num(a["approvals_given"])],
                   ["Exported for publishing", num(a["exports"])],
                   ["Confirmed published", num(a["confirmed_published"])]])]
    if report.get("learnings"):
        blocks += [Block("heading", text="What we learned"),
                   Block("bullets", items=[f"{l['title']} ({humanize(l['kind'])})" for l in report["learnings"]])]
    blocks.append(Block("paragraph", text="Results are entered by your team, not measured by ARC."))
    return blocks


# ---- Colour helpers ---------------------------------------------------------

def _rgb(hex_color: str) -> tuple[int, int, int]:
    h = (hex_color or DEFAULT_PRIMARY).lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _on(hex_color: str) -> str:
    """Black or white text, whichever reads better on this colour."""

    r, g, b = (c / 255 for c in _rgb(hex_color))
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return "#111111" if lum > 0.55 else "#FFFFFF"


def _safe_cell(v: str) -> str:
    # Spreadsheet apps execute cells that start with these as formulas.
    return "'" + v if v[:1] in ("=", "+", "-", "@", "\t", "\r") else v[:MAX_CELL]


# ---- Renderers --------------------------------------------------------------

def render_xlsx(doc: Document, brand: Brand) -> bytes:
    from openpyxl import Workbook
    from openpyxl.drawing.image import Image as XLImage
    from openpyxl.styles import Alignment, Font, PatternFill

    wb = Workbook()
    ws = wb.active
    ws.title = "Summary"
    head_fill = PatternFill("solid", fgColor=brand.primary.lstrip("#"))
    head_font = Font(bold=True, color=_on(brand.primary).lstrip("#"))
    row = 1
    if brand.logo_png:
        img = XLImage(io.BytesIO(brand.logo_png))
        scale = 48 / max(1, img.height)
        img.height, img.width = 48, int(img.width * scale)
        ws.add_image(img, "A1")
        row = 4
    ws.cell(row, 1, _safe_cell(doc.title)).font = Font(bold=True, size=16, color=brand.primary.lstrip("#"))
    ws.cell(row + 1, 1, _safe_cell(doc.subtitle)).font = Font(italic=False, color="666666")
    row += 3
    widths: dict[int, int] = {1: 28}
    tables = 0
    for b in doc.blocks:
        if b.kind == "heading":
            ws.cell(row, 1, _safe_cell(b.text)).font = Font(bold=True, size=13, color=brand.primary.lstrip("#"))
            row += 1
        elif b.kind == "paragraph":
            c = ws.cell(row, 1, _safe_cell(b.text))
            c.alignment = Alignment(wrap_text=True, vertical="top")
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
            ws.row_dimensions[row].height = max(15, min(300, 15 * (len(b.text) // 110 + 1)))
            row += 2
        elif b.kind == "bullets":
            for item in b.items:
                ws.cell(row, 1, _safe_cell("• " + item)).alignment = Alignment(wrap_text=True)
                ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
                row += 1
            row += 1
        elif b.kind == "table":
            tables += 1
            for j, col in enumerate(b.columns, start=1):
                c = ws.cell(row, j, _safe_cell(col))
                c.fill, c.font = head_fill, head_font
                widths[j] = max(widths.get(j, 12), min(60, len(col) + 4))
            row += 1
            for r in b.rows:
                for j, v in enumerate(r, start=1):
                    c = ws.cell(row, j, _safe_cell(v))
                    c.alignment = Alignment(wrap_text=True, vertical="top")
                    widths[j] = max(widths.get(j, 12), min(60, len(v) + 2))
                row += 1
            row += 1
    for j, w in widths.items():
        ws.column_dimensions[chr(64 + min(j, 26))].width = w
    ws.cell(row + 1, 1, _safe_cell(f"Prepared by ARC for {brand.name}" if brand.name else "Prepared by ARC")).font = Font(size=9, color="888888")
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def render_pptx(doc: Document, brand: Brand) -> bytes:
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.util import Inches, Pt

    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    blank = prs.slide_layouts[6]
    primary, on_primary, accent = RGBColor(*_rgb(brand.primary)), RGBColor(*_rgb(_on(brand.primary))), RGBColor(*_rgb(brand.accent))
    ink = RGBColor(0x22, 0x22, 0x22)

    def textbox(slide, x, y, w, h, text, size, bold=False, color=ink):
        tb = slide.shapes.add_textbox(x, y, w, h)
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = text
        p.font.size, p.font.bold, p.font.color.rgb = Pt(size), bold, color
        return tf

    def footer(slide):
        textbox(slide, Inches(0.6), Inches(7.0), Inches(9), Inches(0.3),
                f"{brand.name} · Prepared by ARC" if brand.name else "Prepared by ARC", 10, color=RGBColor(0x88, 0x88, 0x88))

    # Cover
    s = prs.slides.add_slide(blank)
    bg = s.shapes.add_shape(1, 0, 0, prs.slide_width, prs.slide_height)
    bg.fill.solid()
    bg.fill.fore_color.rgb = primary
    bg.line.fill.background()
    if brand.logo_png:
        s.shapes.add_picture(io.BytesIO(brand.logo_png), Inches(0.8), Inches(0.7), height=Inches(0.9))
    textbox(s, Inches(0.8), Inches(2.6), Inches(11.5), Inches(1.6), doc.title, 40, True, on_primary)
    textbox(s, Inches(0.8), Inches(4.2), Inches(11.5), Inches(0.8), doc.subtitle, 18, False, on_primary)

    def new_slide(title):
        sl = prs.slides.add_slide(blank)
        bar = sl.shapes.add_shape(1, 0, 0, Inches(0.18), prs.slide_height)
        bar.fill.solid()
        bar.fill.fore_color.rgb = accent
        bar.line.fill.background()
        textbox(sl, Inches(0.6), Inches(0.4), Inches(12), Inches(0.9), title, 28, True, primary)
        footer(sl)
        return sl

    # One slide per heading section; long lists and tables continue on extra slides.
    sections: list[tuple[str, list[Block]]] = []
    for b in doc.blocks:
        if b.kind == "heading" or not sections:
            sections.append((b.text if b.kind == "heading" else doc.title, []))
            if b.kind == "heading":
                continue
        sections[-1][1].append(b)
    for title, body in sections:
        for b in body:
            if b.kind in ("paragraph", "bullets"):
                lines = [b.text] if b.kind == "paragraph" else b.items
                for start in range(0, max(1, len(lines)), 8):
                    sl = new_slide(title)
                    tf = textbox(sl, Inches(0.6), Inches(1.5), Inches(12), Inches(5.2), "", 18)
                    for i, line in enumerate(lines[start:start + 8]):
                        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                        p.text = ("• " if b.kind == "bullets" else "") + line[:900]
                        p.font.size, p.font.color.rgb = Pt(18 if b.kind == "bullets" else 16), ink
                        p.space_after = Pt(8)
            elif b.kind == "table":
                for start in range(0, max(1, len(b.rows)), 8):
                    sl = new_slide(title)
                    chunk = b.rows[start:start + 8]
                    cols = b.columns[:7]
                    shape = sl.shapes.add_table(len(chunk) + 1, len(cols), Inches(0.6), Inches(1.5),
                                                Inches(12.1), Inches(0.4) * (len(chunk) + 1))
                    t = shape.table
                    for j, col in enumerate(cols):
                        cell = t.cell(0, j)
                        cell.text = col
                        cell.fill.solid()
                        cell.fill.fore_color.rgb = primary
                        para = cell.text_frame.paragraphs[0]
                        para.font.bold, para.font.size, para.font.color.rgb = True, Pt(12), on_primary
                    for i, r in enumerate(chunk, start=1):
                        for j in range(len(cols)):
                            cell = t.cell(i, j)
                            cell.text = (r[j] if j < len(r) else "")[:400]
                            cell.text_frame.paragraphs[0].font.size = Pt(11)
    out = io.BytesIO()
    prs.save(out)
    return out.getvalue()


def render_pdf(doc: Document, brand: Brand) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Image as RLImage
    from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from xml.sax.saxutils import escape

    primary = colors.HexColor(brand.primary)
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Title"], textColor=primary, alignment=0, fontSize=22, leading=26)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], textColor=primary, spaceBefore=12)
    body = ParagraphStyle("b", parent=styles["BodyText"], fontSize=10, leading=14)
    cell = ParagraphStyle("c", parent=body, fontSize=8.5, leading=11)
    out = io.BytesIO()

    def on_page(canvas, d):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawString(18 * mm, 10 * mm, f"{brand.name} · Prepared by ARC" if brand.name else "Prepared by ARC")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, str(canvas.getPageNumber()))
        canvas.restoreState()

    story = []
    if brand.logo_png:
        img = RLImage(io.BytesIO(brand.logo_png))
        ratio = img.imageWidth / max(1, img.imageHeight)
        img.drawHeight, img.drawWidth = 14 * mm, 14 * mm * ratio
        img.hAlign = "LEFT"
        story += [img, Spacer(1, 6 * mm)]
    story += [Paragraph(escape(doc.title), h1), Paragraph(escape(doc.subtitle), body), Spacer(1, 6 * mm)]
    width = A4[0] - 36 * mm
    for b in doc.blocks:
        if b.kind == "heading":
            story.append(Paragraph(escape(b.text), h2))
        elif b.kind == "paragraph":
            story.append(Paragraph(escape(b.text).replace("\n", "<br/>"), body))
        elif b.kind == "bullets":
            story.append(ListFlowable([ListItem(Paragraph(escape(i), body)) for i in b.items], bulletType="bullet"))
        elif b.kind == "table":
            data = [[Paragraph(f"<b>{escape(c)}</b>", cell) for c in b.columns]]
            data += [[Paragraph(escape(v), cell) for v in r] for r in b.rows]
            t = Table(data, colWidths=[width / max(1, len(b.columns))] * len(b.columns), repeatRows=1)
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), primary),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor(_on(brand.primary))),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CCCCCC")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            # Header text colour also needs to apply to the Paragraphs.
            for p in data[0]:
                p.style = ParagraphStyle("ch", parent=cell, textColor=colors.HexColor(_on(brand.primary)))
            story.append(t)
        story.append(Spacer(1, 3 * mm))
    SimpleDocTemplate(out, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=18 * mm,
                      bottomMargin=18 * mm, title=doc.title, author=brand.name or "ARC").build(
        story, onFirstPage=on_page, onLaterPages=on_page)
    return out.getvalue()


RENDERERS = {"xlsx": render_xlsx, "pptx": render_pptx, "pdf": render_pdf}


def render(fmt: str, doc: Document, brand: Brand) -> bytes:
    return RENDERERS[fmt](doc, brand)
