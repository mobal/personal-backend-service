import base64
from typing import Annotated

from pydantic import ConfigDict, Field, field_validator

from app.models.camel_model import CamelModel

MAX_ATTACHMENT_SIZE = 5 * 1024 * 1024
MAX_ENCODED_ATTACHMENT_SIZE = 4 * ((MAX_ATTACHMENT_SIZE + 2) // 3)


class CreateAttachment(CamelModel):
    name: Annotated[
        str,
        Field(
            description="File name, including the extension the MIME type is "
            "guessed from (up to 5 MB)",
            examples=["lorem.txt"],
        ),
    ]
    data: Annotated[
        str,
        Field(
            description="Binary content of the file, base64-encoded",
            examples=["TG9yZW0gaXBzdW0gZG9sb3Igc2l0IGFtZXQu"],
        ),
    ]
    display_name: Annotated[
        str | None,
        Field(
            description="Human-readable name shown in listings; defaults to "
            "`name` when omitted",
            examples=["Lorem ipsum.txt"],
        ),
    ] = None

    model_config = ConfigDict(
        extra="ignore",
        json_schema_extra={
            "examples": [
                {
                    "name": "lorem.txt",
                    "data": "TG9yZW0gaXBzdW0gZG9sb3Igc2l0IGFtZXQu",
                    "displayName": "Lorem ipsum.txt",
                }
            ]
        },
    )

    @field_validator("data")
    @classmethod
    def validate_data(cls, value: str) -> str:
        if len(value) > MAX_ENCODED_ATTACHMENT_SIZE:
            raise ValueError("Attachment exceeds maximum size of 5 MB")
        try:
            decoded = base64.b64decode(value, validate=True)
        except ValueError as exc:
            raise ValueError("Attachment data must be valid base64") from exc
        if not decoded:
            raise ValueError("Attachment must not be empty")
        if len(decoded) > MAX_ATTACHMENT_SIZE:
            raise ValueError("Attachment exceeds maximum size of 5 MB")
        return value
