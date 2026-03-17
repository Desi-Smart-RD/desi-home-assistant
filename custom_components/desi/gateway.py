"""Handle Desi web socket connection."""

import asyncio
import json
import logging
import re
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import WS_URL

_LOGGER = logging.getLogger(__name__)


def parse_json_safe(data: str) -> dict[str, Any] | None:
    """If the JSON is malformed, attempt to fix it."""
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        try:
            fixed_data = data.replace(", ,", ",").replace(",,", ",")
            fixed_data = re.sub(r'(?<!")(\b\w+\b)(?!")(?=:)', r'"\1"', fixed_data)
            return json.loads(fixed_data)
        except (ValueError, TypeError):
            return None


class DesiGateway:
    """Handle the WebSocket connection and message dispatching."""

    def __init__(self, hass: HomeAssistant, session):
        """Initilize the gateway connection."""
        self.hass = hass
        self._session = session
        self._listeners = {}
        self._ws = None
        self._stopping = False

    def register_listener(self, device_id, callback):
        """Register a callback for a specific device."""
        if device_id not in self._listeners:
            self._listeners[device_id] = []
        self._listeners[device_id].append(callback)

        def remove_listener():
            if device_id in self._listeners and callback in self._listeners[device_id]:
                self._listeners[device_id].remove(callback)

        return remove_listener

    async def start_listen(self) -> None:
        """Start the WebSocket listening."""
        _LOGGER.debug("Gateway starts listening...")
        websession = async_get_clientsession(self.hass)

        while not self._stopping:
            try:
                await self._session.async_ensure_token_valid()
                token = self._session.token["access_token"]

                _LOGGER.debug("Connecting to WebSocket...")
                async with websession.ws_connect(  # pyright: ignore[reportAttributeAccessIssue]
                    WS_URL,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "X-Client-Type": "HomeAssistant",
                        "Connection": "Upgrade",
                        "Upgrade": "websocket",
                    },
                    heartbeat=90,
                ) as ws:
                    self._ws = ws
                    _LOGGER.info("WebSocket Connected!")

                    async for msg in ws:
                        if self._stopping:
                            break

                        if msg.type == aiohttp.WSMsgType.TEXT:  # pyright: ignore[reportAttributeAccessIssue]
                            await self._handle_message_async(msg.data)

                        elif msg.type == aiohttp.WSMsgType.CLOSED:  # pyright: ignore[reportAttributeAccessIssue]
                            _LOGGER.warning("WebSocket kapandı (Remote Closed)")
                            break
                        elif msg.type == aiohttp.WSMsgType.ERROR:  # pyright: ignore[reportAttributeAccessIssue]
                            _LOGGER.error("WebSocket hatası!")
                            break

            except aiohttp.ClientError as client_err:
                _LOGGER.error("WebSocket connectşon error: %s", client_err)
            except Exception:
                _LOGGER.exception("WebSocket connectşon error")
            if not self._stopping:
                _LOGGER.debug("Socket disconnected, retrying in 30 seconds...")
                await asyncio.sleep(30)

    async def _handle_message_async(self, data: str):
        """Process incoming WebSocket messages without blocking the event loop."""

        json_data = await self.hass.async_add_executor_job(parse_json_safe, data)

        if json_data is None:
            _LOGGER.warning(
                "Incoming data could not be parsed to JSON: %s...", data[:50]
            )
            return

        try:
            device_id = str(json_data.get("deviceId"))

            if device_id == "None":
                internal_data = json_data.get("data", {})
                device_id = str(internal_data.get("deviceId"))

            payload = json_data.get("data", {})
            if not payload:
                payload = json_data

            if device_id and device_id in self._listeners:
                for callback in self._listeners[device_id]:
                    try:
                        callback(payload)
                    except Exception:
                        _LOGGER.exception(
                            "Callback execution error for device: %s", device_id
                        )
            else:
                _LOGGER.debug("No active listener found for device: %s", device_id)

        except (KeyError, TypeError, ValueError):
            _LOGGER.exception("Message payload processing error")

    async def async_disconnect(self):
        """Disconnect the gateway and stop the background loop."""
        _LOGGER.info("Shutting down gateway...")
        self._stopping = True

        if self._ws:
            await self._ws.close()
