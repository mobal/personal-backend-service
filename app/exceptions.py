from typing import Any

from fastapi import HTTPException, status


class CacheServiceException(HTTPException):
    def __init__(self, detail: Any = None) -> None:
        super().__init__(status.HTTP_500_INTERNAL_SERVER_ERROR, detail)


class PostAlreadyExistsException(HTTPException):
    def __init__(self, detail: Any = None) -> None:
        super().__init__(status.HTTP_409_CONFLICT, detail)


class PostNotFoundException(HTTPException):
    def __init__(self, detail: Any = None) -> None:
        super().__init__(status.HTTP_404_NOT_FOUND, detail=detail)
