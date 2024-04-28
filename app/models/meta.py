from typing import Any

from app.models.camel_model import CamelModel


class Meta(CamelModel):
    key: str
    value: dict[str, Any] | str
