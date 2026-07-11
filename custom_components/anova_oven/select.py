"""Select platform for Anova Precision Oven."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN
from .coordinator import AnovaOvenCoordinator
from .entity import AnovaOvenEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Anova Oven select entities."""
    coordinator: AnovaOvenCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for device_id in coordinator.data:
        entities.append(AnovaOvenRecipeSelect(coordinator, device_id))
        entities.append(AnovaOvenTemperatureUnitSelect(coordinator, device_id))

    async_add_entities(entities)


class AnovaOvenRecipeSelect(AnovaOvenEntity, SelectEntity, RestoreEntity):
    """Select entity for choosing recipes."""

    _attr_icon = "mdi:book-open-variant"

    def __init__(self, coordinator: AnovaOvenCoordinator, device_id: str) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator, device_id, "recipe_select")
        self._attr_name = "Recipe"
        self._attr_options = self._get_recipe_options()

    async def async_added_to_hass(self) -> None:
        """Restore the last known recipe selection, if any.

        This is a best-effort restore: it seeds coordinator state so the
        UI doesn't flash back to "None" on reload while a cook is still
        genuinely in progress, but does not claim to know the real
        cook_id, so get_active_recipe_id() will confirm/adopt it against
        device.cook.cook_id as soon as the next state update arrives.
        """
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if (
            last_state
            and last_state.state in self._attr_options
            and last_state.state != "None"
            and self._device_id not in self.coordinator._active_recipes
        ):
            self.coordinator._active_recipes[self._device_id] = (
                None,
                last_state.state,
            )

    def _get_recipe_options(self) -> list[str]:
        """Get available recipe options."""
        recipes = self.coordinator.get_available_recipes()
        if not recipes:
            return ["None"]
        return ["None"] + recipes

    @property
    def current_option(self) -> str | None:
        """Return the current recipe."""
        recipe_id = self.coordinator.get_active_recipe_id(self._device_id)
        return recipe_id if recipe_id else "None"

    @property
    def options(self) -> list[str]:
        """Return available options."""
        return self._attr_options

    async def async_select_option(self, option: str) -> None:
        """Select a recipe."""
        if option == "None":
            # Stop cooking if "None" is selected
            await self.coordinator.async_stop_cook(self._device_id)
        else:
            # Start the selected recipe
            await self.coordinator.async_start_recipe(self._device_id, option)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        current = self.current_option
        if not current or current == "None":
            return {}

        recipe_info = self.coordinator.get_recipe_info(current)
        if recipe_info:
            return {
                "recipe_description": recipe_info.get("description"),
                "recipe_stages": recipe_info.get("stages"),
                "oven_version": recipe_info.get("oven_version"),
            }

        return {}


class AnovaOvenTemperatureUnitSelect(AnovaOvenEntity, SelectEntity):
    """Select entity for temperature unit."""

    _attr_icon = "mdi:thermometer"
    _attr_options = ["C", "F"]

    def __init__(self, coordinator: AnovaOvenCoordinator, device_id: str) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator, device_id, "temperature_unit")
        self._attr_name = "Temperature Unit"

    @property
    def current_option(self) -> str | None:
        """Return the current temperature unit."""
        device = self.coordinator.get_device(self._device_id)
        if device and device.state_info and hasattr(device.state_info, 'temperature_unit') and device.state_info.temperature_unit:
            return device.state_info.temperature_unit
        return "C"

    async def async_select_option(self, option: str) -> None:
        """Select temperature unit."""
        await self.coordinator.async_set_temperature_unit(self._device_id, option)