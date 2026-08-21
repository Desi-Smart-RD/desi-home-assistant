"""Desi Smart Data Update Coordinator."""

import logging
from types import SimpleNamespace

import async_timeout

from homeassistant.config_entries import ConfigEntryDisabler
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, FULLFILMENT_API_URI

_LOGGER = logging.getLogger(__name__)


class DesiDataUpdateCoordinator(DataUpdateCoordinator):

    def __init__(self, hass, session, entry):
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=None)
        self.session = session
        self.entry = entry

    async def _fetch_endpoint_data(self, endpoint: str, data_key: str) -> list:
        try:
            response = await self.session.async_request(
                "POST", f"{FULLFILMENT_API_URI}/{endpoint}"
            )
            if response.status == 429:
                _LOGGER.warning(
                    "Rate limit hit! Disabling integration. The API that retrieves devices "
                    "can be called a maximum of 15 times per day. To prevent server load, "
                    "further requests are stopped."
                )
                self.entry.disabled_by = ConfigEntryDisabler.USER
                raise UpdateFailed(
                        translation_domain=DOMAIN,
                        translation_key="exceptions.rate_limit_exceeded"
                    )

            response.raise_for_status()
            json_data = await response.json()
            return json_data.get("data", {}).get(data_key, [])

        except UpdateFailed:
            raise
        except Exception as e:

            _LOGGER.warning(f"Failed to retrieve {data_key} data, skipping: {e}")
            return []

    async def _async_update_data(self):
        try:
            async with async_timeout.timeout(15):
                locks_data = await self._fetch_endpoint_data("get-locks", "locks")
                alarms_data = await self._fetch_endpoint_data("get-alarms", "alarms")
                switches_data = await self._fetch_endpoint_data(
                    "get-switches", "switches"
                )

                return SimpleNamespace(
                    locks=locks_data,
                    alarms=alarms_data,
                    switches=switches_data,
                )

        except UpdateFailed:
            raise
        except Exception as err:
            raise UpdateFailed(f"General error: {err}")
