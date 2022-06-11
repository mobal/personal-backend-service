from datetime import datetime
from typing import Optional

from fastapi_camelcase import CamelModel


class Meta(CamelModel):
    reading_time: int


class Post(CamelModel):
    id: str
    author: str
    title: str
    content: str
    created_at: datetime = datetime.now().isoformat()
    deleted_at: Optional[datetime]
    published_at: Optional[datetime]
    updated_at: Optional[datetime]
    slug: str
    meta: Optional[Meta]
