from typing import Optional

from fastapi_camelcase import CamelModel
from pydantic import BaseModel, conlist


class Meta(BaseModel):
    category: str
    description: str
    language: str
    keywords: conlist(item_type=str, min_items=1)
    title: str


class Post(CamelModel):
    id: str
    author: str
    title: str
    content: str
    created_at: str
    deleted_at: Optional[str] = None
    published_at: Optional[str] = None
    updated_at: Optional[str] = None
    slug: str
    tags: conlist(item_type=str, min_items=1)
    meta: Meta

    @property
    def is_deleted(self) -> bool:
        return bool(self.deleted_at)
