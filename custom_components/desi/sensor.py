"""Handle Sensor operations."""

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Desi Lock sensors from a config entry."""
    data_pack = hass.data[DOMAIN][entry.entry_id]
    session = data_pack["session"]
    gateway = data_pack["gateway"]

    devices = data_pack.get("devices", [])

    if not devices:
        _LOGGER.warning("No devices found for Desi sensors")
        return

    entities = []
    for device_data in devices:
        entities.append(DesiBatterySensor(session, gateway, device_data))
        entities.append(DesiLockStatusSensor(session, gateway, device_data))
        entities.append(DesiLockAvailabilitySensor(session, gateway, device_data))
    async_add_entities(entities, update_before_add=True)


class DesiBatterySensor(SensorEntity, RestoreEntity):
    """Representation of a Desi Lock Battery Sensor."""

    _attr_has_entity_name = True
    _attr_translation_key = "battery_status"
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, session, gateway, data):
        """Initialize the sensor."""
        self._session = session
        self._gateway = gateway
        self._data = data
        self._device_id = str(data.get("deviceId"))
        self._attr_unique_id = f"desi_lock_battery_{self._device_id}"

    async def async_added_to_hass(self) -> None:
        """Register callbacks when entity is added to Home Assistant."""
        await super().async_added_to_hass()

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, f"update_{self._device_id}", self._handle_update
            )
        )

    def _handle_update(self, msg_data=None):
        """Handle updated state data received from WebSocket."""
        if isinstance(msg_data, dict):
            self._data.update(msg_data)

        self.schedule_update_ha_state()

    @property
    def device_info(self):
        """Return device registry information for Home Assistant."""
        return {
            "identifiers": {(DOMAIN, self._device_id)}
        }

    @property
    def native_value(self):
        """Return the state of the sensor (Battery Level)."""
        try:
            return int(self._data.get("batteryLevel", 0))
        except (ValueError, TypeError):
            return None


class DesiLockStatusSensor(SensorEntity, RestoreEntity):
    """Representation of a Desi Lock State Sensor."""

    _attr_has_entity_name = True
    _attr_translation_key = "lock_status"
    _attr_icon = "mdi:lock"

    def __init__(self, session, gateway, data):
        """Initialize the sensor."""
        self._session = session
        self._gateway = gateway
        self._data = data
        self._device_id = str(data.get("deviceId"))
        self._attr_unique_id = f"desi_lock_status_{self._device_id}"

    async def async_added_to_hass(self) -> None:
        """Register callbacks when entity is added to Home Assistant."""
        await super().async_added_to_hass()

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, f"update_{self._device_id}", self._handle_update
            )
        )

    def _handle_update(self, msg_data=None):
        """Handle updated state data received from WebSocket."""
        if isinstance(msg_data, dict):
            self._data.update(msg_data)
        self.schedule_update_ha_state()

    @property
    def device_info(self):
        """Return device registry information for Home Assistant."""
        return {
            "identifiers": {(DOMAIN, self._device_id)}
        }

    @property
    def native_value(self):
        """Return the state of the sensor."""
        try:
            status = int(self._data.get("status"))

            return {0: "unlocked", 1: "locked"}.get(status)

        except (ValueError, TypeError):
            return None

    @property
    def icon(self):
        """Return the icon of the sensor."""
        try:
            status = int(self._data.get("status", 0))
            return "mdi:lock" if status == 1 else "mdi:lock-open-variant"  # noqa: TRY300
        except (ValueError, TypeError):
            return "mdi:lock-question"

class DesiLockAvailabilitySensor(SensorEntity, RestoreEntity):
    """Representation of a Desi Lock Online - Offline Sensor."""

    _attr_has_entity_name = True
    _attr_translation_key = "hub_status"

    def __init__(self, session, gateway, data):
        """Initialize the sensor."""
        self._session = session
        self._gateway = gateway
        self._data = data
        self._device_id = str(data.get("deviceId"))
        self._attr_unique_id = f"desi_lock_online_{self._device_id}"

    async def async_added_to_hass(self) -> None:
        """Register callbacks when entity is added to Home Assistant."""
        await super().async_added_to_hass()

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, f"update_{self._device_id}", self._handle_update
            )
        )

    def _handle_update(self, msg_data=None):
        """Handle updated state data received from WebSocket."""
        if isinstance(msg_data, dict):
            self._data.update(msg_data)

        self.schedule_update_ha_state()

    @property
    def device_info(self):
        """Return device registry information for Home Assistant."""
        return {
            "identifiers": {(DOMAIN, self._device_id)}
        }

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        try:
            is_online = int(self._data.get("isOnline", 0)) == 1

            return "online" if is_online else "offline"  # noqa: TRY300
        except (ValueError, TypeError):
            return None

    @property
    def icon(self) -> str:
        """Return the icon of the sensor."""
        return "mdi:router-wireless" if self.native_value == "online" else "mdi:router-wireless-off"
