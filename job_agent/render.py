"""Markdown resume -> HTML (styled like the ohmycv export) -> PDF via the installed Edge, driven by Playwright."""
import html
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")

CSS = """
@page { size: A4; margin: 14mm 16mm; }
body { font-family: "Source Serif Pro", "Noto Serif", Georgia, serif; font-size: 10.5pt; color: #222;
       line-height: 1.35; margin: 0; }
h1 { color: #2f7db5; text-align: center; font-size: 22pt; margin: 0 0 4px; }
h2 { color: #2f7db5; font-size: 12.5pt; border-bottom: 1.5px solid #2f7db5; margin: 12px 0 5px; padding-bottom: 1px; }
h3 { font-size: 10.5pt; margin: 8px 0 2px; }
p { margin: 2px 0; }
ul, ol { margin: 2px 0 2px 18px; padding: 0; }
li { margin: 1px 0; }
a { color: #2f7db5; text-decoration: none; }
"""


def _inline(text: str) -> str:
    text = html.escape(text, quote=False)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<em>\1</em>", text)
    return text


def markdown_to_html(md: str) -> str:
    """The subset the resume uses: #/##/### headings, - and 1. lists (one nesting level), paragraphs."""
    out: list[str] = []
    open_lists: list[list] = []     # stack of [kind, item_open], one entry per open ul/ol
    paragraph: list[str] = []

    def close_paragraph():
        if paragraph:
            out.append(f"<p>{' '.join(paragraph)}</p>")
            paragraph.clear()

    def close_lists(to_depth: int = 0):
        while len(open_lists) > to_depth:
            kind, item_open = open_lists.pop()
            if item_open:
                out.append("</li>")
            out.append(f"</{kind}>")

    for raw in md.splitlines():
        line = raw.rstrip()
        indent = len(raw) - len(raw.lstrip(" "))
        heading = re.match(r"^(#{1,3})\s+(.*)$", line)
        bullet = re.match(r"^\s*([-*]|\d+\.)\s+(.*)$", line)
        if heading:
            close_paragraph(); close_lists()
            level = len(heading.group(1))
            out.append(f"<h{level}>{_inline(heading.group(2))}</h{level}>")
        elif bullet:
            close_paragraph()
            kind = "ol" if bullet.group(1)[0].isdigit() else "ul"
            depth = 2 if indent >= 2 else 1
            if depth > len(open_lists):
                out.append(f"<{kind}>"); open_lists.append([kind, False])
            elif depth < len(open_lists):
                close_lists(depth)
            if open_lists[-1][1]:
                out.append("</li>")
            out.append(f"<li>{_inline(bullet.group(2))}")
            open_lists[-1][1] = True
        elif not line.strip():
            close_paragraph(); close_lists()
        else:
            close_lists()
            paragraph.append(_inline(line.strip()))
    close_paragraph(); close_lists()
    return "\n".join(out)


def render_resume_html(md: str) -> str:
    return f"<!DOCTYPE html>\n<html><head><meta charset=\"utf-8\"><style>{CSS}</style></head>\n" \
           f"<body>\n{markdown_to_html(md)}\n</body></html>\n"


def html_to_pdf(html_path: Path, pdf_path: Path) -> None:
    # Playwright owns the browser process, so there is no "Edge wrote the PDF but never exited" hang
    # that the plain `msedge --headless --print-to-pdf` call had.
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        try:
            page = browser.new_page()
            page.goto(html_path.resolve().as_uri())
            page.pdf(path=str(pdf_path), prefer_css_page_size=True, print_background=True)
        finally:
            browser.close()
    if not pdf_path.exists():
        raise RuntimeError(f"Edge produced no PDF at {pdf_path}")
