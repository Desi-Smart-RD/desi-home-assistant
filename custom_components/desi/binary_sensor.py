"""Handle Binary Sensor operations."""

"""If auto-closer is linked your smartLock you can know the door status other-wise door status is will be unknown"""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, DoorState


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Setup Desi Door Sensors from a config entry."""
    data_pack = hass.data[DOMAIN][entry.entry_id]
    session = data_pack["session"]
    gateway = data_pack["gateway"]
    coordinator = data_pack.get("coordinator", [])

    devices = coordinator.data.locks

    if not devices:
        return

    entities = []
    for device_data in devices:
        entities.append(DesiDoorSensor(session, gateway, device_data))

    async_add_entities(entities)


class DesiDoorSensor(BinarySensorEntity, RestoreEntity):
    """Representation of a Desi Door Status Sensor."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.DOOR

    def __init__(self, session, gateway, data):
        """Initialize the sensor."""
        self._session = session
        self._gateway = gateway
        self._data = data
        self._device_id = str(data.get("deviceId"))
        self._attr_unique_id = f"desi_door_status_{self._device_id}"
        self._attr_translation_key = "door_status"

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""
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
        return {"identifiers": {(DOMAIN, self._device_id)}}

    @property
    def is_on(self) -> bool | None:
        """Return door status (True if open, False if closed, None if unknown)."""
        raw_status = self._data.get("doorStatus")
        if raw_status is None:
            return None

        try:
            status = DoorState(int(raw_status))
        except ValueError:
            return None

        if status == DoorState.UNKNOWN:
            return None

        return status == DoorState.OPENED

    @property
    def icon(self):
        """Return the icon of the binary sensor."""
        raw_status = self._data.get("doorStatus")
        if raw_status is None:
            return "mdi:door"

        try:
            status = DoorState(int(raw_status))
        except ValueError:
            return "mdi:door"

        if status == DoorState.OPENED:
            return "mdi:door-open"
        if status == DoorState.CLOSED:
            return "mdi:door-closed"

        return "mdi:door"
