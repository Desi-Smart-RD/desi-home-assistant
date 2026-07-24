"""Desi Smart Data Update Coordinator."""

import logging
from types import SimpleNamespace

import async_timeout

from homeassistant.config_entries import ConfigEntryDisabler
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, FULLFILMENT_API_URI

_LOGGER = logging.getLogger(__name__)


class DesiDataUpdateCoordinator(DataUpdateCoordinator):
    """Desi Data update coordinator."""

    def __init__(self, hass, session, entry):
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=None)
        self.session = session
        self.entry = entry

    async def _async_update_data(self):

        locks_data = []
        alarms_data = []
        switches_data = []

        try:
            async with async_timeout.timeout(15):
                try:
                    lockResponse = await self.session.async_request(
                        "POST", f"{FULLFILMENT_API_URI}/get-locks"
                    )
                    if lockResponse.status == 429:
                        _LOGGER.critical(
                            "Rate limit hit! Disabling integration. The API that retrieves devices can be called a maximum of 15 times per day. If more than 15 requests are made, Home Assistant will be disabled for the rest of the day. This limitation is implemented to prevent continuous polling and reduce server load."
                        )
                        self.entry.disabled_by = ConfigEntryDisabler.USER
                        await self.hass.config_entries.async_unload(self.entry.entry_id)
                        raise UpdateFailed(
                            "429 Too Many Requests - Integration disabled."
                        )

                    lockResponse.raise_for_status()
                    locks_json = await lockResponse.json()
                    locks_data = locks_json.get("data", {}).get("locks", [])

                except UpdateFailed:
                    raise
                except Exception as e:
                    _LOGGER.warning(f"Failed to retrieve smart lock data, skipping: {e}")
                try:
                    alarmResponse = await self.session.async_request(
                        "POST", f"{FULLFILMENT_API_URI}/get-alarms"
                    )

                    if alarmResponse.status == 429:
                        _LOGGER.critical(
                            "Rate limit hit! Disabling integration. The API that retrieves devices can be called a maximum of 15 times per day. If more than 15 requests are made, Home Assistant will be disabled for the rest of the day. This limitation is implemented to prevent continuous polling and reduce server load."
                        )
                        self.entry.disabled_by = ConfigEntryDisabler.USER
                        await self.hass.config_entries.async_unload(self.entry.entry_id)
                        raise UpdateFailed(
                            "429 Too Many Requests - Integration disabled."
                        )
                    alarmResponse.raise_for_status()
                    alarm_json = await alarmResponse.json()
                    alarms_data = alarm_json.get("data", {}).get("alarms", [])

                except UpdateFailed:
                    raise
                except Exception as e:
                    _LOGGER.warning(f"Failed to retrieve alarm data, skipping: {e}")

                try:
                    switchResponse = await self.session.async_request(
                        "POST", f"{FULLFILMENT_API_URI}/get-switches"
                    )

                    if switchResponse.status == 429:
                        _LOGGER.critical(
                            "Rate limit hit! Disabling integration. The API that retrieves devices can be called a maximum of 15 times per day. If more than 15 requests are made, Home Assistant will be disabled for the rest of the day. This limitation is implemented to prevent continuous polling and reduce server load."
                        )
                        await self.hass.config_entries.async_unload(self.entry.entry_id)
                        raise UpdateFailed(
                            "429 Too Many Requests - Integration disabled."
                        )
                    switchResponse.raise_for_status()
                    switch_json = await switchResponse.json()
                    switches_data = switch_json.get("data", {}).get("switches", [])

                except UpdateFailed:
                    raise
                except Exception as e:
                    _LOGGER.warning(f"Failed to retrieve switch data, skipping: {e}")

                return SimpleNamespace(
                    locks=locks_data,
                    alarms=alarms_data,
                    switches=switches_data,
                )

        except UpdateFailed:
            raise
        except Exception as err:
            raise UpdateFailed(f"Desi API general error or timeout: {err}")
