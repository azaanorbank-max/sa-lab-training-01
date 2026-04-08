"""
PDF generation script for Decision Hub SA Lab training pack.
Generates all 4 PDFs:
  - Candidate_EN.pdf  (from README_EN.md)
  - Candidate_RU.pdf  (from README_RU.md)
  - Facilitator_EN.pdf (from .training-facilitator-notes_EN.md + .training-change-log_EN.md)
  - Facilitator_RU.pdf (from .training-facilitator-notes_RU.md + .training-change-log_RU.md)

Uses Arial Unicode for full Cyrillic support.
"""

import re
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, Preformatted, HRFlowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Fonts ──────────────────────────────────────────────────────────────────
# Arial Unicode supports full Unicode including Cyrillic, box-drawing chars,
# arrows, and all special symbols used in architecture diagrams.
# Courier is NOT used because it lacks these codepoints — they render as black squares.
FONT_PATH = "/Library/Fonts/Arial Unicode.ttf"
pdfmetrics.registerFont(TTFont("ArialUni", FONT_PATH))
# Register the same font as the Bold variant so <b> tags don't crash.
# It won't look visually bold but will render correctly — better than broken glyphs.
pdfmetrics.registerFont(TTFont("ArialUni-Bold", FONT_PATH))
from reportlab.pdfbase.pdfmetrics import registerFontFamily
registerFontFamily("ArialUni", normal="ArialUni", bold="ArialUni-Bold",
                   italic="ArialUni", boldItalic="ArialUni-Bold")

BASE_FONT = "ArialUni"
CODE_FONT = "ArialUni"   # ArialUni for ALL text — Courier lacks Unicode coverage
BODY_SIZE = 9.5
CODE_SIZE = 7.5


# ── Style factory ──────────────────────────────────────────────────────────

def build_styles(accent="#2c2c5e"):
    s = {}
    s["h1"] = ParagraphStyle("h1", fontName=BASE_FONT, fontSize=17, leading=22,
                              spaceBefore=18, spaceAfter=8,
                              textColor=colors.HexColor("#1a1a2e"))
    s["h2"] = ParagraphStyle("h2", fontName=BASE_FONT, fontSize=13, leading=18,
                              spaceBefore=14, spaceAfter=5,
                              textColor=colors.HexColor(accent))
    s["h3"] = ParagraphStyle("h3", fontName=BASE_FONT, fontSize=11, leading=15,
                              spaceBefore=10, spaceAfter=4,
                              textColor=colors.HexColor("#3a3a7a"))
    s["h4"] = ParagraphStyle("h4", fontName=BASE_FONT, fontSize=10, leading=14,
                              spaceBefore=8, spaceAfter=3,
                              textColor=colors.HexColor("#555"))
    s["body"] = ParagraphStyle("body", fontName=BASE_FONT, fontSize=BODY_SIZE,
                                leading=14, spaceBefore=2, spaceAfter=4,
                                textColor=colors.HexColor("#222"))
    s["bullet"] = ParagraphStyle("bullet", fontName=BASE_FONT, fontSize=BODY_SIZE,
                                  leading=14, spaceBefore=1, spaceAfter=1,
                                  leftIndent=14, textColor=colors.HexColor("#222"))
    s["bullet2"] = ParagraphStyle("bullet2", fontName=BASE_FONT, fontSize=BODY_SIZE,
                                   leading=14, spaceBefore=1, spaceAfter=1,
                                   leftIndent=28, textColor=colors.HexColor("#333"))
    return s


# ── Text helpers ───────────────────────────────────────────────────────────

def escape_xml(text):
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    return text

def apply_inline(text):
    text = re.sub(r'\[([^\]]+)\]\([^\)]*\)', r'\1', text)  # strip links
    text = escape_xml(text)
    # Bold: render as slightly larger + underlined since we have one font file
    text = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'__([^_]+)__', r'<b>\1</b>', text)
    # Italic: reportlab handles <i> gracefully even with single-face font
    text = re.sub(r'\*([^*\n]+)\*', r'<i>\1</i>', text)
    text = re.sub(r'`([^`\n]+)`', r'<font name="ArialUni" size="8">\1</font>', text)
    return text


