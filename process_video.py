import argparse
import os
import subprocess

# Default paths
DEFAULT_INPUT = 'assets/sample.mp4'
DEFAULT_PREVIEW_OUTPUT = 'output/preview.mp4'
DEFAULT_RESTORE_OUTPUT = 'output/full_restored.mp4'

# Function to parse command-line arguments
def parse_args():
    parser = argparse.ArgumentParser(description="Video restoration script.")
    parser.add_argument('--input', type=str, default=DEFAULT_INPUT, help="Input video file.")
    parser.add_argument('--preview', type=str, default=DEFAULT_PREVIEW_OUTPUT, help="Preview output.")
    parser.add_argument('--restore', type=str, default=DEFAULT_RESTORE_OUTPUT, help="Restore output.")
    parser.add_argument('--stabilize', action='store_true', help="Enable stabilization.")
    parser.add_argument('--denoise', action='store_true', help="Enable denoising.")
    parser.add_argument('--color', action='store_true', help="Enable color enhancement.")
    parser.add_argument('--upscale', action='store_true', help="Enable upscaling.")
    parser.add_argument('--interpolate', action='store_true', help="Enable interpolation.")
    parser.add_argument('--skip-models', action='store_true', help="Skip heavy model loading.")
    parser.add_argument('--keep-temp', action='store_true', help="Keep temporary files.")
    return parser.parse_args()

# Function for video processing
def process_video(args):
    # Print arguments for confirmation
    print(f"Processing with the following options:")
    print(f"Input file: {args.input}")
    print(f"Preview output: {args.preview}")
    print(f"Restore output: {args.restore}")
    print(f"Stabilize: {args.stabilize}")
    print(f"Denoise: {args.denoise}")
    print(f"Color enhance: {args.color}")
    print(f"Upscale: {args.upscale}")
    print(f"Interpolate: {args.interpolate}")

    # Check if the input video exists
    if not os.path.exists(args.input):
        print(f"❌ Error: Input file {args.input} not found!")
        return

    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(args.preview), exist_ok=True)
    os.makedirs(os.path.dirname(args.restore), exist_ok=True)

    # Preview video processing using ffmpeg
    if args.preview:
        print("⚙️ Generating preview...")
        cmd = f"ffmpeg -i {args.input} -t 10 -c:v libx264 -crf 18 {args.preview}"
        subprocess.run(cmd, shell=True, check=True)

    # Full restoration processing (with stabilization, denoising, etc.)
    if args.restore:
        print("⚙️ Starting full restoration...")
        cmd = f"ffmpeg -i {args.input} -c:v libx264 -crf 18 {args.restore}"
        if args.stabilize:
            cmd += " -filter:v deshake"
        if args.denoise:
            cmd += " -vf hqdn3d"
        if args.color:
            cmd += " -vf eq=brightness=0.05:saturation=1.2"
        if args.upscale:
            cmd += " -vf scale=1920:1080"
        if args.interpolate:
            cmd += " -vf minterpolate=fps=60"
        subprocess.run(cmd, shell=True, check=True)

    print("✅ Processing completed successfully!")

# Main function to execute the processing
def main():
    args = parse_args()
    process_video(args)

if __name__ == "__main__":
    main()

