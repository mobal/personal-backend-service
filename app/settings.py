from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    debug: bool = False
    app_name: str
    app_timezone: str
    aws_access_key_id: str
    aws_secret_access_key: str
    jwt_secret: str
    cache_service_base_url: str
    rate_limit_duration_in_seconds: int
    rate_limit_requests: int
    stage: str
