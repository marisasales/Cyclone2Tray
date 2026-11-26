<h1 align="center">Cyclone2Tray</h1>

<p align="center">
  <img src="assets/app.png" alt="Cyclone2Tray app icon" title="Cyclone2Tray portable battery monitor" width="180">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-0.2.0-blue" alt="Version 0.2.0" title="Cyclone2Tray app version 0.2.0">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB" alt="Python 3.10+" title="Requires Python 3.10 or newer; tested with 3.15.2">
  <img src="https://img.shields.io/badge/platform-Windows%2011-0078D4" alt="Windows 11" title="Validated on Windows 11">
  <img src="https://img.shields.io/badge/controller-GameSir%20Cyclone%202-333333" alt="GameSir Cyclone 2" title="Designed for GameSir Cyclone 2 over its 2.4 GHz dongle">
</p>

An unofficial battery monitor for the **GameSir Cyclone 2**. It reads the controller battery through the **2.4 GHz USB dongle** and displays the percentage in the Windows notification area—no Bluetooth or GameSir Connect required.

**Language:** English | [Português (Brasil)](README.pt-BR.md)

## Features

- Shows battery percentage with a large, high-contrast number in two icon styles: filled battery or battery outline (only the number is colored).
- Colors the icon (or only the number in outline style) by charge level (green, amber, red) and animates it while charging.
- Indicates charging and disconnected states.
- Sends low-battery notifications.
- Rediscovers the controller and can start with Windows.
- Offers English (default), Portuguese, and Spanish; the selection is saved.
- Includes a command-line tool to inspect HID interfaces and reports.

The supported setup is the **Cyclone 2 connected through its dongle in XInput mode**. Other controllers, connection modes, and operating systems have not been validated. The source runs with Python; the portable Windows package bundles its own Python runtime.

## How it works

The dongle and controller expose HID interfaces to Windows. Cyclone2Tray discovers the appropriate vendor collection and keeps its data stream active by sending the `0F F2` keep-alive about every 0.4 seconds. Battery data arrives in the 64-byte input report `0x12`:

| Field | Meaning |
| --- | --- |
| Byte 36 | Battery percentage, 0–100 |
| Byte 35, bit 0 | `1` while charging |

This mapping was verified on Windows 11 with a Cyclone 2 running firmware 1.13 (VID `3537`, PID `100B`, collection `Col04`). Discovery also considers PIDs `0575` and `1053`, which may appear in other states or revisions.

> [!NOTE]
> The application does not use Bluetooth or write configuration, registers, or firmware. Its only HID write is the keep-alive needed to receive reports; all other communication is read-only.
>
> A compatibility fallback treats byte 36 value `0xFF` as 100% and charging. This behavior comes from protocol research and was not observed with the verified firmware 1.13 setup.

## Requirements

- Windows 11.
- GameSir Cyclone 2 and its 2.4 GHz dongle; controller on in XInput mode (green LED).
- Python 3.10 or newer to run from source or build the package. Verified with Python 3.15.2.
- `vendor/hidapi.dll`, included in this repository.

No .NET SDK or native extension compiler is required.

## Install and run

1. Download or clone the repository, then open PowerShell in its root folder.
2. Create a Python virtual environment and install dependencies:

   ```powershell
   py -3 -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

3. Connect the dongle, turn on the controller in XInput mode, and close **GameSir Connect** if it is running (it may hold the HID interface).
4. Run the diagnostic:

   ```powershell
   .\diagnostics.bat
   ```

   If the output shows `BATTERY: NN%`, save the discovered collection to speed up future startup:

   ```powershell
   .\diagnostics.bat --save
   ```

   Saving the path is optional; automatic discovery remains enabled.

5. Start the tray monitor:

   ```powershell
   .\start-monitor.bat
   ```

Windows may place the icon in the hidden notification area. Click the `^` arrow next to the clock to find it.

## Build Windows packages

From the project root on Windows, install the runtime and build dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-build.txt
.\build.bat
```

Place the EXE icon image at `assets\app.png`; the build converts it to a multi-size Windows icon automatically.

The build produces `dist\Cyclone2Tray-portable.zip`. Extract it and run `Cyclone2Tray.exe`; keep the whole `Cyclone2Tray` folder together because it contains the Python runtime, `hidapi.dll`, and its license. No installation or administrator approval is required. The packaged app itself does not require Python or the .NET SDK.

## Privacy and data

- The application does not send telemetry or make network requests.
- It reads only the Cyclone 2 HID reports and sends the `0F F2` keep-alive.
- It stores preferences under `%LOCALAPPDATA%\Cyclone2Tray\settings.json`.
- It optionally writes the startup command under `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`.
- No passwords, tokens, or other credentials are stored by the application.

