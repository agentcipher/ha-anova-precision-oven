"""Switch platform for Anova Oven integration."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from anova_oven_sdk.models import DeviceState

from .const import DOMAIN
from .coordinator import AnovaOvenCoordinator
from .entity import AnovaOvenEntity

import logging

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Anova Oven switch entities."""
    coordinator: AnovaOvenCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for device_id in coordinator.data:
        entities.append(AnovaOvenSwitch(coordinator, device_id))

    async_add_entities(entities)


class AnovaOvenSwitch(AnovaOvenEntity, SwitchEntity):
    """Switch entity for Anova Precision Oven."""

    _attr_translation_key = "cooking"
    _attr_icon = "mdi:stove"

    def __init__(
        self,
        coordinator: AnovaOvenCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, device_id, "cooking")
        self._attr_name = "Cooking"

    @property
    def is_on(self) -> bool:
        """Return True if the oven is cooking."""
        device = self.coordinator.get_device(self._device_id)
        if not device:
            return False

        return device.state in (DeviceState.COOKING, DeviceState.PREHEATING)

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on cooking."""
        device = self.coordinator.get_device(self._device_id)

        _LOGGER.debug("Turning on cooking for %s", device.name if device else "unknown")

        # Get last known temperature or use default
        target_temp = 180.0
        if device and device.nodes and device.nodes.temperature_bulbs:
            if device.nodes.temperature_bulbs.mode == "dry" and device.nodes.temperature_bulbs.dry.setpoint:
                target_temp = device.nodes.temperature_bulbs.dry.setpoint.get('celsius', target_temp)

        try:
            await self.coordinator.async_start_cook(
                device_id=self._device_id,
                temperature=target_temp,
                temperature_unit="C",
            )
        except Exception as err:
            _LOGGER.error("Failed to turn on cooking: %s", err)
            raise

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off cooking."""
        try:
            await self.coordinator.async_stop_cook(self._device_id)
        except Exception as err:
            _LOGGER.error("Failed to turn off cooking: %s", err)
            raise