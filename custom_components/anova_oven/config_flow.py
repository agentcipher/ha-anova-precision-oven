"""Config flow for Anova Precision Oven integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_API_TOKEN
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from anova_oven_sdk import AnovaOven
from anova_oven_sdk.settings import settings
from anova_oven_sdk.exceptions import ConfigurationError

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_TOKEN): str,
    }
)


async def validate_input(data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    # Configure SDK with the provided token
    try:
        settings.configure(TOKEN=data[CONF_API_TOKEN])
    except Exception as e:
        _LOGGER.error("Failed to configure Anova SDK settings: %s", e)
        raise CannotConnect from e

    try:
        async with AnovaOven() as oven:
            # Attempt to discover devices to verify connection
            devices = await oven.discover_devices()
            if not devices:
                raise NoDevicesFound
    except ConfigurationError as e:
        _LOGGER.error("Anova SDK configuration error: %s", e)
        raise InvalidAuth from e
    except Exception as e:
        _LOGGER.error("Failed to connect to Anova API: %s", e)
        raise CannotConnect from e

    # Return info that you want to store in the config entry.
    return {"title": "Anova Precision Oven"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Anova Precision Oven."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except NoDevicesFound:
                errors["base"] = "no_devices_found"
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


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class NoDevicesFound(HomeAssistantError):
    """Error to indicate no devices were found."""
