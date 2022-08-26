from typing import Optional

from fastapi_camelcase import CamelModel
from pydantic import conlist


class Meta(CamelModel):
    description: Optional[str]
    language: Optional[str]
    keywords: Optional[conlist(item_type=str, min_items=1)]
    title: Optional[str]


class Post(CamelModel):
    id: Optional[str]
    author: Optional[str]
    title: Optional[str]
    content: Optional[str]
    created_at: Optional[str]
    deleted_at: Optional[str]
    published_at: Optional[str]
    updated_at: Optional[str]
    slug: Optional[str]
    tags: Optional[conlist(item_type=str, min_items=1)]
    meta: Optional[Meta]

    @property
    def is_deleted(self) -> bool:
        return bool(self.deleted_at)
