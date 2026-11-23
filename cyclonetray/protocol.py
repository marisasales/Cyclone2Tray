"""Protocolo HID do Cyclone 2 no modo XInput.

Mapeamento validado em hardware em 2026-11-23: VID 3537 / PID 100B / MI 01 /
Col04 (Usage Page FFF0, fw 1.13), dongle 2.4 GHz, Windows 11.
"""

from dataclasses import dataclass

VENDOR_ID = 0x3537
CYCLONE_PRODUCT_IDS = {0x0575, 0x100B, 0x1053}

REPORT_ID_INPUT = 0x12
REPORT_ID_COMMAND = 0x0F
REPORT_LEN = 64
HEARTBEAT_INTERVAL = 0.4
HEARTBEAT = bytes([REPORT_ID_COMMAND, 0xF2]) + bytes(REPORT_LEN - 2)

# Confirmado no hardware: 0x64 (100) no byte 36; byte 35 alterna 0x00 -> 0x01
# quando o controle entra no carregamento.
BATTERY_BYTE = 36
CHARGING_BYTE = 35
CHARGING_MASK = 0x01


@dataclass(frozen=True)
class BatteryReport:
    percent: int
    charging: bool
    raw_percent: int
    raw_status: int

    @classmethod
    def from_report(cls, data: bytes) -> "BatteryReport | None":
        if len(data) <= BATTERY_BYTE or data[0] != REPORT_ID_INPUT:
            return None
        raw_percent = data[BATTERY_BYTE]
        raw_status = data[CHARGING_BYTE]
        charging = bool(raw_status & CHARGING_MASK)
        # No relatório 0x12 o byte 36 é a porcentagem. 0xFF aparece em alguns
        # firmwares como "carregando"; não é uma porcentagem válida.
        if raw_percent == 0xFF:
            return cls(100, True, raw_percent, raw_status)
        if raw_percent > 100:
            return None
        return cls(raw_percent, charging, raw_percent, raw_status)


def is_populated_report(data: bytes) -> bool:
    """Distingue o stream real do stream zerado de um dongle sem controle."""
    return (
        len(data) > BATTERY_BYTE
        and data[0] == REPORT_ID_INPUT
        and any(data[1:5])
    )


def declares_vendor_channel(descriptor: bytes) -> bool:
    """Detecta report IDs 0x0F/0x10/0x12 sob um Usage Page vendor-defined."""
    vendor_page = False
    i = 0
    while i < len(descriptor):
        prefix = descriptor[i]
        if prefix == 0xFE:  # item longo
            if i + 1 >= len(descriptor):
                break
            i += 3 + descriptor[i + 1]
            continue
        size = prefix & 0x03
        if size == 3:
            size = 4
        if i + 1 + size > len(descriptor):
            break
        value = int.from_bytes(descriptor[i + 1:i + 1 + size], "little")
        tag = prefix & 0xFC
        if tag == 0x04:  # Usage Page
            vendor_page = value >= 0xFF00
        elif tag == 0x84 and vendor_page and value in (0x0F, 0x10, 0x12):
            return True
        i += 1 + size
    return False
