"""Ícone na system tray, alertas e menu."""

import datetime as dt
import time
from typing import Callable

from PIL import Image, ImageDraw, ImageFont

from .reader import BatteryReader, BatteryStatus
from .settings import (
    Settings,
    get_start_with_windows,
    load_settings,
    save_settings,
    set_start_with_windows,
)

GREEN = (22, 163, 74, 255)
AMBER = (224, 138, 0, 255)
RED = (220, 38, 38, 255)
FG = (255, 255, 255, 255)
MUTED = (170, 170, 170, 255)


def _font(size: int):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def level_color(percent: int, alert: int) -> tuple[int, int, int, int]:
    if percent <= alert:
        return RED
    if percent <= 40:
        return AMBER
    return GREEN


def icon_image(percent: int | None, charging: bool, alert: int) -> Image.Image:
    s = 64
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    if percent is None:
        d.rounded_rectangle((5, 18, 50, 46), radius=7, outline=MUTED, width=4)
        d.rectangle((53, 27, 58, 37), fill=MUTED)
        d.line((15, 32, 40, 32), fill=MUTED, width=4)
        return img

    color = level_color(percent, alert)
    d.rounded_rectangle((4, 13, 52, 51), radius=8, outline=FG, width=4)
    d.rounded_rectangle((55, 25, 61, 39), radius=2, fill=FG)
    fill_w = max(3, int(43 * min(100, max(0, percent)) / 100))
    d.rounded_rectangle((8, 17, 8 + fill_w, 47), radius=3, fill=color)

    if charging:
        d.polygon([(34, 17), (20, 36), (30, 36), (27, 49), (44, 29), (34, 29)], fill=GREEN)
    else:
        label = str(percent)
        font = _font(27 if len(label) < 3 else 22)
        box = d.textbbox((0, 0), label, font=font)
        x = 28 - (box[2] - box[0]) / 2
        y = 32 - (box[3] - box[1]) / 2 - 2
        d.text((x, y), label, font=font, fill=FG)
    return img


class TrayController:
    def __init__(self):
        self.settings: Settings = load_settings()
        self.reader = BatteryReader(self.settings.device_path, on_update=self._on_update)
        self.icon = None
        self.status = BatteryStatus()
        self.low_alerted = False
        self.critical_alerted = False

    def _on_update(self, status: BatteryStatus) -> None:
        self.status = status
        if status.percent is not None and status.connected:
            self.settings.last_percent = status.percent
            self.settings.last_read_at = dt.datetime.now().isoformat(timespec="seconds")
        if status.connected and status.device:
            self.settings.device_path = self.reader.saved_path
        save_settings(self.settings)
        self._check_alerts(status)
        self._paint()

    def _check_alerts(self, status: BatteryStatus) -> None:
        if status.percent is None or not status.connected:
            return
        if status.charging or status.percent > self.settings.alert_percent + 5:
            self.low_alerted = self.critical_alerted = False
            return
        if status.percent <= self.settings.critical_percent and not self.critical_alerted:
            self.critical_alerted = self.low_alerted = True
            self._notify("Bateria crítica", f"Cyclone 2 em {status.percent}%. Conecte o carregador.")
        elif status.percent <= self.settings.alert_percent and not self.low_alerted:
            self.low_alerted = True
            self._notify("Bateria baixa", f"Cyclone 2 em {status.percent}%.")

    def _notify(self, title: str, message: str) -> None:
        if self.icon is not None:
            try:
                self.icon.notify(message, title)
            except Exception:
                pass

    def _paint(self) -> None:
        if self.icon is None:
            return
        shown = self.status.percent if self.status.connected else self.settings.last_percent
        self.icon.icon = icon_image(shown, bool(self.status.charging and self.status.connected),
                                    self.settings.alert_percent)
        self.icon.title = self._title(shown)

    def _title(self, shown: int | None) -> str:
        if self.status.connected and shown is not None:
            state = "carregando" if self.status.charging else f"{shown}%"
            return f"Cyclone 2: {state}"
        if shown is not None:
            return f"Cyclone 2: {shown}% (última leitura)"
        return "Cyclone 2: aguardando controle"

    def _status_text(self) -> str:
        s = self.status
        if s.connected and s.percent is not None:
            extra = " · carregando" if s.charging else ""
            return f"{s.percent}%{extra}"
        if s.percent is not None:
            return f"{s.percent}% (última leitura)"
        return "Sem leitura"

    def _detail_text(self) -> str:
        s = self.status
        if s.connected:
            return f"Dongle conectado · {s.device}"
        if s.last_error:
            return s.last_error
        return "Ligue o controle no modo 2.4 GHz / XInput"

    def _set_alert(self, percent: int):
        def action(_icon, _item):
            self.settings.alert_percent = percent
            self.low_alerted = self.critical_alerted = False
            save_settings(self.settings)
            self._paint()
        return action

    def _alert_checked(self, percent: int) -> Callable:
        return lambda _item: self.settings.alert_percent == percent

    def _toggle_startup(self, _icon, _item) -> None:
        set_start_with_windows(not get_start_with_windows())
        self.icon.update_menu()

    def _refresh(self, _icon, _item) -> None:
        self.reader.rediscover()

    def _exit(self, _icon, _item) -> None:
        self.reader.stop()
        self.icon.stop()

    def build_menu(self):
        from pystray import Menu, MenuItem

        alert_items = [
            MenuItem(f"{p}%", self._set_alert(p), checked=self._alert_checked(p),
                     radio=True)
            for p in (10, 15, 20, 25, 30)
        ]
        return Menu(
            MenuItem(lambda _item: "Bateria: " + self._status_text(), lambda *_: None, enabled=False),
            MenuItem(lambda _item: self._detail_text(), lambda *_: None, enabled=False),
            Menu.SEPARATOR,
            MenuItem("Atualizar agora", self._refresh),
            MenuItem("Alerta em", Menu(*alert_items)),
            MenuItem("Iniciar com Windows", self._toggle_startup,
                     checked=lambda _item: get_start_with_windows()),
            MenuItem("Sair", self._exit),
        )

    def run(self) -> None:
        import pystray

        shown = self.settings.last_percent
        self.icon = pystray.Icon(
            "CycloneTray",
            icon_image(shown, False, self.settings.alert_percent),
            self._title(shown),
            self.build_menu(),
        )
        self.reader.start()
        self.icon.run()
