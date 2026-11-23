# Cyclone2Tray

An unofficial battery monitor for the **GameSir Cyclone 2**. It reads the controller battery through the **2.4 GHz USB dongle** and displays the percentage in the Windows notification area—no Bluetooth or GameSir Connect required.

**Language:** English | [Português (Brasil)](README.pt-BR.md)

## Features

- Shows battery percentage with a colored tray icon.
- Indicates charging and disconnected states.
- Sends low-battery notifications.
- Rediscovers the controller and can start with Windows.
- Includes a command-line tool to inspect HID interfaces and reports.

The supported setup is the **Cyclone 2 connected through its dongle in XInput mode**. Other controllers, connection modes, and operating systems have not been validated. This repository does not include a packaged `.exe`; it runs with Python.

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
- Python 3.10 or newer. Verified with Python 3.15.2.
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

## Tray menu

Right-click the icon to see the current status and use these menu items:

- **Atualizar agora** (Refresh now): search for the device again.
- **Alerta em** (Alert at): choose 10%, 15%, 20%, 25%, or 30% (default: 20%; critical alert: 10%).
- **Iniciar com Windows** (Start with Windows): toggle startup for the current user.
- **Sair** (Exit): stop the monitor.

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

## Credits and references

- [broroeror/gamesir-linux-tools](https://github.com/broroeror/gamesir-linux-tools) — primary reference for the Cyclone 2 HID protocol research: vendor channel, report `0x12`, and keep-alive `0F F2`. The HID descriptor detection in `cyclone2tray/protocol.py` adapts the corresponding function from [`gs_common.py`](https://github.com/broroeror/gamesir-linux-tools/blob/main/gs_common.py). The source project is MIT; copyright for the adapted portion: © 2026 broroeror ([upstream license](https://github.com/broroeror/gamesir-linux-tools/blob/main/LICENSE)).
- [bpbp-boop/GameSirBattery](https://github.com/bpbp-boop/GameSirBattery) — UX reference for the tray icon, alerts, settings, and Windows startup. That project reads the Cyclone Pro (T4cp) over BLE; its protocol is **not** used to read the Cyclone 2 here.
- [pyhidapi (`hid`)](https://github.com/apmorton/pyhidapi) and [hidapi](https://github.com/libusb/hidapi) — Python HID access and the Windows DLL. The included DLL is version 0.15.0; see `vendor/HIDAPI-LICENSE.txt` and the [upstream project](https://github.com/libusb/hidapi).
- [pystray](https://github.com/moses-palmer/pystray) — tray icon and menu.
- [Pillow](https://python-pillow.org/) — icon drawing. Its visual style references Material Symbols Rounded; no external glyph or font file is distributed.

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
