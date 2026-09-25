from app.repositories.rate_limit_repository import RateLimitRepository


class TestRateLimitRepository:
    def test_conditionally_consumes_request_allowance(
        self,
        rate_limit_repository: RateLimitRepository,
    ):
        assert (
            rate_limit_repository.consume_request(
                "1.2.3.4", "/api/v1/posts#100", 2, 100, 220
            )
            == 1
        )
        assert (
            rate_limit_repository.consume_request(
                "1.2.3.4", "/api/v1/posts#100", 2, 100, 220
            )
            == 2
        )
        assert (
            rate_limit_repository.consume_request(
                "1.2.3.4", "/api/v1/posts#100", 2, 100, 220
            )
            is None
        )

    def test_separate_window_key_has_independent_allowance(
        self,
        rate_limit_repository: RateLimitRepository,
    ):
        assert (
            rate_limit_repository.consume_request(
                "1.2.3.4", "/api/v1/posts#100", 1, 100, 220
            )
            == 1
        )
        assert (
            rate_limit_repository.consume_request(
                "1.2.3.4", "/api/v1/posts#200", 1, 200, 320
            )
            == 1
        )
