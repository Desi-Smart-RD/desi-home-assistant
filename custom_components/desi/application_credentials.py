"""Application credentials platform for Desi."""

from homeassistant.components.application_credentials import AuthorizationServer
from homeassistant.core import HomeAssistant

from .const import AUTH_URI, TOKEN_URI


async def async_get_authorization_server(hass: HomeAssistant) -> AuthorizationServer:
    """Initilaze the auth uris."""
    return AuthorizationServer(
        authorize_url=AUTH_URI,
        token_url=TOKEN_URI
    )
