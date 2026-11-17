import pytest

from app.services.post_service import render_markdown


class TestRenderMarkdown:
    def test_renders_common_markdown(self):
        html = render_markdown(
            "# Title\n\n**bold** and *em* and `code`\n\n- one\n- two"
        )

        assert "<h1>Title</h1>" in html
        assert "<strong>bold</strong>" in html
        assert "<em>em</em>" in html
        assert "<code>code</code>" in html
        assert "<ul>" in html
        assert "<li>one</li>" in html

    def test_renders_indented_code_blocks(self):
        html = render_markdown("text\n\n    print(1)\n")

        assert "<pre><code>print(1)" in html

    def test_keeps_links_with_safe_schemes(self):
        html = render_markdown(
            "[web](https://example.com/a?b=1) [mail](mailto:me@example.com)"
        )

        assert 'href="https://example.com/a?b=1"' in html
        assert 'href="mailto:me@example.com"' in html

    def test_keeps_the_rel_attribute_of_links(self):
        html = render_markdown('<a href="https://example.com" rel="nofollow">x</a>')

        assert 'rel="nofollow"' in html

    @pytest.mark.parametrize(
        "unsafe_link",
        [
            "javascript:alert(1)",
            "JaVaScRiPt:alert(1)",
            "data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==",
            "vbscript:msgbox(1)",
        ],
    )
    def test_strips_unsafe_link_schemes(self, unsafe_link: str):
        html = render_markdown(f"[click]({unsafe_link})")

        assert "javascript" not in html.lower()
        assert "vbscript" not in html.lower()
        assert "data:" not in html
        assert "click" in html

    def test_keeps_images_with_dimensions(self):
        html = render_markdown(
            '<img src="https://example.com/a.png" alt="a" width="10" height="20">'
        )

        assert 'src="https://example.com/a.png"' in html
        assert 'alt="a"' in html
        assert 'width="10"' in html
        assert 'height="20"' in html

    def test_strips_data_urls_from_images(self):
        html = render_markdown('<img src="data:image/png;base64,AAAA" alt="a">')

        assert "data:" not in html

    def test_removes_event_handler_and_style_attributes(self):
        html = render_markdown(
            '<p onclick="alert(1)" style="color:red" class="note">hi</p>'
        )

        assert "onclick" not in html
        assert "style" not in html
        assert 'class="note"' in html

    @pytest.mark.parametrize(
        "tag", ["script", "iframe", "object", "embed", "form", "style"]
    )
    def test_removes_dangerous_elements(self, tag: str):
        html = render_markdown(f"before <{tag} src=x>payload</{tag}> after")

        assert f"<{tag}" not in html
        assert "before" in html
        assert "after" in html

    @pytest.mark.parametrize("tag", ["script", "style"])
    def test_drops_the_body_of_script_and_style_elements(self, tag: str):
        html = render_markdown(f"before <{tag}>payload()</{tag}> after")

        assert "payload" not in html
        assert "before" in html
        assert "after" in html

    def test_removes_html_comments(self):
        html = render_markdown("text <!-- secret --> more")

        assert "secret" not in html
        assert "<!--" not in html

    def test_escapes_text_that_only_looks_like_a_tag(self):
        html = render_markdown("1 < 2 and 3 > 2")

        assert "&lt;" in html
        assert "&gt;" in html
