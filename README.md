# PyStats - System Status Monitor

**PyStats** is a comprehensive web-based system monitoring service that provides real-time CPU, memory, and GPU information through an elegant Bootstrap web interface. It features enhanced hardware detection, multiple fallback methods for system monitoring, and runs as a systemd service for continuous operation.

---

## 🧩 Features

- **Web Interface**: Modern Bootstrap 5 UI with responsive design on port 8088
- **Auto-Refresh**: Configurable refresh intervals (5s, 10s, 30s, 60s) with dropdown selector
- **Enhanced System Detection**: 
  - Linux distribution and kernel version detection
  - Advanced psutil detection with multiple fallback methods
  - Comprehensive CPU information with per-core usage
  - Physical and swap memory monitoring with stacked layout
- **GPU Support**: NVIDIA and Intel GPU monitoring with detailed metrics
- **Real-time Data**: JSON API endpoint for system information
- **Robust Monitoring**: Automatic fallback methods when psutil is unavailable
- **Service Integration**: Designed to run as a **systemd service** with auto-restart
- **Easy Installation**: Automated installation script included

---

## 📦 Installation

### Quick Installation (Recommended)

Use the provided installation script for automated setup:

```bash
# Make the script executable
chmod +x install_pystats.sh

# Run the installer (requires sudo)
sudo ./install_pystats.sh
```

The installer will:
- Install Python 3 and pip if needed
- Create a system user `pystats`
- Copy files to `/opt/pystats`
- Install required dependencies (psutil)
- Configure and start the systemd service
- Set up proper permissions and logging

### Manual Installation

If you prefer manual installation:

#### 1. Create installation directory

```bash
sudo mkdir -p /opt/pystats
sudo useradd -r -s /usr/sbin/nologin pystats
sudo chown pystats:pystats /opt/pystats
```

#### 2. Copy project files

Copy the following files into `/opt/pystats`:

```
pystats.py
pystats.service
README.md
install_pystats.sh
```

---

## 🧰 Dependencies

### System Requirements
- Python 3.8 or higher
- Linux-based operating system (Ubuntu, Debian, CentOS, etc.)

### Required Python Packages
- `psutil` (preferred for detailed system monitoring)
- Standard library modules: `json`, `subprocess`, `platform`, `socket`, `time`, `os`, `re`

### Optional Dependencies for Enhanced GPU Monitoring
- `pynvml` (for detailed NVIDIA GPU metrics)
- `nvidia-smi` (fallback for NVIDIA GPU detection)

### Installing Dependencies

For automatic installation, the script will handle dependencies. For manual setup:

```bash
sudo apt update
sudo apt install -y python3 python3-pip

# Install psutil (automatically detects multiple installation paths)
sudo apt install python3-psutil
# OR
pip3 install --user psutil
# OR
sudo pip3 install psutil

# Optional: For enhanced NVIDIA GPU monitoring
pip3 install pynvml
```

**Note**: PyStats includes advanced psutil detection that tries multiple installation paths and methods, providing robust fallback monitoring even when psutil installation issues occur.

---

## ⚙️ Systemd Setup

### 1. Copy the service file

Assuming you already have the file `pystats.service`, copy it into the systemd directory:

```bash
sudo cp /opt/pystats/pystats.service /etc/systemd/system/pystats.service
```

### 2. Review the service file

The included `pystats.service` file contains:

```ini
[Unit]
Description=PyStats System Monitor Web Service
After=network.target
Wants=network-online.target

[Service]
ExecStart=/usr/bin/python3 /opt/pystats/pystats.py
WorkingDirectory=/opt/pystats
Restart=always
RestartSec=5
StandardOutput=append:/var/log/pystats.log
StandardError=append:/var/log/pystats.err
User=pystats
Group=pystats

[Install]
WantedBy=multi-user.target
```

The service runs without authentication tokens and provides web access on port 8088. If `User=pystats` does not exist, create it:

```bash
sudo useradd -r -s /usr/sbin/nologin pystats
sudo chown -R pystats:pystats /opt/pystats
```

---

### 3. Enable and start the service

```bash
sudo systemctl daemon-reload
sudo systemctl enable pystats.service
sudo systemctl start pystats.service
```

---

### 4. Verify operation

Check status:

```bash
sudo systemctl status pystats.service
```

Tail logs:

