"""The Desi Smart Integration."""

from __future__ import annotations

import logging

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.entity_platform import ConfigEntryAuthFailed

from .config_flow import DesiOauth2Implementation
from .const import AUTH_URI, DOMAIN, FULLFILMENT_API_URI, PUBLIC_ID, TOKEN_URI
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

    implementation = DesiOauth2Implementation(
        hass,
        DOMAIN,
        PUBLIC_ID,
        AUTH_URI,
        TOKEN_URI,
    )

    config_entry_oauth2_flow.async_register_implementation(
        hass,
        DOMAIN,
        implementation,
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
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
        await session.async_ensure_token_valid()
    except aiohttp.ClientResponseError as err:
        if err.status == 401 :
            _LOGGER.error(
                "Authentication failed. Please re-authenticate the integration."
            )
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN,
                translation_key="exceptions.auth_failed",
            ) from err
        elif err.status == 429:
            _LOGGER.warning("Token refresh rate limit hit. Retrying later.")
            raise ConfigEntryNotReady(
                translation_domain=DOMAIN,
                translation_key="exceptions.rate_limit_exceeded",
            ) from err
        else:
            raise ConfigEntryNotReady(
                translation_domain=DOMAIN,
                translation_key="exceptions.unexpected_error",
            ) from err

    except Exception as err:
        _LOGGER.error("Unexpected error ensuring token valid: %s", err)
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="exceptions.unexpected_error",
        ) from err
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        _LOGGER.error("Initial refresh failed: %s", err)
        raise ConfigEntryNotReady(f"Could not connect to API: {err}")

    try:
        _LOGGER.debug("Initializing Gateway class...")
        gateway = DesiGateway(hass, session, entry)

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
