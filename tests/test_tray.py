import unittest
from unittest.mock import Mock, patch

from cyclone2tray import __version__
from cyclone2tray.reader import BatteryStatus
from cyclone2tray.settings import Settings
from cyclone2tray.tray import TrayController


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


if __name__ == "__main__":
    unittest.main()
