"""The Desi Smart Integration."""

from __future__ import annotations

import logging

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_entry_oauth2_flow

from .const import AUTH_URI, DOMAIN, FULLFILMENT_API_URI, TOKEN_URI
from .coordinator import DesiDataUpdateCoordinator
from .gateway import DesiGateway

_LOGGER = logging.getLogger(__name__)


PLATFORMS: list[Platform] = [
    Platform.LOCK,
    Platform.ALARM_CONTROL_PANEL,
    Platform.SWITCH,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """OAuth provider implementation."""

    implementation = config_entry_oauth2_flow.LocalOAuth2Implementation(
        hass,
        DOMAIN,
        client_id="",
        client_secret="",
        authorize_url=AUTH_URI,
        token_url=TOKEN_URI,
    )

    config_entry_oauth2_flow.async_register_implementation(
        hass,
        DOMAIN,
        implementation,
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the integration from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    try:
        implementation = (
            await config_entry_oauth2_flow.async_get_config_entry_implementation(
                hass, entry
            )
        )
    except Exception as e:
        _LOGGER.warning("Implementation not ready yet, will retry: %s", e)
        raise ConfigEntryNotReady from e

    session = config_entry_oauth2_flow.OAuth2Session(hass, entry, implementation)

    coordinator = DesiDataUpdateCoordinator(hass, session, entry)

    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        _LOGGER.error("Initial refresh failed: %s", err)
        raise ConfigEntryNotReady(f"Could not connect to API: {err}")

    try:
        _LOGGER.debug("Initializing Gateway class...")
        gateway = DesiGateway(hass, session)

        hass.data[DOMAIN][entry.entry_id] = {
            "session": session,
            "gateway": gateway,
            "coordinator": coordinator,
        }

        entry.async_create_background_task(hass, gateway.start_listen(), "desi_ws_loop")

        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        return True

    except Exception as e:
        _LOGGER.exception("Unexpected error occurred during setup: %s", e)
        return False


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    data = hass.data[DOMAIN].get(entry.entry_id)

    if data:
        gateway = data.get("gateway")
        if gateway:
            _LOGGER.debug("Disconnecting Gateway...")
            await gateway.async_disconnect()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        _LOGGER.debug("Entry data removed from memory.")

    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle removal of an entry."""
    try:
        implementation = (
            await config_entry_oauth2_flow.async_get_config_entry_implementation(
                hass, entry
            )
        )
        session = config_entry_oauth2_flow.OAuth2Session(hass, entry, implementation)

        disconnect_url = f"{FULLFILMENT_API_URI}/disconnect-user"

        _LOGGER.info("Integration is being removed, notifying server.")
        resp = await session.async_request("POST", disconnect_url)

        _LOGGER.debug("Disconnect Response Code: %s", resp.status)

        if resp.status < 400:
            _LOGGER.info("User successfully disconnected from server.")
        else:
            text = await resp.text()
            _LOGGER.warning("Server disconnect error: %s - Body: %s", resp.status, text)

    except (aiohttp.ClientError, TimeoutError) as err:
        _LOGGER.warning("Could not reach server while removing integration: %s", err)
