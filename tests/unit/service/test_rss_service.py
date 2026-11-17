from datetime import UTC, datetime, timedelta
from xml.etree import ElementTree

import pytest

from app.services.rss_service import CONTENT_NAMESPACE, RSSService
from app.settings import Settings


class TestRSSService:
    def test_generate_feed_contains_posts_newest_first(self, posts, settings):
        older = posts[0]
        newer = posts[1]
        older_date = datetime.now(UTC) - timedelta(days=2)
        newer_date = datetime.now(UTC) - timedelta(days=1)
        older.published_at = older_date.isoformat()
        newer.published_at = newer_date.isoformat()
        newer.content = "**Bold** <script>alert(1)</script>claim"

        class StubPostService:
            def get_published_posts(self):
                return posts[:2]

        xml = RSSService(StubPostService(), settings).generate_feed(
            "http://testserver/"
        )
        root = ElementTree.fromstring(xml)

        assert root.tag == "rss"
        items = root.findall("./channel/item")
        ids = [item.findtext("guid") for item in items]
        assert ids == [newer.id, older.id]

        newer_item = items[0]
        assert newer_item.findtext("link") == (
            f"http://testserver/api/v1/posts/{newer.post_path}"
        )
        assert newer_item.findtext(f"{{{CONTENT_NAMESPACE}}}encoded") == (
            "<p><strong>Bold</strong> claim</p>"
        )

    @pytest.fixture
    def blog_settings(self, monkeypatch: pytest.MonkeyPatch) -> Settings:
        monkeypatch.setenv("BLOG_URL", "https://blog.example.com/")
        monkeypatch.setenv("BLOG_TITLE", "Balázs' notes")
        monkeypatch.setenv("BLOG_DESCRIPTION", "Things I learned")
        return Settings()

    def test_generate_feed_links_to_the_blog_when_its_url_is_configured(
        self, posts, blog_settings
    ):
        class StubPostService:
            def get_published_posts(self):
                return posts[:1]

        xml = RSSService(StubPostService(), blog_settings).generate_feed(
            "http://testserver/"
        )
        channel = ElementTree.fromstring(xml).find("./channel")

        assert channel.findtext("title") == "Balázs' notes"
        assert channel.findtext("description") == "Things I learned"
        assert channel.findtext("link") == "https://blog.example.com"
        assert channel.findtext("./item/link") == (
            f"https://blog.example.com/{posts[0].post_path}"
        )

    def test_generate_feed_keeps_the_api_links_without_a_blog_url(
        self, monkeypatch: pytest.MonkeyPatch, posts
    ):
        monkeypatch.delenv("BLOG_URL", raising=False)

        class StubPostService:
            def get_published_posts(self):
                return posts[:1]

        xml = RSSService(StubPostService(), Settings()).generate_feed(
            "http://testserver/"
        )
        channel = ElementTree.fromstring(xml).find("./channel")

        assert channel.findtext("link") == "http://testserver"
        assert channel.findtext("./item/link") == (
            f"http://testserver/api/v1/posts/{posts[0].post_path}"
        )