# ── Table builder ──────────────────────────────────────────────────────────

def parse_md_table(lines):
    rows = []
    for line in lines:
        if re.match(r'^\s*\|[-: |]+\|\s*$', line):
            continue
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        rows.append(cells)
    return rows

def build_table(rows):
    if not rows:
        return None
    cell_s = ParagraphStyle("tc", fontName=BASE_FONT, fontSize=8, leading=11,
                             textColor=colors.HexColor("#222"))
    head_s = ParagraphStyle("th", fontName=BASE_FONT, fontSize=8, leading=11,
                             textColor=colors.white)
    data = []
    for i, row in enumerate(rows):
        s = head_s if i == 0 else cell_s
        data.append([Paragraph(apply_inline(c), s) for c in row])

    col_count = max(len(r) for r in data)
    page_w = A4[0] - 3.6 * cm
    col_w = page_w / col_count

    t = Table(data, colWidths=[col_w] * col_count, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c2c5e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f0f8")]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#ccccdd")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


# ── Code block builder ─────────────────────────────────────────────────────

def build_code_block(lines):
    clipped = []
    for ln in lines:
        if len(ln) > 100:
            ln = ln[:97] + "..."
        clipped.append(ln)
    text = "\n".join(clipped)
    pre = Preformatted(text, ParagraphStyle("pre", fontName=CODE_FONT, fontSize=7.5,
                                             leading=11, textColor=colors.HexColor("#1a1a1a")))
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


# ── Markdown parser ────────────────────────────────────────────────────────

def parse_markdown(md_text, styles):
    flowables = []
    lines = md_text.split("\n")
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]

        # Fenced code block
        if line.strip().startswith("```"):
            i += 1
            code_lines = []
            while i < n and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1
            if code_lines:
                flowables.append(Spacer(1, 2 * mm))
                flowables.append(build_code_block(code_lines))
                flowables.append(Spacer(1, 2 * mm))
            continue

        # Horizontal rule
        if re.match(r'^[-_*]{3,}\s*$', line):
            flowables.append(Spacer(1, 3 * mm))
            flowables.append(HRFlowable(width="100%", thickness=0.5,
                                         color=colors.HexColor("#ccccdd")))
            flowables.append(Spacer(1, 3 * mm))
            i += 1
            continue

        # Markdown table
        if line.strip().startswith("|"):
            table_lines = []
            while i < n and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            rows = parse_md_table(table_lines)
            if rows:
                flowables.append(Spacer(1, 2 * mm))
                t = build_table(rows)
                if t:
                    flowables.append(t)
                flowables.append(Spacer(1, 3 * mm))
            continue

        # Headings
        h_match = re.match(r'^(#{1,4})\s+(.*)', line)
        if h_match:
            level = len(h_match.group(1))
            text = apply_inline(h_match.group(2).strip())
            if level == 1:
                flowables.append(Spacer(1, 4 * mm))
                flowables.append(HRFlowable(width="100%", thickness=2,
                                             color=colors.HexColor("#2c2c5e")))
                flowables.append(Spacer(1, 1 * mm))
            flowables.append(Paragraph(text, styles[f"h{min(level, 4)}"]))
            i += 1
            continue

        # Bullet list
        bullet_m = re.match(r'^(\s*)[-*+]\s+(.*)', line)
        if bullet_m:
            indent = len(bullet_m.group(1))
            text = apply_inline(bullet_m.group(2))
            s = styles["bullet2"] if indent >= 4 else styles["bullet"]
            flowables.append(Paragraph(f"• {text}", s))
            i += 1
            continue

        # Numbered list
        num_m = re.match(r'^(\s*)(\d+)\.\s+(.*)', line)
        if num_m:
            indent = len(num_m.group(1))
            num = num_m.group(2)
            text = apply_inline(num_m.group(3))
            s = styles["bullet2"] if indent >= 4 else styles["bullet"]
            flowables.append(Paragraph(f"{num}. {text}", s))
            i += 1
            continue

        # Blockquote
        if line.strip().startswith(">"):
            text = apply_inline(line.strip().lstrip(">").strip())
            bq_s = ParagraphStyle("bq", parent=styles["body"], leftIndent=12,
                                   textColor=colors.HexColor("#555"), fontSize=9)
            flowables.append(Paragraph(f"<i>{text}</i>", bq_s))
            i += 1
            continue

        # Empty line
        if line.strip() == "":
            flowables.append(Spacer(1, 2 * mm))
            i += 1
            continue

        # Regular paragraph
        text = apply_inline(line.strip())
        if text:
            flowables.append(Paragraph(text, styles["body"]))
        i += 1

    return flowables


