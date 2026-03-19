#!/bin/bash
set -e

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (using: sudo ./setup_linux.sh)"
  exit 1
fi

REAL_USER=${SUDO_USER:-$(whoami)}
PROJECT_DIR=$(pwd)
SERVICE_NAME="jumangoclaw"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

echo "🤖 Setting up JumangoClaw systemd daemon..."
echo "👤 User: $REAL_USER"
echo "📂 Directory: $PROJECT_DIR"

echo "📦 Installing Python dependencies globally for systemd service..."
pip3 install -r $PROJECT_DIR/requirements.txt --break-system-packages

echo "🌐 Installing Chromium browser for AI Web Scraping Skill..."
# Run playwright install as the actual user to avoid root-owned browser binaries
su - $REAL_USER -c "playwright install --with-deps chromium"

cat <<EOF > $SERVICE_FILE
[Unit]
Description=JumangoClaw Autonomous Telegram AI Bot
After=network.target

[Service]
Type=simple
User=$REAL_USER
WorkingDirectory=$PROJECT_DIR
ExecStart=/usr/bin/env python3 $PROJECT_DIR/run.py
Restart=always
RestartSec=10
# Preserve environment variables (like PATH for Playwright/Twitter CLI)
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

[Install]
WantedBy=multi-user.target
EOF

echo "🔄 Reloading systemctl..."
systemctl daemon-reload

echo "✅ Enabling $SERVICE_NAME to start on boot..."
systemctl enable $SERVICE_NAME

echo "🚀 Starting $SERVICE_NAME..."
systemctl restart $SERVICE_NAME

echo "=========================================="
echo "🎉 Setup complete!"
echo "📡 The AI Agent is now running continuously in the background."
echo "📜 To view live logs, run: sudo journalctl -u $SERVICE_NAME -f"
echo "=========================================="
