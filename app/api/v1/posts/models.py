from datetime import datetime
from typing import Optional

from fastapi_camelcase import CamelModel


class Post(CamelModel):
    id: str
    author: str
    title: str
    content: str
    _created_at: datetime
    deleted_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
