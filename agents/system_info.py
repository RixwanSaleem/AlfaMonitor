import json
import time
import psutil
import platform


def human_bytes_per_sec(value):
    if value is None:
        return '--'
    units = ['B/s', 'KB/s', 'MB/s', 'GB/s']
    for unit in units:
        if abs(value) < 1024.0 or unit == units[-1]:
            return f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{value:.1f} TB/s"


def get_os_type():
    return platform.system()


def collect_metrics():
    os_type = get_os_type()
    before_net = psutil.net_io_counters()
    before_disk = psutil.disk_io_counters()
    cpu = psutil.cpu_percent(interval=1)
    after_net = psutil.net_io_counters()
    after_disk = psutil.disk_io_counters()
    memory_data = psutil.virtual_memory()
    
    # Get disk usage (C:\ for Windows, / for Linux)
    disk_path = "C:\\" if os_type == "Windows" else "/"
    try:
        disk = psutil.disk_usage(disk_path).percent
    except Exception:
        disk = 0
    
    temp = "N/A"
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            first = next(iter(temps.values()))
            if first:
                temp = f"{first[0].current:.1f}°C"
    except Exception:
        temp = "N/A"

    services = collect_services(os_type)

    net_in = max(0, after_net.bytes_recv - before_net.bytes_recv)
    net_out = max(0, after_net.bytes_sent - before_net.bytes_sent)
    disk_read = max(0, after_disk.read_bytes - before_disk.read_bytes)
    disk_write = max(0, after_disk.write_bytes - before_disk.write_bytes)

    return {
        "cpu_percent": int(cpu),
        "ram_percent": int(memory_data.percent),
        "ram_used_gb": round(memory_data.used / (1024 ** 3), 1),
        "ram_total_gb": round(memory_data.total / (1024 ** 3), 1),
        "disk_percent": int(disk),
        "disk_read": human_bytes_per_sec(disk_read),
        "disk_write": human_bytes_per_sec(disk_write),
        "network_in": human_bytes_per_sec(net_in),
        "network_out": human_bytes_per_sec(net_out),
        "temperature": temp,
        "services": services,
        "os": os_type,
    }


def collect_services(os_type):
    if os_type == "Windows":
        return collect_windows_services()
    else:
        return collect_linux_services()


def collect_windows_services():
    """Collect Windows service status by checking common process names"""
    services = {
        "rdp": is_process_running("svchost"),
        "iis": is_process_running("w3wp"),
        "sql": is_process_running("sqlservr"),
        "dns": is_process_running("dns"),
    }
    return services


def collect_linux_services():
    """Collect Linux service status"""
    services = {
        "ssh": is_process_running("ssh"),
        "nginx": is_process_running("nginx"),
        "docker": is_process_running("docker"),
    }
    return services


def is_process_running(process_name: str):
    """Cross-platform process detection"""
    for proc in psutil.process_iter(["name"]):
        try:
            if proc.info["name"] and process_name.lower() in proc.info["name"].lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False


def metrics_payload(host: str, username: str = "agent", port: int = 22):
    data = collect_metrics()
    data.update({"host": host, "username": username, "port": port})
    return data
