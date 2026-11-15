#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$ROOT/dist"
# The Lambda base image ships the exact interpreter the function runs on.
BUILDER_IMAGE="public.ecr.aws/lambda/python:3.15.2026.11.11.16"

rm -f "$DIST/api.zip"
mkdir -p "$DIST"

docker run --rm \
  --platform linux/amd64 \
  --user "$(id -u):$(id -g)" \
  --entrypoint bash \
  -e HOME=/tmp \
  -v "$ROOT:/workspace:ro" \
  -v "$DIST:/out" \
  -w /workspace \
  "$BUILDER_IMAGE" -c '
    set -euo pipefail

    if [ ! -f /out/requirements.zip ]; then
      echo "Missing dependency layer artifact; run make build-layer first" >&2
      exit 1
    fi

    python3.15 /workspace/scripts/zip_directory.py /workspace app /out/api.zip
    python3.15 /workspace/scripts/verify_lambda_artifacts.py \
      /out/api.zip /out/requirements.zip
  '