# ── Page number callback factory ───────────────────────────────────────────

def make_page_callback(header_left, header_right, footer_note, accent="#1a1a2e"):
    def callback(canvas, doc):
        canvas.saveState()
        w, h = A4
        # Header
        canvas.setFillColor(colors.HexColor(accent))
        canvas.rect(0, h - 1.1 * cm, w, 1.1 * cm, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont("ArialUni", 8)
        canvas.drawString(1.5 * cm, h - 0.7 * cm, header_left)
        canvas.drawRightString(w - 1.5 * cm, h - 0.7 * cm, header_right)
        # Footer
        canvas.setFillColor(colors.HexColor("#888"))
        canvas.setFont("ArialUni", 7.5)
        canvas.drawString(1.5 * cm, 0.7 * cm, footer_note)
        canvas.drawRightString(w - 1.5 * cm, 0.7 * cm, f"Page {doc.page}")
        canvas.setStrokeColor(colors.HexColor("#ccccdd"))
        canvas.setLineWidth(0.5)
        canvas.line(1.5 * cm, 1.0 * cm, w - 1.5 * cm, 1.0 * cm)
        canvas.restoreState()
    return callback


# ── Title page builder ─────────────────────────────────────────────────────

def build_title_page(title_line1, title_line2, subtitle, version_tag,
                      info_lines, warning, accent="#1a1a2e"):
    """Returns a list of flowables for the title page."""
    flowables = []
    flowables.append(Spacer(1, 4 * cm))

    header_s = ParagraphStyle("tp_h", fontName=BASE_FONT, fontSize=26, leading=34,
                               alignment=TA_CENTER, textColor=colors.white)
    t = Table([[Paragraph(title_line1, header_s)]],
              colWidths=[A4[0] - 3.6 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor(accent)),
        ("TOPPADDING", (0, 0), (0, 0), 22),
        ("BOTTOMPADDING", (0, 0), (0, 0), 22),
        ("LEFTPADDING", (0, 0), (0, 0), 20),
        ("RIGHTPADDING", (0, 0), (0, 0), 20),
    ]))
    flowables.append(t)
    flowables.append(Spacer(1, 8 * mm))

    sub_s = ParagraphStyle("tp_s", fontName=BASE_FONT, fontSize=14, leading=20,
                            alignment=TA_CENTER, textColor=colors.HexColor("#4a4a6a"),
                            spaceAfter=6)
    ver_s = ParagraphStyle("tp_v", fontName=BASE_FONT, fontSize=11, leading=16,
                            alignment=TA_CENTER, textColor=colors.HexColor("#888"),
                            spaceAfter=4)
    tag_s = ParagraphStyle("tp_t", fontName=BASE_FONT, fontSize=10, leading=14,
                            alignment=TA_CENTER, textColor=colors.HexColor("#cc3333"))
    info_s = ParagraphStyle("tp_i", fontName=BASE_FONT, fontSize=9, leading=14,
                             alignment=TA_CENTER, textColor=colors.HexColor("#666"))
    warn_s = ParagraphStyle("tp_w", fontName=BASE_FONT, fontSize=9, leading=14,
                             alignment=TA_CENTER, textColor=colors.HexColor("#cc3333"))

    flowables.append(Paragraph(title_line2, sub_s))
    flowables.append(Spacer(1, 6 * mm))
    flowables.append(Paragraph(subtitle, ver_s))
    flowables.append(Spacer(1, 5 * mm))
    flowables.append(HRFlowable(width="60%", thickness=1, color=colors.HexColor("#ccccdd")))
    flowables.append(Spacer(1, 5 * mm))
    flowables.append(Paragraph(version_tag, tag_s))
    flowables.append(Spacer(1, 2 * cm))
    for info in info_lines:
        flowables.append(Paragraph(info, info_s))
    flowables.append(Spacer(1, 8 * mm))
    flowables.append(Paragraph(warning, warn_s))
    flowables.append(PageBreak())
    return flowables


