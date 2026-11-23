"""Diagnóstico: descobre qual coleção HID do dongle entrega a bateria."""

import argparse
import datetime as dt
import json
import sys
import time

from cyclonetray.discovery import enumerate_candidates, probe_candidate
from cyclonetray.hidapi_loader import hid
from cyclonetray.protocol import (
    BATTERY_BYTE,
    CHARGING_BYTE,
    HEARTBEAT,
    HEARTBEAT_INTERVAL,
    REPORT_ID_INPUT,
    BatteryReport,
    is_populated_report,
)
from cyclonetray.settings import load_settings, save_settings


def watch(candidates, heartbeat: bool = True) -> int:
    target = next((c for c in candidates if c.vendor_channel), None)
    if target is None:
        print("Nenhuma coleção declara os report IDs vendor (0F/10/12).")
        return 1
    print(f"Observando: {target.label}\nLigue/desligue o controle e compare com o GameSir Connect.")
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
                value = f"{reading.percent}% carregando={reading.charging}"
            else:
                value = "sem leitura (controle desligado/dormindo)"
            print(f"{stamp} {value} | byte35={key[1]!r} byte36={key[2]!r} "
                  f"populado={populated} tamanho={key[0]}", flush=True)
    except KeyboardInterrupt:
        return 0
    finally:
        device.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, default=1.6,
                        help="duração do teste por coleção HID")
    parser.add_argument("--no-heartbeat", action="store_true",
                        help="não enviar o keep-alive 0F F2")
    parser.add_argument("--save", action="store_true",
                        help="salvar a coleção encontrada para o app da tray")
    parser.add_argument("--json", action="store_true", help="saída em JSON")
    parser.add_argument("--watch", action="store_true",
                        help="monitora a coleção vendor continuamente (Ctrl+C para sair)")
    args = parser.parse_args()

    candidates = enumerate_candidates()
    if not candidates:
        print("Nenhum dispositivo HID com VID 3537 encontrado.")
        print("Verifique: dongle conectado, controle ligado no modo 2.4 GHz / XInput (LED verde).")
        return 1

    if args.watch:
        return watch(candidates, heartbeat=not args.no_heartbeat)

    results = []
    for index, candidate in enumerate(candidates, 1):
        if not args.json:
            print(f"\n[{index}] {candidate.label}")
            print(f"    usage={candidate.usage:04X} fw={candidate.release / 256:.2f} "
                  f"canal_vendor={'sim' if candidate.vendor_channel else 'nao'}")
        result = probe_candidate(candidate, duration=args.seconds,
                                 heartbeat=not args.no_heartbeat)
        results.append(result)
        if args.json:
            continue
        reports = ", ".join(f"id {k:02X}: {v}" for k, v in sorted(result.reports.items())) or "nenhum"
        print(f"    relatorios: {reports}")
        if result.open_error:
            print(f"    erro ao abrir: {result.open_error}")
        if result.read_error:
            print(f"    erro ao ler: {result.read_error}")
        if result.battery:
            b = result.battery
            print(f"    BATERIA: {b.percent}% carregando={b.charging} "
                  f"(byte35={b.raw_status:#04x}, byte36={b.raw_percent:#04x})")
        for sample in result.raw_samples:
            byte35 = sample[CHARGING_BYTE] if len(sample) > CHARGING_BYTE else None
            byte36 = sample[BATTERY_BYTE] if len(sample) > BATTERY_BYTE else None
            print(f"    amostra 0x12: {sample.hex(' ')}")
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
        print("\n=== Resultado ===")
        if usable:
            for r in usable:
                print(f"OK: {r.candidate.label}")
        else:
            print("Nenhuma coleção entregou 0x12 com bateria.")
            print("Tente: fechar o GameSir Connect, ligar o controle, conferir modo XInput.")

    if args.save and usable:
        settings = load_settings()
        settings.device_path = usable[0].candidate.path
        save_settings(settings)
        print("Coleção salva em settings.json")

    return 0 if usable else 2


if __name__ == "__main__":
    sys.exit(main())
