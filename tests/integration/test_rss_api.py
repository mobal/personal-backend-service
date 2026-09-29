from datetime import UTC, datetime, timedelta
from xml.etree import ElementTree

from fastapi import status
from fastapi.testclient import TestClient

from app.services.rss_service import CONTENT_NAMESPACE


class TestRSSApi:
    @staticmethod
    def _item_ids(root: ElementTree.Element) -> list[str | None]:
        return [item.findtext("guid") for item in root.findall("./channel/item")]

    def test_rss_endpoint_returns_published_posts_from_database(
        self,
        initialize_posts_table,
        posts,
        posts_table,
        test_client: TestClient,
    ):
        older = posts[0]
        newer = posts[1]
        older_date = datetime.now(UTC) - timedelta(days=2)
        newer_date = datetime.now(UTC) - timedelta(days=1)
        posts_table.update_item(
            Key={"id": older.id},
            UpdateExpression="SET published_at = :published_at",
            ExpressionAttributeValues={":published_at": older_date.isoformat()},
        )
        posts_table.update_item(
            Key={"id": newer.id},
            UpdateExpression="SET published_at = :published_at",
            ExpressionAttributeValues={":published_at": newer_date.isoformat()},
        )
        posts_table.update_item(
            Key={"id": posts[2].id},
            UpdateExpression="SET published_at = :published_at",
            ExpressionAttributeValues={
                ":published_at": (datetime.now(UTC) + timedelta(days=1)).isoformat()
            },
        )
        posts_table.update_item(
            Key={"id": posts[3].id},
            UpdateExpression="SET deleted_at = :deleted_at",
            ExpressionAttributeValues={":deleted_at": datetime.now(UTC).isoformat()},
        )

        response = test_client.get("/rss.xml")

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"].startswith("application/rss+xml")
        root = ElementTree.fromstring(response.content)
        item_ids = self._item_ids(root)
        assert newer.id in item_ids
        assert older.id in item_ids
        assert posts[2].id not in item_ids
        assert posts[3].id not in item_ids
        assert item_ids.index(newer.id) < item_ids.index(older.id)

        newer_item = next(
            item
            for item in root.findall("./channel/item")
            if item.findtext("guid") == newer.id
        )
        assert newer_item.findtext("link") == (
            f"http://testserver/api/v1/posts/{newer.post_path}"
        )
        assert newer_item.findtext(f"{{{CONTENT_NAMESPACE}}}encoded") == newer.content
