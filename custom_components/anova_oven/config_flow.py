"""Config flow for Anova Precision Oven integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from custom_components.anova_oven.anova_sdk.oven import AnovaOven

from homeassistant import config_entries
from homeassistant.const import CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import (
    CONF_ENVIRONMENT,
    CONF_RECIPES_PATH,
    CONF_WS_URL,
    DEFAULT_WS_URL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_TOKEN): str,
        vol.Optional(CONF_WS_URL, default=DEFAULT_WS_URL): str,
        vol.Optional(CONF_ENVIRONMENT, default="production"): vol.In(
            ["dev", "staging", "production"]
        ),
        vol.Optional(CONF_RECIPES_PATH, default=""): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """
    Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    # Import here to avoid circular imports
    from .anova_sdk.oven import AnovaOven
    from .anova_sdk.exceptions import AnovaError

    # Validate token format
    token = data[CONF_TOKEN]
    if not token.startswith("anova-"):
        raise InvalidToken("Token must start with 'anova-'")

    # Try to connect and discover devices
    try:
        async with AnovaOven(environment=data.get(CONF_ENVIRONMENT)) as oven:
            # Override settings with user input
            oven.client.ws_url = data.get(CONF_WS_URL, DEFAULT_WS_URL)
            devices = await oven.discover_devices(timeout=5.0)

            if not devices:
                raise CannotConnect("No devices found")

            return {
                "title": f"Anova Oven ({len(devices)} device(s))",
                "device_count": len(devices),
            }
    except AnovaError as err:
        _LOGGER.error("Failed to connect to Anova: %s", err)
        raise CannotConnect(f"Connection failed: {err}") from err
    except Exception as err:
        _LOGGER.exception("Unexpected exception during validation")
        raise CannotConnect(f"Unexpected error: {err}") from err


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Anova Precision Oven."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidToken:
                errors["base"] = "invalid_token"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidToken(HomeAssistantError):
    """Error to indicate the token is invalid."""
