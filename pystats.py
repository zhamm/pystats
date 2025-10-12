#!/usr/bin/env python3
"""
GPU Status Monitor Web Server
A monolithic Python script that displays CPU, RAM, and GPU information
via a web interface on port 8088 using Bootstrap CSS framework.
"""

import json
import subprocess
import threading
import time
import platform
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import socket
import os
import re
import xml.etree.ElementTree as ET

# Try to import psutil with multiple fallback methods
def try_import_psutil():
    """Attempt to import psutil using various methods"""
    import sys
    
    # Method 1: Standard import
    try:
        import psutil
        return psutil, True, "Standard import successful"
    except ImportError:
        pass
    
    # Method 2: Try adding common system paths for psutil
    common_paths = [
        '/usr/lib/python3/dist-packages',
        '/usr/local/lib/python3/dist-packages',
        '/usr/lib/python3.8/site-packages',
        '/usr/lib/python3.9/site-packages',
        '/usr/lib/python3.10/site-packages',
        '/usr/lib/python3.11/site-packages',
        '/usr/lib/python3.12/site-packages',
        '/home/linuxbrew/.linuxbrew/lib/python3.11/site-packages',
        '/opt/homebrew/lib/python3.11/site-packages'
    ]
    
    for path in common_paths:
        if os.path.exists(path) and path not in sys.path:
            sys.path.append(path)
            try:
                import psutil
                return psutil, True, f"Found psutil in {path}"
            except ImportError:
                continue
    
    # Method 3: Try subprocess to find psutil location
    try:
        result = subprocess.run([sys.executable, '-c', 'import psutil; print(psutil.__file__)'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip():
            psutil_path = os.path.dirname(result.stdout.strip())
            if psutil_path not in sys.path:
                sys.path.append(psutil_path)
                import psutil
                return psutil, True, f"Found psutil via subprocess at {psutil_path}"
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, ImportError):
        pass
    
    # Method 4: Try alternative Python executables
    python_executables = ['python3', 'python', '/usr/bin/python3', '/usr/bin/python']
    for python_exec in python_executables:
        try:
            result = subprocess.run([python_exec, '-c', 'import sys; import psutil; sys.path.append(psutil.__path__[0]); print(psutil.__path__[0])'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                psutil_path = result.stdout.strip()
                if psutil_path not in sys.path:
                    sys.path.append(psutil_path)
                    import psutil
                    return psutil, True, f"Found psutil via {python_exec} at {psutil_path}"
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, ImportError, FileNotFoundError):
            continue
    
    return None, False, "psutil not found after trying all methods"

# Attempt to import psutil
psutil, PSUTIL_AVAILABLE, psutil_status = try_import_psutil()
if not PSUTIL_AVAILABLE:
    print(f"Warning: {psutil_status}. Using fallback methods for system monitoring.")
    print("For better performance and more detailed information, try:")
    print("  - sudo apt install python3-psutil python3-pip")
    print("  - pip3 install --user psutil")
    print("  - sudo pip3 install psutil")
else:
    print(f"psutil loaded successfully: {psutil_status}")


class SystemMonitor:
    """Class to handle system monitoring functionality"""
    
    def __init__(self):
        self.gpu_info = {}
        self.last_update = 0
        self.update_interval = 2  # seconds
        self.last_psutil_check = 0
        self.psutil_check_interval = 60  # Check for psutil every 60 seconds
        
    def check_psutil_availability(self):
        """Periodically check if psutil becomes available"""
        global psutil, PSUTIL_AVAILABLE, psutil_status
        
        current_time = time.time()
        if current_time - self.last_psutil_check < self.psutil_check_interval:
            return
            
        self.last_psutil_check = current_time
        
        if not PSUTIL_AVAILABLE:
            # Try to import psutil again
            new_psutil, new_available, new_status = try_import_psutil()
            if new_available:
                psutil = new_psutil
                PSUTIL_AVAILABLE = new_available
                psutil_status = new_status
                print(f"✓ psutil now available: {psutil_status}")
        
    def get_psutil_status(self):
        """Get detailed psutil status information"""
        status_info = {
            'available': PSUTIL_AVAILABLE,
            'status_message': psutil_status,
            'version': None,
            'location': None
        }
        
        if PSUTIL_AVAILABLE:
            try:
                status_info['version'] = psutil.version_info
                status_info['location'] = psutil.__file__
            except Exception as e:
                status_info['error'] = str(e)
                
        return status_info
    
    def get_linux_distribution(self):
        """Get Linux distribution information"""
        try:
            # Try multiple methods to get distribution info
            
            # Method 1: Try /etc/os-release (most modern systems)
            if os.path.exists('/etc/os-release'):
                with open('/etc/os-release', 'r') as f:
                    lines = f.readlines()
                    for line in lines:
                        if line.startswith('PRETTY_NAME='):
                            return line.split('=', 1)[1].strip().strip('"')
                        elif line.startswith('NAME=') and line.find('VERSION=') == -1:
                            name = line.split('=', 1)[1].strip().strip('"')
                            # Try to get version too
                            for version_line in lines:
                                if version_line.startswith('VERSION='):
                                    version = version_line.split('=', 1)[1].strip().strip('"')
                                    return f"{name} {version}"
                            return name
            
            # Method 2: Try /etc/lsb-release
            if os.path.exists('/etc/lsb-release'):
                with open('/etc/lsb-release', 'r') as f:
                    lines = f.readlines()
                    distrib_description = None
                    distrib_id = None
                    distrib_release = None
                    
                    for line in lines:
                        if line.startswith('DISTRIB_DESCRIPTION='):
                            distrib_description = line.split('=', 1)[1].strip().strip('"')
                        elif line.startswith('DISTRIB_ID='):
                            distrib_id = line.split('=', 1)[1].strip().strip('"')
                        elif line.startswith('DISTRIB_RELEASE='):
                            distrib_release = line.split('=', 1)[1].strip().strip('"')
                    
                    if distrib_description:
                        return distrib_description
                    elif distrib_id and distrib_release:
                        return f"{distrib_id} {distrib_release}"
                    elif distrib_id:
                        return distrib_id
            
            # Method 3: Try common distribution-specific files
            dist_files = [
                ('/etc/redhat-release', 'RedHat-based'),
                ('/etc/debian_version', 'Debian'),
                ('/etc/ubuntu-release', 'Ubuntu'),
                ('/etc/fedora-release', 'Fedora'),
                ('/etc/centos-release', 'CentOS'),
                ('/etc/arch-release', 'Arch Linux')
            ]
            
            for file_path, dist_name in dist_files:
                if os.path.exists(file_path):
                    try:
                        with open(file_path, 'r') as f:
                            content = f.read().strip()
                            if content:
                                return content
                            else:
                                return dist_name
                    except:
                        return dist_name
            
            # Method 4: Try uname for basic info
            try:
                result = subprocess.run(['uname', '-o'], capture_output=True, text=True, timeout=5)
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
            except:
                pass
                
        except Exception as e:
            pass
            
        return "Unknown"
    
    def get_kernel_version(self):
        """Get kernel version information"""
        try:
            # Method 1: Use uname -r
            result = subprocess.run(['uname', '-r'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
            
            # Method 2: Try /proc/version
            if os.path.exists('/proc/version'):
                with open('/proc/version', 'r') as f:
                    content = f.read().strip()
                    # Extract kernel version from the string
                    import re
                    match = re.search(r'Linux version (\S+)', content)
                    if match:
                        return match.group(1)
                    
            # Method 3: Use platform.release()
            kernel_version = platform.release()
            if kernel_version:
                return kernel_version
                
        except Exception as e:
            pass
            
        return "Unknown"
        
    def get_cpu_info(self):
        """Get CPU information and statistics"""
        try:
            if PSUTIL_AVAILABLE:
                cpu_info = {
                    'name': platform.processor() or 'Unknown',
                    'cores_physical': psutil.cpu_count(logical=False),
                    'cores_logical': psutil.cpu_count(logical=True),
                    'usage_percent': psutil.cpu_percent(interval=1),
                    'usage_per_core': psutil.cpu_percent(interval=1, percpu=True),
                    'frequency': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
                    'temperature': self.get_cpu_temperature()
                }
            else:
                # Fallback method using /proc filesystem
                cpu_info = self.get_cpu_info_fallback()
            return cpu_info
        except Exception as e:
            return {'error': str(e)}
    
    def get_cpu_info_fallback(self):
        """Fallback CPU info when psutil is not available"""
        cpu_info = {
            'name': platform.processor() or self.get_cpu_name_from_proc(),
            'cores_physical': self.get_cpu_cores_fallback(),
            'cores_logical': self.get_cpu_cores_fallback(logical=True),
            'usage_percent': self.get_cpu_usage_fallback(),
            'usage_per_core': [],
            'frequency': None,
            'temperature': self.get_cpu_temperature_fallback()
        }
        return cpu_info
    
    def get_cpu_name_from_proc(self):
        """Get CPU name from /proc/cpuinfo"""
        try:
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if line.startswith('model name'):
                        return line.split(':', 1)[1].strip()
            return 'Unknown CPU'
        except:
            return 'Unknown CPU'
    
    def get_cpu_cores_fallback(self, logical=False):
        """Get CPU core count from /proc/cpuinfo"""
        try:
            if logical:
                # Count logical processors
                result = subprocess.run(['nproc'], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return int(result.stdout.strip())
            else:
                # Count physical cores
                with open('/proc/cpuinfo', 'r') as f:
                    content = f.read()
                    physical_ids = set()
                    core_ids = set()
                    for line in content.split('\n'):
                        if line.startswith('physical id'):
                            physical_ids.add(line.split(':', 1)[1].strip())
                        elif line.startswith('core id'):
                            core_ids.add(line.split(':', 1)[1].strip())
                    return len(physical_ids) * len(core_ids) if physical_ids and core_ids else 1
            return 1
        except:
            return 1
    
    def get_cpu_usage_fallback(self):
        """Get CPU usage from /proc/stat"""
        try:
            # Read CPU stats twice with a small interval
            def read_cpu_stats():
                with open('/proc/stat', 'r') as f:
                    line = f.readline()
                    values = [int(x) for x in line.split()[1:]]
                    return values
            
            stats1 = read_cpu_stats()
            time.sleep(0.1)
            stats2 = read_cpu_stats()
            
            # Calculate CPU usage
            diff = [stats2[i] - stats1[i] for i in range(len(stats1))]
            idle_time = diff[3]  # idle time
            total_time = sum(diff)
            
            if total_time > 0:
                usage = ((total_time - idle_time) / total_time) * 100
                return round(usage, 1)
            return 0.0
        except:
            return 0.0
    
    def get_cpu_temperature(self):
        """Get CPU temperature if available"""
        if PSUTIL_AVAILABLE:
            try:
                if hasattr(psutil, "sensors_temperatures"):
                    temps = psutil.sensors_temperatures()
                    if temps:
                        # Look for common CPU temperature sensors
                        for name, entries in temps.items():
                            if 'cpu' in name.lower() or 'core' in name.lower() or 'package' in name.lower():
                                if entries:
                                    return entries[0].current
                return None
            except:
                return None
        else:
            return self.get_cpu_temperature_fallback()
    
    def get_cpu_temperature_fallback(self):
        """Get CPU temperature from thermal zone files"""
        try:
            thermal_zones = ['/sys/class/thermal/thermal_zone0/temp',
                           '/sys/class/thermal/thermal_zone1/temp']
            
            for zone_file in thermal_zones:
                if os.path.exists(zone_file):
                    with open(zone_file, 'r') as f:
                        temp_millicelsius = int(f.read().strip())
                        temp_celsius = temp_millicelsius / 1000.0
                        if 20 <= temp_celsius <= 150:  # Reasonable temperature range
                            return temp_celsius
            return None
        except:
            return None
    
    def get_memory_info(self):
        """Get RAM information and statistics"""
        try:
            if PSUTIL_AVAILABLE:
                memory = psutil.virtual_memory()
                swap = psutil.swap_memory()
                
                memory_info = {
                    'total': memory.total,
                    'available': memory.available,
                    'used': memory.used,
                    'free': memory.free,
                    'percent': memory.percent,
                    'swap_total': swap.total,
                    'swap_used': swap.used,
                    'swap_free': swap.free,
                    'swap_percent': swap.percent
                }
            else:
                memory_info = self.get_memory_info_fallback()
            return memory_info
        except Exception as e:
            return {'error': str(e)}
    
    def get_memory_info_fallback(self):
        """Get memory info from /proc/meminfo when psutil is not available"""
        try:
            meminfo = {}
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        # Convert kB to bytes
                        value_kb = int(value.strip().split()[0])
                        meminfo[key.strip()] = value_kb * 1024
            
            total = meminfo.get('MemTotal', 0)
            free = meminfo.get('MemFree', 0)
            available = meminfo.get('MemAvailable', free)
            buffers = meminfo.get('Buffers', 0)
            cached = meminfo.get('Cached', 0)
            used = total - available
            
            swap_total = meminfo.get('SwapTotal', 0)
            swap_free = meminfo.get('SwapFree', 0)
            swap_used = swap_total - swap_free
            
            memory_info = {
                'total': total,
                'available': available,
                'used': used,
                'free': free,
                'percent': (used / total * 100) if total > 0 else 0,
                'swap_total': swap_total,
                'swap_used': swap_used,
                'swap_free': swap_free,
                'swap_percent': (swap_used / swap_total * 100) if swap_total > 0 else 0
            }
            return memory_info
        except Exception as e:
            return {'error': str(e)}
    
    def get_nvidia_info(self):
        """Get NVIDIA GPU information using nvidia-ml-py or nvidia-smi"""
        nvidia_gpus = []
        
        # First check if nvidia-smi works at all
        print("Checking nvidia-smi availability...")
        try:
            result = subprocess.run(['nvidia-smi', '-L'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"nvidia-smi output: {result.stdout}")
                if not result.stdout.strip():
                    print("nvidia-smi returned no output - no GPUs found")
                    return []
            else:
                print(f"nvidia-smi failed with return code {result.returncode}")
                print(f"Error output: {result.stderr}")
                return []
        except FileNotFoundError:
            print("nvidia-smi command not found")
            return []
        except Exception as e:
            print(f"Error running nvidia-smi: {e}")
            return []
        
        # Try nvidia-ml-py first (more detailed info)
        # Note: nvidia-ml-py3 is the more modern alternative to pynvml
        try:
            # Try nvidia-ml-py3 first if available
            try:
                import nvidia_ml_py3 as pynvml
                print("Using nvidia-ml-py3 (modern NVIDIA library)")
            except ImportError:
                # Fall back to legacy pynvml
                import pynvml
                print("Using pynvml (legacy NVIDIA library)")
            
            print("Attempting NVML initialization...")
            pynvml.nvmlInit()
            print("NVML initialization successful")
            device_count = pynvml.nvmlDeviceGetCount()
            print(f"Found {device_count} NVIDIA GPUs via pynvml")
            
            for i in range(device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                
                # Basic info
                name = pynvml.nvmlDeviceGetName(handle).decode('utf-8')
                memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                
                # Temperature
                try:
                    temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                except:
                    temp = None
                
                # Utilization
                try:
                    util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    gpu_util = util.gpu
                    mem_util = util.memory
                except:
                    gpu_util = None
                    mem_util = None
                
                # Power
                try:
                    power = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0  # Convert to watts
                except:
                    power = None
                
                # Fan speed
                try:
                    fan_speed = pynvml.nvmlDeviceGetFanSpeed(handle)
                except:
                    fan_speed = None
                
                # Clock speeds
                try:
                    graphics_clock = pynvml.nvmlDeviceGetClockInfo(handle, pynvml.NVML_CLOCK_GRAPHICS)
                    memory_clock = pynvml.nvmlDeviceGetClockInfo(handle, pynvml.NVML_CLOCK_MEM)
                except:
                    graphics_clock = None
                    memory_clock = None
                
                gpu_info = {
                    'index': i,
                    'name': name,
                    'memory_total': memory_info.total,
                    'memory_used': memory_info.used,
                    'memory_free': memory_info.free,
                    'memory_percent': (memory_info.used / memory_info.total) * 100,
                    'temperature': temp,
                    'gpu_utilization': gpu_util,
                    'memory_utilization': mem_util,
                    'power_usage': power,
                    'fan_speed': fan_speed,
                    'graphics_clock': graphics_clock,
                    'memory_clock': memory_clock,
                    'driver_version': pynvml.nvmlSystemGetDriverVersion().decode('utf-8'),
                    'vendor': 'NVIDIA'
                }
                nvidia_gpus.append(gpu_info)
                
        except ImportError:
            # Fall back to nvidia-smi
            print("pynvml not available, falling back to nvidia-smi")
            nvidia_gpus = self.get_nvidia_smi_info()
        except Exception as e:
            error_msg = str(e)
            if "version mismatch" in error_msg.lower() or "nvml/rm" in error_msg.lower():
                print(f"NVIDIA driver/NVML version mismatch detected: {e}")
                print("This typically happens when:")
                print("  - NVIDIA drivers were updated but system wasn't rebooted")
                print("  - Mixed driver versions are installed")
                print("  - Kernel modules don't match userspace libraries")
                print("Solution: sudo reboot (or reinstall NVIDIA drivers)")
                print("Falling back to nvidia-smi for GPU monitoring...")
                nvidia_gpus = self.get_nvidia_smi_info()
            else:
                print(f"Error getting NVIDIA info via pynvml: {e}")
                print("Note: pynvml is legacy; consider nvidia-smi or nvidia-ml-py3")
                print("Attempting fallback to nvidia-smi...")
                nvidia_gpus = self.get_nvidia_smi_info()
        
        return nvidia_gpus
    
    def get_nvidia_smi_info(self):
        """Get NVIDIA GPU info using nvidia-smi command"""
        nvidia_gpus = []
        print("Attempting to get GPU info via nvidia-smi XML...")
        try:
            # Run nvidia-smi with XML output
            result = subprocess.run(['nvidia-smi', '-q', '-x'], 
                                  capture_output=True, text=True, timeout=10)
            print(f"nvidia-smi XML query return code: {result.returncode}")
            
            if result.returncode == 0:
                print("nvidia-smi XML query successful, parsing...")
                root = ET.fromstring(result.stdout)
                gpu_elements = root.findall('gpu')
                print(f"Found {len(gpu_elements)} GPU elements in XML")
                
                for i, gpu in enumerate(gpu_elements):
                    name = gpu.find('product_name').text if gpu.find('product_name') is not None else 'Unknown'
                    
                    # Memory info
                    fb_memory = gpu.find('fb_memory_usage')
                    memory_total = 0
                    memory_used = 0
                    memory_free = 0
                    
                    if fb_memory is not None:
                        total_elem = fb_memory.find('total')
                        used_elem = fb_memory.find('used')
                        free_elem = fb_memory.find('free')
                        
                        if total_elem is not None:
                            memory_total = int(total_elem.text.split()[0]) * 1024 * 1024  # Convert MB to bytes
                        if used_elem is not None:
                            memory_used = int(used_elem.text.split()[0]) * 1024 * 1024
                        if free_elem is not None:
                            memory_free = int(free_elem.text.split()[0]) * 1024 * 1024
                    
                    # Temperature
                    temp_elem = gpu.find('.//gpu_temp')
                    temperature = int(temp_elem.text.split()[0]) if temp_elem is not None and temp_elem.text != 'N/A' else None
                    
                    # Utilization
                    utilization = gpu.find('utilization')
                    gpu_util = None
                    mem_util = None
                    
                    if utilization is not None:
                        gpu_util_elem = utilization.find('gpu_util')
                        mem_util_elem = utilization.find('memory_util')
                        
                        if gpu_util_elem is not None and gpu_util_elem.text != 'N/A':
                            gpu_util = int(gpu_util_elem.text.split()[0])
                        if mem_util_elem is not None and mem_util_elem.text != 'N/A':
                            mem_util = int(mem_util_elem.text.split()[0])
                    
                    # Power
                    power_elem = gpu.find('.//power_draw')
                    power = float(power_elem.text.split()[0]) if power_elem is not None and power_elem.text != 'N/A' else None
                    
                    # Fan speed
                    fan_elem = gpu.find('.//fan_speed')
                    fan_speed = int(fan_elem.text.split()[0]) if fan_elem is not None and fan_elem.text != 'N/A' else None
                    
                    gpu_info = {
                        'index': i,
                        'name': name,
                        'memory_total': memory_total,
                        'memory_used': memory_used,
                        'memory_free': memory_free,
                        'memory_percent': (memory_used / memory_total * 100) if memory_total > 0 else 0,
                        'temperature': temperature,
                        'gpu_utilization': gpu_util,
                        'memory_utilization': mem_util,
                        'power_usage': power,
                        'fan_speed': fan_speed,
                        'vendor': 'NVIDIA'
                    }
                    nvidia_gpus.append(gpu_info)
                    print(f"Added GPU {i}: {gpu_info['name']}")
            else:
                print(f"nvidia-smi XML query failed with return code {result.returncode}")
                print(f"Error output: {result.stderr}")
                    
        except subprocess.TimeoutExpired:
            print("nvidia-smi command timed out")
        except FileNotFoundError:
            print("nvidia-smi command not found - NVIDIA drivers may not be installed")
        except Exception as e:
            print(f"Error running nvidia-smi: {e}")
        
        if not nvidia_gpus:
            print("No NVIDIA GPUs detected via nvidia-smi")
        else:
            print(f"Successfully detected {len(nvidia_gpus)} NVIDIA GPUs via nvidia-smi")
        
        return nvidia_gpus
    
    def get_intel_gpu_info(self):
        """Get Intel GPU information"""
        intel_gpus = []
        
        # Try to get Intel GPU info from various sources
        try:
            # Check for Intel GPU using lspci
            result = subprocess.run(['lspci', '-v'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                gpu_section = False
                current_gpu = {}
                
                for line in lines:
                    if 'VGA compatible controller' in line and 'Intel' in line:
                        gpu_section = True
                        # Extract GPU name
                        name_match = re.search(r'Intel.*?(\[.*?\])', line)
                        if name_match:
                            current_gpu['name'] = name_match.group(0)
                        else:
                            current_gpu['name'] = 'Intel GPU'
                        current_gpu['vendor'] = 'Intel'
                        current_gpu['index'] = len(intel_gpus)
                        
                    elif gpu_section and line.strip() == '':
                        # End of GPU section
                        if current_gpu:
                            intel_gpus.append(current_gpu)
                            current_gpu = {}
                        gpu_section = False
            
            # Try to get more detailed info from /sys filesystem
            if os.path.exists('/sys/class/drm'):
                for card_dir in os.listdir('/sys/class/drm'):
                    if card_dir.startswith('card') and not card_dir.endswith('-'):
                        card_path = f'/sys/class/drm/{card_dir}'
                        
                        # Check if it's Intel
                        vendor_path = os.path.join(card_path, 'device/vendor')
                        if os.path.exists(vendor_path):
                            with open(vendor_path, 'r') as f:
                                vendor_id = f.read().strip()
                                if vendor_id == '0x8086':  # Intel vendor ID
                                    gpu_info = {
                                        'index': len(intel_gpus),
                                        'name': 'Intel Integrated Graphics',
                                        'vendor': 'Intel',
                                        'card': card_dir
                                    }
                                    
                                    # Try to get memory info if available
                                    try:
                                        # Intel GPUs typically share system memory
                                        gpu_info['memory_type'] = 'Shared System Memory'
                                    except:
                                        pass
                                    
                                    intel_gpus.append(gpu_info)
                                    
        except Exception as e:
            print(f"Error getting Intel GPU info: {e}")
        
        return intel_gpus
    
    def get_gpu_status(self):
        """Get GPU detection status information with timeout protection"""
        status = {
            'nvidia_pynvml_available': False,
            'nvidia_smi_available': False,
            'nvidia_gpus_detected': 0,
            'intel_gpus_detected': 0,
            'gpu_errors': []
        }
        
        # Skip GPU status check if it's taking too long or causing issues
        # This is a quick status check, not the main GPU detection
        try:
            # Quick check for nvidia-smi availability first (faster and more reliable)
            try:
                result = subprocess.run(['nvidia-smi', '-L'], capture_output=True, text=True, timeout=3)
                if result.returncode == 0:
                    status['nvidia_smi_available'] = True
                    # Count GPUs from nvidia-smi output
                    gpu_lines = [line for line in result.stdout.split('\n') if line.startswith('GPU ')]
                    status['nvidia_gpus_detected'] = len(gpu_lines)
            except FileNotFoundError:
                status['gpu_errors'].append("nvidia-smi not found")
            except subprocess.TimeoutExpired:
                status['gpu_errors'].append("nvidia-smi timeout")
            except Exception as e:
                status['gpu_errors'].append(f"nvidia-smi error: {e}")
            
            # Only check NVIDIA ML libraries if nvidia-smi found GPUs
            if status['nvidia_smi_available']:
                nvidia_lib_name = "unknown"
                try:
                    # Try modern library first
                    try:
                        import nvidia_ml_py3 as pynvml
                        nvidia_lib_name = "nvidia-ml-py3 (modern)"
                    except ImportError:
                        # Fall back to legacy library
                        import pynvml
                        nvidia_lib_name = "pynvml (legacy)"
                    
                    # Quick init test - if this hangs, skip it for status
                    try:
                        pynvml.nvmlInit()
                        status['nvidia_pynvml_available'] = True
                        status['nvidia_library'] = nvidia_lib_name
                    except Exception as init_e:
                        if "version mismatch" in str(init_e).lower():
                            status['gpu_errors'].append("NVIDIA driver/NVML version mismatch")
                        else:
                            status['gpu_errors'].append(f"NVIDIA ML library init error: {init_e}")
                        
                except ImportError:
                    status['gpu_errors'].append("No NVIDIA ML library available")
                except Exception as e:
                    status['gpu_errors'].append(f"NVIDIA ML library error: {e}")
            
        except Exception as e:
            status['gpu_errors'].append(f"GPU status check failed: {e}")
        
        return status
    
    def get_gpu_status_safe(self):
        """Get GPU detection status information safely without hanging"""
        status = {
            'nvidia_pynvml_available': False,
            'nvidia_smi_available': False,
            'nvidia_gpus_detected': 0,
            'intel_gpus_detected': 0,
            'gpu_errors': []
        }
        
        # Only check nvidia-smi availability (safe and fast)
        try:
            result = subprocess.run(['nvidia-smi', '-L'], capture_output=True, text=True, timeout=3)
            if result.returncode == 0:
                status['nvidia_smi_available'] = True
                # Count GPUs from nvidia-smi output
                gpu_lines = [line for line in result.stdout.split('\n') if line.startswith('GPU ')]
                status['nvidia_gpus_detected'] = len(gpu_lines)
                
                # Note about pynvml availability without trying to init it
                try:
                    import nvidia_ml_py3
                    status['gpu_errors'].append("nvidia-ml-py3 available but not used due to version mismatch issues")
                except ImportError:
                    try:
                        import pynvml
                        status['gpu_errors'].append("pynvml available but not used due to version mismatch issues")
                    except ImportError:
                        status['gpu_errors'].append("No NVIDIA ML library available")
                        
        except FileNotFoundError:
            status['gpu_errors'].append("nvidia-smi not found")
        except subprocess.TimeoutExpired:
            status['gpu_errors'].append("nvidia-smi timeout")
        except Exception as e:
            status['gpu_errors'].append(f"nvidia-smi error: {e}")
        
        return status
    
    def get_all_gpu_info(self):
        """Get information for all GPUs (NVIDIA and Intel)"""
        all_gpus = []
        
        # Get NVIDIA GPUs
        nvidia_gpus = self.get_nvidia_info()
        all_gpus.extend(nvidia_gpus)
        
        # Get Intel GPUs
        intel_gpus = self.get_intel_gpu_info()
        all_gpus.extend(intel_gpus)
        
        return all_gpus
    
    def get_system_info(self):
        """Get comprehensive system information"""
        current_time = time.time()
        # Check if psutil becomes available
        self.check_psutil_availability()
        
        # Update GPU info less frequently to avoid performance issues
        if current_time - self.last_update > self.update_interval:
            self.gpu_info = self.get_all_gpu_info()
            self.last_update = current_time
        
        cpu_info = self.get_cpu_info()
        memory_info = self.get_memory_info()
        
        system_info = {
            'timestamp': current_time,
            'cpu': cpu_info,
            'memory': memory_info,
            'gpus': self.gpu_info,
            'system': {
                'platform': platform.system(),
                'platform_version': platform.version(),
                'architecture': platform.architecture()[0],
                'hostname': socket.gethostname(),
                'uptime': self.get_uptime(),
                'linux_distribution': self.get_linux_distribution(),
                'kernel_version': self.get_kernel_version(),
                'psutil_available': PSUTIL_AVAILABLE,
                'psutil_status': self.get_psutil_status(),
                'gpu_status': self.get_gpu_status_safe()
            }
        }

        
        return system_info
    
    def get_uptime(self):
        """Get system uptime"""
        if PSUTIL_AVAILABLE:
            try:
                return time.time() - psutil.boot_time()
            except:
                pass
        
        # Fallback method
        try:
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.read().split()[0])
                return uptime_seconds
        except:
            return 0


class WebHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the web server"""
    
    def __init__(self, *args, monitor=None, **kwargs):
        self.monitor = monitor
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/':
            self.serve_main_page()
        elif parsed_path.path == '/api/system':
            self.serve_system_data()
        elif parsed_path.path == '/favicon.ico':
            self.send_response(404)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()
    
    def serve_main_page(self):
        """Serve the main HTML page"""
        html_content = self.get_html_template()
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.send_header('Content-length', len(html_content))
        self.end_headers()
        self.wfile.write(html_content.encode())
    
    def serve_system_data(self):
        """Serve system data as JSON"""
        try:
            system_info = self.monitor.get_system_info()
            json_data = json.dumps(system_info, indent=2)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Content-length', len(json_data))
            self.end_headers()
            self.wfile.write(json_data.encode())
        except Exception as e:
            error_response = json.dumps({'error': str(e)})
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Content-length', len(error_response))
            self.end_headers()
            self.wfile.write(error_response.encode())
    
    def get_html_template(self):
        """Generate the HTML template with Bootstrap styling"""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GPU Status Monitor</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        .card-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .progress {
            height: 25px;
        }
        .progress-bar {
            font-weight: bold;
            line-height: 25px;
        }
        .gpu-card {
            border-left: 4px solid #28a745;
        }
        .nvidia-card {
            border-left-color: #76b900;
        }
        .intel-card {
            border-left-color: #0071c5;
        }
        .stat-icon {
            font-size: 1.2em;
            margin-right: 8px;
        }
        .refresh-controls {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 1000;
        }
        .refresh-controls .form-select {
            width: auto;
            min-width: 70px;
        }
        .refresh-btn {
            border-top-left-radius: 0;
            border-bottom-left-radius: 0;
        }
        .temperature {
            color: #dc3545;
        }
        .temperature.normal {
            color: #28a745;
        }
        .temperature.warning {
            color: #ffc107;
        }
        .temperature.danger {
            color: #dc3545;
        }
    </style>
</head>
<body class="bg-light">
    <div class="container-fluid py-4">
        <div class="row mb-4">
            <div class="col">
                <h1 class="text-center"><i class="bi bi-cpu"></i> System Status Monitor</h1>
                <p class="text-center text-muted">Real-time CPU, RAM, and GPU monitoring</p>
            </div>
        </div>
        
        <!-- System Info and Memory Info -->
        <div class="row mb-4">
            <div class="col-md-6">
                <div class="card h-100">
                    <div class="card-header">
                        <h5 class="mb-0"><i class="bi bi-info-circle stat-icon"></i>System Information</h5>
                    </div>
                    <div class="card-body" id="system-info">
                        <div class="text-center">
                            <div class="spinner-border" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card h-100">
                    <div class="card-header">
                        <h5 class="mb-0"><i class="bi bi-memory stat-icon"></i>Memory Information</h5>
                    </div>
                    <div class="card-body" id="memory-info">
                        <div class="text-center">
                            <div class="spinner-border" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- CPU Info -->
        <div class="row mb-4">
            <div class="col">
                <div class="card">
                    <div class="card-header">
                        <h5 class="mb-0"><i class="bi bi-cpu stat-icon"></i>CPU Information</h5>
                    </div>
                    <div class="card-body" id="cpu-info">
                        <div class="text-center">
                            <div class="spinner-border" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- GPU Info -->
        <div class="row mb-4">
            <div class="col">
                <div class="card">
                    <div class="card-header">
                        <h5 class="mb-0"><i class="bi bi-gpu-card stat-icon"></i>GPU Information</h5>
                    </div>
                    <div class="card-body" id="gpu-info">
                        <div class="text-center">
                            <div class="spinner-border" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Footer -->
    <footer class="text-center text-muted py-3 mt-5">
        <small>&copy; Protective Resources, Inc. 2025</small>
    </footer>
    
    <!-- Refresh Controls -->
    <div class="refresh-controls">
        <div class="btn-group" role="group" aria-label="Refresh controls">
            <select class="form-select" id="refresh-interval" onchange="updateRefreshInterval()" title="Auto-refresh interval">
                <option value="5">5s</option>
                <option value="10">10s</option>
                <option value="30" selected>30s</option>
                <option value="60">60s</option>
            </select>
            <button class="btn btn-primary refresh-btn" onclick="refreshData()" title="Refresh Now">
                <i class="bi bi-arrow-clockwise"></i>
            </button>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Configuration
        let AUTO_REFRESH_INTERVAL = 30; // seconds - default value
        
        let autoRefresh = true;
        let refreshInterval;
        
        function formatBytes(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }
        
        function formatUptime(seconds) {
            const days = Math.floor(seconds / 86400);
            const hours = Math.floor((seconds % 86400) / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            return `${days}d ${hours}h ${minutes}m`;
        }
        
        function getTemperatureClass(temp) {
            if (temp === null || temp === undefined) return '';
            if (temp < 60) return 'normal';
            if (temp < 80) return 'warning';
            return 'danger';
        }
        
        function getProgressBarColor(percent) {
            if (percent < 50) return 'bg-success';
            if (percent < 80) return 'bg-warning';
            return 'bg-danger';
        }
        
        async function fetchSystemData() {
            try {
                const response = await fetch('/api/system');
                const data = await response.json();
                updateDisplay(data);
            } catch (error) {
                console.error('Error fetching system data:', error);
            }
        }
        
        function updateDisplay(data) {
            updateSystemInfo(data.system);
            updateCPUInfo(data.cpu);
            updateMemoryInfo(data.memory);
            updateGPUInfo(data.gpus, data.system.gpu_status || null);
        }
        
        function updateSystemInfo(system) {
            let psutilStatus = '';
            let psutilDetails = '';
            
            if (system.psutil_available) {
                psutilStatus = '<span class="badge bg-success">psutil available</span>';
                if (system.psutil_status && system.psutil_status.version) {
                    psutilDetails = `<br><small class="text-muted">v${system.psutil_status.version.join('.')} - ${system.psutil_status.status_message}</small>`;
                }
            } else {
                psutilStatus = '<span class="badge bg-warning">using fallback methods</span>';
                if (system.psutil_status && system.psutil_status.status_message) {
                    psutilDetails = `<br><small class="text-muted">${system.psutil_status.status_message}</small>`;
                }
            }
            
            const html = `
                <div class="row">
                    <div class="col-sm-6">
                        <strong>Hostname:</strong> ${system.hostname}<br>
                        <strong>Platform:</strong> ${system.platform}<br>
                        <strong>Architecture:</strong> ${system.architecture}<br>
                        <strong>Distribution:</strong> ${system.linux_distribution || 'Unknown'}
                    </div>
                    <div class="col-sm-6">
                        <strong>Kernel:</strong> ${system.kernel_version || 'Unknown'}<br>
                        <strong>Uptime:</strong> ${formatUptime(system.uptime)}<br>
                        <strong>Monitor Status:</strong> ${psutilStatus}${psutilDetails}<br>
                        <strong>Last Updated:</strong> ${new Date().toLocaleTimeString()}
                    </div>
                </div>
            `;
            document.getElementById('system-info').innerHTML = html;
        }
        
        function updateCPUInfo(cpu) {
            if (cpu.error) {
                document.getElementById('cpu-info').innerHTML = `<div class="alert alert-danger">Error: ${cpu.error}</div>`;
                return;
            }
            
            const tempDisplay = cpu.temperature ? 
                `<span class="temperature ${getTemperatureClass(cpu.temperature)}">${cpu.temperature.toFixed(1)}°C</span>` : 
                'N/A';
            
            const freqDisplay = cpu.frequency ? 
                `${cpu.frequency.current.toFixed(0)} MHz (${cpu.frequency.min.toFixed(0)}-${cpu.frequency.max.toFixed(0)} MHz)` : 
                'N/A';
            
            let coreUsageHtml = '';
            if (cpu.usage_per_core) {
                coreUsageHtml = '<div class="mt-3"><strong>Per-Core Usage:</strong><div class="row mt-2">';
                cpu.usage_per_core.forEach((usage, index) => {
                    coreUsageHtml += `
                        <div class="col-md-3 mb-2">
                            <small>Core ${index}</small>
                            <div class="progress">
                                <div class="progress-bar ${getProgressBarColor(usage)}" 
                                     style="width: ${usage}%" 
                                     role="progressbar">${usage.toFixed(1)}%</div>
                            </div>
                        </div>
                    `;
                });
                coreUsageHtml += '</div></div>';
            }
            
            const html = `
                <div class="row">
                    <div class="col-md-6">
                        <strong>Processor:</strong> ${cpu.name}<br>
                        <strong>Physical Cores:</strong> ${cpu.cores_physical}<br>
                        <strong>Logical Cores:</strong> ${cpu.cores_logical}<br>
                        <strong>Temperature:</strong> ${tempDisplay}
                    </div>
                    <div class="col-md-6">
                        <strong>Frequency:</strong> ${freqDisplay}<br>
                        <strong>Overall Usage:</strong>
                        <div class="progress mt-2">
                            <div class="progress-bar ${getProgressBarColor(cpu.usage_percent)}" 
                                 style="width: ${cpu.usage_percent}%" 
                                 role="progressbar">${cpu.usage_percent.toFixed(1)}%</div>
                        </div>
                    </div>
                </div>
                ${coreUsageHtml}
            `;
            document.getElementById('cpu-info').innerHTML = html;
        }
        
        function updateMemoryInfo(memory) {
            if (memory.error) {
                document.getElementById('memory-info').innerHTML = `<div class="alert alert-danger">Error: ${memory.error}</div>`;
                return;
            }
            
            const html = `
                <div class="mb-4">
                    <h6><i class="bi bi-memory"></i> Physical Memory (RAM)</h6>
                    <div class="row">
                        <div class="col-4"><strong>Total:</strong> ${formatBytes(memory.total)}</div>
                        <div class="col-4"><strong>Used:</strong> ${formatBytes(memory.used)}</div>
                        <div class="col-4"><strong>Available:</strong> ${formatBytes(memory.available)}</div>
                    </div>
                    <div class="progress mt-2">
                        <div class="progress-bar ${getProgressBarColor(memory.percent)}" 
                             style="width: ${memory.percent}%" 
                             role="progressbar">${memory.percent.toFixed(1)}%</div>
                    </div>
                </div>
                <div>
                    <h6><i class="bi bi-hdd"></i> Swap Memory</h6>
                    <div class="row">
                        <div class="col-4"><strong>Total:</strong> ${formatBytes(memory.swap_total)}</div>
                        <div class="col-4"><strong>Used:</strong> ${formatBytes(memory.swap_used)}</div>
                        <div class="col-4"><strong>Free:</strong> ${formatBytes(memory.swap_free)}</div>
                    </div>
                    <div class="progress mt-2">
                        <div class="progress-bar ${getProgressBarColor(memory.swap_percent)}" 
                             style="width: ${memory.swap_percent}%" 
                             role="progressbar">${memory.swap_percent.toFixed(1)}%</div>
                    </div>
                </div>
            `;
            document.getElementById('memory-info').innerHTML = html;
        }
        
        function updateGPUInfo(gpus, gpuStatus) {
            if (!gpus || gpus.length === 0) {
                let statusMessage = 'No GPUs detected or GPU monitoring not available.';
                let alertClass = 'alert-info';
                let statusDetails = '';
                
                // Handle case where gpuStatus might be undefined (disabled for debugging)
                if (gpuStatus) {
                    // Show which NVIDIA library is being used if available
                    if (gpuStatus.nvidia_library) {
                        statusDetails += `<div class="small text-muted mb-2">Using: ${gpuStatus.nvidia_library}</div>`;
                    }
                    
                    if (gpuStatus.gpu_errors && gpuStatus.gpu_errors.length > 0) {
                        alertClass = 'alert-warning';
                        statusMessage = 'GPU detection issues found:';
                        statusDetails += '<ul class="mb-0 mt-2">';
                        gpuStatus.gpu_errors.forEach(error => {
                            statusDetails += `<li>${error}</li>`;
                        });
                        statusDetails += '</ul>';
                        
                        // Add helpful suggestions
                        if (gpuStatus.gpu_errors.some(e => e.includes('version mismatch'))) {
                            statusDetails += '<div class="alert alert-info mt-2 mb-0"><small><strong>Suggestion:</strong> Restart the system or reinstall NVIDIA drivers<br>This error occurs when driver components do not match versions.</small></div>';
                        } else if (gpuStatus.gpu_errors.some(e => e.includes('nvidia-smi not found'))) {
                            statusDetails += '<div class="alert alert-info mt-2 mb-0"><small><strong>Suggestion:</strong> Install NVIDIA drivers</small></div>';
                        }
                    }
                } else {
                    statusDetails += '<div class="small text-muted mb-2">GPU status check disabled for debugging</div>';
                }
                
                document.getElementById('gpu-info').innerHTML = 
                    `<div class="alert ${alertClass}">${statusMessage}${statusDetails}</div>`;
                return;
            }
            
            let html = '<div class="row">';
            
            gpus.forEach((gpu, index) => {
                const vendorClass = gpu.vendor === 'NVIDIA' ? 'nvidia-card' : 'intel-card';
                const vendorIcon = gpu.vendor === 'NVIDIA' ? 'bi-nvidia' : 'bi-cpu';
                
                html += `
                    <div class="col-md-6 mb-3">
                        <div class="card gpu-card ${vendorClass}">
                            <div class="card-header">
                                <h6 class="mb-0">
                                    <i class="bi ${vendorIcon}"></i> ${gpu.name} 
                                    <span class="badge bg-light text-dark">${gpu.vendor}</span>
                                </h6>
                            </div>
                            <div class="card-body">
                `;
                
                // Memory information
                if (gpu.memory_total) {
                    html += `
                        <div class="mb-3">
                            <strong>VRAM Usage:</strong><br>
                            <small>Used: ${formatBytes(gpu.memory_used)} / Total: ${formatBytes(gpu.memory_total)}</small>
                            <div class="progress mt-1">
                                <div class="progress-bar ${getProgressBarColor(gpu.memory_percent)}" 
                                     style="width: ${gpu.memory_percent}%" 
                                     role="progressbar">${gpu.memory_percent.toFixed(1)}%</div>
                            </div>
                        </div>
                    `;
                }
                
                // GPU Utilization
                if (gpu.gpu_utilization !== null && gpu.gpu_utilization !== undefined) {
                    html += `
                        <div class="mb-3">
                            <strong>GPU Utilization:</strong>
                            <div class="progress mt-1">
                                <div class="progress-bar ${getProgressBarColor(gpu.gpu_utilization)}" 
                                     style="width: ${gpu.gpu_utilization}%" 
                                     role="progressbar">${gpu.gpu_utilization}%</div>
                            </div>
                        </div>
                    `;
                }
                
                // Additional stats
                html += '<div class="row">';
                
                if (gpu.temperature !== null && gpu.temperature !== undefined) {
                    html += `
                        <div class="col-6">
                            <small><strong>Temperature:</strong></small><br>
                            <span class="temperature ${getTemperatureClass(gpu.temperature)}">${gpu.temperature}°C</span>
                        </div>
                    `;
                }
                
                if (gpu.power_usage !== null && gpu.power_usage !== undefined) {
                    html += `
                        <div class="col-6">
                            <small><strong>Power Usage:</strong></small><br>
                            ${gpu.power_usage.toFixed(1)}W
                        </div>
                    `;
                }
                
                if (gpu.fan_speed !== null && gpu.fan_speed !== undefined) {
                    html += `
                        <div class="col-6">
                            <small><strong>Fan Speed:</strong></small><br>
                            ${gpu.fan_speed}%
                        </div>
                    `;
                }
                
                if (gpu.graphics_clock) {
                    html += `
                        <div class="col-6">
                            <small><strong>Graphics Clock:</strong></small><br>
                            ${gpu.graphics_clock} MHz
                        </div>
                    `;
                }
                
                if (gpu.memory_clock) {
                    html += `
                        <div class="col-6">
                            <small><strong>Memory Clock:</strong></small><br>
                            ${gpu.memory_clock} MHz
                        </div>
                    `;
                }
                
                html += '</div>'; // End row
                html += '</div></div></div>'; // End card
            });
            
            html += '</div>'; // End row
            document.getElementById('gpu-info').innerHTML = html;
        }
        
        function refreshData() {
            fetchSystemData();
        }
        
        function updateRefreshInterval() {
            const selector = document.getElementById('refresh-interval');
            AUTO_REFRESH_INTERVAL = parseInt(selector.value);
            startAutoRefresh(); // Restart with new interval
            console.log(`Auto-refresh interval updated to ${AUTO_REFRESH_INTERVAL} seconds`);
        }
        
        function startAutoRefresh() {
            if (refreshInterval) {
                clearInterval(refreshInterval);
            }
            refreshInterval = setInterval(fetchSystemData, AUTO_REFRESH_INTERVAL * 1000); // Convert seconds to milliseconds
        }
        
        // Initial load
        fetchSystemData();
        startAutoRefresh();
        
        // Initialize dropdown with current interval
        document.getElementById('refresh-interval').value = AUTO_REFRESH_INTERVAL;
        
        // Handle page visibility changes
        document.addEventListener('visibilitychange', function() {
            if (document.hidden) {
                if (refreshInterval) {
                    clearInterval(refreshInterval);
                }
            } else {
                startAutoRefresh();
                fetchSystemData();
            }
        });
    </script>
</body>
</html>
        """
    
    def log_message(self, format, *args):
        """Override to customize logging"""
        pass


def create_handler_class(monitor):
    """Create a handler class with the monitor instance"""
    def handler(*args, **kwargs):
        WebHandler(*args, monitor=monitor, **kwargs)
    return handler


def main():
    """Main function to start the web server"""
    print("GPU Status Monitor Starting...")
    print("Initializing system monitor...")
    
    if not PSUTIL_AVAILABLE:
        print("Warning: psutil is not available. Using fallback methods for system monitoring.")
        print(f"Status: {psutil_status}")
        print("For better performance and more detailed information, try these commands:")
        print("  - sudo apt update && sudo apt install python3-psutil python3-pip")
        print("  - pip3 install --user psutil")
        print("  - sudo pip3 install --upgrade --force-reinstall psutil")
        print("  - python3 -m pip install psutil")
        print("If still having issues, check your Python path and virtual environment settings.")
    else:
        print(f"✓ {psutil_status}")
    
    # Initialize system monitor
    monitor = SystemMonitor()
    
    # Create HTTP server
    server_address = ('', 8088)
    handler_class = create_handler_class(monitor)
    
    try:
        httpd = HTTPServer(server_address, handler_class)
        print(f"GPU Status Monitor running on http://localhost:8088")
        print("Press Ctrl+C to stop the server")
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.shutdown()
    except Exception as e:
        print(f"Error starting server: {e}")


if __name__ == "__main__":
    main()
