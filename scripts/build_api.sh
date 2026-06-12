#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$ROOT/dist"

rm -f "$DIST/api.zip"
mkdir -p "$DIST"

docker run --rm \
  --platform linux/amd64 \
  --user $(id -u):$(id -g) \
  -v "$ROOT:/workspace:ro" \
  -v "$DIST:/out" \
  -w /workspace \
  public.ecr.aws/sam/build-python3.14 bash -c '
    set -e

    mkdir -p /tmp/api
    cp -r app /tmp/api/app

    cd /tmp/api
    zip -r api.zip app

    mv api.zip /out/api.zip
  '
