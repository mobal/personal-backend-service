# personal-backend-service

Personal backend service for a small blog/content application. The API is built with
FastAPI, packaged for AWS Lambda through Mangum, and backed by DynamoDB for posts and
S3 for attachment files.

The service exposes public read endpoints for posts, archives, and attachments, while
post mutations and attachment uploads are protected with HS256 JWT bearer tokens.

## Stack

- Python 3.13+ for local development; deployment artifacts target Python 3.14.
- FastAPI, Pydantic v2, Mangum, Uvicorn.
- AWS Lambda, API Gateway HTTP API, DynamoDB, S3, SSM Parameter Store.
- AWS Lambda Powertools for logging and SSM parameter access.
- `uv` for dependency management.
- `ruff`, `pytest`, `pytest-cov`, `moto`, `pytest-httpx`, `bandit`, and `ty` for quality checks.
- Terraform for AWS infrastructure.
- Docker for Lambda-compatible build artifacts.

## What It Does

- Stores blog posts in a DynamoDB table named `{STAGE}-posts`.
- Generates post paths from the current date and slugified title, for example
  `2026/5/18/example-title`.
- Renders stored Markdown post content to HTML in read responses.
- Supports soft deletion through `deleted_at`.
- Returns only published, non-deleted posts from the list and archive endpoints.
- Uploads base64-encoded attachments to S3 and stores attachment metadata on the post.
- Returns S3 public URLs for attachments.
- Adds an `X-Correlation-ID` response header and uses it in Powertools logging.
- Applies in-memory per-client rate limiting when enabled.
- Blocks clients resolved by `https://api.country.is` to restricted countries currently
  configured as `CN` and `RU`.

## API

All API routes are mounted under `/api/v1`.

### Posts

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| `GET` | `/api/v1/posts` | No | List published, non-deleted posts. Accepts `exclusive_start_key` for DynamoDB pagination. |
| `GET` | `/api/v1/posts/archive` | No | Return monthly post counts as `{ "YYYY-MM": count }`. |
| `GET` | `/api/v1/posts/{uuid}` | No | Return one post by id. |
| `GET` | `/api/v1/posts/{year}/{month}/{day}/{slug}` | No | Return one post by date path and slug. |
| `POST` | `/api/v1/posts` | Yes | Create a post. Returns `201` with a `Location` header. |
| `PUT` | `/api/v1/posts/{uuid}` | Yes | Update mutable post fields. Returns `204`. |
| `DELETE` | `/api/v1/posts/{uuid}` | Yes | Soft-delete a post. Returns `204`. |

### Attachments

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| `GET` | `/api/v1/posts/{post_uuid}/attachments` | No | List attachments for a post. |
| `GET` | `/api/v1/posts/{post_uuid}/attachments/{attachment_uuid}` | No | Return one attachment for a post. |
| `POST` | `/api/v1/posts/{post_uuid}/attachments` | Yes | Upload a base64-encoded attachment. Returns `201` with a `Location` header. |

Authenticated routes accept either:

- `Authorization: Bearer <jwt>`
- `?token=<jwt>`

JWTs are decoded with the secret stored in the SSM parameter named by
`JWT_SECRET_SSM_PARAM_NAME`, using the `HS256` algorithm.

### Request Shapes

Create post:

```json
{
  "author": "Jane Doe",
  "title": "Example post",
  "content": "# Markdown content",
  "tags": ["python", "aws"],
  "publishedAt": "2026-05-18T12:00:00Z",
  "meta": {
    "category": "engineering",
    "description": "Short SEO description",
    "language": "en",
    "keywords": ["fastapi", "lambda"],
    "title": "Example post"
  }
}
```

Upload attachment:

```json
{
  "name": "example.txt",
  "displayName": "Example file",
  "data": "SGVsbG8gd29ybGQ="
}
```

### Adding an Attachment to a Post

Attachments are uploaded to an existing post with:

```text
POST /api/v1/posts/{post_uuid}/attachments
```

The request must be authenticated with a valid JWT. The body contains the original
file name, optional display name, and the file content as a base64-encoded string:

| Field | Required | Description |
| --- | --- | --- |
| `name` | Yes | File name used to infer the MIME type and build the S3 object key. Non-ASCII characters are normalized before storage. |
| `data` | Yes | Base64-encoded file bytes. |
| `displayName` | No | Human-readable name returned by the API. Defaults to `name` when omitted. |

Example:

```sh
POST_UUID="post-id"
JWT_TOKEN="jwt-token"
FILE_PATH="./image.png"
FILE_NAME="$(basename "$FILE_PATH")"
FILE_DATA="$(base64 < "$FILE_PATH" | tr -d '\n')"

curl -i \
  -X POST "http://localhost:8080/api/v1/posts/${POST_UUID}/attachments" \
  -H "Authorization: Bearer ${JWT_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"${FILE_NAME}\",
    \"displayName\": \"${FILE_NAME}\",
    \"data\": \"${FILE_DATA}\"
  }"
```

On success the API returns `201 Created` with a `Location` header pointing to the new
attachment resource:

```text
Location: /api/v1/posts/{post_uuid}/attachments/{attachment_uuid}
```

