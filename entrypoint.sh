#!/bin/bash
set -euo pipefail

MODE=${1:-}
INPUT=${2:-}
OUTPUT=${3:-}
shift 3 2>/dev/null || true

mkdir -p /app/output

case "$MODE" in
  preview)
    echo "ENTRYPOINT: preview -> input=${INPUT} output=${OUTPUT}"
    python3 video-restoration-suite/preview.py --input "${INPUT}" --output "${OUTPUT}" "$@"
    ;;
  restore|full)
    echo "ENTRYPOINT: full restore -> input=${INPUT} output=${OUTPUT}"
    python3 video-restoration-suite/restore.py --input "${INPUT}" --output "${OUTPUT}" "$@"
    ;;
  shell)
    echo "Dropping to shell for debugging..."
    exec /bin/bash "$@"
    ;;
  *)
    echo "Usage: docker run --rm --gpus all -v \$(pwd)/input:/app/input -v \$(pwd)/output:/app/output <image> preview|restore <input> <output>"
    exit 1
    ;;
esac
