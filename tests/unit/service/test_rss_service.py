from datetime import UTC, datetime, timedelta
from xml.etree import ElementTree

from app.services.rss_service import CONTENT_NAMESPACE, RSSService


class TestRSSService:
    def test_generate_feed_contains_posts_newest_first(self, posts):
        older = posts[0]
        newer = posts[1]
        older_date = datetime.now(UTC) - timedelta(days=2)
        newer_date = datetime.now(UTC) - timedelta(days=1)
        older.published_at = older_date.isoformat()
        newer.published_at = newer_date.isoformat()

        class StubPostService:
            def get_published_posts(self):
                return posts[:2]

        xml = RSSService(StubPostService()).generate_feed("http://testserver/")
        root = ElementTree.fromstring(xml)

        assert root.tag == "rss"
        items = root.findall("./channel/item")
        ids = [item.findtext("guid") for item in items]
        assert ids == [newer.id, older.id]

        newer_item = items[0]
        assert newer_item.findtext("link") == (
            f"http://testserver/api/v1/posts/{newer.post_path}"
        )
        assert newer_item.findtext(f"{{{CONTENT_NAMESPACE}}}encoded") == newer.content