Internally the service validates that the post exists, decodes `data`, uploads the
file bytes to the configured S3 attachments bucket under the post path, then appends
attachment metadata to the post record in DynamoDB. The attachment can then be fetched
from `GET /api/v1/posts/{post_uuid}/attachments` or
`GET /api/v1/posts/{post_uuid}/attachments/{attachment_uuid}`.

Responses use camelCase field aliases.

## Configuration

The application reads configuration from environment variables via Pydantic settings.

| Variable | Description |
| --- | --- |
| `APP_NAME` | Application name. |
| `ATTACHMENTS_BUCKET_NAME` | S3 bucket used for attachment objects. |
| `AWS_ACCESS_KEY_ID` | AWS access key for local runs/tests. |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key for local runs/tests. |
| `AWS_DEFAULT_REGION` | AWS region, for example `eu-central-1`. |
| `DEBUG` | Enables FastAPI debug mode and package logging. |
| `DEFAULT_TIMEZONE` | Default timezone name. |
| `JWT_SECRET_SSM_PARAM_NAME` | SSM parameter name containing the JWT secret. |
| `LOG_LEVEL` | Powertools/application log level. |
| `RATE_LIMIT_DURATION_IN_SECONDS` | Rate limit window length. |
| `RATE_LIMIT_REQUESTS` | Max requests per client within the window. |
| `RATE_LIMITING` | Enables or disables rate limiting. |
| `SSH_HOST` | SSH host for the SSHFS storage service. |
| `SSH_PASSWORD` | SSH password for the SSHFS storage service. |
| `SSH_ROOT_PATH` | Remote root path for SSHFS storage. |
| `SSH_USERNAME` | SSH username for SSHFS storage. |
| `STAGE` | Environment/stage name; also prefixes DynamoDB resources. |

Tests provide these values through `pyproject.toml` and use Moto to mock AWS services.

## Local Development

Install dependencies:

```sh
make install
```

Run the API locally after exporting the required environment variables:

```sh
uv run uvicorn app.api_handler:app --host 0.0.0.0 --port 8080 --reload
```

FastAPI documentation is available from a running app at:

- `http://localhost:8080/docs`
- `http://localhost:8080/redoc`

Run the Docker image:

```sh
docker build -t personal-backend-service .
docker run --rm -p 8080:8080 --env-file .env personal-backend-service
```

## Quality Checks

Run the default local check set:

```sh
make all
```

Individual commands:

```sh
make format
make lint
make test
make bandit
make ty
make tflint
```

`make lint` runs Ruff with `--fix`, so it may modify files.

## Build Artifacts

Build both Lambda artifacts:

```sh
make build
```

This creates:

- `dist/api.zip` from the `app/` package.
- `dist/requirements.zip` as a Lambda layer containing production dependencies.

The build scripts run inside `public.ecr.aws/sam/build-python3.14` so the packages are
compatible with the Lambda runtime.

Upload artifacts to the account-level artifacts bucket:

```sh
./scripts/upload_requirements_layer.sh
./scripts/upload_api.sh
```

The upload scripts use AWS credentials from environment variables or `~/.aws`, verify
identity with STS, upload to `s3://artifacts-{account_id}/personal-backend-service/`,
and write hash metadata to:

- `dist/requirements.layer.env`
- `dist/api.env`

## Infrastructure

Terraform files live in `infrastructure/`.

Provisioned resources include:

- API Gateway HTTP API with a `$default` Lambda proxy route.
- Lambda function named `{stage}-personal-backend-service-fastapi`.
- Lambda requirements layer.
- DynamoDB posts table named `{stage}-posts`.
- S3 bucket named `{stage}-attachments-{random_suffix}` with public-read ACL.
- IAM role and policy for Lambda access to DynamoDB, SSM, CloudWatch Logs, and ENI APIs.
- SSM parameter `/{stage}/personal-backend-service/api-gateway/url` containing the API URL.

Required Terraform inputs without defaults:

- `artifacts_bucket`
- `jwt_secret_ssm_param_name`
- `lambda_hash`
- `requirements_layer_hash`
- `ssh_host`
- `ssh_password`
- `ssh_root_path`
- `ssh_username`

Typical deployment flow:

```sh
make build
./scripts/upload_requirements_layer.sh
./scripts/upload_api.sh
terraform -chdir=infrastructure init
terraform -chdir=infrastructure plan
terraform -chdir=infrastructure apply
```

Pass `lambda_hash` and `requirements_layer_hash` from the generated files in `dist/`.
The Terraform variable `artifacts_bucket` should match the bucket used by the upload
scripts, usually `artifacts-{account_id}`.

## Repository Layout

```text
app/
  api_handler.py              FastAPI app, Lambda handler, middleware, error handlers
  api/v1/routers/             Posts and attachments routes
  services/                   Post, attachment, S3, SSHFS, and publisher services
  repositories/               DynamoDB access layer
  models/                     Domain and response models
  schemas/                    Request schemas
  middlewares.py              Correlation id, client validation, rate limiting
  jwt_bearer.py               JWT auth dependency
infrastructure/               Terraform AWS infrastructure
scripts/                      Lambda build and upload scripts
tests/                        Unit and integration tests
```

## License

Copyright 2023 - 2026 mobal

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE).
