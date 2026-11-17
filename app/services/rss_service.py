from datetime import UTC, datetime
from email.utils import format_datetime
from xml.etree import ElementTree

from app.models.post import Post
from app.services.post_service import PostService, render_markdown
from app.settings import Settings

CONTENT_NAMESPACE = "http://purl.org/rss/1.0/modules/content/"
ElementTree.register_namespace("content", CONTENT_NAMESPACE)


class RSSService:
    def __init__(self, post_service: PostService, settings: Settings):
        self._post_service = post_service
        self._settings = settings

    def generate_feed(self, base_url: str) -> bytes:
        """Build the feed.

        With BLOG_URL set the feed points at the blog (`{blog_url}/{post_path}`);
        without it the links address this API, which is all it can know about.
        """
        base_url = base_url.rstrip("/")
        blog_url = (self._settings.blog_url or "").rstrip("/")
        rss = ElementTree.Element("rss", {"version": "2.0"})
        channel = ElementTree.SubElement(rss, "channel")
        self._add_text(channel, "title", self._settings.blog_title)
        self._add_text(channel, "link", blog_url or base_url)
        self._add_text(channel, "description", self._settings.blog_description)

        posts = self._post_service.get_published_posts()
        posts.sort(key=self._published_at, reverse=True)
        for post in posts:
            if not post.published_at or not post.post_path:
                continue
            item = ElementTree.SubElement(channel, "item")
            self._add_text(item, "title", post.title)
            self._add_text(
                item,
                "link",
                (
                    f"{blog_url}/{post.post_path}"
                    if blog_url
                    else f"{base_url}/api/v1/posts/{post.post_path}"
                ),
            )
            ElementTree.SubElement(
                item, "guid", {"isPermaLink": "false"}
            ).text = post.id
            self._add_text(item, "pubDate", format_datetime(self._published_at(post)))
            self._add_text(item, "description", post.meta.description)
            self._add_text(
                item,
                f"{{{CONTENT_NAMESPACE}}}encoded",
                render_markdown(post.content),
            )

        return ElementTree.tostring(rss, encoding="utf-8", xml_declaration=True)

    @staticmethod
    def _add_text(parent: ElementTree.Element, tag: str, value: str) -> None:
        ElementTree.SubElement(parent, tag).text = value

    @staticmethod
    def _published_at(post: Post) -> datetime:
        published_at = datetime.fromisoformat(post.published_at or "")
        return (
            published_at.replace(tzinfo=UTC)
            if published_at.tzinfo is None
            else published_at.astimezone(UTC)
        )
