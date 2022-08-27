from pydantic import BaseSettings


class Settings(BaseSettings):
    app_debug: bool = False
    app_name: str
    app_stage: str
    app_timezone: str
    aws_access_key_id: str
    aws_secret_access_key: str
    jwt_secret: str
    cache_service_base_url: str
