#!/usr/bin/env python3
"""
process_video.py — unified preview + full restore pipeline with robust fallbacks.

Capabilities attempted:
 - stabilization (ffmpeg + vidstab)
 - denoising (ffmpeg hqdn3d or nlmeans)
 - deblocking / artifact reduction (ffmpeg hqdn3d + unsharp)
 - color correction (ffmpeg eq)
 - detail enhancement (unsharp)
 - Real-ESRGAN upscaling (if Real-ESRGAN repo / script present)
 - RIFE frame interpolation (if RIFE repo / script present)
 - preview generation (10s) + full restore
 - safe, non-fatal failures: if advanced model steps are missing, fallback to ffmpeg steps.

Usage examples:
  # preview only
  python3 process_video.py --input assets/sample.mp4 --preview output/preview.mp4

  # full restore only (best-effort)
  python3 process_video.py --input assets/sample.mp4 --restore output/full_restored.mp4

  # both:
  python3 process_video.py --input assets/sample.mp4 --preview output/preview.mp4 --restore output/full_restored.mp4

Notes:
 - For REAL GPU-accelerated ESRGAN/RIFE, run this on a GPU instance (Vast.ai) with proper CUDA drivers and model deps installed.
"""
import argparse, subprocess, sys, os, shutil, shlex

def info(msg): print(f"[INFO] {msg}")
def warn(msg): print(f"[WARN] {msg}")
def err(msg): print(f"[ERR] {msg}")

def safe_run(cmd, desc, check=True):
    info(f"{desc} → {shlex.join(cmd[:10])} ...")
    try:
        proc = subprocess.run(cmd, check=check, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        out = proc.stdout or ""
        if len(out) > 0:
            tail = out[-1500:]
            print("--- output tail ---")
            print(tail)
        return proc.returncode == 0
    except FileNotFoundError:
        warn(f"Command not found: {cmd[0]}. Skipping: {desc}")
        return False
    except subprocess.CalledProcessError as e:
        warn(f"{desc} failed (code {e.returncode}). Output (tail):")
        try:
            print(e.stdout[-1500:])
        except Exception:
            pass
        return False

def exists_and_size(path, min_bytes=2000):
    return os.path.exists(path) and os.path.getsize(path) >= min_bytes

def ensure_dir(path):
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)

# ---------- Simple ffmpeg helpers ----------
def ffprobe_ok(path):
    return safe_run(["ffprobe", "-v", "error", "-show_format", "-show_streams", path], f"ffprobe {path}", check=False)

def run_preview(input_path, out_path, length=10):
    ensure_dir(out_path)
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", input_path,
           "-t", str(length), "-c:v", "libx264", "-preset", "fast", "-crf", "18", out_path]
    return safe_run(cmd, "FFmpeg preview")

# ---------- Stabilization (vidstab) ----------
def do_stabilize(infile, outfile):
    # two-pass vidstab approach
    trans = "transforms.trf"
    ok1 = safe_run(["ffmpeg", "-y", "-i", infile, "-vf", "vidstabdetect=shakiness=5:accuracy=15:result=" + trans, "-f", "null", "-"], "vidstab detect (pass 1)", check=False)
    ok2 = safe_run(["ffmpeg", "-y", "-i", infile, "-vf", f"vidstabtransform=input={trans}:smoothing=30:zoom=5", outfile], "vidstab transform (pass 2)", check=False)
    if ok2 and os.path.exists(outfile):
        try:
            os.remove(trans)
        except Exception:
            pass
        return True
    warn("Stabilization failed or not available; skipping")
    return False

# ---------- Denoise / Deblock ----------
def do_denoise(infile, outfile, method="hqdn3d"):
    ensure_dir(outfile)
    if method == "hqdn3d":
        vf = "hqdn3d=3.0:2.0:3.0:2.0"
        return safe_run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", infile, "-vf", vf, "-c:v", "libx264", "-preset", "fast", "-crf", "18", outfile], "FFmpeg denoise (hqdn3d)")
    elif method == "nlmeans":
        # nlmeans may not be available in some ffmpeg builds; attempt and fallback
        vf = "nlmeans"
        return safe_run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", infile, "-vf", vf, "-c:v", "libx264", "-preset", "fast", "-crf", "18", outfile], "FFmpeg denoise (nlmeans)", check=False)
    else:
        warn("Unknown denoise method, skipping")
        return False

# ---------- Color correction & detail enhancement ----------
def do_color_and_sharpen(infile, outfile, eq_params="contrast=1.05:brightness=0.01:saturation=1.08", unsharp_params="unsharp=5:5:0.8:3:3:0.4"):
    ensure_dir(outfile)
    vf = f"eq={eq_params},{unsharp_params}"
    return safe_run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", infile, "-vf", vf, "-c:v", "libx264", "-preset", "slow", "-crf", "18", outfile], "Color correction + sharpen", check=False)

