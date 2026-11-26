import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from cyclone2tray.i18n import DEFAULT_LANGUAGE
from cyclone2tray.settings import DEFAULT_ICON_STYLE, _startup_command, load_settings


class StartupCommandTests(unittest.TestCase):
    def test_frozen_app_starts_without_script_argument(self):
        command = _startup_command(
            r"C:\Program Files\Cyclone2Tray\Cyclone2Tray.exe",
            True,
            Path(r"C:\app\run_tray.py"),
        )

        self.assertEqual(
            command,
            '"C:\\Program Files\\Cyclone2Tray\\Cyclone2Tray.exe"',
        )

    def test_python_app_starts_with_script_argument(self):
        command = _startup_command(
            r"C:\Python\pythonw.exe",
            False,
            Path(r"C:\app\run_tray.py"),
        )

        self.assertEqual(command, '"C:\\Python\\pythonw.exe" "C:\\app\\run_tray.py"')


class LanguageSettingsTests(unittest.TestCase):
    def test_missing_or_unsupported_language_defaults_to_english(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "settings.json"
            with (
                patch("cyclone2tray.settings.settings_path", return_value=path),
                patch(
                    "cyclone2tray.settings._legacy_settings_path",
                    return_value=Path(temp_dir) / "legacy.json",
                ),
            ):
                for values in ({"alert_percent": 25}, {"language": "fr"}):
                    with self.subTest(values=values):
                        path.write_text(json.dumps(values), encoding="utf-8")
                        self.assertEqual(load_settings().language, DEFAULT_LANGUAGE)

    def test_supported_language_is_loaded(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "settings.json"
            path.write_text(json.dumps({"language": "es"}), encoding="utf-8")
            with (
                patch("cyclone2tray.settings.settings_path", return_value=path),
                patch(
                    "cyclone2tray.settings._legacy_settings_path",
                    return_value=Path(temp_dir) / "legacy.json",
                ),
            ):
                self.assertEqual(load_settings().language, "es")


class IconStyleSettingsTests(unittest.TestCase):
    def test_missing_or_unsupported_icon_style_defaults_to_battery(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "settings.json"
            with (
                patch("cyclone2tray.settings.settings_path", return_value=path),
                patch(
                    "cyclone2tray.settings._legacy_settings_path",
                    return_value=Path(temp_dir) / "legacy.json",
                ),
            ):
                for values in ({"alert_percent": 25}, {"icon_style": "invalid"}):
                    with self.subTest(values=values):
                        path.write_text(json.dumps(values), encoding="utf-8")
                        self.assertEqual(load_settings().icon_style, DEFAULT_ICON_STYLE)

    def test_supported_icon_style_is_loaded(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "settings.json"
            path.write_text(json.dumps({"icon_style": "outline"}), encoding="utf-8")
            with (
                patch("cyclone2tray.settings.settings_path", return_value=path),
                patch(
                    "cyclone2tray.settings._legacy_settings_path",
                    return_value=Path(temp_dir) / "legacy.json",
                ),
            ):
                self.assertEqual(load_settings().icon_style, "outline")

    def test_legacy_percent_style_is_migrated_to_outline(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "settings.json"
            path.write_text(json.dumps({"icon_style": "percent"}), encoding="utf-8")
            with (
                patch("cyclone2tray.settings.settings_path", return_value=path),
                patch(
                    "cyclone2tray.settings._legacy_settings_path",
                    return_value=Path(temp_dir) / "legacy.json",
                ),
            ):
                self.assertEqual(load_settings().icon_style, "outline")


if __name__ == "__main__":
    unittest.main()
