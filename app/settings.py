import os

from aws_lambda_powertools.utilities import parameters
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    debug: bool = False
    app_name: str
    attachments_bucket_name: str
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_region: str = Field(alias="AWS_DEFAULT_REGION")
    default_timezone: str
    rate_limit_duration_in_seconds: int
    rate_limit_requests: int
    rate_limiting: bool
    ssh_host: str
    ssh_password: str
    ssh_username: str
    stage: str

    @computed_field
    @property
    def jwt_secret(self) -> str:
        return parameters.get_parameter(
            os.environ.get("JWT_SECRET_SSM_PARAM_NAME"), decrypt=True
        )
