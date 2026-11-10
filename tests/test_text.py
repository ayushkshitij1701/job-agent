from job_agent.text import html_to_text


def test_html_to_text_keeps_blocks_and_bullets():
    html = "<p>Role&nbsp;summary</p><ul><li><strong>Python</strong> 3+</li><li>SQL &amp; APIs</li></ul>"
    assert html_to_text(html) == "Role summary\n- Python 3+\n- SQL & APIs"


def test_html_to_text_collapses_blank_lines():
    assert html_to_text("<p>a</p>\n\n<p></p>\n<p>b</p>") == "a\nb"
