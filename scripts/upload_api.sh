#!/usr/bin/env sh
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT="$(basename "$ROOT")"

ZIP="/workspace/dist/api.zip"
OUT="/workspace/dist/api.env"
APP="/workspace/app"

docker run --rm \
  --entrypoint sh \
  -e AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY \
  -e AWS_SESSION_TOKEN \
  -e AWS_DEFAULT_REGION \
  -e AWS_PROFILE \
  -v "$HOME/.aws:/root/.aws:ro" \
  -v "$ROOT:/workspace" \
  amazon/aws-cli -c '
    set -e

    echo "🔐 Checking AWS credentials..."
    if ! aws sts get-caller-identity >/dev/null 2>&1; then
      echo ""
      echo "❌ AWS credentials not available inside container."
      echo ""
      echo "👉 Fix one of the following:"
      echo "  - Run: aws sso login"
      echo "  - Or run via: aws-vault exec <profile> -- make upload-api"
      echo "  - Or export AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY"
      echo ""
      exit 1
    fi

    if [ ! -f "'"$ZIP"'" ]; then
      echo "❌ Missing api.zip" >&2
      exit 1
    fi

    if [ ! -d "'"$APP"'" ]; then
      echo "❌ Missing app/ directory" >&2
      exit 1
    fi

    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    BUCKET="artifacts-${ACCOUNT_ID}"

    HASH=$(sha256sum "'"$ZIP"'" | awk "{print \$1}")

    S3_KEY="'"$PROJECT"'/api-${HASH}.zip"

    if aws s3api head-object --bucket "$BUCKET" --key "$S3_KEY" >/dev/null 2>&1; then
      echo "ℹ️ Lambda artifact already exists"
    else
      echo "⬆️ Uploading lambda artifact"
      aws s3 cp "'"$ZIP"'" "s3://$BUCKET/$S3_KEY"
    fi

    cat > "'"$OUT"'" <<EOF
LAMBDA_BUCKET=$BUCKET
LAMBDA_S3_KEY=$S3_KEY
LAMBDA_HASH=$HASH
EOF

    echo "✅ Wrote $OUT"
  '
