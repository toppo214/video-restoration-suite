#!/usr/bin/env python3
import argparse
import subprocess
import sys
import os
import shutil

def run_cmd(cmd, description):
    """Run a command safely, showing warnings instead of crashing."""
    print(f"\n➡️ {description}...")
    try:
        subprocess.run(cmd, check=True)
        print(f"✅ {description} completed.")
    except FileNotFoundError:
        print(f"⚠️ Command not found: {cmd[0]} — skipping {description}")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Error during {description}: {e} — skipping step")

def main():
    parser = argparse.ArgumentParser(description="Crush-proof Video Restoration")
    parser.add_argument("--input", required=True, help="Path to input video")
    parser.add_argument("--output", required=True, help="Path to output video")
    parser.add_argument("--skip-rife", action="store_true", help="Skip RIFE interpolation")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"❌ Input file not found: {args.input}")
        sys.exit(1)

    # Step 1: Upscaling with Real-ESRGAN
    if os.path.exists("Real-ESRGAN"):
        run_cmd([
            "python3", "Real-ESRGAN/inference_realesrgan.py",
            "-n", "RealESRGAN_x4plus",
            "-i", args.input,
            "-o", "temp_upscaled.mp4"
        ], "Upscaling with Real-ESRGAN")
    else:
        print("⚠️ Real-ESRGAN not found — skipping upscaling.")
        shutil.copy(args.input, "temp_upscaled.mp4")

    # Step 2: Frame interpolation with RIFE
    rife_path = shutil.which("python3")
    if not args.skip_rife and os.path.exists("ECCV2022-RIFE"):
        run_cmd([
            "python3", "ECCV2022-RIFE/inference_video.py",
            "--exp", "2",
            "--video", "temp_upscaled.mp4",
            "--output", "temp_interpolated.mp4"
        ], "Frame interpolation with RIFE")
        intermediate_file = "temp_interpolated.mp4"
    else:
        print("⚠️ RIFE missing or skipped — using upscaled video directly.")
        intermediate_file = "temp_upscaled.mp4"

    # Step 3: Encode final output
    run_cmd([
        "ffmpeg", "-y", "-i", intermediate_file,
        "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        args.output
    ], "Encoding final output")

    print(f"\n🎉 Restoration complete! Saved to: {args.output}")

if __name__ == "__main__":
    main()
