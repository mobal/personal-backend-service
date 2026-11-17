from datetime import UTC, datetime
from typing import Annotated, Any, cast

from pydantic import ConfigDict, Field, StringConstraints, field_validator

from app.models.camel_model import CamelModel
from app.models.post import Meta

# Limits for incoming requests only; stored posts are read back unconstrained.
# A post is one DynamoDB item (400 KB at most, with the attachment metadata
# embedded) and the title is an index key (1 KB at most). Counting characters,
# not bytes, the title, content and tag limits stay inside both with room for
# multi-byte text.
MAX_AUTHOR_LENGTH = 100
MAX_TITLE_LENGTH = 200
MAX_CONTENT_LENGTH = 100_000
MAX_TAGS = 30
MAX_TAG_LENGTH = 50
MAX_META_CATEGORY_LENGTH = 100
MAX_META_DESCRIPTION_LENGTH = 500
MAX_META_LANGUAGE_LENGTH = 20


AuthorText = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=3, max_length=MAX_AUTHOR_LENGTH
    ),
]
TitleText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=3, max_length=MAX_TITLE_LENGTH),
]
ContentText = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=3, max_length=MAX_CONTENT_LENGTH
    ),
]
Tag = Annotated[str, StringConstraints(max_length=MAX_TAG_LENGTH)]
Tags = Annotated[list[Tag], Field(min_length=1, max_length=MAX_TAGS)]
OptionalTags = Tags | None


class MetaInput(Meta):
    category: Annotated[
        str,
        Field(
            max_length=MAX_META_CATEGORY_LENGTH,
            description="Section of the blog the post belongs to",
            examples=["tech"],
        ),
    ]
    description: Annotated[
        str,
        Field(
            max_length=MAX_META_DESCRIPTION_LENGTH,
            description="One-paragraph summary of the post, used in listings and feeds",
            examples=["Working notes on the Analytical Engine."],
        ),
    ]
    language: Annotated[
        str,
        Field(
            max_length=MAX_META_LANGUAGE_LENGTH,
            description="Language of the post",
            examples=["en"],
        ),
    ]
    keywords: Annotated[
        Tags,
        Field(
            description="Search keywords describing the post",
            examples=[["engine", "notes"]],
        ),
    ]
    title: Annotated[
        str,
        Field(
            max_length=MAX_TITLE_LENGTH,
            description="SEO title of the page; may differ from the post title",
            examples=["Notes on the Analytical Engine"],
        ),
    ]


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
        AuthorText,
        Field(
            description=f"Author of the post, 3 to {MAX_AUTHOR_LENGTH} characters",
            examples=["Ada Lovelace"],
        ),
    ]
    title: Annotated[
        TitleText,
        Field(
            description=f"Title of the post, 3 to {MAX_TITLE_LENGTH} characters; "
            "must be unique among non-deleted posts",
            examples=["Notes on the Analytical Engine"],
        ),
    ]
    content: Annotated[
        ContentText,
        Field(
            description="Body of the post in Markdown, 3 to "
            f"{MAX_CONTENT_LENGTH} characters",
            examples=["**First draft** of the notes."],
        ),
    ]
    tags: Annotated[
        Tags,
        Field(
            description=f"Free-form tags used for grouping posts; up to {MAX_TAGS} "
            f"tags of up to {MAX_TAG_LENGTH} characters",
            examples=[["notes", "analytical-engine"]],
        ),
    ]
    meta: Annotated[
        MetaInput,
        Field(description="SEO-style metadata embedded in the rendered page"),
    ]
    published_at: Annotated[
        str | None,
        Field(
            description="ISO 8601 publication timestamp; absent or null keeps "
            "the post unpublished and unlisted",
            examples=["2026-09-05T12:00:00+00:00"],
        ),
    ] = None

    @field_validator("published_at")
    @classmethod
    def validate_published_at(cls, value: str | None) -> str | None:
        if value is None:
            return value
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            raise ValueError("publishedAt must include a timezone")
        return parsed.astimezone(UTC).isoformat()

    model_config = ConfigDict(
        extra="ignore",
        json_schema_extra=cast(
            dict[str, Any], {"examples": [CreatePostExample["value"]]}
        ),
    )


class UpdatePost(CamelModel):
    author: Annotated[
        AuthorText | None,
        Field(
            description=f"Author of the post, 3 to {MAX_AUTHOR_LENGTH} characters",
            examples=["Ada Lovelace"],
        ),
    ] = None
    title: Annotated[
        TitleText | None,
        Field(
            description=f"Title of the post, 3 to {MAX_TITLE_LENGTH} characters; "
            "must be unique among non-deleted posts",
            examples=["Notes on the Analytical Engine"],
        ),
    ] = None
    content: Annotated[
        ContentText | None,
        Field(
            description="Body of the post in Markdown, 3 to "
            f"{MAX_CONTENT_LENGTH} characters",
            examples=["**First draft** of the notes."],
        ),
    ] = None
    tags: Annotated[
        OptionalTags,
        Field(
            description=f"Free-form tags used for grouping posts; up to {MAX_TAGS} "
            f"tags of up to {MAX_TAG_LENGTH} characters",
            examples=[["notes", "analytical-engine"]],
        ),
    ] = None
    meta: Annotated[
        MetaInput | None,
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

    @field_validator("author", "title", "content", "tags", "meta", mode="before")
    @classmethod
    def reject_explicit_null(cls, value: Any) -> Any:
        # Only publishedAt may be cleared; a stored null in any other field
        # would make the post unreadable.
        if value is None:
            raise ValueError("must not be null; omit the field to keep its value")
        return value

    @field_validator("published_at")
    @classmethod
    def validate_published_at(cls, value: str | None) -> str | None:
        if value is None:
            return value
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            raise ValueError("publishedAt must include a timezone")
        return parsed.astimezone(UTC).isoformat()

    model_config = ConfigDict(
        extra="ignore",
        json_schema_extra={"examples": [{"publishedAt": "2026-09-06T09:00:00+00:00"}]},
    )
