import logging

import pytest
from aws_lambda_powertools import Logger


class TestLogLevel:
    @pytest.mark.parametrize(
        ("variable", "expected"),
        [
            ("POWERTOOLS_LOG_LEVEL", logging.WARNING),
            # Not a variable Powertools knows: it must stay at its INFO default.
            ("POWERTOOLS_LOGGER_LOG_LEVEL", logging.INFO),
        ],
    )
    def test_the_powertools_logger_honors_only_its_own_variable(
        self, monkeypatch: pytest.MonkeyPatch, variable: str, expected: int
    ):
        for name in (
            "POWERTOOLS_LOG_LEVEL",
            "LOG_LEVEL",
            "POWERTOOLS_LOGGER_LOG_LEVEL",
        ):
            monkeypatch.delenv(name, raising=False)
        monkeypatch.setenv(variable, "WARNING")

        assert Logger(service=f"probe-{variable}").log_level == expected
