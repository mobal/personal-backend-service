from typing import Any

import pytest
from pydantic import ValidationError

from app.schemas.post_schema import (
    MAX_AUTHOR_LENGTH,
    MAX_CONTENT_LENGTH,
    MAX_META_DESCRIPTION_LENGTH,
    MAX_TAG_LENGTH,
    MAX_TAGS,
    MAX_TITLE_LENGTH,
    CreatePost,
    UpdatePost,
)


@pytest.fixture
def create_payload() -> dict[str, Any]:
    return {
        "author": "Ada Lovelace",
        "title": "Notes on the Analytical Engine",
        "content": "**First draft** of the notes.",
        "tags": ["notes"],
        "meta": {
            "category": "tech",
            "description": "Working notes on the engine.",
            "language": "en",
            "keywords": ["engine"],
            "title": "Notes on the Analytical Engine",
        },
    }


def _with_meta(payload: dict[str, Any], **meta: Any) -> dict[str, Any]:
    return payload | {"meta": payload["meta"] | meta}


def _oversized_cases() -> list[tuple[str, Any]]:
    return [
        ("author", "a" * (MAX_AUTHOR_LENGTH + 1)),
        ("title", "t" * (MAX_TITLE_LENGTH + 1)),
        ("content", "c" * (MAX_CONTENT_LENGTH + 1)),
        ("tags", ["tag"] * (MAX_TAGS + 1)),
        ("tags", ["t" * (MAX_TAG_LENGTH + 1)]),
    ]


def _maximal_cases() -> list[tuple[str, Any]]:
    return [
        ("author", "a" * MAX_AUTHOR_LENGTH),
        ("title", "t" * MAX_TITLE_LENGTH),
        ("content", "c" * MAX_CONTENT_LENGTH),
        ("tags", ["tag"] * MAX_TAGS),
        ("tags", ["t" * MAX_TAG_LENGTH]),
    ]


class TestPostSchemaLimits:
    @pytest.mark.parametrize(("field", "value"), _oversized_cases())
    def test_create_rejects_oversized_field(
        self, create_payload: dict[str, Any], field: str, value: Any
    ):
        with pytest.raises(ValidationError) as error:
            CreatePost(**(create_payload | {field: value}))

        assert error.value.errors()[0]["loc"][0] == field

    @pytest.mark.parametrize(("field", "value"), _maximal_cases())
    def test_create_accepts_field_at_the_limit(
        self, create_payload: dict[str, Any], field: str, value: Any
    ):
        assert getattr(CreatePost(**(create_payload | {field: value})), field)

    @pytest.mark.parametrize(("field", "value"), _oversized_cases())
    def test_update_rejects_oversized_field(self, field: str, value: Any):
        with pytest.raises(ValidationError) as error:
            UpdatePost(**{field: value})

        assert error.value.errors()[0]["loc"][0] == field

    @pytest.mark.parametrize(("field", "value"), _maximal_cases())
    def test_update_accepts_field_at_the_limit(self, field: str, value: Any):
        assert getattr(UpdatePost(**{field: value}), field)

    @pytest.mark.parametrize(
        ("meta_field", "value"),
        [
            ("category", "c" * 101),
            ("description", "d" * (MAX_META_DESCRIPTION_LENGTH + 1)),
            ("language", "l" * 21),
            ("keywords", ["keyword"] * (MAX_TAGS + 1)),
            ("keywords", ["k" * (MAX_TAG_LENGTH + 1)]),
            ("title", "t" * (MAX_TITLE_LENGTH + 1)),
        ],
    )
    def test_meta_rejects_oversized_field(
        self, create_payload: dict[str, Any], meta_field: str, value: Any
    ):
        with pytest.raises(ValidationError) as error:
            CreatePost(**_with_meta(create_payload, **{meta_field: value}))

        assert error.value.errors()[0]["loc"][:2] == ("meta", meta_field)

    def test_stored_posts_are_not_limited_when_they_are_read(self):
        # The limits apply to incoming requests only: a post that is already
        # stored must stay readable even if it exceeds a later limit.
        from app.models.post import Post

        long_text = "x" * (MAX_CONTENT_LENGTH + 1)
        post = Post(
            id="1",
            author="Ada Lovelace",
            title="Notes",
            content=long_text,
            post_path="2026/09/05/notes",
            created_at="2026-09-05T12:00:00+00:00",
            slug="notes",
            tags=["notes"],
            meta={
                "category": "tech",
                "description": "d",
                "language": "en",
                "keywords": ["engine"],
                "title": "Notes",
            },
        )

        assert post.content == long_text
