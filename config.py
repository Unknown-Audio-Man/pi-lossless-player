#!/usr/bin/env python3
# Configuration settings for the lossless audio player

# Telegram settings
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"  # Get this from @BotFather
AUTHORIZED_USERS = [                            # Telegram user IDs that can control the player
    # Add your Telegram user ID(s) here
]

# Network settings
MUSIC_SERVER_IP = "192.168.0.3"
MUSIC_SERVER_SHARE = "music"  # SMB share name
MUSIC_SERVER_USERNAME = None  # Set to None if no authentication needed
MUSIC_SERVER_PASSWORD = None  # Set to None if no authentication needed
MOUNT_POINT = "/mnt/music"    # Where to mount the remote share

# MPD settings
MPD_HOST = "localhost"
MPD_PORT = 6600
MPD_PASSWORD = None  # Set to None if no password

# Audio settings for IQAudio DAC+
AUDIO_DEVICE = "hw:CARD=sndrpihifiberry,DEV=0"
AUDIO_FORMAT = "44100:16:2"  # Sample rate:bit depth:channels
VOLUME_DEFAULT = 80  # Default volume level (0-100)

# Database settings
DB_PATH = "/home/pi/pi_lossless_player/music_library.db"

# Cache settings
CACHE_ENABLED = True
CACHE_PATH = "/home/pi/pi_lossless_player/cache"
CACHE_MAX_SIZE_GB = 2