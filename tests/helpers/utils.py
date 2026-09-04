import uuid
from datetime import UTC, datetime, timedelta

import jwt


def generate_jwt_token(
    jwt_secret: str, user_dict: dict[str, str | None], exp: int = 1
) -> tuple[str, str]:
    iat = datetime.now(UTC)
    exp = iat + timedelta(hours=exp)
    token_id = str(uuid.uuid4())
    return (
        jwt.encode(
            {
                "exp": int(exp.timestamp()),
                "iat": int(iat.timestamp()),
                "jti": token_id,
                "sub": user_dict["id"],
                "user": user_dict,
            },
            jwt_secret,
        ),
        token_id,
    )
