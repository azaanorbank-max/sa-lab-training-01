"""
PDF generation script for Decision Hub SA Lab training pack.
Generates Candidate_EN.pdf from README_EN.md.
Uses reportlab Platypus with Arial Unicode for full Unicode/Cyrillic support.
"""

import re
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, Preformatted, KeepTogether, HRFlowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── Fonts ──────────────────────────────────────────────────────────────────
FONT_PATH = "/Library/Fonts/Arial Unicode.ttf"
pdfmetrics.registerFont(TTFont("ArialUni", FONT_PATH))
pdfmetrics.registerFont(TTFont("ArialUniBold", FONT_PATH))  # fallback same font for bold

# For code blocks we use Courier (built-in, ASCII-only) — acceptable for EN doc
# For body text we use ArialUni

# ── Styles ─────────────────────────────────────────────────────────────────
BASE_FONT = "ArialUni"
CODE_FONT = "Courier"
BODY_SIZE = 9.5
CODE_SIZE = 8

def build_styles():
    styles = {}

    styles["title"] = ParagraphStyle(
        "title",
        fontName=BASE_FONT,
        fontSize=24,
        leading=32,
        alignment=TA_CENTER,
        spaceAfter=10,
        textColor=colors.HexColor("#1a1a2e"),
    )
    styles["subtitle"] = ParagraphStyle(
        "subtitle",
        fontName=BASE_FONT,
        fontSize=14,
        leading=20,
        alignment=TA_CENTER,
        spaceAfter=6,
        textColor=colors.HexColor("#4a4a6a"),
    )
    styles["version"] = ParagraphStyle(
        "version",
        fontName=BASE_FONT,
        fontSize=11,
        leading=16,
        alignment=TA_CENTER,
        spaceAfter=4,
        textColor=colors.HexColor("#888"),
    )
    styles["h1"] = ParagraphStyle(
        "h1",
        fontName=BASE_FONT,
        fontSize=17,
        leading=22,
        spaceBefore=18,
        spaceAfter=8,
        textColor=colors.HexColor("#1a1a2e"),
        borderPad=4,
    )
    styles["h2"] = ParagraphStyle(
        "h2",
        fontName=BASE_FONT,
        fontSize=13,
        leading=18,
        spaceBefore=14,
        spaceAfter=5,
        textColor=colors.HexColor("#2c2c5e"),
    )
    styles["h3"] = ParagraphStyle(
        "h3",
        fontName=BASE_FONT,
        fontSize=11,
        leading=15,
        spaceBefore=10,
        spaceAfter=4,
        textColor=colors.HexColor("#3a3a7a"),
    )
    styles["h4"] = ParagraphStyle(
        "h4",
        fontName=BASE_FONT,
        fontSize=10,
        leading=14,
        spaceBefore=8,
        spaceAfter=3,
        textColor=colors.HexColor("#555"),
    )
    styles["body"] = ParagraphStyle(
        "body",
        fontName=BASE_FONT,
        fontSize=BODY_SIZE,
        leading=14,
        spaceBefore=2,
        spaceAfter=4,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#222"),
    )
    styles["bullet"] = ParagraphStyle(
        "bullet",
        fontName=BASE_FONT,
        fontSize=BODY_SIZE,
        leading=14,
        spaceBefore=1,
        spaceAfter=1,
        leftIndent=14,
        bulletIndent=4,
        textColor=colors.HexColor("#222"),
    )
    styles["bullet2"] = ParagraphStyle(
        "bullet2",
        fontName=BASE_FONT,
        fontSize=BODY_SIZE,
        leading=14,
        spaceBefore=1,
        spaceAfter=1,
        leftIndent=28,
        bulletIndent=18,
        textColor=colors.HexColor("#333"),
    )
    styles["code_block"] = ParagraphStyle(
        "code_block",
        fontName=CODE_FONT,
        fontSize=CODE_SIZE,
        leading=12,
        spaceBefore=4,
        spaceAfter=4,
        leftIndent=0,
        textColor=colors.HexColor("#1a1a1a"),
        backColor=colors.HexColor("#f5f5f5"),
    )
    styles["label"] = ParagraphStyle(
        "label",
        fontName=BASE_FONT,
        fontSize=8,
        leading=11,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#666"),
        spaceAfter=16,
    )
    return styles


# ── Text cleaning / escaping ───────────────────────────────────────────────

def escape_xml(text):
    """Escape characters that break reportlab XML parser."""
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    return text

