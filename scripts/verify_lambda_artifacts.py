"""Validate the assembled Lambda ZIPs before they are uploaded or deployed."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

MAX_COMPRESSED_BYTES = 50 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 250 * 1024 * 1024
SITE_PACKAGES = "python/lib/python3.14/site-packages/"
REQUIRED_LAYER_IMPORTS = (
    "aws_lambda_powertools/",
    "boto3/",
    "fastapi/",
    "mangum/",
)
FORBIDDEN_ARTIFACT_PATHS = (
    "boto3_stubs",
    "httpx2_pytest",
    "pytest",
    "ruff",
    "ty",
    "bandit",
    "tests",
    "__pycache__",
)
IMPORT_ENV = {
    "APP_NAME": "artifact-smoke-test",
    "ATTACHMENTS_BUCKET_NAME": "artifact-smoke-test",
    "AWS_ACCESS_KEY_ID": "test",
    "AWS_SECRET_ACCESS_KEY": "test",
    "AWS_DEFAULT_REGION": "eu-central-1",
    "DEBUG": "true",
    "DEFAULT_TIMEZONE": "UTC",
    "JWT_SECRET_SSM_PARAM_NAME": "/artifact-smoke-test/jwt",
    "SSH_HOST": "localhost",
    "SSH_PASSWORD_SSM_PARAM_NAME": "/artifact-smoke-test/ssh/password",
    "SSH_ROOT_PATH": "/",
    "SSH_USERNAME": "artifact-smoke-test",
    "STAGE": "test",
}


def inspect_archive(archive_path: Path) -> tuple[zipfile.ZipFile, list[str], int]:
    if not archive_path.is_file():
        raise ValueError(f"Artifact does not exist: {archive_path}")
    if archive_path.stat().st_size > MAX_COMPRESSED_BYTES:
        raise ValueError(
            f"Artifact exceeds the 50 MiB compressed limit: {archive_path}"
        )

    archive = zipfile.ZipFile(archive_path)
    members = archive.namelist()
    for member in members:
        path = PurePosixPath(member)
        if path.is_absolute() or ".." in path.parts:
            archive.close()
            raise ValueError(f"Unsafe path in artifact {archive_path}: {member}")

    uncompressed_size = sum(info.file_size for info in archive.infolist())
    return archive, members, uncompressed_size


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("Usage: verify_lambda_artifacts.py API_ZIP REQUIREMENTS_ZIP")

    api_zip_path, layer_zip_path = map(Path, sys.argv[1:])
    api_zip, api_members, api_size = inspect_archive(api_zip_path)
    layer_zip, layer_members, layer_size = inspect_archive(layer_zip_path)
    try:
        if api_size + layer_size > MAX_UNCOMPRESSED_BYTES:
            raise ValueError(
                "Combined Lambda artifacts exceed the 250 MiB uncompressed limit"
            )
        if "app/api_handler.py" not in api_members:
            raise ValueError("API artifact is missing app/api_handler.py")

        all_members = api_members + layer_members
        forbidden_members = [
            member
            for member in all_members
            if any(
                path in PurePosixPath(member).parts for path in FORBIDDEN_ARTIFACT_PATHS
            )
            or member.endswith(".pyc")
        ]
        if forbidden_members:
            raise ValueError(
                f"Development files found in Lambda artifacts: {forbidden_members[:5]}"
            )

        missing_imports = [
            import_path
            for import_path in REQUIRED_LAYER_IMPORTS
            if not any(
                member.startswith(SITE_PACKAGES + import_path)
                for member in layer_members
            )
        ]
        if missing_imports:
            raise ValueError(
                f"Dependency layer is missing imports: {', '.join(missing_imports)}"
            )

        with tempfile.TemporaryDirectory(prefix="lambda-artifact-") as temp_dir:
            assembled = Path(temp_dir)
            api_zip.extractall(assembled)
            layer_zip.extractall(assembled)
            env = os.environ | IMPORT_ENV
            env["PYTHONPATH"] = os.pathsep.join(
                (
                    str(assembled),
                    str(assembled / "python/lib/python3.14/site-packages"),
                )
            )
            subprocess.run(
                [sys.executable, "-c", "import app.api_handler"],
                cwd=assembled,
                env=env,
                check=True,
            )
    finally:
        api_zip.close()
        layer_zip.close()

    print("Lambda artifact size and import checks passed")


if __name__ == "__main__":
    main()
