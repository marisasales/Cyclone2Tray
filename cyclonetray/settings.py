"""Configurações persistidas e inicialização automática no Windows."""

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

APP_NAME = "CycloneTray"


@dataclass
class Settings:
    alert_percent: int = 20
    critical_percent: int = 10
    last_percent: int | None = None
    last_read_at: str | None = None
    device_path_hex: str | None = None
    heartbeat_enabled: bool = True

    @property
    def device_path(self) -> bytes | None:
        if not self.device_path_hex:
            return None
        try:
            return bytes.fromhex(self.device_path_hex)
        except ValueError:
            return None

    @device_path.setter
    def device_path(self, value: bytes | None) -> None:
        self.device_path_hex = value.hex() if value else None


def settings_path() -> Path:
    root = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(root) / APP_NAME / "settings.json"


def load_settings() -> Settings:
    path = settings_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return Settings(**{k: v for k, v in data.items() if k in Settings.__annotations__})
    except (OSError, ValueError, TypeError):
        return Settings()


def save_settings(settings: Settings) -> None:
    path = settings_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
    except OSError:
        pass


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def get_start_with_windows() -> bool:
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            return bool(winreg.QueryValueEx(key, APP_NAME)[0])
    except OSError:
        return False


def set_start_with_windows(enabled: bool) -> None:
    try:
        import winreg

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            if enabled:
                import sys

                script = Path(__file__).resolve().parents[1] / "run_tray.py"
                command = f'"{sys.executable}" "{script}"'
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, command)
            else:
                winreg.DeleteValue(key, APP_NAME)
    except OSError:
        pass
