from typing import Optional

from pydantic import ConfigDict, conlist, constr

from app.models.camel_model import CamelModel
from app.models.post import Meta


class CreatePost(CamelModel):
    author: constr(strip_whitespace=True, min_length=3)
    title: constr(strip_whitespace=True, min_length=3)
    content: constr(strip_whitespace=True, min_length=3)
    tags: conlist(str, min_length=1)
    meta: Meta
    published_at: Optional[str]

    model_config = ConfigDict(extra='ignore')


class UpdatePost(CreatePost):
    author: Optional[constr(strip_whitespace=True, min_length=3)] = None
    title: Optional[constr(strip_whitespace=True, min_length=3)] = None
    content: Optional[constr(strip_whitespace=True, min_length=3)] = None
    tags: Optional[conlist(str, min_length=1)] = None
    meta: Optional[Meta] = None
    published_at: Optional[str] = None
