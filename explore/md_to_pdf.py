#!/usr/bin/env python3
"""
Convert Markdown files to PDF using markdown + reportlab.
Usage: python md_to_pdf.py <input.md> [output.pdf]
"""
import re
import sys
from pathlib import Path

import markdown
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
)


def md_to_flowables(md_path):
    """Convert markdown file to list of ReportLab flowables."""
    text = Path(md_path).read_text(encoding="utf-8")
    html = markdown.markdown(
        text,
        extensions=["extra", "tables", "nl2br"],
        output_format="html5",
    )

    styles = getSampleStyleSheet()
    # Custom styles
    styles.add(ParagraphStyle(
        name="H1", fontSize=18, spaceAfter=12, textColor=colors.HexColor("#1a1a1a"),
        parent=styles["Heading1"],
    ))
    styles.add(ParagraphStyle(
        name="H2", fontSize=14, spaceAfter=10, spaceBefore=14, textColor=colors.HexColor("#333333"),
        parent=styles["Heading2"],
    ))
    styles.add(ParagraphStyle(
        name="H3", fontSize=12, spaceAfter=8, spaceBefore=10, textColor=colors.HexColor("#444444"),
        parent=styles["Heading3"],
    ))
    body = ParagraphStyle(
        name="Body", fontSize=10, spaceAfter=6, leading=12,
    )

    flowables = []

    # Simple HTML parsing (tag-based split)
    # Remove style/script if any
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)

    def tag_pattern(tag):
        return re.compile(rf"<{tag}[^>]*>(.*?)</{tag}>", re.DOTALL | re.IGNORECASE)

    def extract_blocks(html_str):
        """Extract top-level blocks: h1, h2, h3, p, ul, ol, table."""
        blocks = []
        pos = 0
        # Match blocks in order
        pattern = re.compile(
            r"<(h[1-3]|p|ul|ol|table)[^>]*>(.*?)</\1>",
            re.DOTALL | re.IGNORECASE,
        )
        for m in pattern.finditer(html_str):
            if m.start() > pos:
                raw = html_str[pos : m.start()].strip()
                if raw and not raw.startswith("<"):
                    blocks.append(("text", raw))
            tag = m.group(1).lower()
            content = m.group(2).strip()
            blocks.append((tag, content))
            pos = m.end()
        rest = html_str[pos:].strip()
        if rest and not rest.startswith("<"):
            blocks.append(("text", rest))
        return blocks

    def strip_tags(s):
        return re.sub(r"<[^>]+>", "", s).replace("&nbsp;", " ").strip()

    def html_to_reportlab(s):
        """Convert simple HTML inline tags to ReportLab markup."""
        s = s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        s = re.sub(r"<strong>(.*?)</strong>", r"<b>\1</b>", s, flags=re.IGNORECASE)
        s = re.sub(r"<b>(.*?)</b>", r"<b>\1</b>", s, flags=re.IGNORECASE)
        s = re.sub(r"<em>(.*?)</em>", r"<i>\1</i>", s, flags=re.IGNORECASE)
        s = re.sub(r"<i>(.*?)</i>", r"<i>\1</i>", s, flags=re.IGNORECASE)
        s = re.sub(r"<br\s*/?>", "<br/>", s, flags=re.IGNORECASE)
        s = re.sub(r"<code>(.*?)</code>", r"<font face='Courier'>\1</font>", s, flags=re.IGNORECASE)
        return s

    blocks = extract_blocks(html)

    for kind, content in blocks:
        content = content.strip()
        if not content:
            continue
        if kind == "h1":
            flowables.append(Paragraph(html_to_reportlab(strip_tags(content)), styles["H1"]))
            flowables.append(Spacer(1, 6))
        elif kind == "h2":
            flowables.append(Paragraph(html_to_reportlab(strip_tags(content)), styles["H2"]))
            flowables.append(Spacer(1, 4))
        elif kind == "h3":
            flowables.append(Paragraph(html_to_reportlab(strip_tags(content)), styles["H3"]))
            flowables.append(Spacer(1, 2))
        elif kind == "p":
            flowables.append(Paragraph(html_to_reportlab(content), body))
        elif kind == "ul":
            items = re.findall(r"<li>(.*?)</li>", content, re.DOTALL | re.IGNORECASE)
            for item in items:
                flowables.append(
                    Paragraph(html_to_reportlab("• " + strip_tags(item)), body)
                )
        elif kind == "ol":
            items = re.findall(r"<li>(.*?)</li>", content, re.DOTALL | re.IGNORECASE)
            for i, item in enumerate(items, 1):
                flowables.append(
                    Paragraph(html_to_reportlab(f"{i}. " + strip_tags(item)), body)
                )
        elif kind == "table":
            rows = re.findall(r"<tr>(.*?)</tr>", content, re.DOTALL | re.IGNORECASE)
            data = []
            for row in rows:
                cells = re.findall(r"<t[hd](?:[^>]*)>(.*?)</t[hd]>", row, re.DOTALL | re.IGNORECASE)
                data.append([strip_tags(c) for c in cells])
            if data:
                t = Table(data)
                t.setStyle(
                    TableStyle(
                        [
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, -1), 9),
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8e8e8")),
                            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ]
                    )
                )
                flowables.append(t)
                flowables.append(Spacer(1, 10))
        elif kind == "text":
            # Unwrapped text (e.g. between blocks)
            for line in content.split("\n"):
                line = line.strip()
                if line:
                    flowables.append(Paragraph(html_to_reportlab(line), body))

    return flowables


def main():
    if len(sys.argv) < 2:
        print("Usage: python md_to_pdf.py <input.md> [output.pdf]")
        sys.exit(1)
    md_path = Path(sys.argv[1])
    if not md_path.exists():
        print(f"File not found: {md_path}")
        sys.exit(1)
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else md_path.with_suffix(".pdf")

    flowables = md_to_flowables(md_path)
    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )
    doc.build(flowables)
    print(f"Created: {out_path}")


if __name__ == "__main__":
    main()
