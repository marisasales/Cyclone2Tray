import unittest
from unittest.mock import Mock, patch

from cyclone2tray import __version__
from cyclone2tray.reader import BatteryStatus
from cyclone2tray.settings import Settings
from cyclone2tray.tray import (
    GREEN,
    RED,
    TEXT,
    WHITE,
    TrayController,
    _contrast_text,
    battery_image,
)


class TrayMenuVersionTests(unittest.TestCase):
    def test_context_menu_shows_app_version_as_informational_item(self):
        controller = TrayController.__new__(TrayController)
        controller.settings = Settings(language="pt-BR")
        menu = controller.build_menu()
        version_item = menu.items[2]

        self.assertEqual(version_item.text, f"Versão do app: {__version__}")
        self.assertFalse(version_item.enabled)


class TrayLanguageTests(unittest.TestCase):
    def test_selecting_language_persists_and_refreshes_the_tray(self):
        controller = TrayController.__new__(TrayController)
        controller.settings = Settings()
        controller._paint = Mock()
        controller.icon = Mock()

        with patch("cyclone2tray.tray.save_settings") as save_settings:
            controller._set_language("es")(None, None)

        self.assertEqual(controller.settings.language, "es")
        save_settings.assert_called_once_with(controller.settings)
        controller._paint.assert_called_once_with()
        self.assertEqual(controller.icon.menu.items[7].text, "Idioma")

    def test_selecting_unsupported_language_fails(self):
        controller = TrayController.__new__(TrayController)
        controller.settings = Settings()

        with self.assertRaises(ValueError):
            controller._set_language("fr")

        self.assertEqual(controller.settings.language, "en")

    def test_tray_title_uses_selected_language(self):
        controller = TrayController.__new__(TrayController)
        controller.settings = Settings()
        controller.status = BatteryStatus()

        for language, expected in (
            ("en", "Cyclone 2: waiting for controller"),
            ("pt-BR", "Cyclone 2: aguardando controle"),
            ("es", "Cyclone 2: esperando el control"),
        ):
            with self.subTest(language=language):
                controller.settings.language = language
                self.assertEqual(controller._title(None), expected)


class TrayIconStyleTests(unittest.TestCase):
    def test_battery_and_outline_styles_render_different_images(self):
        battery = battery_image(85, False, 20, style="battery")
        outline = battery_image(85, False, 20, style="outline")

        self.assertNotEqual(battery.tobytes(), outline.tobytes())

    def test_outline_style_uses_color_by_charge_level(self):
        low = battery_image(10, False, 20, style="outline")
        high = battery_image(90, False, 20, style="outline")

        self.assertIn(RED, {color for _, color in low.getcolors(64 * 64)})
        self.assertIn(GREEN, {color for _, color in high.getcolors(64 * 64)})

    def test_outline_style_has_no_fill_background(self):
        icon = battery_image(85, False, 20, style="outline")

        self.assertEqual(icon.getpixel((29, 12)), (0, 0, 0, 0))
        green_pixels = sum(
            count for count, color in icon.getcolors(64 * 64) if color == GREEN
        )
        self.assertGreater(green_pixels, 200)

    def test_legacy_percent_style_maps_to_outline(self):
        self.assertEqual(
            battery_image(80, False, 20, style="percent").tobytes(),
            battery_image(80, False, 20, style="outline").tobytes(),
        )

    def test_battery_style_is_filled_with_charge_color_and_contrasting_text(self):
        low = battery_image(10, False, 20, style="battery")
        high = battery_image(85, False, 20, style="battery")

        self.assertEqual(low.getpixel((29, 12)), RED)
        self.assertEqual(high.getpixel((29, 12)), GREEN)
        text_pixels = sum(
            count
            for count, color in high.getcolors(64 * 64)
            if color == _contrast_text(GREEN)
        )
        self.assertGreater(text_pixels, 200)

    def test_text_color_is_picked_by_contrast(self):
        self.assertEqual(_contrast_text(GREEN), TEXT)
        self.assertEqual(_contrast_text((30, 30, 120, 255)), WHITE)

    def test_unknown_style_falls_back_to_battery(self):
        self.assertEqual(
            battery_image(80, False, 20, style="unknown").tobytes(),
            battery_image(80, False, 20, style="battery").tobytes(),
        )


class ChargingAnimationTests(unittest.TestCase):
    def test_battery_style_only_animates_while_charging(self):
        self.assertNotEqual(
            battery_image(80, True, 20, frame=0).tobytes(),
            battery_image(80, True, 20, frame=1).tobytes(),
        )
        self.assertEqual(
            battery_image(80, False, 20, frame=0).tobytes(),
            battery_image(80, False, 20, frame=1).tobytes(),
        )

    def test_outline_style_only_animates_while_charging(self):
        self.assertNotEqual(
            battery_image(80, True, 20, style="outline", frame=0).tobytes(),
            battery_image(80, True, 20, style="outline", frame=1).tobytes(),
        )
        self.assertEqual(
            battery_image(80, False, 20, style="outline", frame=0).tobytes(),
            battery_image(80, False, 20, style="outline", frame=1).tobytes(),
        )


class TrayIconStyleMenuTests(unittest.TestCase):
    def test_menu_offers_both_icon_styles_in_selected_language(self):
        controller = TrayController.__new__(TrayController)
        controller.settings = Settings(language="pt-BR")
        style_item = controller.build_menu().items[8]

        self.assertEqual(style_item.text, "Estilo do ícone")
        self.assertEqual(
            [item.text for item in style_item.submenu.items],
            ["Ícone de bateria", "Bateria sem preencher"],
        )
        self.assertTrue(style_item.submenu.items[0].checked)
        self.assertFalse(style_item.submenu.items[1].checked)

    def test_selecting_icon_style_persists_and_refreshes_the_tray(self):
        controller = TrayController.__new__(TrayController)
        controller.settings = Settings()
        controller._paint = Mock()
        controller._update_menu = Mock()

        with patch("cyclone2tray.tray.save_settings") as save_settings:
            controller._set_icon_style("outline")(None, None)

        self.assertEqual(controller.settings.icon_style, "outline")
        save_settings.assert_called_once_with(controller.settings)
        controller._paint.assert_called_once_with()
        controller._update_menu.assert_called_once_with()

    def test_selecting_unsupported_icon_style_fails(self):
        controller = TrayController.__new__(TrayController)
        controller.settings = Settings()

        with self.assertRaises(ValueError):
            controller._set_icon_style("unknown")

        self.assertEqual(controller.settings.icon_style, "battery")


if __name__ == "__main__":
    unittest.main()
