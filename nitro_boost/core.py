#!/usr/bin/env python3
"""
Nitro 5 Cooler Boost - Core EC control module
Controls fan speed via Embedded Controller registers.
Supports: AN515-44, AN515-46, AN515-56, AN515-58, AN515-57
"""

import os
import struct
import subprocess
from pathlib import Path
from typing import Optional, Tuple

# EC Register addresses (Acer Nitro 5)
EC_WRITE_ENABLE = 0x03
EC_GPU_FAN_MODE = 0x21  # 0x10=auto, 0x20=max, 0x30=custom
EC_CPU_FAN_MODE = 0x22  # 0x04=auto, 0x08=max, 0x0c=custom
EC_CPU_FAN_PCT = 0x37   # 0-100%
EC_GPU_FAN_PCT = 0x3A   # 0-100%
# RPM (alguns modelos - valores brutos podem precisar de conversão)
EC_CPU_FAN_RPM_LO = 0x13  # byte baixo
EC_CPU_FAN_RPM_HI = 0x14  # byte alto (se 16-bit)
EC_GPU_FAN_RPM_LO = 0x15
EC_GPU_FAN_RPM_HI = 0x16

# EC interface paths
EC_SYS_PATH = Path("/sys/kernel/debug/ec/ec0/io")
EC_ACPI_PATH = Path("/dev/ec")


class NitroBoostError(Exception):
    """Base exception for Nitro Boost operations."""
    pass


class ECNotAvailableError(NitroBoostError):
    """EC interface not available."""
    pass


