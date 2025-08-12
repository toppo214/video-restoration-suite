#!/usr/bin/env python3
import argparse, subprocess, sys, os

parser = argparse.ArgumentParser()
parser.add_argument("--input", required=True, help="Path to input video")
parser.add_argument("--output", required=True, help="Path to output video")
parser.add_argument("--mode", choices=["preview", "full"], default="preview")
args = parser.parse_args()

if not os.path.exists(args.input):
    print("Input not found:", args.input, file=sys.stderr)
    sys.exit(1)

if args.mode == "preview":
    cmd = [
        "ffmpeg", "-y", "-i", args.input,
        "-t", "10",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        args.output
    ]
else:  # full mode
    cmd = [
        "ffmpeg", "-y", "-i", args.input,
        "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        args.output
    ]

print("Running:", " ".join(cmd))
subprocess.run(cmd, check=True)
print("Done. Output at", args.output)
