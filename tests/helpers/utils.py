import uuid

import jwt
import pendulum


async def generate_jwt_token(
    jwt_secret: str, user_dict: dict[str, str | None], exp: int = 1
) -> tuple[str, str]:
    iat = pendulum.now()
    exp = iat.add(hours=exp)
    token_id = str(uuid.uuid4())
    return (
        jwt.encode(
            {
                "exp": exp.int_timestamp,
                "iat": iat.int_timestamp,
                "jti": token_id,
                "sub": user_dict["id"],
                "user": user_dict,
            },
            jwt_secret,
        ),
        token_id,
    )
