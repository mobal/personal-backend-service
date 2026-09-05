from typing import Annotated

from pydantic import ConfigDict, Field, conlist, constr

from app.models.camel_model import CamelModel
from app.models.post import Meta

CreatePostExample = {
    "summary": "A minimal Markdown blog post",
    "value": {
        "author": "Ada Lovelace",
        "title": "Notes on the Analytical Engine",
        "content": "**First draft** of the notes.",
        "tags": ["notes", "analytical-engine"],
        "meta": {
            "category": "tech",
            "description": "Working notes on the engine.",
            "language": "en",
            "keywords": ["engine", "notes"],
            "title": "Notes on the Analytical Engine",
        },
        "publishedAt": "2026-09-05T12:00:00+00:00",
    },
}


class CreatePost(CamelModel):
    author: Annotated[
        constr(strip_whitespace=True, min_length=3),
        Field(
            description="Author of the post, at least 3 characters",
            examples=["Ada Lovelace"],
        ),
    ]
    title: Annotated[
        constr(strip_whitespace=True, min_length=3),
        Field(
            description="Title of the post, at least 3 characters; must be "
            "unique among non-deleted posts",
            examples=["Notes on the Analytical Engine"],
        ),
    ]
    content: Annotated[
        constr(strip_whitespace=True, min_length=3),
        Field(
            description="Body of the post in Markdown, at least 3 characters",
            examples=["**First draft** of the notes."],
        ),
    ]
    tags: Annotated[
        conlist(str, min_length=1),
        Field(
            description="Free-form tags used for grouping posts",
            examples=[["notes", "analytical-engine"]],
        ),
    ]
    meta: Annotated[
        Meta,
        Field(description="SEO-style metadata embedded in the rendered page"),
    ]
    published_at: Annotated[
        str | None,
        Field(
            description="ISO 8601 publication timestamp; absent or null keeps "
            "the post unpublished and unlisted",
            examples=["2026-09-05T12:00:00+00:00"],
        ),
    ]

    model_config = ConfigDict(
        extra="ignore",
        json_schema_extra={"examples": [CreatePostExample["value"]]},
    )


class UpdatePost(CamelModel):
    author: Annotated[
        constr(strip_whitespace=True, min_length=3) | None,
        Field(
            description="Author of the post, at least 3 characters",
            examples=["Ada Lovelace"],
        ),
    ] = None
    title: Annotated[
        constr(strip_whitespace=True, min_length=3) | None,
        Field(
            description="Title of the post, at least 3 characters; must be "
            "unique among non-deleted posts",
            examples=["Notes on the Analytical Engine"],
        ),
    ] = None
    content: Annotated[
        constr(strip_whitespace=True, min_length=3) | None,
        Field(
            description="Body of the post in Markdown, at least 3 characters",
            examples=["**First draft** of the notes."],
        ),
    ] = None
    tags: Annotated[
        conlist(str, min_length=1) | None,
        Field(
            description="Free-form tags used for grouping posts",
            examples=[["notes", "analytical-engine"]],
        ),
    ] = None
    meta: Annotated[
        Meta | None,
        Field(description="SEO-style metadata embedded in the rendered page"),
    ] = None
    published_at: Annotated[
        str | None,
        Field(
            description="ISO 8601 publication timestamp; set it to publish a "
            "draft, null keeps it unpublished",
            examples=["2026-09-06T09:00:00+00:00"],
        ),
    ] = None

    model_config = ConfigDict(
        extra="ignore",
        json_schema_extra={"examples": [{"publishedAt": "2026-09-06T09:00:00+00:00"}]},
    )
