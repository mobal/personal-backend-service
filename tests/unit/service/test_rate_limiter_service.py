from datetime import UTC, datetime

import boto3
import pytest

from app.services.rate_limiter_service import RateLimiterService
from app.settings import Settings


@pytest.fixture
def initialize_rate_limits_table(aws_default_region: str, settings: Settings):
    resource = boto3.Session().resource(
        "dynamodb",
        region_name=aws_default_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )
    resource.create_table(
        TableName="test-rate-limits",
        KeySchema=[
            {"AttributeName": "client_id", "KeyType": "HASH"},
            {"AttributeName": "endpoint", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "client_id", "AttributeType": "S"},
            {"AttributeName": "endpoint", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    yield


@pytest.fixture
def rate_limiter_service(initialize_rate_limits_table) -> RateLimiterService:
    return RateLimiterService(stage="test")


class TestRateLimiterService:
    def test_first_request_creates_record_and_allows(
        self,
        rate_limiter_service: RateLimiterService,
    ):
        result = rate_limiter_service.check_rate_limit("1.2.3.4", "/api/v1/posts")

        assert result.allowed is True
        assert result.request_count == 1
        assert result.limit == 60
        assert result.remaining == 59
        assert result.reset_at > datetime.now(UTC).timestamp()

    def test_subsequent_request_increments_counter(
        self,
        rate_limiter_service: RateLimiterService,
    ):
        rate_limiter_service.check_rate_limit("1.2.3.4", "/api/v1/posts")

        result = rate_limiter_service.check_rate_limit("1.2.3.4", "/api/v1/posts")

        assert result.allowed is True
        assert result.request_count == 2
        assert result.remaining == 58

    def test_rate_limit_exceeded(
        self,
        rate_limiter_service: RateLimiterService,
    ):
        client_id = "1.2.3.4"
        endpoint = "/api/v1/posts"

        # Make max_requests (60) calls
        for _ in range(60):
            rate_limiter_service.check_rate_limit(client_id, endpoint)

        result = rate_limiter_service.check_rate_limit(client_id, endpoint)

        assert result.allowed is False
        assert result.request_count == 60
        assert result.remaining == 0

    def test_different_endpoints_tracked_separately(
        self,
        rate_limiter_service: RateLimiterService,
    ):
        client_id = "1.2.3.4"

        rate_limiter_service.check_rate_limit(client_id, "/api/v1/posts")
        rate_limiter_service.check_rate_limit(client_id, "/api/v1/attachments")

        result_posts = rate_limiter_service.check_rate_limit(client_id, "/api/v1/posts")
        result_attachments = rate_limiter_service.check_rate_limit(
            client_id, "/api/v1/attachments"
        )

        assert result_posts.request_count == 2
        assert result_attachments.request_count == 2
        assert result_posts.allowed is True
        assert result_attachments.allowed is True

    def test_different_clients_tracked_separately(
        self,
        rate_limiter_service: RateLimiterService,
    ):
        endpoint = "/api/v1/posts"

        rate_limiter_service.check_rate_limit("1.2.3.4", endpoint)
        rate_limiter_service.check_rate_limit("5.6.7.8", endpoint)

        result_a = rate_limiter_service.check_rate_limit("1.2.3.4", endpoint)
        result_b = rate_limiter_service.check_rate_limit("5.6.7.8", endpoint)

        assert result_a.request_count == 2
        assert result_b.request_count == 2

    def test_ttl_is_set_on_new_records(
        self,
        aws_default_region: str,
        rate_limiter_service: RateLimiterService,
    ):
        rate_limiter_service.check_rate_limit("1.2.3.4", "/api/v1/posts")

        table = boto3.resource("dynamodb", region_name=aws_default_region).Table(
            "test-rate-limits"
        )
        response = table.get_item(
            Key={"client_id": "1.2.3.4", "endpoint": "/api/v1/posts"}
        )

        assert "ttl" in response["Item"]
        assert response["Item"]["ttl"] > datetime.now(UTC).timestamp()

    def test_reset_at_increases_with_each_request(
        self,
        rate_limiter_service: RateLimiterService,
    ):
        client_id = "1.2.3.4"
        endpoint = "/api/v1/posts"

        result1 = rate_limiter_service.check_rate_limit(client_id, endpoint)
        result2 = rate_limiter_service.check_rate_limit(client_id, endpoint)

        assert result2.reset_at >= result1.reset_at
