import wmi
import psutil
import requests
import socket
import getpass
import hashlib
import subprocess
from datetime import datetime, timezone, timedelta
from screeninfo import get_monitors
import tkinter as tk
from tkinter import messagebox
from dotenv import load_dotenv
import os

load_dotenv()
API_URL = os.getenv("URL_DESTINO")

# API_URL = "http://172.19.25.97:8000/audit/"
AGENT_VERSION = "1.1.0"

c = wmi.WMI()

PERU_TZ = timezone(timedelta(hours=-5))



# ------------------- HARDWARE -------------------

def get_device_type():
    try:
        chassis_types = c.Win32_SystemEnclosure()[0].ChassisTypes

        if not chassis_types:
            return "Unknown"

        ct = chassis_types[0]

        if ct in [8, 9, 10, 14]:
            return "Laptop"
        elif ct in [13]:
            return "All-in-One"
        elif ct in [30, 31, 32]:
            return "Tablet"
        elif ct in [3, 4, 6]:
            return "Desktop"
        else:
            return f"Other ({ct})"

    except:
        return "Unknown"

def get_serial():
    try:
        return c.Win32_BIOS()[0].SerialNumber.strip()
    except:
        return None

def get_brand_model():
    try:
        cs = c.Win32_ComputerSystem()[0]
        return f"{cs.Manufacturer} {cs.Model}"
    except:
        return None

def get_cpu():
    cpu = c.Win32_Processor()[0]
    return {
        "name": cpu.Name,
        "cores": cpu.NumberOfCores,
        "threads": cpu.NumberOfLogicalProcessors
    }

def get_gpu():
    return [g.Name for g in c.Win32_VideoController()]

# def get_storage():
#     return [{
#         "model": d.Model,
#         "size_gb": round(int(d.Size) / (1024**3), 2)
#     } for d in c.Win32_DiskDrive()]
def get_storage():
    disks = []

    for d in c.Win32_DiskDrive():
        try:
            if not d.Size:
                continue  # ignora discos sin tamaño

            disks.append({
                "model": d.Model.strip() if d.Model else "Unknown",
                "size_gb": round(int(d.Size) / (1024**3), 2)
            })
        except:
            continue

    return disks

def get_ram():
    total = round(psutil.virtual_memory().total / (1024**3), 2)
    modules = [{
        "capacity_gb": round(int(m.Capacity) / (1024**3), 2),
        "manufacturer": m.Manufacturer,
        "part_number": m.PartNumber.strip(),
        "type": m.SMBIOSMemoryType
    } for m in c.Win32_PhysicalMemory()]
    return {"total_gb": total, "modules": modules}

def get_motherboard():
    b = c.Win32_BaseBoard()[0]
    return f"{b.Manufacturer} {b.Product}"

def get_monitors_info():
    return [{
        "name": m.name,
        "resolution": f"{m.width}x{m.height}"
    } for m in get_monitors()]

# ------------------- NETWORK -------------------

def get_network_info():
    interfaces = []
    addrs = psutil.net_if_addrs()
    stats = psutil.net_if_stats()

    for iface, addr_list in addrs.items():
        data = {
            "interface": iface,
            "mac": None,
            "ips": [],
            "is_up": stats.get(iface).isup if iface in stats else False
        }
        for addr in addr_list:
            if addr.family.name == "AF_LINK":
                data["mac"] = addr.address
            elif addr.family.name == "AF_INET":
                data["ips"].append(addr.address)
        interfaces.append(data)
    return interfaces

# ------------------- SECURITY -------------------

def get_bitlocker_status():
    try:
        result = subprocess.check_output(
            "manage-bde -status C:",
            shell=True,
            stderr=subprocess.DEVNULL
        ).decode()
        return "Protection On" in result
    except:
        return None

def get_secure_boot():
    try:
        sb = c.MS_SecureBoot()[0]
        return sb.SecureBootEnabled
    except:
        return None

def get_tpm_info():
    try:
        tpm = wmi.WMI(namespace="root\\CIMV2\\Security\\MicrosoftTpm").Win32_Tpm()[0]
        return {
            "present": True,
            "version": tpm.SpecVersion
        }
    except:
        return {"present": False, "version": None}