```bash
sudo journalctl -u pystats.service -f
```

You should see output indicating PyStats has started and is serving on port 8088.

---

## 🌐 Web Interface

Once running, access the PyStats web interface at:
```
http://localhost:8088
```

### Features:
- **System Information**: Hostname, platform, architecture, Linux distribution, kernel version, uptime, and psutil status
- **Memory Information**: Physical RAM and swap memory with usage bars (stacked layout)
- **CPU Information**: Processor details, core count, temperature, frequency, and per-core usage
- **GPU Information**: NVIDIA and Intel GPU monitoring with memory, temperature, and utilization
- **Auto-Refresh**: Configurable refresh intervals (5s, 10s, 30s, 60s) via dropdown
- **Real-time Updates**: Automatic data refresh with manual refresh button
- **Responsive Design**: Bootstrap 5 interface that works on desktop and mobile

### API Endpoint
Raw system data is available in JSON format at:
```
http://localhost:8088/api/system
```

## 🧾 Logs

Logs are stored in:
```
/var/log/pystats.log
/var/log/pystats.err
```

Monitor startup and psutil detection status:
```bash
sudo journalctl -u pystats -f
```

Rotate or clear them periodically if the service runs long-term.

---

## 🔁 Managing the Service

| Command | Description |
|----------|-------------|
| `sudo systemctl start pystats` | Start the service |
| `sudo systemctl stop pystats` | Stop the service |
| `sudo systemctl restart pystats` | Restart the service |
| `sudo systemctl status pystats` | Show service status |
| `sudo journalctl -u pystats -f` | Follow live logs |

---

## 🔧 Configuration

PyStats runs on port 8088 by default and requires no additional configuration. The service automatically:

- Detects and uses psutil if available, with multiple fallback detection methods
- Monitors NVIDIA GPUs via pynvml or nvidia-smi
- Detects Intel integrated graphics
- Provides Linux distribution and kernel information
- Offers configurable refresh intervals via web interface

### Port Configuration
To change the default port (8088), modify the `pystats.py` file:
```python
server_address = ('', 8088)  # Change 8088 to desired port
```

### Advanced psutil Detection
PyStats includes robust psutil detection that tries:
1. Standard Python import
2. Common system package paths
3. Subprocess detection methods
4. Alternative Python executable paths

This ensures monitoring works even with problematic psutil installations.

---

## 📋 System Compatibility

- **Tested Platforms**: Ubuntu 20.04 LTS, Ubuntu 24.04 LTS, Debian, CentOS, Red Hat
- **Python Version**: Requires Python ≥ 3.8
- **GPU Support**: 
  - NVIDIA GPUs via `pynvml` library or `nvidia-smi` command
  - Intel integrated graphics via system detection
- **Fallback Support**: Works without psutil using /proc filesystem
- **Architecture**: Designed for physical servers, VMs, and edge devices
- **No Container Required**: Native Python service, no Docker needed

## 🚀 Quick Start

1. Download or clone the PyStats files
2. Run the installer: `sudo ./install_pystats.sh`
3. Access the web interface: `http://localhost:8088`
4. Configure refresh interval using the dropdown (upper right)

## 🔍 Troubleshooting

### psutil Issues
If psutil installation fails, PyStats will automatically use fallback methods and display warnings in the web interface. The service will continue to work with reduced functionality.

### GPU Detection
- For NVIDIA GPUs: Install `nvidia-drivers` and optionally `python3-pynvml`
- For Intel GPUs: Most modern Linux kernels include necessary drivers

### Service Issues
```bash
# Check service status
sudo systemctl status pystats

# View live logs
sudo journalctl -u pystats -f

# Restart service
sudo systemctl restart pystats
```

---

## 🧹 Uninstall

To completely remove PyStats:

```bash
sudo systemctl stop pystats
sudo systemctl disable pystats
sudo rm /etc/systemd/system/pystats.service
sudo rm -rf /opt/pystats
sudo rm -f /var/log/pystats.log /var/log/pystats.err
sudo userdel pystats
sudo systemctl daemon-reload
```

## 📁 Project Structure

```
pystats/
├── pystats.py           # Main monitoring service
├── pystats.service      # Systemd service configuration
├── install_pystats.sh   # Automated installation script
└── README.md           # This documentation
```

---

**© Protective Resources, Inc. 2025**
