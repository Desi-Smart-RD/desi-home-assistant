"""Handle Switch operation."""

from __future__ import annotations

import json
import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import dispatcher_send
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, FULLFILMENT_API_URI, OnlineStatus, SwitchStatus

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Desi Switch entities from a config entry."""

    data_pack = hass.data[DOMAIN][entry.entry_id]
    session = data_pack["session"]
    gateway = data_pack["gateway"]
    coordinator = data_pack["coordinator"]
    devices = coordinator.data.switches


    entities = [DesiSwitch(session, gateway, device_data) for device_data in devices]

    async_add_entities(entities, update_before_add=True)


class DesiSwitch(SwitchEntity, RestoreEntity):
    """Representation of a Desi Switch entity."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, session, gateway, data):
        """Initializing properties."""
        self._session = session
        self._gateway = gateway
        self._data = data
        self._device_id = str(data.get("deviceId"))
        self._attr_unique_id = f"desi_switch_{self._device_id}"

    @property
    def device_info(self):
        """The device reports the information to Home Assistant."""
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._data.get("deviceName", "Desi Switch"),
            "manufacturer": "Desi Smart Lock and Security Systems",
            "model": self._data.get("deviceModel"),
            "suggested_area": self._data.get("deviceName")
        }

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

            self.async_write_ha_state()
            dispatcher_send(self.hass, f"update_{self._device_id}", msg_data)

    @property
    def is_on(self) -> bool | None:
        """Return true if switch is on."""
        try:
            status = int(self._data.get("status"))
        except (ValueError, TypeError):
            return None
        return status == SwitchStatus.ON

    @property
    def available(self) -> bool:
        """Return True if the lock is online."""
        try:
            val = int(self._data.get("isOnline"))
        except (ValueError, TypeError):
            return False
        return val == OnlineStatus.ONLINE


    @property
    def should_poll(self) -> bool:
        """Disable pooling. Websocket drives updates."""
        return False


    async def _send_command(self, operation_type):
        """Send command to API."""
        url = f"{FULLFILMENT_API_URI}/on-off-command"

        await self._session.async_ensure_token_valid()
        access_token = self._session.token["access_token"]

        payload = {
            "token": access_token,
            "switchId": self._device_id,
            "switchOperation": operation_type
        }

        resp = await self._session.async_request("POST", url, json=payload)

        if resp.status >= 400:
            _LOGGER.info("Error response: %s", resp)
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

            self.async_write_ha_state()

            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="command_failed",
                translation_placeholders={"server_msg": msg_text},
            )


    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        _LOGGER.info("async_turn_on")
        await self._send_command("ON")
        self._data["status"] = SwitchStatus.ON
        self.async_write_ha_state()


    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        _LOGGER.info("async_turn_off")
        await self._send_command("OFF")
        self._data["status"] = SwitchStatus.OFF
        self.async_write_ha_state()
