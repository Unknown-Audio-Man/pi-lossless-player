#!/bin/bash
set -e

echo "Installing Lossless Audio Player for Raspberry Pi 3a+ with IQAudio DAC+"
echo "=================================================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

# Define variables
INSTALL_DIR="/home/pi/pi_lossless_player"
USER="pi"
PROJECT_NAME="pi_lossless_player"

echo "Updating package lists..."
apt-get update

echo "Installing required system packages..."
apt-get install -y mpd python3-pip python3-venv cifs-utils

echo "Configuring MPD for IQAudio DAC+..."
# Backup original MPD config
if [ -f "/etc/mpd.conf" ]; then
  cp /etc/mpd.conf /etc/mpd.conf.backup
fi

# Create new MPD config
cat > /etc/mpd.conf << EOF
music_directory         "/mnt/music"
playlist_directory      "/var/lib/mpd/playlists"
db_file                 "/var/lib/mpd/tag_cache"
log_file                "/var/log/mpd/mpd.log"
pid_file                "/run/mpd/pid"
state_file              "/var/lib/mpd/state"
sticker_file            "/var/lib/mpd/sticker.sql"
user                    "mpd"
bind_to_address         "localhost"
port                    "6600"
auto_update             "yes"
follow_outside_symlinks "yes"
follow_inside_symlinks  "yes"

input {
        plugin "curl"
}

audio_output {
    type            "alsa"
    name            "IQAudio DAC+"
    device          "hw:CARD=sndrpihifiberry,DEV=0"
    auto_resample   "no"
    auto_format     "no"
    auto_channels   "no"
    mixer_type      "software"
    mixer_control   "Digital"
}
EOF

echo "Creating system service for Music Player..."
cat > /etc/systemd/system/pi-lossless-player.service << EOF
[Unit]
Description=Pi Lossless Audio Player
After=network.target mpd.service

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=${INSTALL_DIR}
ExecStart=${INSTALL_DIR}/venv/bin/python3 ${INSTALL_DIR}/main.py
Restart=on-failure
RestartSec=30
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "Creating install directory..."
mkdir -p ${INSTALL_DIR}
mkdir -p ${INSTALL_DIR}/logs
mkdir -p ${INSTALL_DIR}/cache
mkdir -p /mnt/music

echo "Setting up Python virtual environment..."
cd ${INSTALL_DIR}
python3 -m venv venv
source venv/bin/activate

echo "Installing Python dependencies..."
# Create requirements.txt
cat > ${INSTALL_DIR}/requirements.txt << EOF
python-telegram-bot>=13.0
python-mpd2>=3.0.0
tinytag>=1.5.0
EOF

pip install -r requirements.txt

echo "Ensuring correct permissions..."
chown -R ${USER}:${USER} ${INSTALL_DIR}
chown -R ${USER}:${USER} /mnt/music

echo "Enabling and starting services..."
systemctl daemon-reload
systemctl enable mpd
systemctl restart mpd
systemctl enable pi-lossless-player

echo "Installation complete!"
echo ""
echo "IMPORTANT: You need to update the config.py file with your Telegram bot token."
echo "Edit ${INSTALL_DIR}/config.py and set TELEGRAM_BOT_TOKEN to your token from @BotFather."
echo "Then restart the service: sudo systemctl restart pi-lossless-player"