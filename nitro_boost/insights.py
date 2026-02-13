#!/usr/bin/env python3
"""System insights: temperatures, GPU, power, etc."""

import os
import re
import subprocess
from typing import Any, Dict, List, Optional


def _run(cmd: List[str], timeout: float = 2.0) -> Optional[str]:
    try:
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return r.stdout.strip() if r.returncode == 0 else None
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


def get_sensors() -> Dict[str, Any]:
    """Parse lm-sensors output for temperatures."""
    out = _run(["sensors", "-u"])
    if not out:
        return {"temps": [], "raw": None}

    temps: List[Dict[str, Any]] = []
    current_chip = ""
    current_label = ""

    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("Adapter:"):
            pass
        elif ":" not in line:
            current_chip = line
        elif ":" in line and "_input:" in line:
            # e.g. temp1_input: 45.000
            match = re.match(r"(\w+)_input:\s*([\d.]+)", line)
            if match:
                name, val = match.groups()
                try:
                    val_f = float(val)
                    label = name.replace("temp", "Temp ").replace("_", " ")
                    temps.append({
                        "label": label,
                        "value": round(val_f, 1),
                        "chip": current_chip or "unknown",
                    })
                except ValueError:
                    pass

    # Fallback: parse human-readable sensors output
    if not temps:
        out = _run(["sensors"])
        if out:
            for m in re.finditer(r"([^:]+):\s*\+?([\d.]+)°C", out):
                label, val = m.groups()
                try:
                    temps.append({
                        "label": label.strip(),
                        "value": round(float(val), 1),
                        "chip": "",
                    })
                except ValueError:
                    pass

    # Fan RPM (fan1_input, fan2_input em RPM)
    fans = []
    if out:
        for m in re.finditer(r"fan(\d+)_input:\s*([\d.]+)", out):
            fans.append({"fan": int(m.group(1)), "rpm": int(float(m.group(2)))})
        for m in re.finditer(r"([^:]+fan[^:]*):\s*(\d+)\s*RPM", out, re.I):
            fans.append({"label": m.group(1).strip(), "rpm": int(m.group(2))})

    return {"temps": temps[:12], "fans": fans, "raw": out[:500] if out else None}


def get_nvidia_gpu() -> Optional[Dict[str, Any]]:
    """Get NVIDIA GPU info via nvidia-smi."""
    out = _run([
        "nvidia-smi",
        "--query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total,power.draw",
        "--format=csv,noheader,nounits",
    ])
    if not out:
        return None

    parts = [p.strip() for p in out.split(",")]
    if len(parts) < 4:
        return None

    try:
        name = parts[0].strip('"')
        temp = int(float(parts[1])) if parts[1] != "[N/A]" else None
        util = int(float(parts[2])) if len(parts) > 2 and parts[2] != "[N/A]" else None
        mem_used = int(float(parts[3])) if len(parts) > 3 and parts[3] != "[N/A]" else None
        mem_total = int(float(parts[4])) if len(parts) > 4 and parts[4] != "[N/A]" else None
        power = float(parts[5]) if len(parts) > 5 and parts[5] != "[N/A]" else None

        return {
            "name": name,
            "temperature": temp,
            "utilization": util,
            "memory_used_mb": mem_used,
            "memory_total_mb": mem_total,
            "power_watts": round(power, 1) if power else None,
        }
    except (ValueError, IndexError):
        return None


_prev_stat = None


def get_cpu_usage() -> Optional[float]:
    """Get CPU usage percentage from /proc/stat (requires two samples)."""
    global _prev_stat
    try:
        with open("/proc/stat", "r") as f:
            first = f.readline()
        parts = first.split()
        if len(parts) < 8:
            return None
        # user, nice, system, idle, iowait, irq, softirq, steal
        total = sum(int(x) for x in parts[1:8])
        idle = int(parts[4])
        curr = (total, idle)
        if _prev_stat is not None:
            dt = total - _prev_stat[0]
            di = idle - _prev_stat[1]
            if dt > 0:
                _prev_stat = curr
                return round(100 * (1 - di / dt), 1)
        _prev_stat = curr
        return None  # First sample
    except (IOError, ValueError):
        return None


