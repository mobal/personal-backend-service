from decimal import Decimal

from app.repositories.rate_limit_repository import RateLimitRepository


class TestRateLimitRepository:
    def test_successfully_get_rate_limit(
        self,
        rate_limit_repository: RateLimitRepository,
    ):
        rate_limit_repository.create_rate_limit(
            "1.2.3.4", "/api/v1/posts", 1, Decimal("100"), Decimal("160")
        )

        item = rate_limit_repository.get_rate_limit("1.2.3.4", "/api/v1/posts")

        assert item == {
            "client_id": "1.2.3.4",
            "endpoint": "/api/v1/posts",
            "request_count": 1,
            "window_start": Decimal("100"),
            "ttl": Decimal("160"),
        }

    def test_fail_to_get_rate_limit(
        self,
        rate_limit_repository: RateLimitRepository,
    ):
        assert rate_limit_repository.get_rate_limit("1.2.3.4", "/api/v1/posts") is None

    def test_successfully_create_rate_limit(
        self,
        rate_limit_repository: RateLimitRepository,
        rate_limits_table,
    ):
        rate_limit_repository.create_rate_limit(
            "1.2.3.4", "/api/v1/posts", 1, Decimal("100"), Decimal("160")
        )

        assert (
            rate_limits_table.get_item(
                Key={"client_id": "1.2.3.4", "endpoint": "/api/v1/posts"}
            )["Item"]["request_count"]
            == 1
        )

    def test_successfully_reset_rate_limit(
        self,
        rate_limit_repository: RateLimitRepository,
    ):
        rate_limit_repository.create_rate_limit(
            "1.2.3.4", "/api/v1/posts", 60, Decimal("100"), Decimal("160")
        )

        rate_limit_repository.reset_rate_limit(
            "1.2.3.4", "/api/v1/posts", 1, Decimal("200"), Decimal("260")
        )

        assert rate_limit_repository.get_rate_limit("1.2.3.4", "/api/v1/posts") == {
            "client_id": "1.2.3.4",
            "endpoint": "/api/v1/posts",
            "request_count": 1,
            "window_start": Decimal("200"),
            "ttl": Decimal("260"),
        }

    def test_successfully_increment_rate_limit(
        self,
        rate_limit_repository: RateLimitRepository,
    ):
        rate_limit_repository.create_rate_limit(
            "1.2.3.4", "/api/v1/posts", 1, Decimal("100"), Decimal("160")
        )

        rate_limit_repository.increment_rate_limit("1.2.3.4", "/api/v1/posts")

        item = rate_limit_repository.get_rate_limit("1.2.3.4", "/api/v1/posts")
        assert item is not None
        assert item["request_count"] == 2
