"""Handle Alarm Operations."""

import json
import logging
from typing import Any

import aiohttp

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
    CodeFormat,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, FULLFILMENT_API_URI

_LOGGER = logging.getLogger(__name__)

# consts
STATUS_DISARMED = 0
STATUS_ARMED = 1
MODE_AWAY = 0
MODE_HOME = 1
RINGING_OFF = 0
RINGING_ON = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Desi Alarm entities from a config entry."""
    data_pack = hass.data[DOMAIN][entry.entry_id]
    session = data_pack["session"]
    gateway = data_pack["gateway"]

    try:
        resp = await session.async_request("POST", f"{FULLFILMENT_API_URI}/get-alarms")
        resp.raise_for_status()
        json_data = await resp.json()
        devices = json_data.get("data", {}).get("alarms", [])
    except (aiohttp.ClientError, TimeoutError, ValueError) as err:
        _LOGGER.error("Failed to fetch alarms from API: %s", err)
        return

    entities = [DesiAlarm(session, gateway, device_data) for device_data in devices]

    async_add_entities(entities, update_before_add=True)


class DesiAlarm(AlarmControlPanelEntity, RestoreEntity):
    """Representation of a Alarm Control Panel."""

    _attr_code_arm_required = False

    def __init__(self, session: Any, gateway: Any, data: dict[str, Any]) -> None:
        """Initialize the alarm entity."""
        self._session = session
        self._gateway = gateway
        self._data = data
        self._device_id = str(data.get("deviceId"))
        self._attr_unique_id = f"desi_alarm_{self._device_id}"
        self._attr_has_entity_name = True
        self._attr_name = None

    @property
    def supported_features(self) -> AlarmControlPanelEntityFeature:
        """Return the list of supported features based on current state."""
        features = (
            AlarmControlPanelEntityFeature.ARM_HOME
            | AlarmControlPanelEntityFeature.ARM_AWAY
            | AlarmControlPanelEntityFeature.TRIGGER
        )

        # Disable opposite arming options if already armed
        if self.state == AlarmControlPanelState.ARMED_HOME:
            features &= ~AlarmControlPanelEntityFeature.ARM_AWAY
        if self.state == AlarmControlPanelState.ARMED_AWAY:
            features &= ~AlarmControlPanelEntityFeature.ARM_HOME

        return features

    @property
    def code_format(self) -> CodeFormat | None:
        """Return the expected code format."""
        if self.state == AlarmControlPanelState.DISARMED:
            return None
        return CodeFormat.NUMBER

    @property
    def state(self) -> AlarmControlPanelState | None:
        """Map the raw device status to Home Assistant alarm states."""
        try:
            status = int(self._data.get("status", -1))
            ringing = int(self._data.get("isRinging", 0))
            is_armed_away_mode = int(self._data.get("isActiveMode", 0))
        except (ValueError, TypeError):
            return None

        if ringing == RINGING_ON:
            return AlarmControlPanelState.TRIGGERED
        if status == STATUS_DISARMED:
            return AlarmControlPanelState.DISARMED
        if status == STATUS_ARMED:
            if is_armed_away_mode == MODE_AWAY and ringing == RINGING_OFF:
                return AlarmControlPanelState.ARMED_AWAY
            if is_armed_away_mode == MODE_HOME and ringing == RINGING_OFF:
                return AlarmControlPanelState.ARMED_HOME

        return None

    async def async_added_to_hass(self) -> None:
        """Register callbacks when entity is added to HA."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self._gateway.register_listener(self._device_id, self._handle_update)
        )

    def _handle_update(self, msg_data: dict[str, Any]) -> None:
        """Update entity data when a push message is received."""
        if msg_data:
            self._data.update(msg_data)
            self.async_write_ha_state()

    @property
    def should_poll(self) -> bool:
        """Disable polling."""
        return False

    @property
    def available(self) -> bool:
        """Return True if the alarm system is online."""
        return str(self._data.get("isOnline")) == "1"

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device registry information."""
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._data.get("deviceName", "Desi Alarm"),
            "manufacturer": "Desi Smart Lock and Security Systems",
            "model": self._data.get("deviceModel"),
            "sw_version": self._data.get("firmwareVersion"),
            "hw_version": self._data.get("hardwareVersion"),
            "suggested_area": self._data.get("deviceName")
        }

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        is_online = str(self._data.get("isOnline")) == "1"
        return {
            "firmware": self._data.get("firmwareVersion"),
            "hardware": self._data.get("hardwareVersion"),
            "model": self._data.get("deviceModel", "Desi Alarm"),
            "online": is_online,
        }

    async def _send_command(self, operation_type: str, code: str | None = None) -> None:
        """Send a control command to the API."""
        url = f"{FULLFILMENT_API_URI}/alarm-command"
        await self._session.async_ensure_token_valid()
        access_token = self._session.token["access_token"]
        payload = {
            "token": access_token,
            "alarmId": self._device_id,
            "alarmOperation": operation_type,
            "alarmCode": code,
        }

        resp = await self._session.async_request("POST", url, json=payload)

        if resp.status >= 400:
            error_body = await resp.text()
            msg_text = error_body

            try:
                if error_body:
                    err_payload = json.loads(error_body)
                    if isinstance(err_payload, dict) and "message" in err_payload:
                        msg_text = err_payload["message"]
            except ValueError:
                pass

            _LOGGER.warning("Cloud server message: %s", msg_text)

            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="command_failed",
                translation_placeholders={"server_msg": msg_text},
            )

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        """Send arm home command."""
        await self._send_command("ARM_HOME", code)

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        """Send arm away command."""
        await self._send_command("ARM_AWAY", code)

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        """Send disarm command."""
        await self._send_command("DISARM", code)

    async def async_alarm_trigger(self, code: str | None = None) -> None:
        """Send manual trigger (panic) command."""
        await self._send_command("TRIGGER", code)
