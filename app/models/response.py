from app.models.camel_model import CamelModel
from app.models.post import Meta


class Attachment(CamelModel):
    id: str
    content_length: int
    description: str | None = None
    display_name: str
    mime_type: str
    url: str


class Post(CamelModel):
    id: str | None = None
    author: str | None = None
    title: str | None = None
    content: str | None = None
    post_path: str | None = None
    published_at: str | None = None
    updated_at: str | None = None
    slug: str | None = None
    tags: list[str] | None = None
    meta: Meta | None = None
    attachments: list[Attachment] | None = None


class Page(CamelModel):
    exclusive_start_key: str | None = None
    posts: list[Post]