def apply_inline(text):
    """Apply inline markdown formatting: bold, inline code, links."""
    # Strip markdown links [text](url) → text
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # Escape XML special chars
    text = escape_xml(text)
    # Bold: **text** or __text__
    text = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'__([^_]+)__', r'<b>\1</b>', text)
    # Italic: *text*
    text = re.sub(r'\*([^*]+)\*', r'<i>\1</i>', text)
    # Inline code: `text`
    text = re.sub(r'`([^`]+)`', r'<font name="Courier" size="8">\1</font>', text)
    return text


# ── Table parsing ──────────────────────────────────────────────────────────

def parse_md_table(lines):
    """Parse markdown table lines into list of rows (list of lists)."""
    rows = []
    for line in lines:
        if re.match(r'^\s*\|[-: |]+\|\s*$', line):
            continue  # separator line
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        rows.append(cells)
    return rows

def build_table(rows, styles):
    """Build a reportlab Table from parsed rows."""
    if not rows:
        return None

    cell_style = ParagraphStyle(
        "cell",
        fontName=BASE_FONT,
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#222"),
    )
    header_style = ParagraphStyle(
        "header",
        fontName=BASE_FONT,
        fontSize=8,
        leading=11,
        textColor=colors.white,
    )

    data = []
    for i, row in enumerate(rows):
        style = header_style if i == 0 else cell_style
        data.append([Paragraph(apply_inline(cell), style) for cell in row])

    col_count = max(len(r) for r in data)
    page_width = A4[0] - 3.6 * cm
    col_width = page_width / col_count

    t = Table(data, colWidths=[col_width] * col_count, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c2c5e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), BASE_FONT),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f0f8")]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#ccccdd")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


# ── Code block rendering ───────────────────────────────────────────────────

def build_code_block(lines):
    """Render a fenced code block as a styled Preformatted block inside a Table."""
    text = "\n".join(lines)
    # Truncate very long individual lines to avoid overflow
    clipped = []
    for ln in lines:
        if len(ln) > 100:
            ln = ln[:97] + "..."
        clipped.append(ln)
    text = "\n".join(clipped)

    pre = Preformatted(text, ParagraphStyle(
        "pre",
        fontName=CODE_FONT,
        fontSize=7.5,
        leading=11,
        textColor=colors.HexColor("#1a1a1a"),
    ))

    t = Table([[pre]], colWidths=[A4[0] - 3.6 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#f4f4f4")),
        ("BOX", (0, 0), (0, 0), 0.5, colors.HexColor("#cccccc")),
        ("LEFTPADDING", (0, 0), (0, 0), 8),
        ("RIGHTPADDING", (0, 0), (0, 0), 8),
        ("TOPPADDING", (0, 0), (0, 0), 6),
        ("BOTTOMPADDING", (0, 0), (0, 0), 6),
    ]))
    return t


# ── Main markdown → flowables parser ─────────────────────────────────────

