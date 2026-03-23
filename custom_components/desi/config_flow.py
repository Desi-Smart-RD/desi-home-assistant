"""Config flow for Desi OAuth2 integration."""

import logging

import jwt  # type: ignore  # noqa: PGH003

from homeassistant.config_entries import ConfigFlowResult
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.network import get_url

from .const import AUTH_URI, DOMAIN, TOKEN_URI

_LOGGER = logging.getLogger(__name__)


class DesiLocalOAuth2Implementation(
    config_entry_oauth2_flow.LocalOAuth2ImplementationWithPkce
):
    """Get redirect uri for callback."""

    @property
    def redirect_uri(self) -> str:
        """Get users network address for redirict."""
        base_url = get_url(self.hass)
        # Hata ayıklama için burayı error seviyesinde logluyoruz
        _LOGGER.info("Redirect Uri: %s", base_url)
        return f"{base_url}/auth/external/callback?desi=1"


class DesiConfigFlow(config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN):
    """Desi Smart OAuth2 Flow."""

    VERSION = 1
    DOMAIN = DOMAIN

    @property
    def logger(self) -> logging.Logger:
        """Logger."""
        return _LOGGER

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""

        implementations = await config_entry_oauth2_flow.async_get_implementations(
            self.hass, DOMAIN
        )

        self.flow_impl = next(
            (
                impl
                for impl in implementations.values()
                if isinstance(impl, DesiLocalOAuth2Implementation)
            ),
            None,
        ) # type: ignore  # noqa: PGH003

        if self.flow_impl is None:
            config_entry_oauth2_flow.async_register_implementation(
                self.hass,
                DOMAIN,
                DesiLocalOAuth2Implementation(
                    self.hass,
                    DOMAIN,
                    "",
                    AUTH_URI,
                    TOKEN_URI,
                    "",
                    128,
                ),
            )
            implementations = await config_entry_oauth2_flow.async_get_implementations(
                self.hass, DOMAIN
            )
            self.flow_impl = next(
                    impl
                    for impl in implementations.values()
                    if isinstance(impl, DesiLocalOAuth2Implementation)
            )

        # Redirect the user directly to the OAuth authentication page
        return await self.async_step_auth()

    async def async_oauth_create_entry(self, data: dict) -> ConfigFlowResult:
        """Create an entry after successful OAuth authentication."""
        try:

            token_data = data["token"]["access_token"]
            decoded = jwt.decode(token_data, options={"verify_signature": False})
            user_id = decoded["sub"]

            await self.async_set_unique_id(user_id)
            self._abort_if_unique_id_configured()

        except (jwt.InvalidTokenError, KeyError):
            _LOGGER.exception("Failed to parse token or extract user ID during setup")
            return self.async_abort(reason="oauth_error")

        else:
            return self.async_create_entry(title=f"Desi Smart ({user_id})", data=data)
