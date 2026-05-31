import os
from functools import cached_property

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
    ssh_root_path: str
    ssh_username: str
    stage: str
    log_event: bool = False
    log_format: str = "json"
    log_level: str = "INFO"

    @computed_field
    @cached_property
    def jwt_secret(self) -> str:
        return parameters.get_parameter(
            os.environ.get("JWT_SECRET_SSM_PARAM_NAME"), decrypt=True
        )

    @computed_field
    @cached_property
    def ssh_secret(self) -> dict:
        return parameters.get_parameter(
            os.environ.get("SSH_SECRET_SSM_PARAM_NAME"), transform="json", decrypt=True
        )

    @computed_field
    @cached_property
    def logging_config(self) -> dict:
        return {
            "log_format": self.log_format,
            "log_level": self.log_level,
            "log_stream": f"{self.app_name}-{self.stage}",
            "sampling_rate": 1.0 if self.debug else 0.1,
        }
