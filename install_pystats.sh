#!/bin/bash
# ============================================================
# PyStats Installer Script
# Protective Resources, Inc. — 2025
# ============================================================
# Must be run as root (sudo)
# Installs pystats into /opt/pystats and configures systemd service
# ============================================================

set -e

SERVICE_NAME="pystats"
INSTALL_DIR="/opt/pystats"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
PYTHON_BIN="/usr/bin/python3"
LOG_FILE="/var/log/${SERVICE_NAME}.log"
ERR_FILE="/var/log/${SERVICE_NAME}.err"

echo "--------------------------------------------"
echo " PyStats Installer"
echo "--------------------------------------------"

# --- Root check ---
if [ "$EUID" -ne 0 ]; then
  echo "❌  Please run this script as root (sudo)."
  exit 1
fi

# --- Check Python ---
if ! command -v python3 >/dev/null 2>&1; then
  echo "Installing Python3..."
  apt update
  apt install -y python3 python3-pip
fi

# --- Create system user if not exists ---
if ! id "$SERVICE_NAME" >/dev/null 2>&1; then
  echo "Creating system user '${SERVICE_NAME}'..."
  useradd -r -s /usr/sbin/nologin "$SERVICE_NAME"
fi

# --- Create install directory ---
echo "Creating installation directory at ${INSTALL_DIR}..."
mkdir -p "$INSTALL_DIR"
chown "$SERVICE_NAME":"$SERVICE_NAME" "$INSTALL_DIR"

# --- Copy files from current directory ---
echo "Copying files..."
cp -f pystats.py "$INSTALL_DIR"/
[ -f requirements.txt ] && cp -f requirements.txt "$INSTALL_DIR"/
[ -f README.md ] && cp -f README.md "$INSTALL_DIR"/

# --- Install Python dependencies ---
echo "Installing dependencies..."
cd "$INSTALL_DIR"
if [ -f requirements.txt ]; then
  pip3 install -r requirements.txt
else
  pip3 install psutil flask
fi

# --- Copy systemd service file ---
if [ -f pystats.service ]; then
  echo "Installing systemd service file..."
  cp -f pystats.service "$SERVICE_FILE"
else
  echo "❌ pystats.service not found in current directory."
  exit 1
fi

# --- Adjust permissions ---
chown -R "$SERVICE_NAME":"$SERVICE_NAME" "$INSTALL_DIR"
touch "$LOG_FILE" "$ERR_FILE"
chown "$SERVICE_NAME":"$SERVICE_NAME" "$LOG_FILE" "$ERR_FILE"

# --- Reload systemd and enable service ---
echo "Enabling ${SERVICE_NAME}.service..."
systemctl daemon-reload
systemctl enable "$SERVICE_NAME".service
systemctl restart "$SERVICE_NAME".service

sleep 2
systemctl status "$SERVICE_NAME".service --no-pager

echo "--------------------------------------------"
echo "✅ Installation complete!"
echo "Service file: $SERVICE_FILE"
echo "Logs: $LOG_FILE / $ERR_FILE"
echo "To view logs: sudo journalctl -u ${SERVICE_NAME} -f"
echo "--------------------------------------------"
