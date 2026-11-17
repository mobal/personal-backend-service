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
    aws_region: str = Field(alias="AWS_DEFAULT_REGION")
    blog_description: str = "Published articles"
    blog_title: str = "Personal Backend Service"
    blog_url: str | None = None
    jwt_secret_ssm_param_name: str = Field(alias="JWT_SECRET_SSM_PARAM_NAME")
    ssh_host: str
    ssh_known_hosts: str | None = None
    ssh_password_ssm_param_name: str | None = None
    ssh_root_path: str
    ssh_username: str
    stage: str

    @computed_field
    @cached_property
    def jwt_audience(self) -> str:
        return f"https://{self.stage}-{self.app_name}"

    @cached_property
    def jwt_secret(self) -> str:
        return parameters.get_parameter(self.jwt_secret_ssm_param_name, decrypt=True)

    @property
    def _ssh_password_parameter_name(self) -> str:
        return self.ssh_password_ssm_param_name or (
            f"/{self.stage}/{self.app_name}/ssh/password"
        )

    @property
    def ssh_password(self) -> str:
        return parameters.get_parameter(
            self._ssh_password_parameter_name, decrypt=True, max_age=60
        )
