"""Ícone na system tray, alertas e menu."""

import datetime as dt
import threading
from typing import Callable

from PIL import Image, ImageDraw, ImageFont

from . import __version__
from .i18n import LANGUAGE_OPTIONS, SUPPORTED_LANGUAGES, translate
from .reader import BatteryReader, BatteryStatus
from .settings import (
    DEFAULT_ICON_STYLE,
    ICON_STYLES,
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
WHITE = (255, 255, 255, 255)
SHIMMER = (255, 255, 255, 64)
CHARGING_BRIGHT = (150, 255, 180, 255)
CHARGING_DIM = (62, 152, 92, 255)
PULSE_LIGHT = (235, 240, 245, 255)
PULSE_DARK = (110, 120, 130, 255)

CHARGING_FRAMES = 4
CHARGING_FRAME_SECONDS = 0.35


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


def _contrast_text(color: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    r, g, b = color[:3]
    luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
    black_contrast = (luminance + 0.05) / 0.05
    white_contrast = 1.05 / (luminance + 0.05)
    return TEXT if black_contrast >= white_contrast else WHITE


def _fit_font(
    draw: ImageDraw.ImageDraw,
    label: str,
    max_width: int = 60,
    sizes: tuple[int, ...] = (38, 34, 30, 26, 22),
):
    for size in sizes:
        font = _font(size)
        if draw.textbbox((0, 0), label, font=font)[2] <= max_width:
            return font
    return _font(sizes[-1])


def _outline_image(
    label: str,
    color: tuple[int, int, int, int],
    charging: bool,
    frame: int,
) -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Sem preenchimento: só o contorno da bateria; a cor fica no número.
    d.rounded_rectangle((1, 6, 57, 58), radius=10, outline=TEXT, width=3)
    d.rounded_rectangle(
        (58, 24, 63, 40), radius=3, fill=MUTED, outline=TEXT, width=1
    )

    font = _fit_font(d, label, 50, sizes=(46, 44, 42, 40, 38, 36, 34, 32, 30, 28))
    box = d.textbbox((0, 0), label, font=font)
    x = 29 - (box[2] - box[0]) / 2 - box[0]
    y = 32 - (box[3] - box[1]) / 2 - box[1]
    d.text(
        (x, y),
        label,
        font=font,
        fill=color,
        stroke_width=2,
        stroke_fill=TEXT,
    )

    if charging:
        pulse = PULSE_LIGHT if frame % 2 == 0 else PULSE_DARK
        start = 6 + (frame % CHARGING_FRAMES) * 12
        d.rounded_rectangle(
            (start, 49, min(start + 10, 53), 52), radius=2, fill=pulse
        )
    return img


def battery_image(
    percent: int | None,
    charging: bool,
    alert: int,
    connected: bool = True,
    style: str = DEFAULT_ICON_STYLE,
    frame: int = 0,
) -> Image.Image:
    known = percent is not None
    shown = min(100, max(0, percent or 0))
    color = level_color(shown, alert) if known and connected else MUTED
    label = str(shown) if known else "--"

    if style in ("outline", "percent"):
        # "percent" é o nome antigo da opção, mantido para perfis salvos.
        return _outline_image(label, color, charging and connected, frame)

    # Corpo preenchido pela cor do nível; o texto usa preto ou branco,
    # conforme o maior contraste com essa cor.
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((1, 6, 57, 58), radius=10, fill=color, outline=TEXT, width=3)

    if charging and connected and shown > 0:
        # Brilho móvel sobre o preenchimento, desenhado antes do número.
        x = 5 + (frame % CHARGING_FRAMES) * 12
        right = min(x + 8, 53)
        if right > x + 1:
            overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
            ImageDraw.Draw(overlay).rounded_rectangle(
                (x, 10, right, 54), radius=4, fill=SHIMMER
            )
            img = Image.alpha_composite(img, overlay)
            d = ImageDraw.Draw(img)

    terminal_color = color
    if charging and connected:
        terminal_color = CHARGING_BRIGHT if frame % 2 == 0 else CHARGING_DIM
    d.rounded_rectangle((58, 24, 63, 40), radius=3, fill=terminal_color,
                        outline=TEXT, width=1)

    font = _fit_font(d, label, 50, sizes=(46, 44, 42, 40, 38, 36, 34, 32, 30, 28))
    box = d.textbbox((0, 0), label, font=font)
    x = 29 - (box[2] - box[0]) / 2 - box[0]
    y = 32 - (box[3] - box[1]) / 2 - box[1]
    d.text((x, y), label, font=font, fill=_contrast_text(color))
    return img


class TrayController:
    def __init__(self):
        self.settings: Settings = load_settings()
        self.reader = BatteryReader(self.settings.device_path, on_update=self._on_update)
        self.icon = None
        self.status = BatteryStatus()
        self.low_alerted = False
        self.critical_alerted = False
        self._frame = 0
        self._stop_animation = threading.Event()

    def _on_update(self, status: BatteryStatus) -> None:
        menu_before = self._menu_signature(self.status)
        self.status = status
        if not (status.charging and status.connected):
            self._frame = 0
        if status.percent is not None and status.connected:
            self.settings.last_percent = status.percent
            self.settings.last_read_at = dt.datetime.now().isoformat(timespec="seconds")
        if status.connected and status.device:
            self.settings.device_path = self.reader.saved_path
        save_settings(self.settings)
        self._check_alerts(status)
        self._paint()
        if menu_before != self._menu_signature(status):
            self._update_menu()

    @staticmethod
    def _menu_signature(status: BatteryStatus) -> tuple:
        return (status.percent, status.charging, status.connected, status.device)

    def _update_menu(self) -> None:
        if self.icon is not None:
            try:
                self.icon.menu = self.build_menu()
            except Exception:
                pass

    def _check_alerts(self, status: BatteryStatus) -> None:
        if status.percent is None or not status.connected:
            return
        if status.charging or status.percent > self.settings.alert_percent + 5:
            self.low_alerted = self.critical_alerted = False
            return
        if status.percent <= self.settings.critical_percent and not self.critical_alerted:
            self.critical_alerted = self.low_alerted = True
            self._notify(
                translate(self.settings.language, "critical_title"),
                translate(
                    self.settings.language,
                    "critical_message",
                    percent=status.percent,
                ),
            )
        elif status.percent <= self.settings.alert_percent and not self.low_alerted:
            self.low_alerted = True
            self._notify(
                translate(self.settings.language, "low_title"),
                translate(
                    self.settings.language,
                    "low_message",
                    percent=status.percent,
                ),
            )

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
            style=self.settings.icon_style,
            frame=self._frame,
        )
        self.icon.title = self._title(shown)

    def _title(self, shown: int | None) -> str:
        if self.status.connected and shown is not None:
            if self.status.charging:
                return translate(self.settings.language, "status_charging")
            return translate(
                self.settings.language,
                "status_percent",
                percent=shown,
            )
        if shown is not None:
            return translate(
                self.settings.language,
                "status_last_reading",
                percent=shown,
            )
        return translate(self.settings.language, "status_waiting")

    def _status_text(self) -> str:
        s = self.status
        if s.connected and s.percent is not None:
            extra = translate(self.settings.language, "charging") if s.charging else ""
            return f"{s.percent}%{extra}"
        if s.percent is not None:
            return f"{s.percent}%{translate(self.settings.language, 'last_reading')}"
        return translate(self.settings.language, "no_reading")

    def _detail_text(self) -> str:
        s = self.status
        if s.connected:
            label = translate(self.settings.language, "dongle_connected")
        else:
            label = translate(self.settings.language, "dongle_disconnected")
        return f"{label} · {s.device}" if s.device else label

    def _set_alert(self, percent: int):
        def action(_icon, _item):
            self.settings.alert_percent = percent
            self.low_alerted = self.critical_alerted = False
            save_settings(self.settings)
            self._paint()
        return action

    def _alert_checked(self, percent: int) -> Callable:
        return lambda _item: self.settings.alert_percent == percent

    def _set_language(self, language: str):
        if language not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {language}")

        def action(_icon, _item):
            self.settings.language = language
            save_settings(self.settings)
            self._paint()
            self._update_menu()

        return action

    def _language_checked(self, language: str) -> Callable:
        return lambda _item: self.settings.language == language

    def _toggle_startup(self, _icon, _item) -> None:
        set_start_with_windows(not get_start_with_windows())
        self._update_menu()

    def _refresh(self, _icon, _item) -> None:
        self.reader.rediscover()

    def _animate_charging(self) -> None:
        while not self._stop_animation.wait(CHARGING_FRAME_SECONDS):
            if self.status.charging and self.status.connected:
                self._frame = (self._frame + 1) % CHARGING_FRAMES
                self._paint()

    def _set_icon_style(self, style: str):
        if style not in ICON_STYLES:
            raise ValueError(f"Unsupported icon style: {style}")

        def action(_icon, _item):
            self.settings.icon_style = style
            save_settings(self.settings)
            self._paint()
            self._update_menu()

        return action

    def _icon_style_checked(self, style: str) -> Callable:
        return lambda _item: self.settings.icon_style == style

    def _exit(self, _icon, _item) -> None:
        self._stop_animation.set()
        self.reader.stop()
        if self.icon is not None:
            self.icon.stop()

    def build_menu(self):
        from pystray import Menu, MenuItem

        alert_items = [
            MenuItem(f"{p}%", self._set_alert(p), checked=self._alert_checked(p),
                     radio=True)
            for p in (10, 15, 20, 25, 30)
        ]
        language_items = [
            MenuItem(
                name,
                self._set_language(code),
                checked=self._language_checked(code),
                radio=True,
            )
            for code, name in LANGUAGE_OPTIONS
        ]
        lang = self.settings.language
        style_items = [
            MenuItem(
                label,
                self._set_icon_style(code),
                checked=self._icon_style_checked(code),
                radio=True,
            )
            for code, label in (
                ("battery", translate(lang, "icon_battery")),
                ("outline", translate(lang, "icon_outline")),
            )
        ]
        return Menu(
            MenuItem(
                lambda _item: translate(
                    self.settings.language,
                    "battery",
                    value=self._status_text(),
                ),
                lambda *_: None,
                enabled=False,
            ),
            MenuItem(lambda _item: self._detail_text(), lambda *_: None, enabled=False),
            MenuItem(
                translate(
                    self.settings.language,
                    "app_version",
                    version=__version__,
                ),
                lambda *_: None,
                enabled=False,
            ),
            Menu.SEPARATOR,
            MenuItem(translate(self.settings.language, "refresh"), self._refresh),
            MenuItem(translate(self.settings.language, "alert_at"), Menu(*alert_items)),
            MenuItem(translate(self.settings.language, "startup"), self._toggle_startup,
                     checked=lambda _item: get_start_with_windows()),
            MenuItem(
                translate(self.settings.language, "language"),
                Menu(*language_items),
            ),
            MenuItem(translate(lang, "icon_style"), Menu(*style_items)),
            Menu.SEPARATOR,
            MenuItem(translate(self.settings.language, "exit"), self._exit),
        )

    def run(self) -> None:
        import pystray

        shown = self.settings.last_percent
        self.icon = pystray.Icon(
            "Cyclone2Tray",
            battery_image(
                shown,
                False,
                self.settings.alert_percent,
                connected=False,
                style=self.settings.icon_style,
            ),
            self._title(shown),
            self.build_menu(),
        )
        self.reader.start()
        self._stop_animation.clear()
        threading.Thread(
            target=self._animate_charging,
            name="cyclone-charging-animation",
            daemon=True,
        ).start()
        self.icon.run()
