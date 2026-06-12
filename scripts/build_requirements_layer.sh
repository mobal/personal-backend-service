#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$ROOT/dist"

mkdir -p "$DIST"
rm -f "$DIST/requirements.zip"

docker run --rm \
  --platform linux/amd64 \
  --user $(id -u):$(id -g) \
  -e HOME=/tmp \
  -e UV_NO_MODIFY_PATH=1 \
  -v "$ROOT:/workspace:ro" \
  -v "$DIST:/out" \
  -w /tmp \
  public.ecr.aws/sam/build-python3.14 bash -c '
    set -e

    mkdir -p /tmp/project
    cp /workspace/pyproject.toml /workspace/uv.lock /tmp/project/

    cd /tmp/project

    export UV_INSTALL_DIR=/tmp/uv
    curl -Ls https://astral.sh/uv/install.sh | sh
    export PATH=$UV_INSTALL_DIR:$PATH

    uv export --locked --no-dev --format requirements.txt > requirements.txt

    mkdir -p /out/python/lib/python3.14/site-packages
    pip install -r requirements.txt \
      -t /out/python/lib/python3.14/site-packages \
      --platform manylinux2014_x86_64 \
      --python-version 3.14 \
      --no-deps

    cd /out
    zip -r requirements.zip python
    rm -rf /out/python
  '