# ---------- Upscale with Real-ESRGAN if available ----------
def try_realesrgan(infile, outfile):
    # search for known script entrypoints
    candidates = [
        "Real-ESRGAN/inference_realesrgan.py",
        "Real-ESRGAN/inference.py",
        "realesrgan/inference_realesrgan.py"
    ]
    for c in candidates:
        if os.path.isfile(c):
            # many forks expect different args; attempt a common one
            ok = safe_run(["python3", c, "-i", infile, "-o", outfile, "-n", "RealESRGAN_x4plus"], f"Real-ESRGAN upscaling via {c}", check=False)
            if ok and os.path.exists(outfile):
                return True
    # try pip-installed tool (best-effort, won't assume API)
    try:
        import importlib
        if importlib.util.find_spec("realesrgan") is not None:
            warn("realesrgan python package detected but no stable CLI used; falling back to ffmpeg upscale")
    except Exception:
        pass
    # fallback: upscale with ffmpeg (not AI but keeps pipeline moving)
    return safe_run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", infile, "-vf", "scale=3840:trunc(ow/a/2)*2", "-c:v", "libx264", "-preset", "fast", "-crf", "18", outfile], "FFmpeg upscale fallback")

# ---------- Interpolation with RIFE ----------
def try_rife_interpolate(infile, outfile, target_fps=60):
    candidates = [
        "ECCV2022-RIFE/inference_video.py",
        "RIFE/inference_video.py",
        "rife/inference_video.py"
    ]
    for c in candidates:
        if os.path.isfile(c):
            # try a few argument variants
            ok1 = safe_run(["python3", c, "--exp", "2", "--video", infile, "--output", outfile], f"RIFE interp (via {c})", check=False)
            if ok1 and os.path.exists(outfile):
                return True
            ok2 = safe_run(["python3", c, "--input", infile, "--output", outfile], f"RIFE interp alt (via {c})", check=False)
            if ok2 and os.path.exists(outfile):
                return True
    warn("No RIFE inference entrypoint found; skipping interpolation")
    return False

# ---------- Final encode ----------
def final_encode(src, dst):
    ensure_dir(dst)
    return safe_run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", src, "-c:v", "libx264", "-preset", "slow", "-crf", "18", dst], "Final encode")

# ---------- Main pipeline ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--preview", help="path to preview (10s)")
    ap.add_argument("--restore", help="path to full restored output")
    ap.add_argument("--stabilize", action="store_true", help="apply stabilization")
    ap.add_argument("--denoise", action="store_true", help="apply denoising (hqdn3d)")
    ap.add_argument("--color", action="store_true", help="apply color correction + sharpen")
    ap.add_argument("--upscale", action="store_true", help="attempt Real-ESRGAN upscaling")
    ap.add_argument("--interpolate", action="store_true", help="attempt RIFE interpolation")
    ap.add_argument("--skip-models", action="store_true", help="skip attempting Real-ESRGAN/RIFE (force ffmpeg-only pipeline)")
    ap.add_argument("--keep-temp", action="store_true")
    args = ap.parse_args()

    if not exists_and_size(args.input, min_bytes=2000):
        err(f"Input missing or too small: {args.input}")
        sys.exit(2)

    # temporary files
    tmp_stab = "tmp_stab.mp4"
    tmp_deno = "tmp_deno.mp4"
    tmp_color = "tmp_color.mp4"
    tmp_up = "tmp_upscaled.mp4"
    tmp_inter = "tmp_interpolated.mp4"
    current = args.input

    # PREVIEW
    if args.preview:
        info("Creating preview...")
        if not run_preview(current, args.preview):
            warn("Preview creation failed; continuing.")

    # FULL RESTORE
    if args.restore:
        info("Starting full restore pipeline (best-effort)")

        # 1) Stabilize
        if args.stabilize:
            info("Attempting stabilization")
            if do_stabilize(current, tmp_stab):
                current = tmp_stab
            else:
                warn("Stabilization failed; continuing with original")

        # 2) Denoise / deblock
        if args.denoise:
            info("Attempting denoise")
            if do_denoise(current, tmp_deno, method="hqdn3d"):
                current = tmp_deno
            else:
                warn("Denoise failed; continuing")

        # 3) Color & sharpen
        if args.color:
            info("Attempting color correction + sharpen")
            if do_color_and_sharpen(current, tmp_color):
                current = tmp_color
            else:
                warn("Color/sharpen failed; continuing")

        # 4) Upscale with Real-ESRGAN (or ffmpeg fallback)
        if args.upscale and (not args.skip_models):
            info("Attempting Real-ESRGAN upscale")
            if try_realesrgan(current, tmp_up):
                current = tmp_up
            else:
                warn("Real-ESRGAN upscale failed; using current intermediate")

        elif args.upscale and args.skip_models:
            warn("--upscale requested but --skip-models set -> skipping model upscale")

        # 5) Interpolate with RIFE
        if args.interpolate and (not args.skip_models):
            info("Attempting RIFE interpolation")
            if try_rife_interpolate(current, tmp_inter):
                current = tmp_inter
            else:
                warn("RIFE interpolation failed or missing; continuing without interp")

        # 6) Final encode
        info("Final encoding to target path")
        if not final_encode(current, args.restore):
            warn("Final encode failed")
        else:
            info(f"Restore complete -> {args.restore}")

    # Cleanup
    if not args.keep_temp:
        for f in [tmp_stab, tmp_deno, tmp_color, tmp_up, tmp_inter]:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except Exception:
                pass

if __name__ == '__main__':
    main()
