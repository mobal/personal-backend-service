from pydantic import ConfigDict, conlist, constr

from app.models.camel_model import CamelModel
from app.models.post import Meta


class CreatePost(CamelModel):
    author: constr(strip_whitespace=True, min_length=3)
    title: constr(strip_whitespace=True, min_length=3)
    content: constr(strip_whitespace=True, min_length=3)
    tags: conlist(str, min_length=1)
    meta: Meta
    published_at: str | None

    model_config = ConfigDict(extra="ignore")


class UpdatePost(CamelModel):
    author: constr(strip_whitespace=True, min_length=3) | None = None
    title: constr(strip_whitespace=True, min_length=3) | None = None
    content: constr(strip_whitespace=True, min_length=3) | None = None
    tags: conlist(str, min_length=1) | None = None
    meta: Meta | None = None
    published_at: str | None = None

    model_config = ConfigDict(extra="ignore")
