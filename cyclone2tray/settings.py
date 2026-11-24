"""Configurações persistidas e inicialização automática no Windows."""

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

APP_NAME = "Cyclone2Tray"
LEGACY_APP_NAME = "CycloneTray"


@dataclass
class Settings:
    alert_percent: int = 20
    critical_percent: int = 10
    last_percent: int | None = None
    last_read_at: str | None = None
    device_path_hex: str | None = None

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


def _local_app_data() -> Path:
    root = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(root)


def settings_path() -> Path:
    return _local_app_data() / APP_NAME / "settings.json"


def _legacy_settings_path() -> Path:
    return _local_app_data() / LEGACY_APP_NAME / "settings.json"


def load_settings() -> Settings:
    for path in (settings_path(), _legacy_settings_path()):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return Settings(**{k: v for k, v in data.items() if k in Settings.__annotations__})
        except (OSError, ValueError, TypeError):
            continue
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
            try:
                return bool(winreg.QueryValueEx(key, APP_NAME)[0])
            except FileNotFoundError:
                return bool(winreg.QueryValueEx(key, LEGACY_APP_NAME)[0])
    except OSError:
        return False


def _startup_command(executable: str, frozen: bool, script: Path) -> str:
    if frozen:
        return f'"{executable}"'
    return f'"{executable}" "{script}"'


def set_start_with_windows(enabled: bool) -> None:
    try:
        import winreg

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            if enabled:
                import sys

                script = Path(__file__).resolve().parents[1] / "run_tray.py"
                command = _startup_command(
                    sys.executable,
                    getattr(sys, "frozen", False),
                    script,
                )
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, command)
            for name in (APP_NAME, LEGACY_APP_NAME):
                try:
                    if not enabled or name == LEGACY_APP_NAME:
                        winreg.DeleteValue(key, name)
                except FileNotFoundError:
                    pass
    except OSError:
        pass
