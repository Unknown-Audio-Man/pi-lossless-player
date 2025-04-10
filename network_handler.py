#!/usr/bin/env python3
import os
import re
from pathlib import Path
import subprocess
import time
import shutil
from config import (MUSIC_SERVER_IP, MUSIC_SERVER_SHARE, 
                   MUSIC_SERVER_USERNAME, MUSIC_SERVER_PASSWORD,
                   MOUNT_POINT, CACHE_PATH, CACHE_ENABLED)
from utils import logger, execute_command

class NetworkHandler:
    def __init__(self):
        self.mount_point = Path(MOUNT_POINT)
        self.cache_path = Path(CACHE_PATH)
        self.server_ip = MUSIC_SERVER_IP
        self.share = MUSIC_SERVER_SHARE
        self.username = MUSIC_SERVER_USERNAME
        self.password = MUSIC_SERVER_PASSWORD
        
        # Create mount point and cache directory if they don't exist
        os.makedirs(self.mount_point, exist_ok=True)
        if CACHE_ENABLED:
            os.makedirs(self.cache_path, exist_ok=True)
        
        # Try to mount the network share
        self.ensure_mounted()
    
    def ensure_mounted(self):
        """Check if the network share is mounted and mount it if not."""
        if not self.is_mounted():
            return self.mount_share()
        return True
    
    def is_mounted(self):
        """Check if the network share is currently mounted."""
        try:
            result = execute_command("mount | grep -q " + str(self.mount_point))
            # If grep finds the mount point, the command succeeds
            return result is not None
        except Exception as e:
            logger.error(f"Error checking mount status: {e}")
            return False
    
    def mount_share(self):
        """Mount the network share."""
        try:
            # Unmount if there's a stale mount
            self.unmount_share()
            
            # Construct the mount command
            if self.username and self.password:
                creds = f"username={self.username},password={self.password}"
            else:
                creds = "guest"
                
            cmd = (f"mount -t cifs //{self.server_ip}/{self.share} {self.mount_point} "
                   f"-o {creds},vers=3.0,uid=$(id -u pi),gid=$(id -g pi)")
            
            result = execute_command(cmd)
            
            if self.is_mounted():
                logger.info(f"Successfully mounted share from {self.server_ip}")
                return True
            else:
                logger.error(f"Failed to mount share: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Error mounting share: {e}")
            return False
    
    def unmount_share(self):
        """Unmount the network share if it's mounted."""
        try:
            if self.is_mounted():
                result = execute_command(f"umount {self.mount_point}")
                logger.info(f"Unmounted share from {self.server_ip}")
                return True
            return True
        except Exception as e:
            logger.error(f"Error unmounting share: {e}")
            return False
    
    def list_directories(self, path=""):
        """List directories at the given path on the mounted share."""
        if not self.ensure_mounted():
            return []
        
        try:
            full_path = self.mount_point / path if path else self.mount_point
            return [d for d in os.listdir(full_path) 
                   if os.path.isdir(os.path.join(full_path, d))]
        except Exception as e:
            logger.error(f"Error listing directories at {path}: {e}")
            return []
    
    def list_files(self, path="", filter_pattern=None):
        """List files at the given path on the mounted share."""
        if not self.ensure_mounted():
            return []
        
        try:
            full_path = self.mount_point / path if path else self.mount_point
            files = [f for f in os.listdir(full_path) 
                    if os.path.isfile(os.path.join(full_path, f))]
            
            if filter_pattern:
                pattern = re.compile(filter_pattern, re.IGNORECASE)
                files = [f for f in files if pattern.search(f)]
                
            return files
        except Exception as e:
            logger.error(f"Error listing files at {path}: {e}")
            return []
    
    def get_file_path(self, relative_path):
        """Get the full path to a file."""
        if CACHE_ENABLED:
            # Check if file is in cache
            cache_file = self.cache_path / relative_path
            if os.path.exists(cache_file):
                return str(cache_file)
            
            # Ensure the file exists on the network share
            if not self.ensure_mounted():
                return None
            
            network_file = self.mount_point / relative_path
            if not os.path.exists(network_file):
                return None
            
            # Copy to cache
            try:
                os.makedirs(os.path.dirname(cache_file), exist_ok=True)
                shutil.copy2(network_file, cache_file)
                return str(cache_file)
            except Exception as e:
                logger.error(f"Error caching file {relative_path}: {e}")
                # Fall back to network file
                return str(network_file)
        else:
            # No caching, use network file directly
            if not self.ensure_mounted():
                return None
                
            network_file = self.mount_point / relative_path
            return str(network_file) if os.path.exists(network_file) else None