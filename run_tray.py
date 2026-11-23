"""Ponto de entrada do monitor na bandeja."""

from cyclone2tray.tray import TrayController


def main() -> None:
    TrayController().run()


if __name__ == "__main__":
    main()
