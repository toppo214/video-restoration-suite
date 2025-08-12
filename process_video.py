#!/usr/bin/env python3
import argparse, subprocess, sys, os

def safe_run(cmd, desc):
    print(f"🔹 Running: {desc}")
    try:
        subprocess.run(cmd, check=True)
        print(f"✅ {desc} completed successfully")
    except Exception as e:
        print(f"⚠️ {desc} failed: {e}")

def ensure_exists(path, kind="file"):
    if not os.path.exists(path):
        print(f"❌ {kind.capitalize()} not found: {path}")
        sys.exit(2)

parser = argparse.ArgumentParser(description="Video processing tool")
parser.add_argument("--input", required=True, help="Path to input video")
parser.add_argument("--output", required=True, help="Path to output video")
parser.add_argument("--mode", required=True, choices=["preview", "restore"], help="Processing mode")
args = parser.parse_args()

ensure_exists(args.input, "input file")
os.makedirs(os.path.dirname(args.output), exist_ok=True)

if args.mode == "preview":
    print("🎬 Generating preview (first 10 seconds)...")
    cmd = [
        "ffmpeg", "-y", "-i", args.input,
        "-t", "10", "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        args.output
    ]
    safe_run(cmd, "FFmpeg preview extraction")

elif args.mode == "restore":
    print("🛠 Starting restoration pipeline...")

    # Step 1: Attempt upscale with Real-ESRGAN
    if os.path.isdir("Real-ESRGAN"):
        safe_run([
            "python3", "Real-ESRGAN/inference_realesrgan.py",
            "-i", args.input, "-o", "tmp_upscaled.mp4"
        ], "Real-ESRGAN upscaling")
        intermediate = "tmp_upscaled.mp4" if os.path.exists("tmp_upscaled.mp4") else args.input
    else:
        print("⚠️ Real-ESRGAN not found, skipping upscale")
        intermediate = args.input

    # Step 2: Attempt frame interpolation with RIFE
    if os.path.isdir("RIFE"):
        safe_run([
            "python3", "RIFE/inference_video.py",
            "--input", intermediate, "--output", args.output
        ], "RIFE frame interpolation")
    else:
        print("⚠️ RIFE not found, skipping interpolation")
        if intermediate != args.output:
            safe_run([
                "ffmpeg", "-y", "-i", intermediate,
                "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                args.output
            ], "FFmpeg copy after upscale")

print(f"🎯 Output saved to {args.output}")