def get_uac_status():
    try:
        reg = subprocess.check_output(
            'reg query HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\System /v EnableLUA',
            shell=True
        ).decode()
        return "0x1" in reg
    except:
        return None

# ------------------- USERS -------------------

def get_local_users():
    try:
        return [u.Name for u in c.Win32_UserAccount(LocalAccount=True)]
    except:
        return []

def get_last_logged_user():
    try:
        return c.Win32_ComputerSystem()[0].UserName
    except:
        return None

def get_last_logon_time():
    try:
        os = c.Win32_OperatingSystem()[0]
        return os.LastBootUpTime
    except:
        return None

# ------------------- NETWORK DRIVES -------------------

def get_network_drives():
    drives = []
    try:
        output = subprocess.check_output(
            "net use",
            shell=True,
            stderr=subprocess.DEVNULL
        ).decode(errors="ignore")

        for line in output.splitlines():
            if ":" in line and "\\" in line:
                parts = line.split()
                drives.append({
                    "drive_letter": parts[1],
                    "remote_path": parts[2],
                    "status": parts[0]
                })
    except:
        pass

    return drives

# ------------------- SOFTWARE -------------------

def get_installed_software():
    software = []
    try:
        for s in c.Win32_Product():
            software.append({
                "name": s.Name,
                "version": s.Version,
                "vendor": s.Vendor,
                "install_date": format_wmi_date(s.InstallDate),
                "licensed": "unknown"
            })
    except:
        pass
    return software

# ------------------- OS -------------------

def get_os_info():
    try:
        os = c.Win32_OperatingSystem()[0]
        return {
            "name": os.Caption,
            "version": os.Version,
            "build": os.BuildNumber,
            "architecture": os.OSArchitecture
        }
    except:
        return {}

# ------------------- UTIL -------------------

def get_device_hash(serial, motherboard, hostname):
    raw = f"{serial}-{motherboard}-{hostname}"
    return hashlib.sha256(raw.encode()).hexdigest()

def now_peru_iso():
    return datetime.now(PERU_TZ).isoformat()

def show_finished_message():
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo(
        "Auditoría TI",
        "Programa finalizado.\nLa información fue enviada correctamente."
    )
    root.destroy()

def format_wmi_date(date_str):
    """
    Convertirr 'YYYYMMDD' -> 'YYYY-MM-DD'
    """
    if not date_str or len(date_str) != 8:
        return None
    try:
        return f"{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]}"
    except:
        return None

# ------------------- MAIN -------------------

def collect_data():
    serial = get_serial()
    motherboard = get_motherboard()
    hostname = socket.gethostname()

    return {
        "audit": {
            "executed_at_utc": datetime.utcnow().isoformat(),
            "executed_at_peru": now_peru_iso(),
            "agent_version": AGENT_VERSION,
            "ip": socket.gethostbyname(hostname),
            "device_hash": get_device_hash(serial, motherboard, hostname)
        },
        "hostname": hostname,
        "username": getpass.getuser(),
        "last_user": get_last_logged_user(),
        "last_logon": get_last_logon_time(),
        "os": get_os_info(),
        "device_type": get_device_type(),
        "serial_number": serial,
        "brand_model": get_brand_model(),
        "cpu": get_cpu(),
        "gpu": get_gpu(),
        "ram": get_ram(),
        "storage": get_storage(),
        "motherboard": motherboard,
        "monitors": get_monitors_info(),
        "network": get_network_info(),
        "security": {
            "bitlocker_enabled": get_bitlocker_status(),
            "secure_boot": get_secure_boot(),
            "tpm": get_tpm_info(),
            "uac_enabled": get_uac_status()
        },
        "users": {
            "local_users": get_local_users()
        },
        "network_drives": get_network_drives(),
        "software": get_installed_software()
    }

def send_data(payload):
    try:
        requests.post(API_URL, json=payload, timeout=10)
    except:
        pass

if __name__ == "__main__":
    payload = collect_data()
    send_data(payload)
    show_finished_message()