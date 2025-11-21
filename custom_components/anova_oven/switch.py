"""Switch platform for Anova Oven integration."""
from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import AnovaOvenCoordinator
from .entity import AnovaOvenEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Anova Oven switch entities from config entry."""
    coordinator: AnovaOvenCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        AnovaOvenCookingSwitch(coordinator, device_id)
        for device_id in coordinator.data
    ]

    async_add_entities(entities)


class AnovaOvenCookingSwitch(AnovaOvenEntity, SwitchEntity):
    """Switch entity to control oven cooking state."""

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
    def device(self):
        """Return the device."""
        return self.coordinator.get_device(self._device_id)

    @property
    def is_on(self) -> bool:
        """Return True if the oven is cooking."""
        device = self.device
        if not device:
            return False

        # Handle DeviceState enum
        if hasattr(device.state, 'value'):
            return device.state.value in ("cooking", "preheating")

        # Handle detailed state
        if hasattr(device.state, 'state'):
            return device.state.state in ("cooking", "preheating")

        # Fallback to is_cooking property
        return device.is_cooking if hasattr(device, 'is_cooking') else False

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on cooking."""
        device = self.device
        _LOGGER.debug("Turning on cooking for %s", device.name if device else "unknown")

        # Get last known temperature or use default
        target_temp = 180.0
        if device:
            # Try to get from simple model first
            if hasattr(device, 'target_temperature') and device.target_temperature:
                target_temp = device.target_temperature
            # Try detailed state
            else:
                temp_bulbs = device.nodes.get("temperatureBulbs", {})
                setpoint = temp_bulbs.get("dry", {}).get("setpoint", {})
                target_temp = setpoint.get("celsius", target_temp)

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
        device = self.device
        _LOGGER.debug("Turning off cooking for %s", device.name if device else "unknown")

        try:
            await self.coordinator.async_stop_cook(self._device_id)
        except Exception as err:
            _LOGGER.error("Failed to turn off cooking: %s", err)
            raise