def parse_markdown(md_text, styles):
    """Convert markdown text to a list of reportlab flowables."""
    flowables = []
    lines = md_text.split("\n")
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]

        # ── Fenced code block ──────────────────────────────────────────
        if line.strip().startswith("```"):
            i += 1
            code_lines = []
            while i < n and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1  # skip closing ```
            if code_lines:
                flowables.append(Spacer(1, 2 * mm))
                flowables.append(build_code_block(code_lines))
                flowables.append(Spacer(1, 2 * mm))
            continue

        # ── Horizontal rule ────────────────────────────────────────────
        if re.match(r'^-{3,}\s*$', line) or re.match(r'^_{3,}\s*$', line) or re.match(r'^\*{3,}\s*$', line):
            flowables.append(Spacer(1, 3 * mm))
            flowables.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#ccccdd")))
            flowables.append(Spacer(1, 3 * mm))
            i += 1
            continue

        # ── Markdown table ─────────────────────────────────────────────
        if line.strip().startswith("|"):
            table_lines = []
            while i < n and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            rows = parse_md_table(table_lines)
            if rows:
                flowables.append(Spacer(1, 2 * mm))
                t = build_table(rows, styles)
                if t:
                    flowables.append(t)
                flowables.append(Spacer(1, 3 * mm))
            continue

        # ── Headings ───────────────────────────────────────────────────
        h_match = re.match(r'^(#{1,4})\s+(.*)', line)
        if h_match:
            level = len(h_match.group(1))
            text = apply_inline(h_match.group(2).strip())
            style_key = f"h{min(level, 4)}"
            if level == 1:
                flowables.append(Spacer(1, 4 * mm))
                # Add a colored bar above H1
                flowables.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#2c2c5e")))
                flowables.append(Spacer(1, 1 * mm))
            flowables.append(Paragraph(text, styles[style_key]))
            i += 1
            continue

        # ── Bullet list items ──────────────────────────────────────────
        bullet_match = re.match(r'^(\s*)[-*+]\s+(.*)', line)
        if bullet_match:
            indent = len(bullet_match.group(1))
            text = apply_inline(bullet_match.group(2))
            s = styles["bullet2"] if indent >= 4 else styles["bullet"]
            flowables.append(Paragraph(f"• {text}", s))
            i += 1
            continue

        # ── Numbered list items ────────────────────────────────────────
        num_match = re.match(r'^(\s*)\d+\.\s+(.*)', line)
        if num_match:
            indent = len(num_match.group(1))
            text = apply_inline(num_match.group(2))
            s = styles["bullet2"] if indent >= 4 else styles["bullet"]
            num = re.match(r'^(\s*)(\d+)\.', line).group(2)
            flowables.append(Paragraph(f"{num}. {text}", s))
            i += 1
            continue

        # ── Blockquote ─────────────────────────────────────────────────
        if line.strip().startswith(">"):
            text = apply_inline(line.strip().lstrip(">").strip())
            bq_style = ParagraphStyle(
                "bq",
                parent=styles["body"],
                leftIndent=12,
                borderPad=4,
                textColor=colors.HexColor("#555"),
                fontSize=9,
            )
            flowables.append(Paragraph(f"<i>{text}</i>", bq_style))
            i += 1
            continue

        # ── Empty line ─────────────────────────────────────────────────
        if line.strip() == "":
            flowables.append(Spacer(1, 2 * mm))
            i += 1
            continue

        # ── Regular paragraph ──────────────────────────────────────────
        text = apply_inline(line.strip())
        if text:
            flowables.append(Paragraph(text, styles["body"]))
        i += 1

    return flowables


# ── Page template callbacks ────────────────────────────────────────────────

def add_page_number(canvas, doc):
    """Draw header and footer on each page."""
    canvas.saveState()
    w, h = A4

    # Header bar
    canvas.setFillColor(colors.HexColor("#1a1a2e"))
    canvas.rect(0, h - 1.1 * cm, w, 1.1 * cm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("ArialUni", 8)
    canvas.drawString(1.5 * cm, h - 0.7 * cm, "Decision Hub — System Analysis Training")
    canvas.drawRightString(w - 1.5 * cm, h - 0.7 * cm, "Wave 1 · Candidate Pack")

    # Footer
    canvas.setFillColor(colors.HexColor("#888"))
    canvas.setFont("ArialUni", 7.5)
    canvas.drawString(1.5 * cm, 0.7 * cm, "CANDIDATE DOCUMENT — NOT FOR DISTRIBUTION")
    canvas.drawRightString(w - 1.5 * cm, 0.7 * cm, f"Page {doc.page}")
    canvas.setStrokeColor(colors.HexColor("#ccccdd"))
    canvas.setLineWidth(0.5)
    canvas.line(1.5 * cm, 1.0 * cm, w - 1.5 * cm, 1.0 * cm)

    canvas.restoreState()


# ── Title page ─────────────────────────────────────────────────────────────

def build_title_page(styles):
    flowables = []
    flowables.append(Spacer(1, 5 * cm))

    # Large colored block
    t = Table(
        [[Paragraph("Decision Hub", styles["title"]),]],
        colWidths=[A4[0] - 3.6 * cm],
    )
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0, 0), (0, 0), colors.white),
        ("TOPPADDING", (0, 0), (0, 0), 20),
        ("BOTTOMPADDING", (0, 0), (0, 0), 20),
        ("LEFTPADDING", (0, 0), (0, 0), 20),
        ("RIGHTPADDING", (0, 0), (0, 0), 20),
    ]))
    flowables.append(t)
    flowables.append(Spacer(1, 1 * cm))

    title_style = ParagraphStyle("tp_title", fontName=BASE_FONT, fontSize=28,
                                  leading=36, alignment=TA_CENTER,
                                  textColor=colors.HexColor("#1a1a2e"))
    sub_style = ParagraphStyle("tp_sub", fontName=BASE_FONT, fontSize=15,
                                leading=22, alignment=TA_CENTER,
                                textColor=colors.HexColor("#4a4a6a"), spaceAfter=8)
    ver_style = ParagraphStyle("tp_ver", fontName=BASE_FONT, fontSize=11,
                                leading=16, alignment=TA_CENTER,
                                textColor=colors.HexColor("#888"), spaceAfter=4)
    tag_style = ParagraphStyle("tp_tag", fontName=BASE_FONT, fontSize=10,
                                leading=14, alignment=TA_CENTER,
                                textColor=colors.HexColor("#cc3333"))

    flowables.append(Paragraph("System Analysis Training", sub_style))
    flowables.append(Spacer(1, 8 * mm))
    flowables.append(Paragraph("Analytical Sandbox for Fintech Systems", ver_style))
    flowables.append(Spacer(1, 6 * mm))
    flowables.append(HRFlowable(width="60%", thickness=1, color=colors.HexColor("#ccccdd")))
    flowables.append(Spacer(1, 6 * mm))
    flowables.append(Paragraph("Wave 1 — Degraded System", tag_style))
    flowables.append(Spacer(1, 2 * cm))

    info_style = ParagraphStyle("tp_info", fontName=BASE_FONT, fontSize=9,
                                 leading=14, alignment=TA_CENTER,
                                 textColor=colors.HexColor("#666"))
    flowables.append(Paragraph("Candidate Assessment Document", info_style))
    flowables.append(Paragraph("This document contains the complete training assignment.", info_style))
    flowables.append(Spacer(1, 1 * cm))
    flowables.append(Paragraph("⚠  Do not share answers with other candidates.", ParagraphStyle(
        "warn", fontName=BASE_FONT, fontSize=9, leading=14, alignment=TA_CENTER,
        textColor=colors.HexColor("#cc3333"))))

    flowables.append(PageBreak())
    return flowables


