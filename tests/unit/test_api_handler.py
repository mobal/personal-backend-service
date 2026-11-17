import json
from unittest.mock import Mock

from botocore.exceptions import ClientError
from fastapi import HTTPException, status

from app import api_handler


class TestExceptionLogging:
    def test_http_exception_handler_does_not_log_a_traceback(self, mocker):
        exception_log = mocker.patch.object(api_handler.logger, "exception")
        error_log = mocker.patch.object(api_handler.logger, "error")
        info_log = mocker.patch.object(api_handler.logger, "info")

        response = api_handler.http_exception_handler(
            Mock(),
            HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="missing"),
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        exception_log.assert_not_called()
        error_log.assert_not_called()
        info_log.assert_called_once()

    def test_http_exception_handler_keeps_exception_headers(self):
        response = api_handler.http_exception_handler(
            Mock(),
            HTTPException(
                status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                detail="Method Not Allowed",
                headers={"Allow": "GET"},
            ),
        )

        assert response.headers["Allow"] == "GET"

    def test_cloud_error_handler_logs_the_cause_without_exposing_it(self, mocker):
        exception_log = mocker.patch.object(api_handler.logger, "exception")
        error_log = mocker.patch.object(api_handler.logger, "error")
        mocker.patch.object(api_handler.settings, "debug", False)
        error = ClientError(
            {"Error": {"Code": "InternalError", "Message": "failed"}}, "PutItem"
        )

        response = api_handler.botocore_error_handler(Mock(), error)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert json.loads(response.body)["message"] == "Internal Server Error"
        exception_log.assert_not_called()
        error_log.assert_called_once()
        assert error_log.call_args.kwargs["exc_info"] is error

    def test_unhandled_error_handler_returns_the_standard_error_shape(self, mocker):
        error_log = mocker.patch.object(api_handler.logger, "error")
        error = RuntimeError("database password is hunter2")

        response = api_handler.unhandled_exception_handler(Mock(), error)

        body = json.loads(response.body)
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert body["status"] == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert body["message"] == "Internal Server Error"
        assert body["id"]
        assert error_log.call_args.kwargs["exc_info"] is error
