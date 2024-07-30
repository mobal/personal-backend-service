import functools

from aws_lambda_powertools import Logger
from fastapi import HTTPException, status

from app.models.auth import User

logger = Logger(utc=True)


def authorize(roles: list[str]):
    def decorator_wrapper(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            user = User(**kwargs["token"].sub)
            if all(role in user.roles for role in roles):
                return await func(*args, **kwargs)
            else:
                logger.warning(f"The {user=} does not have the appropriate {roles=}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authorized"
                )

        return wrapper

    return decorator_wrapper
