import urllib.parse

from pydantic import BaseModel, computed_field, conlist, constr

from app.models.camel_model import CamelModel


class Attachment(CamelModel):
    id: str
    bucket: str
    content_length: int
    mime_type: str
    name: str

    @computed_field
    @property
    def url(self) -> str:
        return urllib.parse.urljoin(
            f"https://{self.bucket}.s3.amazonaws.com", self.name
        )


class Meta(BaseModel):
    category: str
    description: str
    language: str
    keywords: conlist(item_type=str, min_length=1)
    title: str


class Post(CamelModel):
    id: str
    author: constr(strip_whitespace=True, min_length=3)
    title: constr(strip_whitespace=True, min_length=3)
    content: constr(strip_whitespace=True, min_length=3)
    post_path: str
    created_at: str
    deleted_at: str | None = None
    published_at: str | None = None
    updated_at: str | None = None
    slug: str
    tags: conlist(item_type=str, min_length=1)
    meta: Meta
    attachments: list[Attachment] | None = None

    @property
    def is_deleted(self) -> bool:
        return bool(self.deleted_at)
