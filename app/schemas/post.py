from typing import Optional

from fastapi_camelcase import CamelModel
from pydantic import conlist, constr

from app.models.post import Meta


class CreatePost(CamelModel):
    author: constr(strip_whitespace=True, min_length=3)
    title: constr(strip_whitespace=True, min_length=3)
    content: constr(strip_whitespace=True, min_length=3)
    tags: Optional[conlist(str, min_items=1)] = None
    meta: Optional[Meta] = None
    published_at: Optional[str] = None


class UpdatePost(CreatePost):
    pass
