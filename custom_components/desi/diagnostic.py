from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry

from .const import DOMAIN

TO_REDACT = {
    "access_token",
    "refresh_token",
    "token",
    "client_secret",
}

async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:

    data_pack = hass.data[DOMAIN][entry.entry_id]
    coordinator = data_pack.get("coordinator")
    session = data_pack.get("session")

    token_exists = False
    if session and hasattr(session, "token") and session.token:
        token_exists = True

    coordinator_data = {}
    if coordinator and coordinator.data:
        coordinator_data = {
            "locks": coordinator.data.locks,
            "alarms": coordinator.data.alarms,
            "switches": coordinator.data.switches,
        }

    diagnostics_data = {
        "setup_info": {
            "entry_title": entry.title,
            "has_token": token_exists,
            "data": dict(entry.data),
            "options": dict(entry.options),
        },
        "api_raw_data": coordinator_data,
    }

    return async_redact_data(diagnostics_data, TO_REDACT)


async def async_get_device_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry, device: DeviceEntry
) -> dict[str, Any]:

    device_id = next(
        (id_val for id_domain, id_val in device.identifiers if id_domain == DOMAIN),
        None,
    )

    config_entry_diags = await async_get_config_entry_diagnostics(hass, entry)

    device_raw_data = None
    coordinator_data = config_entry_diags.get("api_raw_data", {})

    for category in ["locks", "alarms", "switches"]:
        for item in coordinator_data.get(category, []):
            if str(item.get("deviceId")) == str(device_id):
                device_raw_data = item
                break
        if device_raw_data:
            break

    diagnostics_data = {
        "device_info": {
            "name": device.name,
            "manufacturer": device.manufacturer,
            "model": device.model,
            "identifiers": device.identifiers,
            "internal_id": device_id,
        },
        "device_api_data": device_raw_data,
    }

    return async_redact_data(diagnostics_data, TO_REDACT)
