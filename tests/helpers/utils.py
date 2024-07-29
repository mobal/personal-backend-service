import uuid

import jwt
import pendulum


async def generate_jwt_token(
    roles: list[str], jwt_secret: str, exp: int = 1
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
                "sub": {"id": str(uuid.uuid4()), "roles": roles},
            },
            jwt_secret,
        ),
        token_id,
    )
