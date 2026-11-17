#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$ROOT/dist"
# The Lambda base image ships the exact interpreter the function runs on.
BUILDER_IMAGE="public.ecr.aws/lambda/python:3.15.2026.11.11.16"
UV_VERSION="0.12.19"

mkdir -p "$DIST"
rm -f "$DIST/requirements.zip"

docker run --rm \
  --platform linux/amd64 \
  --user "$(id -u):$(id -g)" \
  --entrypoint bash \
  -e HOME=/tmp \
  -e UV_VERSION="$UV_VERSION" \
  -e UV_NO_MODIFY_PATH=1 \
  -v "$ROOT:/workspace:ro" \
  -v "$DIST:/out" \
  -w /tmp \
  "$BUILDER_IMAGE" -c '
    set -euo pipefail

    mkdir -p /tmp/project
    cp /workspace/pyproject.toml /workspace/uv.lock /tmp/project/

    cd /tmp/project

    python3.15 -m pip install --prefix=/tmp/uv --no-cache-dir "uv==$UV_VERSION"
    export PATH="/tmp/uv/bin:$PATH"

    uv export --locked --no-dev --no-emit-project --format requirements.txt > requirements.txt

    python3.15 -m pip install -r requirements.txt \
      -t /tmp/layer/python/lib/python3.15/site-packages \
      --platform manylinux2014_x86_64 \
      --python-version 3.15 \
      --no-deps

    python3.15 /workspace/scripts/zip_directory.py \
      /tmp/layer python /out/requirements.zip --exclude-dir tests
  '
