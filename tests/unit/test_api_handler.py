from unittest.mock import Mock

from botocore.exceptions import ClientError
from fastapi import HTTPException, status

from app import api_handler


class TestExceptionLogging:
    def test_http_exception_handler_does_not_log_a_traceback(self, mocker):
        exception_log = mocker.patch.object(api_handler.logger, "exception")
        error_log = mocker.patch.object(api_handler.logger, "error")

        response = api_handler.http_exception_handler(
            Mock(),
            HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="missing"),
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        exception_log.assert_not_called()
        error_log.assert_called_once()

    def test_cloud_error_handler_does_not_log_a_traceback(self, mocker):
        exception_log = mocker.patch.object(api_handler.logger, "exception")
        error_log = mocker.patch.object(api_handler.logger, "error")
        error = ClientError(
            {"Error": {"Code": "InternalError", "Message": "failed"}}, "PutItem"
        )

        response = api_handler.botocore_error_handler(Mock(), error)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        exception_log.assert_not_called()
        error_log.assert_called_once()
