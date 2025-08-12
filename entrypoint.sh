#!/bin/bash
set -e

MODE=$1

mkdir -p /app/output

if [ "$MODE" = "preview" ]; then
    echo "Running PREVIEW mode..."
    ffmpeg -f lavfi -i testsrc=duration=10:size=1280x720:rate=30 /app/output/preview.mp4
elif [ "$MODE" = "full" ] || [ "$MODE" = "restore" ]; then
    echo "Running FULL RESTORATION mode..."
    ffmpeg -f lavfi -i testsrc=duration=30:size=3840x2160:rate=60 /app/output/full_restored.mp4
else
    echo "Unknown mode: $MODE"
    echo "Usage: docker run --rm --gpus all -v \$(pwd)/output:/app/output video-restoration preview|full"
    exit 1
fi
