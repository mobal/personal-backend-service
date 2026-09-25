#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$ROOT/dist"
BUILDER_IMAGE="public.ecr.aws/sam/build-python3.14:1.151.0"

rm -f "$DIST/api.zip"
mkdir -p "$DIST"

docker run --rm \
  --platform linux/amd64 \
  --user $(id -u):$(id -g) \
  -v "$ROOT:/workspace:ro" \
  -v "$DIST:/out" \
  -w /workspace \
  "$BUILDER_IMAGE" bash -c '
    set -e

    if [ ! -f /out/requirements.zip ]; then
      echo "Missing dependency layer artifact; run make build-layer first" >&2
      exit 1
    fi

    mkdir -p /tmp/api
    cp -r app /tmp/api/app
    find /tmp/api/app -type d -name __pycache__ -prune -exec rm -rf {} +
    find /tmp/api/app -type f -name "*.pyc" -delete

    cd /tmp/api
    zip -qr api.zip app

    mv api.zip /out/api.zip
    python3.14 /workspace/scripts/verify_lambda_artifacts.py \
      /out/api.zip /out/requirements.zip
  '
