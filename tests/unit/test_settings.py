import pytest

from app.settings import Settings


class TestSettings:
    def test_ssh_password_parameter_name_is_read_from_environment(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv("SSH_PASSWORD_SSM_PARAM_NAME", "/custom/ssh/password")

        assert Settings()._ssh_password_parameter_name == "/custom/ssh/password"

    def test_ssh_password_parameter_name_defaults_to_stage_and_app_name(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.delenv("SSH_PASSWORD_SSM_PARAM_NAME")
        settings = Settings()

        assert settings._ssh_password_parameter_name == (
            f"/{settings.stage}/{settings.app_name}/ssh/password"
        )

    def test_secrets_are_not_part_of_the_serialized_settings(self, settings: Settings):
        _ = settings.jwt_secret

        serialized = settings.model_dump()

        assert "jwt_secret" not in serialized
        assert "ssh_password" not in serialized
        assert "aws_secret_access_key" not in serialized
        assert settings.jwt_secret not in repr(settings)

    def test_settings_do_not_require_static_aws_credentials(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.delenv("AWS_ACCESS_KEY_ID")
        monkeypatch.delenv("AWS_SECRET_ACCESS_KEY")

        assert Settings().aws_region == "eu-central-1"
