#!/bin/bash
# build_image.sh – convenience wrapper around docker build for bot images.

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <bot_id> [tag]"
  echo "Example: $0 usdjpy beta-v2"
  exit 1
fi

BOT_ID="$1"
TAG="${2:-latest}"

DOCKERFILE="bots/bot-${BOT_ID}/Dockerfile"
CONTEXT="."  # build from repo root so shared code is available

if [[ ! -f "$DOCKERFILE" ]]; then
  echo "❌ Dockerfile not found for bot '${BOT_ID}'. Expected path: ${DOCKERFILE}"
  exit 1
fi

echo "▶️ Building image bot-${BOT_ID}:${TAG} …"

docker build -f "$DOCKERFILE" -t "bot-${BOT_ID}:${TAG}" "$CONTEXT"

echo "✅ Successfully built bot-${BOT_ID}:${TAG}" 