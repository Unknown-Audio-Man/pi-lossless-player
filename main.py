#!/usr/bin/env python3
import asyncio
import signal
import sys
import time
import os
from pathlib import Path
import subprocess
from utils import logger, clean_cache
from network_handler import NetworkHandler
from music_library import MusicLibrary
from audio_player import AudioPlayer
from telegram_bot import TelegramBot
import config

class LosslessAudioPlayer:
    def __init__(self):
        logger.info("Initializing Lossless Audio Player")
        
        # Initialize components
        self.network_handler = NetworkHandler()
        self.music_library = MusicLibrary(self.network_handler)
        self.audio_player = AudioPlayer(self.network_handler)
        self.telegram_bot = TelegramBot(self.music_library, self.audio_player)
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        self.running = True
    
    def setup(self):
        """Setup necessary components and scan library."""
        # Ensure MPD service is running
        self._ensure_mpd_running()
        
        # Ensure the network share is mounted
        if not self.network_handler.ensure_mounted():
            logger.error("Failed to mount network share. Check configuration and network connection.")
            return False
        
        # Scan music library if database doesn't exist or is empty
        if not os.path.exists(config.DB_PATH):
            logger.info("Music library database not found. Performing initial scan...")
            self.music_library.scan_library()
        
        return True
    
    def _ensure_mpd_running(self):
        """Ensure MPD service is running."""
        try:
            # Check if MPD is running
            result = subprocess.run(
                "systemctl is-active --quiet mpd", 
                shell=True, 
                check=False
            )
            
            if result.returncode != 0:
                logger.info("MPD service not running. Starting it...")
                subprocess.run("systemctl start mpd", shell=True, check=True)
                # Give MPD time to start
                time.sleep(3)
        except Exception as e:
            logger.error(f"Error ensuring MPD is running: {e}")
    
    async def run(self):
        """Run the player."""
        if not self.setup():
            logger.error("Setup failed. Exiting.")
            return
        
        # Start the Telegram bot
        await self.telegram_bot.start()
        
        try:
            # Main loop - perform maintenance tasks
            while self.running:
                # Clean cache if enabled
                if config.CACHE_ENABLED:
                    clean_cache(config.CACHE_PATH, config.CACHE_MAX_SIZE_GB)
                
                # Check network connection
                self.network_handler.ensure_mounted()
                
                # Sleep for a while before next check
                await asyncio.sleep(300)  # 5 minutes
        except asyncio.CancelledError:
            logger.info("Main loop cancelled")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up resources...")
        
        # Stop Telegram bot
        self.telegram_bot.stop()
        
        # Disconnect from MPD
        self.audio_player.disconnect()
        
        # Unmount network share
        self.network_handler.unmount_share()
    
    def signal_handler(self, sig, frame):
        """Handle termination signals."""
        logger.info(f"Received signal {sig}. Shutting down...")
        self.running = False
        # Force exit if not exiting cleanly
        sys.exit(0)

if __name__ == "__main__":
    player = LosslessAudioPlayer()
    try:
        asyncio.run(player.run())
    except KeyboardInterrupt:
        logger.info("Program interrupted by user")
    finally:
        logger.info("Lossless Audio Player shutdown complete")