## Tray menu

The interface defaults to English. Right-click the icon to see the battery status, connection details, and app version:

- **Refresh now**: search for the device again.
- **Alert at**: choose 10%, 15%, 20%, 25%, or 30% (default: 20%; critical alert: 10%).
- **Start with Windows**: toggle startup for the current user.
- **Language**: choose English (default), Português, or Español; the selection is saved in settings.
- **Icon style**: choose **Battery icon** (filled with the charge color) or **Empty battery** (outline only, charge color on the number); the selection is saved in settings.
- **Exit**: stop the monitor.

Alerts reset when charging starts or when the battery rises at least 5 percentage points above the alert threshold. Settings are stored in `%LOCALAPPDATA%\Cyclone2Tray\settings.json`. Existing settings under `%LOCALAPPDATA%\CycloneTray\settings.json` are read as a fallback. Startup uses the `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` registry key.

## Diagnostics

`diagnostics.bat` accepts these arguments:

| Command | Purpose |
| --- | --- |
| `.\diagnostics.bat --seconds 3` | Test each HID collection for 3 seconds |
| `.\diagnostics.bat --save` | Test collections and save the one returning battery data |
| `.\diagnostics.bat --json` | Print results as JSON |
| `.\diagnostics.bat --watch` | Watch for changes continuously; stop with `Ctrl+C` |
| `.\diagnostics.bat --no-heartbeat` | Test without sending the keep-alive (for investigation) |

In `--watch` mode, byte 35 and byte 36 are printed when they change. If the controller is off or asleep, no battery reading is expected.

## Troubleshooting

- **No HID device or collection found:** check that the dongle is connected and the controller is on in 2.4 GHz/XInput mode.
- **The dongle is listed, but no `BATTERY` reading appears:** close GameSir Connect, wake the controller, and run `.\diagnostics.bat --watch`.
- **The tray icon is missing:** check the hidden notification area using the `^` arrow.
- **A `.bat` file does not start:** run it from the project root and confirm `.venv\Scripts\python.exe` and `.venv\Scripts\pythonw.exe` exist.
- **Readings differ on another firmware:** inspect the raw `0x12` report with the diagnostic tool; the mapping above was verified with firmware 1.13.

## Project layout

- `cyclone2tray/protocol.py`: HID identifiers and battery report parsing.
- `cyclone2tray/discovery.py` and `reader.py`: device discovery, reading, and reconnection.
- `cyclone2tray/tray.py`: tray icon, menu, and alerts.
- `cyclone2tray/settings.py`: preferences and Windows startup.
- `probe.py`: diagnostic tool.
- `vendor/hidapi.dll`: HID library for Windows.
- `diagnostics.bat` and `start-monitor.bat`: diagnostic and launch shortcuts.
- `build.bat`: Windows portable-package build script.

## Credits and references

- [broroeror/gamesir-linux-tools](https://github.com/broroeror/gamesir-linux-tools) — primary reference for the Cyclone 2 HID protocol research: vendor channel, report `0x12`, and keep-alive `0F F2`. The HID descriptor detection in `cyclone2tray/protocol.py` adapts the corresponding function from [`gs_common.py`](https://github.com/broroeror/gamesir-linux-tools/blob/main/gs_common.py). The source project is MIT; copyright for the adapted portion: © 2026 broroeror ([upstream license](https://github.com/broroeror/gamesir-linux-tools/blob/main/LICENSE)).
- [bpbp-boop/GameSirBattery](https://github.com/bpbp-boop/GameSirBattery) — UX reference for the tray icon, alerts, settings, and Windows startup. That project reads the Cyclone Pro (T4cp) over BLE; its protocol is **not** used to read the Cyclone 2 here.
- [pyhidapi (`hid`)](https://github.com/apmorton/pyhidapi) and [hidapi](https://github.com/libusb/hidapi) — Python HID access and the Windows DLL. The included DLL is version 0.15.0; see `vendor/HIDAPI-LICENSE.txt` and the [upstream project](https://github.com/libusb/hidapi).
- [pystray](https://github.com/moses-palmer/pystray) — tray icon and menu.
- [Pillow](https://python-pillow.org/) — icon drawing. Its battery shape references Material Symbols Rounded; bold text uses Segoe UI Bold when available. No external font file is distributed.

<details>
<summary>MIT notice for the adapted gamesir-linux-tools code</summary>

Copyright (c) 2026 broroeror

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

</details>
