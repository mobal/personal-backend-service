from datetime import datetime
from typing import Optional

from fastapi_camelcase import CamelModel


class Post(CamelModel):
    uuid: str
    author: str
    title: str
    content: str
    created_at: datetime
    deleted_at: Optional[datetime]
    updated_at: Optional[datetime]
