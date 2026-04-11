"""Convert gclib-communication-reference.md to a printable PDF."""
import re
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, HRFlowable,
)

WIDTH, HEIGHT = letter
MARGIN = 0.75 * inch

styles = getSampleStyleSheet()

# Custom styles
styles.add(ParagraphStyle("DocTitle", parent=styles["Title"], fontSize=18, spaceAfter=4, textColor=HexColor("#1a1a2e")))
styles.add(ParagraphStyle("Subtitle", parent=styles["Normal"], fontSize=10, textColor=HexColor("#555555"), spaceAfter=16, alignment=TA_CENTER))
styles.add(ParagraphStyle("H1", parent=styles["Heading1"], fontSize=14, spaceBefore=18, spaceAfter=8, textColor=HexColor("#1a1a2e"), borderWidth=0, borderPadding=0))
styles.add(ParagraphStyle("H2", parent=styles["Heading2"], fontSize=12, spaceBefore=14, spaceAfter=6, textColor=HexColor("#2d3436")))
styles.add(ParagraphStyle("H3", parent=styles["Heading3"], fontSize=10, spaceBefore=10, spaceAfter=4, textColor=HexColor("#2d3436")))
styles.add(ParagraphStyle("Body", parent=styles["Normal"], fontSize=9, leading=13, spaceAfter=6))
styles.add(ParagraphStyle("Bold", parent=styles["Normal"], fontSize=9, leading=13, spaceAfter=6))
styles.add(ParagraphStyle("BulletItem", parent=styles["Normal"], fontSize=9, leading=13, leftIndent=20, bulletIndent=8, spaceAfter=3))
styles.add(ParagraphStyle("CodeBlock", fontName="Courier", fontSize=7.5, leading=10, leftIndent=16, spaceAfter=2, backColor=HexColor("#f5f5f5"), textColor=HexColor("#2d3436")))
styles.add(ParagraphStyle("CodeComment", fontName="Courier", fontSize=7.5, leading=10, leftIndent=16, spaceAfter=2, backColor=HexColor("#f5f5f5"), textColor=HexColor("#6c7a89")))
styles.add(ParagraphStyle("TableCell", fontName="Helvetica", fontSize=8, leading=10))
styles.add(ParagraphStyle("TableHeader", fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=HexColor("#ffffff")))
styles.add(ParagraphStyle("Note", parent=styles["Normal"], fontSize=8.5, leading=12, leftIndent=12, textColor=HexColor("#e17055"), spaceAfter=6))

HEADER_BG = HexColor("#2d3436")
ALT_ROW = HexColor("#f0f0f0")
BORDER_COLOR = HexColor("#cccccc")


def escape(text):
    """Escape XML special chars for ReportLab Paragraph."""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return text


def inline_format(text):
    """Convert markdown inline formatting to ReportLab XML."""
    # Bold + code combined
    text = re.sub(r'\*\*`([^`]+)`\*\*', r'<b><font name="Courier" size="8">\1</font></b>', text)
    # Code spans
    text = re.sub(r'`([^`]+)`', r'<font name="Courier" size="8" color="#c0392b">\1</font>', text)
    # Bold
    text = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', text)
    return text


def make_table(headers, rows):
    """Build a formatted table."""
    col_count = len(headers)
    avail = WIDTH - 2 * MARGIN
    col_widths = [avail / col_count] * col_count

    header_cells = [Paragraph(escape(h), styles["TableHeader"]) for h in headers]
    data = [header_cells]
    for row in rows:
        cells = [Paragraph(inline_format(escape(c.strip())), styles["TableCell"]) for c in row]
        data.append(cells)

    t = Table(data, colWidths=col_widths, repeatRows=1)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            style_cmds.append(("BACKGROUND", (0, i), (-1, i), ALT_ROW))
    t.setStyle(TableStyle(style_cmds))
    return t


