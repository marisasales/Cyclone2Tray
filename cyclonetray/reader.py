"""Leitura contínua do relatório 0x12 com reconexão automática."""

import threading
import time
from dataclasses import dataclass

from .discovery import find_battery_device, enumerate_candidates, probe_candidate
from .hidapi_loader import hid
from .protocol import (
    HEARTBEAT,
    HEARTBEAT_INTERVAL,
    REPORT_ID_INPUT,
    BatteryReport,
    is_populated_report,
)

STALE_AFTER = 5.0
READ_TIMEOUT_MS = 100


@dataclass
class BatteryStatus:
    percent: int | None = None
    charging: bool = False
    updated_at: float | None = None
    connected: bool = False
    device: str = ""
    last_error: str = ""
    raw_percent: int | None = None
    raw_status: int | None = None

    @property
    def age(self) -> float | None:
        return None if self.updated_at is None else time.time() - self.updated_at


class BatteryReader:
    """Um único handle HID, um único thread: heartbeat + leitura."""

    def __init__(self, saved_path: bytes | None = None, on_update=None):
        self.saved_path = saved_path
        self.on_update = on_update
        self.status = BatteryStatus()
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._rediscover = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is None:
            self._stop.clear()
            self._thread = threading.Thread(target=self._run, daemon=True, name="hid-reader")
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None

    def rediscover(self) -> None:
        self._rediscover.set()

    def _publish(self, **changes) -> None:
        with self._lock:
            for key, value in changes.items():
                setattr(self.status, key, value)
            snapshot = BatteryStatus(**self.status.__dict__)
        if self.on_update:
            self.on_update(snapshot)

    def snapshot(self) -> BatteryStatus:
        with self._lock:
            return BatteryStatus(**self.status.__dict__)

    def _open_saved(self):
        if not self.saved_path:
            return None
        for candidate in enumerate_candidates():
            if candidate.path != self.saved_path:
                continue
            result = probe_candidate(candidate, duration=0.8)
            if result.usable:
                return candidate, result.battery
            break
        return None

    def _discover(self):
        found = self._open_saved()
        return found or self._discover_all()

    @staticmethod
    def _discover_all():
        result = find_battery_device()
        if result is None or result.battery is None:
            return None
        return result.candidate, result.battery

    def _run(self) -> None:
        while not self._stop.is_set():
            self._rediscover.clear()
            self._publish(connected=False, last_error="")
            found = self._discover()
            if found is None:
                self._publish(last_error="Controle não encontrado no dongle (modo XInput).")
                if self._stop.wait(2):
                    return
                continue

            candidate, battery = found
            self.saved_path = candidate.path
            self._apply(battery, self._mode_name(candidate))
            try:
                self._stream(candidate)
            except Exception as exc:
                self._publish(connected=False, last_error=str(exc))
            if not self._stop.is_set():
                if self._stop.wait(0.5):
                    return

    def _stream(self, candidate) -> None:
        device = hid.Device(path=candidate.path)
        last_heartbeat = 0.0
        last_report = time.monotonic()
        try:
            while not self._stop.is_set() and not self._rediscover.is_set():
                now = time.monotonic()
                if now - last_heartbeat >= HEARTBEAT_INTERVAL:
                    device.write(HEARTBEAT)
                    last_heartbeat = now
                if now - last_report > STALE_AFTER:
                    self._publish(connected=False, last_error="Leitura parou; procurando novamente.")
                    return
                data = device.read(64, timeout=READ_TIMEOUT_MS)
                if not data or data[0] != REPORT_ID_INPUT:
                    continue
                if not is_populated_report(data):
                    continue
                battery = BatteryReport.from_report(data)
                if battery is None:
                    continue
                last_report = now
                self._apply(battery, self._mode_name(candidate))
        finally:
            try:
                device.close()
            except Exception:
                pass

    def _apply(self, battery: BatteryReport, label: str) -> None:
        self._publish(
            percent=battery.percent,
            charging=battery.charging,
            updated_at=time.time(),
            connected=True,
            device=label,
            last_error="",
            raw_percent=battery.raw_percent,
            raw_status=battery.raw_status,
        )

    @staticmethod
    def _mode_name(candidate) -> str:
        return candidate.product.strip() or "GameSir Cyclone 2"
