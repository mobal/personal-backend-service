from typing import Optional

import boto3
from aws_lambda_powertools import Logger

from app.models.meta import Meta
from app.settings import Settings


class MetaRepository:
    def __init__(self):
        self._logger = Logger()
        settings = Settings()
        self._table = (
            boto3.Session().resource("dynamodb").Table(f"{settings.stage}-meta")
        )

    async def get_meta_by_key(self, key: str) -> dict | None:
        response = self._table.get_item(Key={"key": key})
        return response["Item"] if response["Item"] else None