# ── Document builder ───────────────────────────────────────────────────────

def build_doc(output_path, md_content_blocks, title_kwargs, page_cb_kwargs,
              pdf_meta, styles):
    """
    md_content_blocks: list of (source_label, md_text) tuples.
    Between blocks a PageBreak is inserted.
    """
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
        **pdf_meta,
    )

    story = []
    story.extend(build_title_page(**title_kwargs))

    for idx, (label, md_text) in enumerate(md_content_blocks):
        if idx > 0:
            story.append(PageBreak())
        story.extend(parse_markdown(md_text, styles))

    cb = make_page_callback(**page_cb_kwargs)
    doc.build(story, onFirstPage=cb, onLaterPages=cb)
    print(f"Generated: {output_path}")


# ── Individual document generators ────────────────────────────────────────

def generate_candidate_en():
    src = os.path.join(BASE_DIR, "README_EN.md")
    out = os.path.join(BASE_DIR, "Candidate_EN.pdf")
    with open(src, encoding="utf-8") as f:
        md = f.read()

    styles = build_styles()
    build_doc(
        output_path=out,
        md_content_blocks=[("candidate", md)],
        title_kwargs=dict(
            title_line1="Decision Hub",
            title_line2="System Analysis Training",
            subtitle="Analytical Sandbox for Fintech Systems",
            version_tag="Wave 1 — Degraded System",
            info_lines=["Candidate Assessment Document",
                        "This document contains the complete training assignment."],
            warning="Do not share answers with other candidates.",
            accent="#1a1a2e",
        ),
        page_cb_kwargs=dict(
            header_left="Decision Hub — System Analysis Training",
            header_right="Wave 1 · Candidate Pack (EN)",
            footer_note="CANDIDATE DOCUMENT",
            accent="#1a1a2e",
        ),
        pdf_meta=dict(
            title="Decision Hub — Candidate Training Pack (EN)",
            author="SA Lab Training",
            subject="Candidate Assessment — Wave 1",
        ),
        styles=styles,
    )


def generate_candidate_ru():
    src = os.path.join(BASE_DIR, "README_RU.md")
    out = os.path.join(BASE_DIR, "Candidate_RU.pdf")
    with open(src, encoding="utf-8") as f:
        md = f.read()

    styles = build_styles()
    build_doc(
        output_path=out,
        md_content_blocks=[("candidate_ru", md)],
        title_kwargs=dict(
            title_line1="Decision Hub",
            title_line2="Обучение системному анализу",
            subtitle="Аналитический sandbox для финтех-систем",
            version_tag="Wave 1 — Деградированная система",
            info_lines=["Документ для кандидата",
                        "Содержит полное задание для тренинга."],
            warning="Не передавайте ответы другим кандидатам.",
            accent="#1a1a2e",
        ),
        page_cb_kwargs=dict(
            header_left="Decision Hub — Обучение системному анализу",
            header_right="Wave 1 · Кандидат (RU)",
            footer_note="ДОКУМЕНТ ДЛЯ КАНДИДАТА",
            accent="#1a1a2e",
        ),
        pdf_meta=dict(
            title="Decision Hub — Candidate Training Pack (RU)",
            author="SA Lab Training",
            subject="Candidate Assessment — Wave 1",
        ),
        styles=styles,
    )


