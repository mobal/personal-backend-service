from typing import Annotated

from pydantic import BaseModel, Field, computed_field, conlist, constr

from app.models.camel_model import CamelModel


class Attachment(CamelModel):
    id: str
    bucket: str
    content_length: int
    description: str | None = None
    display_name: str
    mime_type: str
    name: str
    region: str

    @computed_field
    @property
    def url(self) -> str:
        return (
            f"https://{self.bucket}.s3.{self.region}.amazonaws.com/"
            f"{self.name.lstrip('/')}"
        )


class Meta(BaseModel):
    category: Annotated[
        str,
        Field(
            description="Section of the blog the post belongs to",
            examples=["tech"],
        ),
    ]
    description: Annotated[
        str,
        Field(
            description="One-paragraph summary of the post, used in listings and feeds",
            examples=["Working notes on the Analytical Engine."],
        ),
    ]
    language: Annotated[
        str,
        Field(
            description="Language of the post",
            examples=["en"],
        ),
    ]
    keywords: Annotated[
        conlist(item_type=str, min_length=1),
        Field(
            description="Search keywords describing the post",
            examples=[["engine", "notes"]],
        ),
    ]
    title: Annotated[
        str,
        Field(
            description="SEO title of the page; may differ from the post title",
            examples=["Notes on the Analytical Engine"],
        ),
    ]


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
