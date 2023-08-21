from typing import List, Optional

from app.models.camel_model import CamelModel
from app.models.post import Meta


class Post(CamelModel):
    id: Optional[str] = None
    author: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    published_at: Optional[str] = None
    updated_at: Optional[str] = None
    slug: Optional[str] = None
    tags: Optional[List[str]] = None
    meta: Optional[Meta] = None


class Page(CamelModel):
    exclusive_start_key: Optional[str] = None
    data: List[Post]
