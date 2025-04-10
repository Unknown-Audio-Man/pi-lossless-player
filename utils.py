#!/usr/bin/env python3
import logging
import os
import time
import shutil
import subprocess
from pathlib import Path

# Set up logging
def setup_logging():
    log_dir = Path("/home/pi/pi_lossless_player/logs")
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / "player.log"),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger("pi_lossless_player")

logger = setup_logging()

def execute_command(command):
    """Execute a shell command and return the output."""
    logger.debug(f"Executing command: {command}")
    try:
        result = subprocess.run(command, shell=True, check=True, 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e.stderr}")
        return None

def format_time(seconds):
    """Format seconds to mm:ss format."""
    minutes, seconds = divmod(int(seconds), 60)
    return f"{minutes:02d}:{seconds:02d}"

def format_album_info(album_info):
    """Format album information for Telegram display."""
    if not album_info:
        return "No album found"
    
    formatted = f"🎵 *{album_info['title']}*\n"
    formatted += f"👤 {album_info['artist']}\n"
    formatted += f"💿 {album_info['year']}\n"
    formatted += f"🎧 {len(album_info['tracks'])} tracks"
    
    return formatted

def clean_cache(cache_path, max_size_gb):
    """Clean cache if it exceeds the maximum size."""
    try:
        cache_size = sum(os.path.getsize(os.path.join(dirpath, filename)) 
                         for dirpath, _, filenames in os.walk(cache_path) 
                         for filename in filenames)
        
        # Convert to GB
        cache_size_gb = cache_size / (1024**3)
        
        if cache_size_gb > max_size_gb:
            logger.info(f"Cache size ({cache_size_gb:.2f} GB) exceeds limit, cleaning...")
            # Sort files by access time and remove oldest until under limit
            files = []
            for dirpath, _, filenames in os.walk(cache_path):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    files.append((file_path, os.path.getatime(file_path)))
            
            # Sort by access time (oldest first)
            files.sort(key=lambda x: x[1])
            
            # Remove files until under limit
            for file_path, _ in files:
                os.remove(file_path)
                new_size = sum(os.path.getsize(os.path.join(dirpath, f)) 
                              for dirpath, _, fs in os.walk(cache_path) 
                              for f in fs) / (1024**3)
                if new_size < max_size_gb * 0.8:  # Keep 20% margin
                    break
                
            logger.info(f"Cache cleaned, new size: {new_size:.2f} GB")
    except Exception as e:
        logger.error(f"Error cleaning cache: {e}")