def generate_facilitator_en():
    notes_src = os.path.join(BASE_DIR, ".training-facilitator-notes_EN.md")
    log_src = os.path.join(BASE_DIR, ".training-change-log_EN.md")
    out = os.path.join(BASE_DIR, "Facilitator_EN.pdf")

    with open(notes_src, encoding="utf-8") as f:
        notes_md = f.read()
    with open(log_src, encoding="utf-8") as f:
        log_md = f.read()

    styles = build_styles(accent="#8b0000")
    build_doc(
        output_path=out,
        md_content_blocks=[
            ("notes", notes_md),
            ("log", log_md),
        ],
        title_kwargs=dict(
            title_line1="Decision Hub",
            title_line2="Facilitator Guide",
            subtitle="Grading Guide & Degradation Log",
            version_tag="Wave 1 — INTERNAL — NOT FOR CANDIDATES",
            info_lines=["This document is for facilitators only.",
                        "Contains full grading criteria, red flags, and probing questions.",
                        "Do not share with candidates."],
            warning="CONFIDENTIAL — INTERNAL USE ONLY",
            accent="#5c0000",
        ),
        page_cb_kwargs=dict(
            header_left="Decision Hub — Facilitator Guide",
            header_right="Wave 1 · INTERNAL (EN)",
            footer_note="INTERNAL — NOT FOR CANDIDATES",
            accent="#5c0000",
        ),
        pdf_meta=dict(
            title="Decision Hub — Facilitator Guide (EN)",
            author="SA Lab Training",
            subject="Facilitator Grading Guide — Wave 1 — INTERNAL",
        ),
        styles=styles,
    )


def generate_facilitator_ru():
    notes_src = os.path.join(BASE_DIR, ".training-facilitator-notes_RU.md")
    log_src = os.path.join(BASE_DIR, ".training-change-log_RU.md")
    out = os.path.join(BASE_DIR, "Facilitator_RU.pdf")

    with open(notes_src, encoding="utf-8") as f:
        notes_md = f.read()
    with open(log_src, encoding="utf-8") as f:
        log_md = f.read()

    styles = build_styles(accent="#8b0000")
    build_doc(
        output_path=out,
        md_content_blocks=[
            ("notes_ru", notes_md),
            ("log_ru", log_md),
        ],
        title_kwargs=dict(
            title_line1="Decision Hub",
            title_line2="Руководство фасилитатора",
            subtitle="Руководство по оценке и журнал деградации",
            version_tag="Wave 1 — ВНУТРЕННИЙ ДОКУМЕНТ — НЕ ДЛЯ КАНДИДАТОВ",
            info_lines=["Этот документ предназначен только для фасилитаторов.",
                        "Содержит критерии оценки, красные флаги и уточняющие вопросы.",
                        "Не передавать кандидатам."],
            warning="КОНФИДЕНЦИАЛЬНО — ТОЛЬКО ДЛЯ ВНУТРЕННЕГО ИСПОЛЬЗОВАНИЯ",
            accent="#5c0000",
        ),
        page_cb_kwargs=dict(
            header_left="Decision Hub — Руководство фасилитатора",
            header_right="Wave 1 · ВНУТРЕННИЙ (RU)",
            footer_note="ВНУТРЕННИЙ ДОКУМЕНТ — НЕ ДЛЯ КАНДИДАТОВ",
            accent="#5c0000",
        ),
        pdf_meta=dict(
            title="Decision Hub — Facilitator Guide (RU)",
            author="SA Lab Training",
            subject="Facilitator Grading Guide — Wave 1 — INTERNAL",
        ),
        styles=styles,
    )


if __name__ == "__main__":
    import sys
    os.chdir(BASE_DIR)

    targets = sys.argv[1:] if len(sys.argv) > 1 else ["all"]
    if "all" in targets or "candidate_en" in targets:
        generate_candidate_en()
    if "all" in targets or "candidate_ru" in targets:
        generate_candidate_ru()
    if "all" in targets or "facilitator_en" in targets:
        generate_facilitator_en()
    if "all" in targets or "facilitator_ru" in targets:
        generate_facilitator_ru()
    print("Done.")
