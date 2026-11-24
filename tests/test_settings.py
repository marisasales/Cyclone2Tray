import unittest
from pathlib import Path

from cyclone2tray.settings import _startup_command


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


if __name__ == "__main__":
    unittest.main()
