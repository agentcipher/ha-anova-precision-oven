"""Services for Anova Oven integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import async_extract_entity_ids

from homeassistant.components.climate import (
    ATTR_TEMPERATURE,
)

from .const import (
    DOMAIN,
    SERVICE_START_COOK,
    SERVICE_STOP_COOK,
    SERVICE_START_RECIPE,
    SERVICE_SET_PROBE,
    SERVICE_SET_TEMPERATURE_UNIT,
    ATTR_TEMPERATURE_UNIT,
    ATTR_DURATION,
    ATTR_RECIPE_ID,
    ATTR_FAN_SPEED,
)
from .coordinator import AnovaOvenCoordinator

_LOGGER = logging.getLogger(__name__)

# Service schemas
SERVICE_START_COOK_SCHEMA = cv.make_entity_service_schema(
    {
        vol.Required(ATTR_TEMPERATURE): cv.positive_float,
        vol.Optional(ATTR_TEMPERATURE_UNIT, default="C"): vol.In(["C", "F"]),
        vol.Optional(ATTR_DURATION): cv.positive_int,
        vol.Optional(ATTR_FAN_SPEED, default=100): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=100)
        ),
    }
)

SERVICE_START_RECIPE_SCHEMA = cv.make_entity_service_schema(
    {
        vol.Required(ATTR_RECIPE_ID): cv.string,
    }
)

SERVICE_SET_PROBE_SCHEMA = cv.make_entity_service_schema(
    {
        vol.Required("target"): cv.positive_float,
        vol.Optional(ATTR_TEMPERATURE_UNIT, default="C"): vol.In(["C", "F"]),
    }
)

SERVICE_SET_TEMPERATURE_UNIT_SCHEMA = cv.make_entity_service_schema(
    {
        vol.Required("unit"): vol.In(["C", "F"]),
    }
)

SERVICE_STOP_COOK_SCHEMA = cv.make_entity_service_schema({})



async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for Anova Oven integration."""

    async def async_handle_start_cook(call: ServiceCall) -> None:
        """Handle start_cook service call."""
        entity_ids = await async_extract_entity_ids(hass, call)

        for entity_id in entity_ids:
            # Get device_id from entity
            device_id = await _get_device_id_from_entity(hass, entity_id)
            if not device_id:
                continue

            coordinator = await _get_coordinator_for_device(hass, device_id)
            if not coordinator:
                continue

            try:
                await coordinator.async_start_cook(
                    device_id=device_id,
                    temperature=call.data[ATTR_TEMPERATURE],
                    temperature_unit=call.data.get(ATTR_TEMPERATURE_UNIT, "C"),
                    duration=call.data.get(ATTR_DURATION),
                    fan_speed=call.data.get(ATTR_FAN_SPEED, 100),
                )
                _LOGGER.info("Started cooking on %s", entity_id)
            except Exception as err:
                _LOGGER.error("Failed to start cooking on %s: %s", entity_id, err)

    async def async_handle_stop_cook(call: ServiceCall) -> None:
        """Handle stop_cook service call."""
        entity_ids = await async_extract_entity_ids(hass, call)

        for entity_id in entity_ids:
            device_id = await _get_device_id_from_entity(hass, entity_id)
            if not device_id:
                continue

            coordinator = await _get_coordinator_for_device(hass, device_id)
            if not coordinator:
                continue

            try:
                await coordinator.async_stop_cook(device_id)
                _LOGGER.info("Stopped cooking on %s", entity_id)
            except Exception as err:
                _LOGGER.error("Failed to stop cooking on %s: %s", entity_id, err)

    async def async_handle_start_recipe(call: ServiceCall) -> None:
        """Handle start_recipe service call."""
        entity_ids = await async_extract_entity_ids(hass, call)
        recipe_id = call.data[ATTR_RECIPE_ID]

        for entity_id in entity_ids:
            device_id = await _get_device_id_from_entity(hass, entity_id)
            if not device_id:
                continue

            coordinator = await _get_coordinator_for_device(hass, device_id)
            if not coordinator:
                continue

            try:
                await coordinator.async_start_recipe(device_id, recipe_id)
                _LOGGER.info("Started recipe '%s' on %s", recipe_id, entity_id)
            except Exception as err:
                _LOGGER.error(
                    "Failed to start recipe '%s' on %s: %s",
                    recipe_id,
                    entity_id,
                    err,
                )

    async def async_handle_set_probe(call: ServiceCall) -> None:
        """Handle set_probe service call."""
        entity_ids = await async_extract_entity_ids(hass, call)

        for entity_id in entity_ids:
            device_id = await _get_device_id_from_entity(hass, entity_id)
            if not device_id:
                continue

            coordinator = await _get_coordinator_for_device(hass, device_id)
            if not coordinator:
                continue

            try:
                await coordinator.async_set_probe(
                    device_id=device_id,
                    target=call.data["target"],
                    temperature_unit=call.data.get(ATTR_TEMPERATURE_UNIT, "C"),
                )
                _LOGGER.info("Set probe on %s", entity_id)
            except Exception as err:
                _LOGGER.error("Failed to set probe on %s: %s", entity_id, err)

    async def async_handle_set_temperature_unit(call: ServiceCall) -> None:
        """Handle set_temperature_unit service call."""
        entity_ids = await async_extract_entity_ids(hass, call)

        for entity_id in entity_ids:
            device_id = await _get_device_id_from_entity(hass, entity_id)
            if not device_id:
                continue

            coordinator = await _get_coordinator_for_device(hass, device_id)
            if not coordinator:
                continue

            try:
                await coordinator.async_set_temperature_unit(
                    device_id, call.data["unit"]
                )
                _LOGGER.info("Set temperature unit on %s", entity_id)
            except Exception as err:
                _LOGGER.error(
                    "Failed to set temperature unit on %s: %s", entity_id, err
                )

    # Register services
    hass.services.async_register(
        DOMAIN,
        SERVICE_START_COOK,
        async_handle_start_cook,
        schema=SERVICE_START_COOK_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_STOP_COOK,
        async_handle_stop_cook,
        schema=SERVICE_STOP_COOK_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_START_RECIPE,
        async_handle_start_recipe,
        schema=SERVICE_START_RECIPE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_PROBE,
        async_handle_set_probe,
        schema=SERVICE_SET_PROBE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_TEMPERATURE_UNIT,
        async_handle_set_temperature_unit,
        schema=SERVICE_SET_TEMPERATURE_UNIT_SCHEMA,
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload services."""
    hass.services.async_remove(DOMAIN, SERVICE_START_COOK)
    hass.services.async_remove(DOMAIN, SERVICE_STOP_COOK)
    hass.services.async_remove(DOMAIN, SERVICE_START_RECIPE)
    hass.services.async_remove(DOMAIN, SERVICE_SET_PROBE)
    hass.services.async_remove(DOMAIN, SERVICE_SET_TEMPERATURE_UNIT)


async def _get_device_id_from_entity(
    hass: HomeAssistant, entity_id: str
) -> str | None:
    """Get device_id from entity_id."""
    state = hass.states.get(entity_id)
    if state:
        return state.attributes.get("device_id")
    return None


async def _get_coordinator_for_device(
    hass: HomeAssistant, device_id: str
) -> AnovaOvenCoordinator | None:
    """Get coordinator for device."""
    for entry_id, coordinator in hass.data.get(DOMAIN, {}).items():
        if isinstance(coordinator, AnovaOvenCoordinator):
            if device_id in coordinator.data:
                return coordinator
    return None