"""Render the job-match Markdown report into a single, styled PDF (bytes).

Uses reportlab's Platypus flowables so text wraps and paginates automatically.
Supports the Markdown subset the agents actually emit: headings, bullet and
numbered lists, tables, horizontal rules, and inline bold/italic/code.
"""

import io
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

NAVY = colors.HexColor("#0e2d63")
BLUE = colors.HexColor("#1f5edb")
MUTED = colors.HexColor("#5f6f89")
BORDER = colors.HexColor("#cfd9e8")
HEADER_BG = colors.HexColor("#eaf2ff")

MARGIN = 18 * mm
CONTENT_WIDTH = A4[0] - 2 * MARGIN

# Common typographic characters that Helvetica (WinAnsi) can render; map the
# rarer ones to safe equivalents so the PDF stays clean and never errors.
_NORMALIZE = {
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", "•": "-", " ": " ",
    "…": "...", "→": "->", "≥": ">=", "≤": "<=",
}


def _normalize(text: str) -> str:
    for bad, good in _NORMALIZE.items():
        text = text.replace(bad, good)
    return text


def _inline(text: str) -> str:
    """Escape XML then convert inline Markdown to reportlab mini-HTML."""
    text = _normalize(text)
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"__(.+?)__", r"<b>\1</b>", text)
    text = re.sub(r"`(.+?)`", r'<font face="Courier">\1</font>', text)
    text = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<i>\1</i>", text)
    return text


def _styles():
    base = getSampleStyleSheet()
    body = ParagraphStyle(
        "Body", parent=base["BodyText"], fontName="Helvetica", fontSize=10,
        leading=15, textColor=colors.HexColor("#18243a"), spaceAfter=4, alignment=TA_LEFT,
    )
    return {
        "title": ParagraphStyle("H1", parent=body, fontName="Helvetica-Bold", fontSize=19,
                                 leading=23, textColor=NAVY, spaceAfter=10, spaceBefore=2),
        "h2": ParagraphStyle("H2", parent=body, fontName="Helvetica-Bold", fontSize=14.5,
                             leading=19, textColor=NAVY, spaceBefore=12, spaceAfter=6),
        "h3": ParagraphStyle("H3", parent=body, fontName="Helvetica-Bold", fontSize=12,
                             leading=16, textColor=BLUE, spaceBefore=9, spaceAfter=4),
        "h4": ParagraphStyle("H4", parent=body, fontName="Helvetica-Bold", fontSize=10.5,
                             leading=14, textColor=NAVY, spaceBefore=7, spaceAfter=3),
        "body": body,
        "cell": ParagraphStyle("Cell", parent=body, fontSize=9, leading=12, spaceAfter=0),
        "cellhead": ParagraphStyle("CellHead", parent=body, fontName="Helvetica-Bold",
                                   fontSize=9, leading=12, textColor=NAVY, spaceAfter=0),
        "muted": ParagraphStyle("Muted", parent=body, fontSize=9, textColor=MUTED, spaceAfter=2),
    }


def _is_table_sep(line: str) -> bool:
    return bool(re.match(r"^\s*\|?[\s:|\-]+\|?\s*$", line)) and "-" in line


def _make_table(block, styles):
    rows = []
    for ln in block:
        if _is_table_sep(ln):
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        rows.append(cells)
    if not rows:
        return None
    ncols = max(len(r) for r in rows)
    data = []
    for r_index, cells in enumerate(rows):
        cells = cells + [""] * (ncols - len(cells))
        style = styles["cellhead"] if r_index == 0 else styles["cell"]
        data.append([Paragraph(_inline(c), style) for c in cells])

    col_width = CONTENT_WIDTH / ncols
    table = Table(data, colWidths=[col_width] * ncols, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def _markdown_to_flowables(markdown_text, styles):
    lines = markdown_text.split("\n")
    flow = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            flow.append(Spacer(1, 5))
            i += 1
            continue

        # Table block
        if "|" in stripped and i + 1 < n and _is_table_sep(lines[i + 1]):
            block = []
            while i < n and "|" in lines[i]:
                block.append(lines[i])
                i += 1
            table = _make_table(block, styles)
            if table is not None:
                flow.append(table)
                flow.append(Spacer(1, 6))
            continue

        # Heading
        heading = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if heading:
            level = min(len(heading.group(1)), 4)
            style = styles.get(f"h{level}" if level > 1 else "title", styles["h2"])
            if level == 1:
                style = styles["title"]
            flow.append(Paragraph(_inline(heading.group(2)), style))
            i += 1
            continue

        # Horizontal rule
        if re.match(r"^(-{3,}|\*{3,}|_{3,})$", stripped):
            flow.append(Spacer(1, 2))
            flow.append(HRFlowable(width="100%", thickness=0.6, color=BORDER,
                                   spaceBefore=2, spaceAfter=6))
            i += 1
            continue

        # Bullet list
        if re.match(r"^[-*+]\s+", stripped):
            items = []
            while i < n and re.match(r"^\s*[-*+]\s+", lines[i]):
                content = re.sub(r"^\s*[-*+]\s+", "", lines[i])
                items.append(ListItem(Paragraph(_inline(content), styles["body"]), leftIndent=10))
                i += 1
            flow.append(ListFlowable(items, bulletType="bullet", bulletColor=BLUE,
                                     leftIndent=14, bulletFontSize=7))
            continue

        # Numbered list
        if re.match(r"^\d+\.\s+", stripped):
            items = []
            while i < n and re.match(r"^\s*\d+\.\s+", lines[i]):
                content = re.sub(r"^\s*\d+\.\s+", "", lines[i])
                items.append(ListItem(Paragraph(_inline(content), styles["body"]), leftIndent=10))
                i += 1
            flow.append(ListFlowable(items, bulletType="1", leftIndent=16))
            continue

        # Plain paragraph
        flow.append(Paragraph(_inline(stripped), styles["body"]))
        i += 1

    return flow


def build_report_pdf(markdown_text: str, title: str = "Job Match Report") -> bytes:
    """Compile the given Markdown report text into a single PDF, returned as bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN, topMargin=MARGIN, bottomMargin=MARGIN,
        title=title,
    )
    styles = _styles()
    flowables = _markdown_to_flowables(markdown_text or "", styles)
    if not flowables:
        flowables = [Paragraph("No report content is available.", styles["body"])]
    doc.build(flowables)
    return buffer.getvalue()
