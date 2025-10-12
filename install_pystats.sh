
#!/bin/bash
# ============================================================
# PyStats Installer Script
# install_pystats.sh
# Protective Resources, Inc. — 2025
# ============================================================
# Must be run as root (sudo)
# Installs pystats into /opt/pystats and configures systemd service
# ============================================================

set -e

# Store the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

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

# --- Ensure pip3 is available ---
if ! command -v pip3 >/dev/null 2>&1; then
  echo "Installing pip3..."
  apt update
  apt install -y python3-pip
  # If still not available, try alternative methods
  if ! command -v pip3 >/dev/null 2>&1; then
    echo "Trying alternative pip installation..."
    python3 -m ensurepip --default-pip
  fi
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
echo "Copying files from $SCRIPT_DIR to $INSTALL_DIR..."
cp -f "$SCRIPT_DIR/pystats.py" "$INSTALL_DIR"/
[ -f "$SCRIPT_DIR/requirements.txt" ] && cp -f "$SCRIPT_DIR/requirements.txt" "$INSTALL_DIR"/
[ -f "$SCRIPT_DIR/README.md" ] && cp -f "$SCRIPT_DIR/README.md" "$INSTALL_DIR"/

# --- Install Python dependencies ---
echo "Installing dependencies..."
cd "$INSTALL_DIR"

# For Ubuntu 24.04+ with externally-managed-environment, use apt packages
echo "Installing Python packages via apt (Ubuntu 24.04+ compatibility)..."
apt update
apt install -y python3-psutil python3-flask

# If there's a requirements.txt, try to handle it with apt equivalents
if [ -f requirements.txt ]; then
  echo "Note: requirements.txt found, but using system packages instead."
  echo "If you need specific versions, consider using a virtual environment."
fi

# --- Copy systemd service file ---
if [ -f "$SCRIPT_DIR/pystats.service" ]; then
  echo "Installing systemd service file from $SCRIPT_DIR..."
  cp -f "$SCRIPT_DIR/pystats.service" "$SERVICE_FILE"
else
  echo "❌ pystats.service not found in $SCRIPT_DIR."
  echo "Files in $SCRIPT_DIR:"
  ls -la "$SCRIPT_DIR"
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


