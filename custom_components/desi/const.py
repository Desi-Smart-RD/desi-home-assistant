"""Constants for the Desi."""

from homeassistant.const import Platform

MANUFACTURER = "Desi Smart Lock and Security Systems"
DEFAULT_NAME = "Desi Smart"
DOMAIN = "desi"

LOGIN_METHODS = ["phone", "email"]
DEFAULT_LOGIN_METHOD = "email"


AUTH_URI = "https://desismart.io/api/third_part_devices/ds/home_assistant/oauth/authorize"
TOKEN_URI = "https://desismart.io/api/third_part_devices/ds/home_assistant/token"
FULLFILMENT_API_URI = (
    "https://desismart.io/api/third_part_devices/ds/home_assistant/control"
)
API_URL = "https://desismart.io"
SOCKET_PATH = "/api/third_part_devices/ds/home_assistant/ws"
WS_URL = API_URL + SOCKET_PATH


PLATFORMS = [
    Platform.LOCK,
    Platform.ALARM_CONTROL_PANEL,
    Platform.SWITCH,
    Platform.SENSOR,
]
