"""Diagnose which HID collection on the dongle provides battery data."""

import argparse
import datetime as dt
import json
import sys
import time

from cyclone2tray.discovery import enumerate_candidates, probe_candidate
from cyclone2tray.hidapi_loader import hid
from cyclone2tray.protocol import (
    BATTERY_BYTE,
    CHARGING_BYTE,
    HEARTBEAT,
    HEARTBEAT_INTERVAL,
    REPORT_ID_INPUT,
    BatteryReport,
    is_populated_report,
)
from cyclone2tray.settings import load_settings, save_settings


def watch(candidates, heartbeat: bool = True) -> int:
    target = next((c for c in candidates if c.vendor_channel), None)
    if target is None:
        print("No collection declares vendor report IDs (0F/10/12).")
        return 1
    print(f"Watching: {target.label}\nTurn the controller on/off and compare with GameSir Connect.")
    last = None
    last_heartbeat = 0.0
    device = hid.Device(path=target.path)
    try:
        while True:
            now = time.monotonic()
            if heartbeat and now - last_heartbeat >= HEARTBEAT_INTERVAL:
                device.write(HEARTBEAT)
                last_heartbeat = now
            data = device.read(64, timeout=100)
            if not data or data[0] != REPORT_ID_INPUT:
                continue
            populated = is_populated_report(data)
            key = (
                len(data),
                data[CHARGING_BYTE] if len(data) > CHARGING_BYTE else None,
                data[BATTERY_BYTE] if len(data) > BATTERY_BYTE else None,
                populated,
            )
            if key == last:
                continue
            last = key
            reading = BatteryReport.from_report(data) if populated else None
            stamp = dt.datetime.now().strftime("%H:%M:%S")
            if reading:
                value = f"{reading.percent}% charging={reading.charging}"
            else:
                value = "no reading (controller off/asleep)"
            print(f"{stamp} {value} | byte35={key[1]!r} byte36={key[2]!r} "
                  f"populated={populated} length={key[0]}", flush=True)
    except KeyboardInterrupt:
        return 0
    finally:
        device.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, default=1.6,
                        help="test duration per HID collection")
    parser.add_argument("--no-heartbeat", action="store_true",
                        help="do not send the 0F F2 keep-alive")
    parser.add_argument("--save", action="store_true",
                        help="save the discovered collection for the tray app")
    parser.add_argument("--json", action="store_true", help="print JSON output")
    parser.add_argument("--watch", action="store_true",
                        help="watch the vendor collection continuously (Ctrl+C to stop)")
    args = parser.parse_args()

    candidates = enumerate_candidates()
    if not candidates:
        print("No HID device with VID 3537 found.")
        print("Check that the dongle is connected and the controller is on in 2.4 GHz / XInput mode (green LED).")
        return 1

    if args.watch:
        return watch(candidates, heartbeat=not args.no_heartbeat)

    results = []
    for index, candidate in enumerate(candidates, 1):
        if not args.json:
            print(f"\n[{index}] {candidate.label}")
            print(f"    usage={candidate.usage:04X} fw={candidate.release / 256:.2f} "
                  f"vendor_channel={'yes' if candidate.vendor_channel else 'no'}")
        result = probe_candidate(candidate, duration=args.seconds,
                                 heartbeat=not args.no_heartbeat)
        results.append(result)
        if args.json:
            continue
        reports = ", ".join(f"id {k:02X}: {v}" for k, v in sorted(result.reports.items())) or "none"
        print(f"    reports: {reports}")
        if result.open_error:
            print(f"    open error: {result.open_error}")
        if result.read_error:
            print(f"    read error: {result.read_error}")
        if result.battery:
            b = result.battery
            print(f"    BATTERY: {b.percent}% charging={b.charging} "
                  f"(byte35={b.raw_status:#04x}, byte36={b.raw_percent:#04x})")
        for sample in result.raw_samples:
            byte35 = sample[CHARGING_BYTE] if len(sample) > CHARGING_BYTE else None
            byte36 = sample[BATTERY_BYTE] if len(sample) > BATTERY_BYTE else None
            print(f"    sample 0x12: {sample.hex(' ')}")
            print(f"    byte35={byte35!r} byte36={byte36!r} "
                  f"nonzero={sum(1 for b in sample[1:5] if b)}")

    usable = [r for r in results if r.usable]
    if args.json:
        print(json.dumps([
            {
                "path": r.candidate.path.hex(),
                "pid": r.candidate.product_id,
                "product": r.candidate.product,
                "vendor_channel": r.candidate.vendor_channel,
                "reports": {hex(k): v for k, v in r.reports.items()},
                "battery": (
                    {"percent": r.battery.percent, "charging": r.battery.charging,
                     "byte35": r.battery.raw_status, "byte36": r.battery.raw_percent}
                    if r.battery else None
                ),
                "usable": r.usable,
                "raw_samples": [sample.hex() for sample in r.raw_samples],
                "error": r.open_error or r.read_error,
            }
            for r in results
        ], indent=2, ensure_ascii=False))
    else:
        print("\n=== Result ===")
        if usable:
            for r in usable:
                print(f"OK: {r.candidate.label}")
        else:
            print("No collection returned a populated 0x12 battery report.")
            print("Try closing GameSir Connect, waking the controller, and checking XInput mode.")

    if args.save and usable:
        settings = load_settings()
        settings.device_path = usable[0].candidate.path
        save_settings(settings)
        print("Collection saved to settings.json")

    return 0 if usable else 2


if __name__ == "__main__":
    sys.exit(main())