# ── Main ───────────────────────────────────────────────────────────────────

def generate_candidate_en():
    output_path = os.path.join(os.path.dirname(__file__), "Candidate_EN.pdf")
    source_path = os.path.join(os.path.dirname(__file__), "README_EN.md")

    with open(source_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    styles = build_styles()

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
        title="Decision Hub — System Analysis Training (Candidate EN)",
        author="SA Lab Training",
        subject="Candidate Training Pack — Wave 1",
    )

    story = []
    story.extend(build_title_page(styles))

    # Table of Contents placeholder
    toc_style = ParagraphStyle("toc_h", fontName=BASE_FONT, fontSize=14,
                                leading=20, spaceBefore=10, spaceAfter=8,
                                textColor=colors.HexColor("#1a1a2e"))
    story.append(Paragraph("Contents", toc_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#2c2c5e")))
    story.append(Spacer(1, 4 * mm))

    toc_items = [
        ("About This Assignment", "p. 3"),
        ("Business Context", "p. 3"),
        ("System Architecture", "p. 3"),
        ("Services in Scope", "p. 4"),
        ("How to Work Through This Assignment", "p. 4"),
        ("Flow 1: Idempotency / Retry Safety", "p. 5"),
        ("Flow 2: Transfer Status Machine", "p. 8"),
        ("Flow 3: Decision Logic / Service Ownership", "p. 12"),
        ("Flow 4: Observability / Tracing / RCA", "p. 16"),
        ("Flow 5: API Contracts vs Runtime Behavior", "p. 19"),
        ("Question Bank (Step 6)", "p. 23"),
        ("Deliverable Format", "p. 31"),
    ]
    toc_entry = ParagraphStyle("toc_e", fontName=BASE_FONT, fontSize=9.5,
                                leading=15, textColor=colors.HexColor("#222"))
    toc_pg = ParagraphStyle("toc_p", fontName=BASE_FONT, fontSize=9.5,
                              leading=15, alignment=TA_LEFT,
                              textColor=colors.HexColor("#888"))
    for title, pg in toc_items:
        row_data = [[Paragraph(title, toc_entry), Paragraph(pg, toc_pg)]]
        t = Table(row_data, colWidths=[13 * cm, 3 * cm])
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#eeeeee")),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(t)

    story.append(PageBreak())

    # Parse and add content
    content_flowables = parse_markdown(md_text, styles)
    story.extend(content_flowables)

    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    print(f"Generated: {output_path}")


if __name__ == "__main__":
    generate_candidate_en()
