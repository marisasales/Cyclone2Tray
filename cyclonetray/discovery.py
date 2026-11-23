"""Enumeração e teste das coleções HID com VID da GameSir."""

import time
from dataclasses import dataclass, field

from .hidapi_loader import hid
from .protocol import (
    CYCLONE_PRODUCT_IDS,
    HEARTBEAT,
    HEARTBEAT_INTERVAL,
    REPORT_ID_INPUT,
    VENDOR_ID,
    BatteryReport,
    declares_vendor_channel,
    is_populated_report,
)


@dataclass
class Candidate:
    path: bytes
    product_id: int
    product: str
    usage_page: int
    usage: int
    interface: int
    release: int
    vendor_channel: bool = False
    cyclone_pid: bool = False

    @property
    def label(self) -> str:
        path = self.path.decode("utf-8", "replace") if isinstance(self.path, bytes) else str(self.path)
        return f"PID {self.product_id:04X} | iface {self.interface} | page {self.usage_page:04X} | {self.product!r} | {path}"

    @property
    def score(self) -> int:
        return (4 if self.vendor_channel else 0) + (2 if self.cyclone_pid else 0)


@dataclass
class ProbeResult:
    candidate: Candidate
    open_error: str | None = None
    read_error: str | None = None
    reports: dict[int, int] = field(default_factory=dict)
    populated: int = 0
    battery: BatteryReport | None = None
    raw_samples: list[bytes] = field(default_factory=list)

    @property
    def usable(self) -> bool:
        return self.populated > 0 and self.battery is not None


def enumerate_candidates() -> list[Candidate]:
    out: list[Candidate] = []
    for info in hid.enumerate(VENDOR_ID, 0):
        path = info.get("path")
        if not path:
            continue
        candidate = Candidate(
            path=path,
            product_id=info.get("product_id") or 0,
            product=info.get("product_string") or "",
            usage_page=info.get("usage_page") or 0,
            usage=info.get("usage") or 0,
            interface=info.get("interface_number") or -1,
            release=info.get("release_number") or 0,
            cyclone_pid=(info.get("product_id") or 0) in CYCLONE_PRODUCT_IDS,
        )
        try:
            with hid.Device(path=path) as device:
                candidate.vendor_channel = declares_vendor_channel(device.get_report_descriptor())
        except Exception:
            pass
        out.append(candidate)
    return sorted(out, key=lambda c: (-c.score, c.product_id, c.interface))


def probe_candidate(
    candidate: Candidate,
    duration: float = 1.6,
    heartbeat: bool = True,
) -> ProbeResult:
    """Abre uma coleção e verifica se nela chega o relatório 0x12 com bateria.

    Só envia o keep-alive 0F F2 quando a coleção declara os report IDs da família
    GameSir; nunca envia comandos de configuração ou escrita de registro.
    """
    result = ProbeResult(candidate=candidate)
    try:
        device = hid.Device(path=candidate.path)
    except Exception as exc:
        result.open_error = str(exc)
        return result

    deadline = time.monotonic() + duration
    last_heartbeat = 0.0
    try:
        while time.monotonic() < deadline:
            now = time.monotonic()
            if heartbeat and candidate.vendor_channel and now - last_heartbeat >= HEARTBEAT_INTERVAL:
                try:
                    device.write(HEARTBEAT)
                except Exception as exc:
                    result.read_error = f"heartbeat: {exc}"
                last_heartbeat = now
            try:
                data = device.read(64, timeout=50)
            except Exception as exc:
                result.read_error = str(exc)
                break
            if not data:
                continue
            report_id = data[0]
            result.reports[report_id] = result.reports.get(report_id, 0) + 1
            if report_id != REPORT_ID_INPUT:
                continue
            if len(result.raw_samples) < 2:
                result.raw_samples.append(data)
            if is_populated_report(data):
                result.populated += 1
                parsed = BatteryReport.from_report(data)
                if parsed is not None:
                    result.battery = parsed
    finally:
        try:
            device.close()
        except Exception:
            pass
    return result


def find_battery_device(duration: float = 1.6) -> ProbeResult | None:
    """Testa as coleções em ordem de probabilidade e devolve a que responde."""
    best: ProbeResult | None = None
    for candidate in enumerate_candidates():
        result = probe_candidate(candidate, duration=duration)
        if result.usable:
            return result
        if best is None and result.populated:
            best = result
    return best
