"""Nitro 5 Cooler Boost - Control Cooler Boost on Acer Nitro 5 (Linux/Unix)."""

from .core import NitroBoost, NitroBoostError, ECNotAvailableError

__all__ = ["NitroBoost", "NitroBoostError", "ECNotAvailableError"]
__version__ = "1.0.0"
