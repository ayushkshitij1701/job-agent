import pytest
from pypdf import PdfReader

from job_agent.render import EDGE, html_to_pdf, markdown_to_html, render_resume_html


def test_markdown_to_html_basic_blocks_and_inline():
    md = "# Name\n\n**SDE** | *Goa* | [site](https://x.y)\n\n## Skills\n- Python & Java\n- SQL\n\n1. First\n   - sub\n"
    html = markdown_to_html(md)
    assert "<h1>Name</h1>" in html
    assert "<strong>SDE</strong>" in html
    assert "<em>Goa</em>" in html
    assert '<a href="https://x.y">site</a>' in html
    assert "<h2>Skills</h2>" in html
    assert "<ul><li>Python &amp; Java</li><li>SQL</li></ul>" in html.replace("\n", "")
    assert "<ol><li>First<ul><li>sub</li></ul></li></ol>" in html.replace("\n", "")


def test_render_resume_html_is_a_full_styled_document():
    html = render_resume_html("# Ayush\n## Experience\n- x")
    assert html.startswith("<!DOCTYPE html>")
    assert "<style>" in html
    assert "<h1>Ayush</h1>" in html


@pytest.mark.skipif(not EDGE.exists(), reason="Microsoft Edge not installed")
def test_html_to_pdf_produces_readable_pdf(tmp_path):
    html_path = tmp_path / "r.html"
    html_path.write_text(render_resume_html("# Ayush Kshitij\n## Skills\n- Python"), encoding="utf-8")
    pdf_path = tmp_path / "r.pdf"
    html_to_pdf(html_path, pdf_path)
    reader = PdfReader(str(pdf_path))
    assert len(reader.pages) >= 1
    assert "Ayush Kshitij" in reader.pages[0].extract_text()
