#!/usr/bin/env python3
import argparse, subprocess, sys, os

parser = argparse.ArgumentParser()
parser.add_argument("--input", required=True)
parser.add_argument("--output", required=True)
args = parser.parse_args()

# Ensure input exists
if not os.path.exists(args.input):
    print("Input not found:", args.input, file=sys.stderr)
    sys.exit(2)

# Extract first 10 seconds as the preview (placeholder for real pipeline)
cmd = [
    "ffmpeg", "-y", "-i", args.input,
    "-t", "10",
    "-c:v", "libx264", "-preset", "fast", "-crf", "18",
    args.output
]
print("Running preview command:", " ".join(cmd))
subprocess.run(cmd, check=True)
print("Preview saved to", args.output)
