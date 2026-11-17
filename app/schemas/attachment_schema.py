import base64
from typing import Annotated

from pydantic import ConfigDict, Field, field_validator

from app.models.camel_model import CamelModel

# Lambda accepts at most 6 MB per request. The file travels base64-encoded
# inside the JSON body, which inflates it by a third, so 4 MB is the largest
# size that still reaches the function.
MAX_ATTACHMENT_SIZE_MB = 4
MAX_ATTACHMENT_SIZE = MAX_ATTACHMENT_SIZE_MB * 1024 * 1024
MAX_ENCODED_ATTACHMENT_SIZE = 4 * ((MAX_ATTACHMENT_SIZE + 2) // 3)
ERROR_ATTACHMENT_TOO_LARGE = (
    f"Attachment exceeds maximum size of {MAX_ATTACHMENT_SIZE_MB} MB"
)


class CreateAttachment(CamelModel):
    name: Annotated[
        str,
        Field(
            description="File name, including the extension the MIME type is "
            "guessed from",
            examples=["lorem.txt"],
        ),
    ]
    data: Annotated[
        str,
        Field(
            description="Binary content of the file, base64-encoded "
            f"(up to {MAX_ATTACHMENT_SIZE_MB} MB before encoding)",
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
            raise ValueError(ERROR_ATTACHMENT_TOO_LARGE)
        try:
            decoded = base64.b64decode(value, validate=True)
        except ValueError as exc:
            raise ValueError("Attachment data must be valid base64") from exc
        if not decoded:
            raise ValueError("Attachment must not be empty")
        if len(decoded) > MAX_ATTACHMENT_SIZE:
            raise ValueError(ERROR_ATTACHMENT_TOO_LARGE)
        return value