class NitroBoost:
    """Control Cooler Boost (max fan) on Acer Nitro 5 laptops."""

    def __init__(self):
        self._ec_path: Optional[Path] = None
        self._use_ec_sys = False

    def _detect_ec_interface(self) -> bool:
        """Detect EC interface (ec_sys or acpi_ec)."""
        if EC_SYS_PATH.exists():
            self._ec_path = EC_SYS_PATH
            self._use_ec_sys = True
            return True
        if EC_ACPI_PATH.exists():
            self._ec_path = EC_ACPI_PATH
            self._use_ec_sys = False
            return True
        return False

    def _ensure_ec_sys(self) -> bool:
        """Ensure ec_sys module is loaded with write support."""
        try:
            result = subprocess.run(
                ["modprobe", "ec_sys", "write_support=1"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and EC_SYS_PATH.exists():
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return False

    def _ensure_ec_sys_grub(self) -> bool:
        """Check if ec_sys.write_support=1 is in kernel params."""
        try:
            with open("/proc/cmdline", "r") as f:
                cmdline = f.read()
            return "ec_sys.write_support=1" in cmdline or "ec_sys.write_support=1" in cmdline
        except (IOError, PermissionError):
            return False

    def _write_ec_sys(self, offset: int, value: int) -> bool:
        """Write to EC via ec_sys debugfs."""
        if not self._ec_path or not self._ec_path.exists():
            return False
        try:
            with open(self._ec_path, "r+b") as f:
                f.seek(offset)
                f.write(bytes([value]))
            return True
        except (IOError, PermissionError, OSError):
            return False

    def _write_acpi_ec(self, offset: int, value: int) -> bool:
        """Write to EC via /dev/ec (acpi_ec module)."""
        if not self._ec_path or not self._ec_path.exists():
            return False
        try:
            with open(self._ec_path, "r+b") as f:
                f.seek(offset)
                f.write(bytes([value]))
            return True
        except (IOError, PermissionError, OSError):
            return False

    def _write_ec(self, offset: int, value: int) -> bool:
        """Write byte to EC register."""
        if not self._ec_path:
            if not self._detect_ec_interface():
                return False
        if not self._ec_path.exists():
            return False
        if self._use_ec_sys:
            return self._write_ec_sys(offset, value)
        return self._write_acpi_ec(offset, value)

    def _read_ec(self, offset: int) -> Optional[int]:
        """Read byte from EC register."""
        if not self._ec_path:
            if not self._detect_ec_interface():
                return None
        if not self._ec_path.exists():
            return None
        try:
            with open(self._ec_path, "rb") as f:
                f.seek(offset)
                data = f.read(1)
                return data[0] if data else None
        except (IOError, PermissionError, OSError):
            return None

    def _enable_write(self) -> bool:
        """Enable EC write access."""
        return self._write_ec(EC_WRITE_ENABLE, 0x11)

    def is_available(self) -> Tuple[bool, str]:
        """
        Check if EC control is available.
        Returns (success, message).
        """
        if os.geteuid() != 0:
            return False, "Requer privilégios de root (sudo)"

        if self._ensure_ec_sys():
            self._detect_ec_interface()

        if not self._detect_ec_interface():
            msg = (
                "Interface EC não encontrada.\n\n"
                "Configure o kernel:\n"
                "1. Edite /etc/default/grub\n"
                "2. Adicione ec_sys.write_support=1 em GRUB_CMDLINE_LINUX_DEFAULT\n"
                "3. Execute: sudo update-grub\n"
                "4. Reinicie o sistema"
            )
            return False, msg

        return True, "OK"

    def set_cooler_boost(self, enabled: bool) -> bool:
        """
        Enable or disable Cooler Boost (max fan speed) for both CPU and GPU.
        Returns True on success.
        """
        return self.set_cooler_boost_individual(enabled, enabled)

    def set_cooler_boost_individual(self, cpu_max: bool, gpu_max: bool) -> bool:
        """
        Set Cooler Boost (max fan) for CPU and GPU independently.
        cpu_max=True = CPU ventoinha no máximo, gpu_max=True = GPU ventoinha no máximo.
        Returns True on success.
        """
        if not self._enable_write():
            return False

        # Lê estado atual para preservar o que não está sendo alterado
        cpu_mode = self._read_ec(EC_CPU_FAN_MODE)
        gpu_mode = self._read_ec(EC_GPU_FAN_MODE)

        # CPU: 0x04=auto, 0x08=max, 0x0c=custom
        new_cpu = 0x08 if cpu_max else 0x04
        # GPU: 0x10=auto, 0x20=max, 0x30=custom
        new_gpu = 0x20 if gpu_max else 0x10

        self._write_ec(EC_CPU_FAN_MODE, new_cpu)
        self._write_ec(EC_GPU_FAN_MODE, new_gpu)
        return True

    def set_custom_fan(self, percent: int) -> bool:
        """
        Set custom fan speed for both CPU and GPU (0-100%).
        Returns True on success.
        """
        return self.set_custom_fans(percent, percent)

    def set_custom_fans(self, cpu_percent: int, gpu_percent: int) -> bool:
        """
        Set custom fan speed for CPU and GPU independently (0-100% each).
        Returns True on success.
        """
        if not 0 <= cpu_percent <= 100 or not 0 <= gpu_percent <= 100:
            return False
        if not self._enable_write():
            return False

        # Custom mode
        self._write_ec(EC_GPU_FAN_MODE, 0x30)
        self._write_ec(EC_CPU_FAN_MODE, 0x0C)
        self._write_ec(EC_CPU_FAN_PCT, cpu_percent)
        self._write_ec(EC_GPU_FAN_PCT, gpu_percent)
        return True

    def get_cooler_boost_status(self) -> Optional[bool]:
        """
        Get current Cooler Boost status.
        Returns True if max, False if auto/custom, None if unknown.
        """
        cpu_mode = self._read_ec(EC_CPU_FAN_MODE)
        gpu_mode = self._read_ec(EC_GPU_FAN_MODE)
        if cpu_mode is None or gpu_mode is None:
            return None
        # Max: CPU 0x08, GPU 0x20
        return cpu_mode == 0x08 and gpu_mode == 0x20

    def get_fan_info(self) -> dict:
        """Get fan mode and percentage (CPU/GPU)."""
        cpu_mode = self._read_ec(EC_CPU_FAN_MODE)
        gpu_mode = self._read_ec(EC_GPU_FAN_MODE)
        cpu_pct = self._read_ec(EC_CPU_FAN_PCT)
        gpu_pct = self._read_ec(EC_GPU_FAN_PCT)

        mode = "unknown"
        if cpu_mode is not None and gpu_mode is not None:
            if cpu_mode == 0x08 and gpu_mode == 0x20:
                mode = "max"
            elif cpu_mode == 0x04 and gpu_mode == 0x10:
                mode = "auto"
            elif cpu_mode == 0x0C and gpu_mode == 0x30:
                mode = "custom"

        cpu_cb = cpu_mode == 0x08 if cpu_mode is not None else None
        gpu_cb = gpu_mode == 0x20 if gpu_mode is not None else None

        # RPM: tenta EC ou estima a partir de %
        cpu_rpm = self._read_fan_rpm_ec(EC_CPU_FAN_RPM_LO, EC_CPU_FAN_RPM_HI)
        gpu_rpm = self._read_fan_rpm_ec(EC_GPU_FAN_RPM_LO, EC_GPU_FAN_RPM_HI)
        if cpu_rpm is None and cpu_pct is not None:
            cpu_rpm = int(cpu_pct * 55)  # ~0-5500 RPM típico
        if gpu_rpm is None and gpu_pct is not None:
            gpu_rpm = int(gpu_pct * 55)

        return {
            "mode": mode,
            "cpu_percent": cpu_pct if cpu_pct is not None else None,
            "gpu_percent": gpu_pct if gpu_pct is not None else None,
            "cpu_rpm": cpu_rpm,
            "gpu_rpm": gpu_rpm,
            "cooler_boost": self.get_cooler_boost_status(),
            "cpu_cooler_boost": cpu_cb,
            "gpu_cooler_boost": gpu_cb,
        }

    def _read_fan_rpm_ec(self, lo_reg: int, hi_reg: Optional[int] = None) -> Optional[int]:
        """Lê RPM do EC (8 ou 16-bit). Retorna None se não disponível."""
        lo = self._read_ec(lo_reg)
        if lo is None:
            return None
        if hi_reg is not None:
            hi = self._read_ec(hi_reg)
            val = (hi << 8) | lo if hi is not None else lo
        else:
            val = lo
        if val == 0 or val > 65000:
            return None
        return val
