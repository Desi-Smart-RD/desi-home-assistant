"""Handle Lock operations."""

import json
import logging

from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry, ConfigEntryDisabler
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers.dispatcher import dispatcher_send
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, FULLFILMENT_API_URI, LockIsJammed, LockStatus, OnlineStatus

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Desi Lock entities from a config entry."""
    data_pack = hass.data[DOMAIN][entry.entry_id]
    session = data_pack["session"]
    gateway = data_pack["gateway"]
    coordinator = data_pack["coordinator"]
    devices = coordinator.data.locks

    entities = [
        DesiLock(session, gateway, device_data, entry) for device_data in devices
    ]

    async_add_entities(entities)


class DesiLock(LockEntity, RestoreEntity):

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, session, gateway, data, entry):
        """Initializing properties."""
        self._session = session
        self._gateway = gateway
        self._data = data
        self._device_id = str(data.get("deviceId"))
        self._attr_unique_id = f"desi_lock_{self._device_id}"
        self._is_locking = False
        self._is_unlocking = False
        self.entry = entry

    async def async_added_to_hass(self) -> None:
        """Register callbacks when entity is added to Home Assistant."""
        await super().async_added_to_hass()

        self.async_on_remove(
            self._gateway.register_listener(self._device_id, self._handle_update)
        )

    def _handle_update(self, msg_data):
        """Handle updated state data received from WebSocket."""
        if msg_data:
            self._data.update(msg_data)
            self._is_locking = False
            self._is_unlocking = False

            self.async_write_ha_state()
            dispatcher_send(self.hass, f"update_{self._device_id}", msg_data)

    @property
    def device_info(self):
        """Return device registry information for Home Assistant."""
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._data.get("deviceName", "Desi"),
            "manufacturer": "Desi Smart Lock",
            "model": self._data.get("deviceModel"),
            "sw_version": self._data.get("firmwareVersion"),
            "hw_version": self._data.get("hardwareVersion"),
            "suggested_area": self._data.get("deviceName"),
        }

    @property
    def code_format(self) -> str | None:
        """Return the required code format."""
        if self.is_locked:
            return r"^\d*$"
        return None

    @property
    def should_poll(self) -> bool:
        """Disable polling. Websocket drives updates."""
        return False

    @property
    def is_locking(self) -> bool:
        """Return True if the lock is currently locking."""
        return self._is_locking

    @property
    def is_unlocking(self) -> bool:
        """Return True if the lock is currently unlocking."""
        return self._is_unlocking

    @property
    def is_locked(self) -> bool | None:
        """Return true if lock is locked."""
        try:
            val = int(self._data.get("status"))
        except (ValueError, TypeError):
            return None
        return val == LockStatus.LOCKED

    @property
    def is_unlocked(self) -> bool | None:
        """Return True if the lock is unlocked."""
        try:
            val = int(self._data.get("status"))
        except (ValueError, TypeError):
            return None
        return val == LockStatus.UNLOCKED

    @property
    def is_jammed(self) -> bool | None:
        """Return True if the lock is jammed."""
        try:
            val = int(self._data.get("isJammed"))
        except (ValueError, TypeError):
            return None
        return val == LockIsJammed.JAMMED

    @property
    def available(self) -> bool:
        """Return True if the lock is online."""
        try:
            val = int(self._data.get("isOnline"))
        except (ValueError, TypeError):
            return False
        return val == OnlineStatus.ONLINE

    @property
    def extra_state_attributes(self):
        """Return entity specific state attributes."""
        return {
            "Battery Level": self._data.get("batteryLevel"),
            "Online": self.available,
            "Firmware Version": self._data.get("firmwareVersion"),
            "Device Version": self._data.get("deviceVersion"),
            "Device Model": self._data.get("deviceModel"),
        }

    async def _send_command(self, operation_type, code):
        """Send command to the API."""
        url = f"{FULLFILMENT_API_URI}/lock-unlock-command"

        try:
            await self._session.async_ensure_token_valid()
        except Exception as err:
            if getattr(err, "status", None) == 429:
                _LOGGER.warning("Token refresh rate limit hit. Retrying later.")
                self.entry.disabled_by = ConfigEntryDisabler.USER
                raise ConfigEntryNotReady(
                    translation_domain=DOMAIN,
                    translation_key="exceptions.rate_limit_exceeded"
                ) from err

            raise

        payload = {
            "smartLockId": self._device_id,
            "smartLockOperation": operation_type,
            "smartLockCode": str(code) if code else "",
        }

        resp = await self._session.async_request("POST", url, json=payload)

        if resp.status >= 400:
            error_body = await resp.text()
            msg_text = error_body
            try:
                if error_body:
                    err_json = json.loads(error_body)
                    if isinstance(err_json, dict) and "message" in err_json:
                        msg_text = err_json["message"]
            except ValueError:
                pass

            _LOGGER.warning("Server Message -> %s", msg_text)
            self._is_locking = False
            self._is_unlocking = False
            self.async_write_ha_state()

            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="command_failed",
                translation_placeholders={"server_msg": msg_text},
            )

    async def async_lock(self, **kwargs):
        """Send lock command."""
        code = kwargs.get("code")
        self._is_locking = True
        self._is_unlocking = False
        self.async_write_ha_state()

        try:
            await self._send_command("LOCK", code)
        except Exception:
            self._is_locking = False
            self.async_write_ha_state()
            raise

    async def async_unlock(self, **kwargs):
        """Send unlock command."""
        code = kwargs.get("code")
        if not code:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="code_required"
            )

        self._is_locking = False
        self._is_unlocking = True
        self.async_write_ha_state()

        try:
            await self._send_command("UNLOCK", code)
        except Exception:
            self._is_unlocking = False
            self.async_write_ha_state()
            raise
