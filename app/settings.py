from functools import cached_property

from aws_lambda_powertools.utilities import parameters
from dotenv import load_dotenv
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    debug: bool = False
    app_name: str
    attachments_bucket_name: str
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_region: str = Field(alias="AWS_DEFAULT_REGION")
    jwt_secret_ssm_param_name: str = Field(alias="JWT_SECRET_SSM_PARAM_NAME")
    default_timezone: str
    ssh_host: str
    ssh_password_ssm_parameter_name: str | None = None
    ssh_root_path: str
    ssh_username: str
    stage: str
    log_format: str = "json"
    log_level: str = "INFO"

    @computed_field
    @cached_property
    def jwt_audience(self) -> str:
        return f"https://{self.stage}-{self.app_name}"

    @computed_field
    @cached_property
    def jwt_secret(self) -> str:
        return parameters.get_parameter(self.jwt_secret_ssm_param_name, decrypt=True)

    @property
    def _ssh_password_parameter_name(self) -> str:
        return self.ssh_password_ssm_parameter_name or (
            f"/{self.stage}/{self.app_name}/ssh/password"
        )

    @property
    def ssh_password(self) -> str:
        return parameters.get_parameter(
            self._ssh_password_parameter_name, decrypt=True, max_age=60
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
