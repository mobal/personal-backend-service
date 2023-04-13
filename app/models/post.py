from typing import Optional

from fastapi_camelcase import CamelModel
from pydantic import BaseModel, conlist, constr


class Meta(BaseModel):
    category: str
    description: str
    language: str
    keywords: conlist(item_type=str, min_items=1)
    title: str


class Post(CamelModel):
    id: str
    author: constr(strip_whitespace=True, min_length=3)
    title: constr(strip_whitespace=True, min_length=3)
    content: constr(strip_whitespace=True, min_length=3)
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