def parse_md(filepath):
    """Parse the markdown file and return a list of flowables."""
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    story = []
    i = 0
    in_code = False
    code_lines = []
    in_table = False
    table_headers = []
    table_rows = []

    def flush_table():
        nonlocal in_table, table_headers, table_rows
        if table_headers and table_rows:
            story.append(make_table(table_headers, table_rows))
            story.append(Spacer(1, 8))
        in_table = False
        table_headers = []
        table_rows = []

    def flush_code():
        nonlocal in_code, code_lines
        if code_lines:
            for cl in code_lines:
                escaped = escape(cl.rstrip())
                if escaped.strip().startswith("#") or escaped.strip().startswith("//") or escaped.strip().startswith("'"):
                    story.append(Paragraph(escaped if escaped.strip() else "&nbsp;", styles["CodeComment"]))
                else:
                    story.append(Paragraph(escaped if escaped.strip() else "&nbsp;", styles["CodeBlock"]))
            story.append(Spacer(1, 6))
        in_code = False
        code_lines = []

    while i < len(lines):
        line = lines[i].rstrip()

        # Code blocks
        if line.startswith("```"):
            if in_code:
                flush_code()
            else:
                if in_table:
                    flush_table()
                in_code = True
            i += 1
            continue

        if in_code:
            code_lines.append(line)
            i += 1
            continue

        # Horizontal rules
        if line.startswith("---") and len(line.strip()) >= 3 and all(c == '-' for c in line.strip()):
            if in_table:
                flush_table()
            story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER_COLOR, spaceAfter=8, spaceBefore=8))
            i += 1
            continue

        # Tables
        if "|" in line and line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if not in_table:
                table_headers = cells
                in_table = True
                i += 1
                continue
            # Separator row
            if all(re.match(r'^[-:]+$', c.strip()) for c in cells):
                i += 1
                continue
            table_rows.append(cells)
            i += 1
            continue
        else:
            if in_table:
                flush_table()

        # Empty lines
        if not line.strip():
            i += 1
            continue

        # Title
        if line.startswith("# ") and i < 3:
            story.append(Paragraph(escape(line[2:].strip()), styles["DocTitle"]))
            i += 1
            continue

        # Subtitle lines (bold metadata at top)
        if i < 10 and line.startswith("**") and ":" in line:
            text = inline_format(escape(line))
            story.append(Paragraph(text, styles["Subtitle"]))
            i += 1
            continue

        # Headings
        if line.startswith("### "):
            story.append(Paragraph(escape(line[4:].strip()), styles["H3"]))
            i += 1
            continue
        if line.startswith("## "):
            story.append(Paragraph(escape(line[3:].strip()), styles["H2"]))
            i += 1
            continue
        if line.startswith("# "):
            story.append(Paragraph(escape(line[2:].strip()), styles["H1"]))
            i += 1
            continue

        # Bullet points
        if line.strip().startswith("- "):
            text = line.strip()[2:]
            text = inline_format(escape(text))
            story.append(Paragraph(text, styles["BulletItem"], bulletText="\u2022"))
            i += 1
            continue

        # Numbered list
        m = re.match(r'^(\d+)\.\s+(.*)', line.strip())
        if m:
            text = inline_format(escape(m.group(2)))
            story.append(Paragraph(text, styles["BulletItem"], bulletText=f"{m.group(1)}."))
            i += 1
            continue

        # Regular paragraph
        text = inline_format(escape(line.strip()))
        # Italic footer lines
        if line.strip().startswith("*") and line.strip().endswith("*"):
            text = f"<i>{escape(line.strip().strip('*'))}</i>"
            story.append(Paragraph(text, styles["Body"]))
            i += 1
            continue

        story.append(Paragraph(text, styles["Body"]))
        i += 1

    if in_code:
        flush_code()
    if in_table:
        flush_table()

    return story


def build_pdf(md_path, pdf_path):
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
    )

    story = parse_md(md_path)

    def add_page_number(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(HexColor("#999999"))
        canvas.drawCentredString(WIDTH / 2, 0.5 * inch, f"Page {doc.page}")
        canvas.drawString(MARGIN, 0.5 * inch, "gclib Communication Reference")
        canvas.drawRightString(WIDTH - MARGIN, 0.5 * inch, "2026-04-11")
        canvas.restoreState()

    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    print(f"PDF created: {pdf_path}")


if __name__ == "__main__":
    import os
    base = os.path.dirname(os.path.abspath(__file__))
    md = os.path.join(base, "gclib-communication-reference.md")
    pdf = os.path.join(base, "gclib-communication-reference.pdf")
    build_pdf(md, pdf)
