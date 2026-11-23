"""Carrega a DLL do hidapi antes de importar o wrapper Python."""

import ctypes
import os
import sys
from pathlib import Path

VENDOR_DIR = Path(__file__).resolve().parents[1] / "vendor"
DLL = VENDOR_DIR / "hidapi.dll"

if sys.platform == "win32":
    if not DLL.exists():
        raise FileNotFoundError(f"DLL do hidapi ausente: {DLL}")
    os.add_dll_directory(str(VENDOR_DIR))
    ctypes.WinDLL(str(DLL))

import hid  # noqa: E402

__all__ = ["hid"]
