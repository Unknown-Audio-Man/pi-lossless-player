#!/usr/bin/env python3
import mpd
import time
from pathlib import Path
import os
from config import MPD_HOST, MPD_PORT, MPD_PASSWORD, VOLUME_DEFAULT
from utils import logger, format_time

class AudioPlayer:
    def __init__(self, network_handler):
        self.network_handler = network_handler
        self.client = mpd.MPDClient()
        self.client.timeout = 10
        self.client.idletimeout = None
        self.connected = False
        self.connect()
    
    def connect(self):
        """Connect to the MPD server."""
        try:
            self.client.connect(MPD_HOST, MPD_PORT)
            if MPD_PASSWORD:
                self.client.password(MPD_PASSWORD)
            self.connected = True
            self.set_volume(VOLUME_DEFAULT)
            logger.info(f"Connected to MPD server at {MPD_HOST}:{MPD_PORT}")
            return True
        except Exception as e:
            self.connected = False
            logger.error(f"Failed to connect to MPD server: {e}")
            return False
    
    def ensure_connected(self):
        """Ensure connection to MPD server."""
        if not self.connected:
            return self.connect()
        try:
            # Ping to check if connection is still active
            self.client.ping()
            return True
        except Exception:
            return self.connect()
    
    def play_album(self, album):
        """Play an album."""
        if not self.ensure_connected() or not album or not album['tracks']:
            logger.error("Cannot play album: not connected to MPD or album is empty")
            return False
        
        try:
            # Clear current playlist
            self.client.clear()
            
            # Add all tracks to playlist
            for track in album['tracks']:
                # Get the actual file path
                file_path = self.network_handler.get_file_path(track['file_path'])
                if file_path:
                    self.client.add(f"file://{file_path}")
                else:
                    logger.warning(f"Could not find file for track: {track['title']}")
            
            # Start playback
            self.client.play()
            logger.info(f"Started playback of album: {album['title']} by {album['artist']}")
            return True
        except Exception as e:
            logger.error(f"Error playing album: {e}")
            return False
    
    def play(self):
        """Start or resume playback."""
        if not self.ensure_connected():
            return False
        
        try:
            self.client.play()
            return True
        except Exception as e:
            logger.error(f"Error starting playback: {e}")
            return False
    
    def pause(self):
        """Pause playback."""
        if not self.ensure_connected():
            return False
        
        try:
            self.client.pause()
            return True
        except Exception as e:
            logger.error(f"Error pausing playback: {e}")
            return False
    
    def stop(self):
        """Stop playback."""
        if not self.ensure_connected():
            return False
        
        try:
            self.client.stop()
            return True
        except Exception as e:
            logger.error(f"Error stopping playback: {e}")
            return False
    
    def next_track(self):
        """Skip to next track."""
        if not self.ensure_connected():
            return False
        
        try:
            self.client.next()
            return True
        except Exception as e:
            logger.error(f"Error skipping to next track: {e}")
            return False
    
    def previous_track(self):
        """Go to previous track."""
        if not self.ensure_connected():
            return False
        
        try:
            self.client.previous()
            return True
        except Exception as e:
            logger.error(f"Error going to previous track: {e}")
            return False
    
    def set_volume(self, volume):
        """Set volume (0-100)."""
        if not self.ensure_connected():
            return False
        
        try:
            # Ensure volume is within bounds
            volume = max(0, min(100, int(volume)))
            self.client.setvol(volume)
            return True
        except Exception as e:
            logger.error(f"Error setting volume: {e}")
            return False
    
    def get_status(self):
        """Get current playback status."""
        if not self.ensure_connected():
            return None
        
        try:
            status = self.client.status()
            current_song = self.client.currentsong() if status.get('state') != 'stop' else {}
            
            return {
                'state': status.get('state', 'stop'),
                'volume': int(status.get('volume', '0')),
                'elapsed': float(status.get('elapsed', '0')),
                'duration': float(status.get('duration', '0')),
                'title': current_song.get('title', 'Unknown'),
                'artist': current_song.get('artist', 'Unknown'),
                'album': current_song.get('album', 'Unknown')
            }
        except Exception as e:
            logger.error(f"Error getting playback status: {e}")
            return None
    
    def disconnect(self):
        """Disconnect from MPD server."""
        try:
            if self.connected:
                self.client.close()
                self.client.disconnect()
                self.connected = False
                logger.info("Disconnected from MPD server")
        except Exception as e:
            logger.error(f"Error disconnecting from MPD server: {e}")