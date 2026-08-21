"""Config flow for Desi Smart OAuth2 integration."""

import base64
import hashlib
import logging
import secrets

import jwt

from homeassistant.config_entries import ConfigFlowResult
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.network import get_url

from .const import AUTH_URI, DOMAIN, PUBLIC_ID, TOKEN_URI

_LOGGER = logging.getLogger(__name__)


def generate_pkce_pair():
    code_verifier = (
        base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode("utf-8")
    )


    code_challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest())
        .rstrip(b"=")
        .decode("utf-8")
    )

    return code_verifier, code_challenge


class DesiOauth2Implementation(config_entry_oauth2_flow.LocalOAuth2Implementation):
    def __init__(self, hass, domain, client_id, authorize_url, token_url) -> None:

        super().__init__(hass, domain, client_id, None, authorize_url, token_url)

        self._pkce_data: dict[str, str] = {}

    @property
    def name(self) -> str:
        return "Desi Smart"

    @property
    def redirect_uri(self) -> str:
        base_url = get_url(self.hass)
        return f"{base_url}/auth/external/callback"

    async def async_generate_authorize_url(self, flow_id: str) -> str:
        code_verifier, code_challenge = generate_pkce_pair()

        self.code_verifier = code_verifier

        url = await super().async_generate_authorize_url(flow_id)

        return f"{url}&code_challenge={code_challenge}&code_challenge_method=S256"

    async def async_resolve_external_data(self, external_data: dict) -> dict:
        code = external_data.get("code")

        if not self.code_verifier:
            _LOGGER.error("PKCE code verifier not found")
            raise ValueError("Missing PKCE code verifier")

        session = async_get_clientsession(self.hass)

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "code_verifier": self.code_verifier,
        }

        async with session.post(self.token_url, data=data) as resp:
            resp.raise_for_status()
            return await resp.json()


class DesiOauthConfigFlow(
    config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN
):

    DOMAIN = DOMAIN

    @property
    def logger(self) -> logging.Logger:
        """Return logger instance."""
        return _LOGGER

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        """Start OAuth flow triggered by the user in the UI."""

        implementations = await config_entry_oauth2_flow.async_get_implementations(
            self.hass, DOMAIN
        )

        if DOMAIN not in implementations:
            implementation = DesiOauth2Implementation(
                self.hass,
                DOMAIN,
                PUBLIC_ID,
                AUTH_URI,
                TOKEN_URI,
            )
            config_entry_oauth2_flow.async_register_implementation(
                self.hass, DOMAIN, implementation
            )

        return await super().async_step_user(user_input)

    async def async_oauth_create_entry(self, data: dict) -> ConfigFlowResult:
        try:
            token_data = data["token"]["access_token"]

            decoded = jwt.decode(token_data, options={"verify_signature": False})

            user_id = decoded.get("sub")

            if not user_id:
                raise KeyError("No 'sub' parameter found in token.")

            await self.async_set_unique_id(user_id)

            self._abort_if_unique_id_configured()

        except (jwt.InvalidTokenError, KeyError):
            _LOGGER.exception("Failed to parse token or extract user ID during setup")
            return self.async_abort(reason="oauth_error")
        return self.async_create_entry(title=f"Desi Smart ({user_id})", data=data)
