#!/usr/bin/env python3
import argparse
import os
import subprocess
import shutil
import cv2
import torch
import logging
from tqdm import tqdm
from basicsr.archs.rrdbnet_arch import RRDBNet
from realesrgan import RealESRGANer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VideoUpscaler:
    def __init__(self, args):
        self.args = args
        self.temp_dir = os.path.abspath(args.temp_dir)
        self.frame_dir = os.path.join(self.temp_dir, "frames")
        self.enhanced_dir = os.path.join(self.temp_dir, "enhanced")
        self.ensure_paths()
        
    def ensure_paths(self):
        os.makedirs(self.frame_dir, exist_ok=True)
        os.makedirs(self.enhanced_dir, exist_ok=True)
        
    def get_video_fps(self, video_path):
        result = subprocess.run([
            'ffprobe', '-v', 'error',
            '-select_streams', 'v',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            '-show_entries', 'stream=r_frame_rate',
            video_path
        ], stdout=subprocess.PIPE, text=True)
        return float(eval(result.stdout.strip()))
    
    def extract_frames(self):
        logger.info(f"Extracting frames to {self.frame_dir}")
        subprocess.run([
            'ffmpeg', '-hide_banner', '-loglevel', 'error',
            '-i', self.args.input,
            '-qscale:v', '1',
            '-vsync', '0',
            f'{self.frame_dir}/%06d.jpg'
        ], check=True)
        
    def initialize_upscaler(self):
        model = RRDBNet(
            num_in_ch=3, num_out_ch=3,
            num_feat=64, num_block=23,
            num_grow_ch=32, scale=self.args.scale
        )
        return RealESRGANer(
            scale=self.args.scale,
            model_path=self.args.model_path,
            model=model,
            tile=self.args.tile_size,
            tile_pad=10,
            pre_pad=0,
            device='cuda' if torch.cuda.is_available() else 'cpu'
        )
    
    def process_frames(self):
        upscaler = self.initialize_upscaler()
        frame_files = sorted([f for f in os.listdir(self.frame_dir) if f.endswith('.jpg')])
        
        logger.info(f"Processing {len(frame_files)} frames")
        for frame_file in tqdm(frame_files, desc="Upscaling"):
            try:
                frame_path = os.path.join(self.frame_dir, frame_file)
                frame = cv2.imread(frame_path)
                if frame is None:
                    raise ValueError(f"Failed to read {frame_path}")
                
                enhanced, _ = upscaler.enhance(frame, outscale=self.args.scale)
                cv2.imwrite(os.path.join(self.enhanced_dir, frame_file), enhanced)
                
                if not self.args.keep_temp:
                    os.remove(frame_path)
                    
            except Exception as e:
                logger.error(f"Error processing {frame_file}: {str(e)}")
                if self.args.skip_errors:
                    continue
                raise
                
    def reconstruct_video(self):
        fps = self.get_video_fps(self.args.input)
        logger.info(f"Reconstructing video at {fps} FPS")
        
        subprocess.run([
            'ffmpeg', '-hide_banner', '-loglevel', 'error',
            '-framerate', str(fps),
            '-i', f'{self.enhanced_dir}/%06d.jpg',
            '-i', self.args.input,
            '-map', '0:v:0',
            '-map', '1:a:0?',  # Optional audio
            '-c:a', 'copy',
            '-c:v', 'libx264',
            '-crf', '18',
            '-preset', 'slow',
            '-pix_fmt', 'yuv420p',
            '-y',  # Overwrite without asking
            self.args.output
        ], check=True)
        
    def cleanup(self):
        if not self.args.keep_temp:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            
    def run(self):
        try:
            self.extract_frames()
            self.process_frames()
            self.reconstruct_video()
            logger.info(f"Successfully created {self.args.output}")
            return True
        except Exception as e:
            logger.error(f"Processing failed: {str(e)}")
            return False
        finally:
            self.cleanup()

def parse_args():
    parser = argparse.ArgumentParser(description="AI Video Upscaler")
    parser.add_argument('--input', required=True, help="Input video file")
    parser.add_argument('--output', required=True, help="Output video file")
    parser.add_argument('--temp_dir', default='temp', help="Temporary working directory")
    parser.add_argument('--scale', type=int, default=4, choices=[2,4], help="Upscaling factor")
    parser.add_argument('--tile_size', type=int, default=400, help="Tile size for GPU memory management")
    parser.add_argument('--model_path', default='weights/RealESRGAN_x4plus.pth', help="Path to model weights")
    parser.add_argument('--keep_temp', action='store_true', help="Keep temporary files")
    parser.add_argument('--skip_errors', action='store_true', help="Continue on frame processing errors")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    upscaler = VideoUpscaler(args)
    success = upscaler.run()
    exit(0 if success else 1)