def get_cpu_temp_thermal() -> Optional[float]:
    """Lê temperatura CPU de /sys/class/thermal (fallback)."""
    try:
        import glob
        for path in sorted(glob.glob("/sys/class/thermal/thermal_zone*/temp")):
            try:
                with open(path, "r") as f:
                    val = int(f.read().strip())
                if 0 < val < 150000:  # 0-150°C em millidegrees
                    return round(val / 1000, 1)
            except (IOError, ValueError):
                continue
        for path in sorted(glob.glob("/sys/class/thermal/thermal_zone*")):
            type_path = path + "/type"
            temp_path = path + "/temp"
            try:
                with open(type_path, "r") as f:
                    t = f.read().strip().lower()
                if "pkg" in t or "cpu" in t or "x86" in t:
                    with open(temp_path, "r") as f:
                        val = int(f.read().strip())
                    if 0 < val < 150000:
                        return round(val / 1000, 1)
            except (IOError, ValueError):
                continue
    except Exception:
        pass
    return None


def get_cpu_freq() -> Optional[float]:
    """Get current CPU frequency in MHz."""
    try:
        with open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq", "r") as f:
            return round(int(f.read().strip()) / 1000, 0)
    except (IOError, ValueError):
        return None


def get_uptime() -> Optional[str]:
    """Get system uptime as human string."""
    try:
        with open("/proc/uptime", "r") as f:
            secs = float(f.read().split()[0])
        m, s = divmod(int(secs), 60)
        h, m = divmod(m, 60)
        d, h = divmod(h, 24)
        if d > 0:
            return f"{d}d {h}h"
        if h > 0:
            return f"{h}h {m}m"
        return f"{m}m {s}s"
    except (IOError, ValueError):
        return None


def get_all_insights() -> Dict[str, Any]:
    """Aggregate all system insights."""
    sensors = get_sensors()
    gpu = get_nvidia_gpu()
    cpu_usage = get_cpu_usage()
    cpu_freq = get_cpu_freq()
    uptime = get_uptime()

    # Pick main temps
    temps = sensors.get("temps", [])
    cpu_temp = None
    gpu_temp_from_sensors = None
    first_temp = None
    for t in temps:
        lbl = t.get("label", "").lower()
        chip = t.get("chip", "").lower()
        val = t.get("value")
        if first_temp is None and val is not None:
            first_temp = val
        if "core" in lbl or "package" in lbl or "cpu" in lbl or "k10" in lbl:
            if cpu_temp is None:
                cpu_temp = val
        elif "coretemp" in chip or "k10temp" in chip or "zenpower" in chip:
            if cpu_temp is None:
                cpu_temp = val
        elif "gpu" in lbl or "nvidia" in lbl or "amdgpu" in lbl:
            gpu_temp_from_sensors = val
    if cpu_temp is None:
        cpu_temp = get_cpu_temp_thermal()
    if cpu_temp is None:
        cpu_temp = first_temp

    if gpu and gpu.get("temperature") is not None:
        gpu_temp = gpu["temperature"]
    else:
        gpu_temp = gpu_temp_from_sensors

    fans = sensors.get("fans", [])
    cpu_fan_rpm = None
    gpu_fan_rpm = None
    for f in fans:
        if f.get("fan") == 1 or "cpu" in str(f.get("label", "")).lower():
            cpu_fan_rpm = f.get("rpm")
        elif f.get("fan") == 2 or "gpu" in str(f.get("label", "")).lower():
            gpu_fan_rpm = f.get("rpm")
    if len(fans) == 1:
        cpu_fan_rpm = fans[0].get("rpm")
    elif len(fans) >= 2:
        cpu_fan_rpm = fans[0].get("rpm")
        gpu_fan_rpm = fans[1].get("rpm")

    return {
        "cpu": {
            "temperature": cpu_temp,
            "usage": cpu_usage,
            "frequency_mhz": cpu_freq,
        },
        "gpu": gpu,
        "gpu_temperature": gpu_temp if gpu else gpu_temp_from_sensors,
        "temperatures": temps,
        "uptime": uptime,
        "cpu_fan_rpm": cpu_fan_rpm,
        "gpu_fan_rpm": gpu_fan_rpm,
    }
