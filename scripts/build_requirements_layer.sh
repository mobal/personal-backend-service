#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$ROOT/dist"
BUILDER_IMAGE="public.ecr.aws/sam/build-python3.14:1.151.0"
UV_VERSION="0.12.19"

mkdir -p "$DIST"
rm -f "$DIST/requirements.zip"

docker run --rm \
  --platform linux/amd64 \
  --user $(id -u):$(id -g) \
  -e HOME=/tmp \
  -e UV_VERSION="$UV_VERSION" \
  -e UV_NO_MODIFY_PATH=1 \
  -v "$ROOT:/workspace:ro" \
  -v "$DIST:/out" \
  -w /tmp \
  "$BUILDER_IMAGE" bash -c '
    set -e

    mkdir -p /tmp/project
    cp /workspace/pyproject.toml /workspace/uv.lock /tmp/project/

    cd /tmp/project

    python3.14 -m pip install --prefix=/tmp/uv --no-cache-dir "uv==$UV_VERSION"
    export PATH="/tmp/uv/bin:$PATH"

    uv export --locked --no-dev --no-emit-project --format requirements.txt > requirements.txt

    mkdir -p /out/python/lib/python3.14/site-packages
    pip install -r requirements.txt \
      -t /out/python/lib/python3.14/site-packages \
      --platform manylinux2014_x86_64 \
      --python-version 3.14 \
      --no-deps

    find /out/python -type d -name __pycache__ -prune -exec rm -rf {} +
    find /out/python -type f -name "*.pyc" -delete
    find /out/python -type d -name tests -prune -exec rm -rf {} +

    cd /out
    zip -qr requirements.zip python
    rm -rf /out/python
  '
