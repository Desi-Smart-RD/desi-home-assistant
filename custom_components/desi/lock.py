"""Handle Lock operations."""

import json
import logging

import aiohttp

from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, FULLFILMENT_API_URI

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

    try:
        resp = await session.async_request("POST", f"{FULLFILMENT_API_URI}/get-locks")
        resp.raise_for_status()
        json_data = await resp.json()
        devices = json_data.get("data", {}).get("locks", [])
    except (aiohttp.ClientError, TimeoutError, ValueError) as err:
        _LOGGER.error("Failed to fetch locks from API: %s", err)
        return

    entities = [DesiLock(session, gateway, device_data) for device_data in devices]

    async_add_entities(entities, update_before_add=True)


class DesiLock(LockEntity, RestoreEntity):
    """Representation of a Desi Lock entity."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, session, gateway, data):
        """Initializing properties."""
        self._session = session
        self._gateway = gateway
        self._data = data
        self._device_id = str(data.get("deviceId"))
        self._attr_unique_id = f"desi_lock_{self._device_id}"
        self._is_locking = False
        self._is_unlocking = False

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

            async_dispatcher_send(self.hass, f"update_{self._device_id}")

    @property
    def device_info(self):
        """Return device registry information for Home Assistant."""
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._data.get("deviceName", "Desi Lock"),
            "manufacturer": "Desi Smart Lock and Security Systems",
            "model": self._data.get("deviceModel"),
            "sw_version": self._data.get("firmwareVersion"),
            "hw_version": self._data.get("hardwareVersion"),
            "suggested_area": self._data.get("deviceName")
        }

    @property
    def code_format(self) -> str | None:
        """Return the required code format, or None if no code is required."""
        if self.is_locked:
            return r"^\d*$"
        return None

    @property
    def should_poll(self) -> bool:
        """Disable polling."""
        return False

    @property
    def is_locking(self) -> bool:
        """Return True if the lock is currently locking."""
        return self._is_locking

    @property
    def is_unlocking(self) -> bool:
        """Return True if the lock is currently unlocking."""
        return self._is_unlocking

    async def async_update(self):
        """Fetch the latest state directly from the API."""
        try:
            resp = await self._session.async_request(
                "POST", f"{FULLFILMENT_API_URI}/get-locks"
            )
            resp.raise_for_status()
            json_data = await resp.json()
            locks = json_data.get("data", {}).get("locks", [])

            for lock in locks:
                if str(lock.get("deviceId")) == self._device_id:
                    self._data = lock
                    self._is_locking = False
                    self._is_unlocking = False
                    async_dispatcher_send(self.hass, f"update_{self._device_id}")
                    break
        except Exception:
            _LOGGER.exception("Error: %s")

    @property
    def is_locked(self) -> bool:
        """Return True if the lock is locked."""
        try:
            val = int(self._data.get("status", 0))
        except (ValueError, TypeError):
            return False
        return val == 1

    @property
    def is_unlocked(self) -> bool:
        """Return True if the lock is unlocked."""
        try:
            val = int(self._data.get("status", 1))
        except (ValueError, TypeError):
            return False
        return val == 0

    @property
    def is_jammed(self) -> bool:
        """Return True if the lock is jammed."""
        try:
            val = int(self._data.get("isJammed", 0))
        except (ValueError, TypeError):
            return False
        return val == 1

    @property
    def available(self) -> bool:
        """Return True if the lock is online and available."""
        return str(self._data.get("isOnline")) == "1"

    @property
    def extra_state_attributes(self):
        """Return entity specific state attributes."""
        return {
            "Battery Level": self._data.get("batteryLevel"),
            "Online": str(str(self._data.get("isOnline")) == "1"),
            "Firmware Version": self._data.get("firmwareVersion"),
            "Device Version": self._data.get("deviceVersion"),
            "Device Model": self._data.get("deviceModel"),
        }

    async def _send_command(self, operation_type, code):
        """Send a control command to the API."""
        url = f"{FULLFILMENT_API_URI}/lock-unlock-command"

        await self._session.async_ensure_token_valid()
        access_token = self._session.token["access_token"]

        payload = {
            "token": access_token,
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

        await self._send_command("LOCK", code)

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

        await self._send_command("UNLOCK", code)
