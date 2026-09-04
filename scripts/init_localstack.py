import os

import boto3

REGION = os.getenv("AWS_DEFAULT_REGION", "eu-central-1")
STAGE = os.getenv("STAGE", "local")
ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")
SSM_PARAM_NAME = os.getenv("JWT_SECRET_SSM_PARAM_NAME", "/dev/secrets/secret")
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
    tables = {
        f"{STAGE}-posts": {
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
        f"{STAGE}-rate-limits": {
            "AttributeDefinitions": [
                {"AttributeName": "client_id", "AttributeType": "S"},
                {"AttributeName": "endpoint", "AttributeType": "S"},
            ],
            "KeySchema": [
                {"AttributeName": "client_id", "KeyType": "HASH"},
                {"AttributeName": "endpoint", "KeyType": "RANGE"},
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


def enable_rate_limit_ttl() -> None:
    dynamodb = _client("dynamodb")
    table_name = f"{STAGE}-rate-limits"
    dynamodb.update_time_to_live(
        TableName=table_name,
        TimeToLiveSpecification={
            "AttributeName": "ttl",
            "Enabled": True,
        },
    )
    print(f"enabled TTL on {table_name}")


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


if __name__ == "__main__":
    create_tables()
    enable_rate_limit_ttl()
    create_attachments_bucket()
    put_ssm_parameters()
    print("localstack seeded")
