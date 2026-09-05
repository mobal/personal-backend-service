from typing import Annotated

from pydantic import ConfigDict, Field

from app.models.camel_model import CamelModel


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
