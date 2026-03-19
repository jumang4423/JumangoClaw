#!/bin/bash
set -e

SERVICE_NAME="jumangoclaw"

echo "⬇️ Pulling latest code from git repository..."
git pull

echo "🔄 Restarting JumangoClaw daemon..."
# Sudo is required to restart systemd services
sudo systemctl restart $SERVICE_NAME

echo "=========================================="
echo "✅ Update complete! JumangoClaw has been refreshed."
echo "📜 To view live logs, run: sudo journalctl -u $SERVICE_NAME -f"
echo "=========================================="
