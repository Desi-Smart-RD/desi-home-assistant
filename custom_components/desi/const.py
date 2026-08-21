"""Constants for the Desi Smart."""

from homeassistant.const import Platform
from enum import IntEnum

MANUFACTURER = "Desi Smart Lock and Security Systems"
DEFAULT_NAME = "Desi Smart"
DOMAIN = "desi"

LOGIN_METHODS = ["phone", "email"]
DEFAULT_LOGIN_METHOD = "email"

PUBLIC_ID = "home_assistant"


AUTH_URI = "https://web.desismart.io/ds/sign-in-for-home-assistant"
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
    Platform.BINARY_SENSOR,
]


class DoorState(IntEnum):
    UNKNOWN = 0
    CLOSED = 1
    OPENED = 2


class OnlineStatus(IntEnum):
    OFFLINE = 0
    ONLINE = 1


class AlarmStatus(IntEnum):
    DISARMED = 0
    ARMED = 1


class AlarmModes(IntEnum):
    MODE_AWAY = 0
    MODE_STAY_ARMED = 1


class RingingStatus(IntEnum):
    RINGING_OFF = 0
    RINGING_ON = 1


class LockStatus(IntEnum):
    UNLOCKED = 0
    LOCKED= 1

class LockIsJammed(IntEnum):
    OK = 0
    JAMMED = 1

class SwitchStatus(IntEnum):
    ON = 1
    OFF = 2