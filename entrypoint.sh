#!/bin/bash
set -euo pipefail

# Configuration
LOG_DIR="/app/logs"
MODEL_DIR="/app/weights"
TEMP_DIR="/app/temp"

# Initialize directories
mkdir -p "$LOG_DIR" "$MODEL_DIR" "$TEMP_DIR"

# Parse arguments
MODE=${1:-}
INPUT=${2:-}
OUTPUT=${3:-}
shift 3 2>/dev/null || true

# Logging setup
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/execution_$TIMESTAMP.log"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "----- Cloud Upscaler Startup [$(date)] -----"
echo "Mode: $MODE | Input: $INPUT | Output: $OUTPUT"

# GPU Verification
verify_gpu() {
    if ! nvidia-smi &>/dev/null; then
        echo "❌ ERROR: No GPU detected! Ensure you're using --gpus all flag"
        exit 1
    fi
    echo "✅ Verified NVIDIA GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader)"
}

# Dependency Check
check_deps() {
    local missing=()
    for dep in python3 ffmpeg; do
        if ! command -v $dep &>/dev/null; then
            missing+=("$dep")
        fi
    done
    
    if [ ${#missing[@]} -gt 0 ]; then
        echo "❌ Missing dependencies: ${missing[*]}"
        exit 1
    fi
    echo "✅ All dependencies available"
}

# Main Processing Functions
run_preview() {
    local args=("--input" "$INPUT" "--output" "$OUTPUT" "--temp_dir" "$TEMP_DIR")
    [ -n "$*" ] && args+=("$@")
    
    echo "🔍 Starting preview mode with args: ${args[*]}"
    python3 video-restoration-suite/preview.py "${args[@]}"
}

run_restore() {
    verify_gpu
    
    local args=(
        "--input" "$INPUT" 
        "--output" "$OUTPUT" 
        "--model_path" "$MODEL_DIR/RealESRGAN_x4plus.pth"
        "--temp_dir" "$TEMP_DIR"
    )
    [ -n "$*" ] && args+=("$@")
    
    echo "✨ Starting full restoration with args: ${args[*]}"
    python3 video-restoration-suite/restore.py "${args[@]}"
}

# Execution Flow
case "$MODE" in
  preview)
    check_deps
    run_preview "$@"
    ;;
  restore|full)
    check_deps
    run_restore "$@"
    ;;
  shell)
    echo "💻 Entering debug shell..."
    exec /bin/bash "$@"
    ;;
  test)
    echo "🧪 Running system tests..."
    verify_gpu
    check_deps
    python3 -c "import torch; print(f'PyTorch CUDA: {torch.cuda.is_available()}')"
    ;;
  *)
    cat << EOF
❌ Invalid mode specified. Available options:

Usage:
  docker run --rm --gpus all \\
    -v \$(pwd)/input:/app/input \\
    -v \$(pwd)/output:/app/output \\
    <image> MODE INPUT OUTPUT [ARGS...]

Modes:
  preview   - Fast low-res preview
  restore   - Full AI upscaling
  shell     - Debug shell
  test      - System verification

Example:
  docker run ... <image> restore input.mp4 output_4k.mp4 \\
    --scale 4 --tile_size 400
EOF
    exit 1
    ;;
esac

# Cleanup and exit
echo "✅ Completed $MODE mode successfully"
exit 0
