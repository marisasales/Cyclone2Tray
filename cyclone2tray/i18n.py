"""Interface translations for the tray application."""

LANGUAGE_OPTIONS = (
    ("en", "English"),
    ("pt-BR", "Português"),
    ("es", "Español"),
)
SUPPORTED_LANGUAGES = tuple(code for code, _ in LANGUAGE_OPTIONS)
DEFAULT_LANGUAGE = "en"

_TRANSLATIONS = {
    "en": {
        "battery": "Battery: {value}",
        "charging": " · charging",
        "last_reading": " (last reading)",
        "no_reading": "No reading",
        "dongle_connected": "Dongle connected",
        "dongle_disconnected": "Dongle disconnected",
        "app_version": "App version: {version}",
        "status_charging": "Cyclone 2: charging",
        "status_percent": "Cyclone 2: {percent}%",
        "status_last_reading": "Cyclone 2: {percent}% (last reading)",
        "status_waiting": "Cyclone 2: waiting for controller",
        "critical_title": "Critical battery",
        "critical_message": "Cyclone 2 is at {percent}%. Connect the charger.",
        "low_title": "Low battery",
        "low_message": "Cyclone 2 is at {percent}%.",
        "refresh": "Refresh now",
        "alert_at": "Alert at",
        "startup": "Start with Windows",
        "language": "Language",
        "exit": "Exit",
    },
    "pt-BR": {
        "battery": "Bateria: {value}",
        "charging": " · carregando",
        "last_reading": " (última leitura)",
        "no_reading": "Sem leitura",
        "dongle_connected": "Dongle conectado",
        "dongle_disconnected": "Dongle desconectado",
        "app_version": "Versão do app: {version}",
        "status_charging": "Cyclone 2: carregando",
        "status_percent": "Cyclone 2: {percent}%",
        "status_last_reading": "Cyclone 2: {percent}% (última leitura)",
        "status_waiting": "Cyclone 2: aguardando controle",
        "critical_title": "Bateria crítica",
        "critical_message": "Cyclone 2 em {percent}%. Conecte o carregador.",
        "low_title": "Bateria baixa",
        "low_message": "Cyclone 2 em {percent}%.",
        "refresh": "Atualizar agora",
        "alert_at": "Alerta em",
        "startup": "Iniciar com Windows",
        "language": "Idioma",
        "exit": "Sair",
    },
    "es": {
        "battery": "Batería: {value}",
        "charging": " · cargando",
        "last_reading": " (última lectura)",
        "no_reading": "Sin lectura",
        "dongle_connected": "Dongle conectado",
        "dongle_disconnected": "Dongle desconectado",
        "app_version": "Versión de la app: {version}",
        "status_charging": "Cyclone 2: cargando",
        "status_percent": "Cyclone 2: {percent}%",
        "status_last_reading": "Cyclone 2: {percent}% (última lectura)",
        "status_waiting": "Cyclone 2: esperando el control",
        "critical_title": "Batería crítica",
        "critical_message": "Cyclone 2 está al {percent}%. Conecta el cargador.",
        "low_title": "Batería baja",
        "low_message": "Cyclone 2 está al {percent}%.",
        "refresh": "Actualizar ahora",
        "alert_at": "Avisar al",
        "startup": "Iniciar con Windows",
        "language": "Idioma",
        "exit": "Salir",
    },
}


def translate(language: str, key: str, **values: object) -> str:
    messages = _TRANSLATIONS.get(language, _TRANSLATIONS[DEFAULT_LANGUAGE])
    return messages[key].format(**values)
