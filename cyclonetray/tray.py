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

GREEN = (72, 255, 112, 255)
AMBER = (255, 190, 48, 255)
RED = (255, 82, 82, 255)
MUTED = (174, 184, 198, 255)
TEXT = (18, 22, 29, 255)


def _font(size: int):
    bold_font = r"C:\Windows\Fonts\segoeuib.ttf"
    try:
        return ImageFont.truetype(bold_font, size=size)
    except OSError:
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


def battery_image(
    percent: int | None,
    charging: bool,
    alert: int,
    connected: bool = True,
) -> Image.Image:
    # Material Symbols Rounded-style horizontal battery, composed at 64px so
    # Windows can downsample it cleanly for the notification area.
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    known = percent is not None
    shown = min(100, max(0, percent or 0))
    color = level_color(shown, alert) if known and connected else MUTED

    d.rounded_rectangle((2, 11, 55, 53), radius=10, fill=color, outline=TEXT, width=2)
    terminal_color = GREEN if charging and connected else color
    d.rounded_rectangle((56, 22, 63, 42), radius=4, fill=terminal_color, outline=TEXT, width=2)
    label = str(shown) if known else "--"
    font = _font(28 if len(label) <= 2 else 30)
    box = d.textbbox((0, 0), label, font=font)
    x = (55 - (box[2] - box[0])) / 2 + 2 - box[0]
    y = (64 - (box[3] - box[1])) / 2 - box[1]
    d.text((x, y), label, font=font, fill=TEXT)
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
        self.icon.icon = battery_image(
            shown,
            bool(self.status.charging and self.status.connected),
            self.settings.alert_percent,
            connected=self.status.connected,
        )
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
            battery_image(shown, False, self.settings.alert_percent, connected=False),
            self._title(shown),
            self.build_menu(),
        )
        self.reader.start()
        self.icon.run()
