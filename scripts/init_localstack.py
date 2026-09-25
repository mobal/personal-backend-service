import os

import boto3

REGION = os.getenv("AWS_DEFAULT_REGION", "eu-central-1")
STAGE = os.getenv("STAGE", "local")
APP_NAME = os.getenv("APP_NAME", "personal-backend-service")
ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")
SSM_PARAM_NAME = os.getenv("JWT_SECRET_SSM_PARAM_NAME", "/dev/secrets/secret")
SSH_PASSWORD_PARAM_NAME = os.getenv(
    "SSH_PASSWORD_SSM_PARAM_NAME", f"/{STAGE}/{APP_NAME}/ssh/password"
)
JWT_SECRET = os.getenv(
    "JWT_SECRET_SSM_PARAM_VALUE",
    "9f4a2c8e1b7d0f3a6e5c9b2a4d7f0e1c3f8a9c7e2b1d0f5a6e4c8b9a2d7f0e1c",
)
ATTACHMENTS_BUCKET = os.getenv("ATTACHMENTS_BUCKET_NAME", "attachments")


def _client(service: str) -> boto3.client:
    return boto3.client(
        service,
        region_name=REGION,
        endpoint_url=ENDPOINT_URL,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
    )


def create_tables() -> None:
    """Create the DynamoDB tables the app expects (mirrors infrastructure/*.tf)."""
    dynamodb = _client("dynamodb")
    table_prefix = f"{STAGE}-{APP_NAME}"
    tables = {
        f"{table_prefix}-posts": {
            "AttributeDefinitions": [
                {"AttributeName": "id", "AttributeType": "S"},
                {"AttributeName": "post_path", "AttributeType": "S"},
                {"AttributeName": "title", "AttributeType": "S"},
                {"AttributeName": "created_at", "AttributeType": "S"},
            ],
            "KeySchema": [{"AttributeName": "id", "KeyType": "HASH"}],
            "GlobalSecondaryIndexes": [
                {
                    "IndexName": "PostPathIndex",
                    "KeySchema": [{"AttributeName": "post_path", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "TitleIndex",
                    "KeySchema": [{"AttributeName": "title", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "CreatedAtIndex",
                    "KeySchema": [{"AttributeName": "created_at", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                },
            ],
        },
    }

    for name, schema in tables.items():
        if name in dynamodb.list_tables().get("TableNames", []):
            print(f"table {name} already exists")
            continue
        dynamodb.create_table(
            TableName=name,
            BillingMode="PAY_PER_REQUEST",
            **schema,
        )
        print(f"created table {name}")


def create_attachments_bucket() -> None:
    s3 = _client("s3")
    buckets = [bucket["Name"] for bucket in s3.list_buckets().get("Buckets", [])]
    if ATTACHMENTS_BUCKET in buckets:
        print(f"bucket {ATTACHMENTS_BUCKET} already exists")
        return
    s3.create_bucket(
        Bucket=ATTACHMENTS_BUCKET,
        CreateBucketConfiguration={"LocationConstraint": REGION},
    )
    print(f"created bucket {ATTACHMENTS_BUCKET}")


def put_ssm_parameters() -> None:
    ssm = _client("ssm")
    ssm.put_parameter(
        Name=SSM_PARAM_NAME,
        Value=JWT_SECRET,
        Type="SecureString",
        Overwrite=True,
    )
    print(f"put parameter {SSM_PARAM_NAME}")
    ssm.put_parameter(
        Name=SSH_PASSWORD_PARAM_NAME,
        Value="local-test-only",
        Type="SecureString",
        Overwrite=True,
    )
    print(f"put parameter {SSH_PASSWORD_PARAM_NAME}")


if __name__ == "__main__":
    create_tables()
    create_attachments_bucket()
    put_ssm_parameters()
    print("localstack seeded")
