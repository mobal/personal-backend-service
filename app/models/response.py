from typing import Optional, List

from fastapi_camelcase import CamelModel

from app.models.post import Meta


class Post(CamelModel):
    id: Optional[str]
    author: Optional[str]
    title: Optional[str]
    content: Optional[str]
    published_at: Optional[str]
    updated_at: Optional[str]
    slug: Optional[str]
    tags: Optional[List[str]]
    meta: Optional[Meta]
