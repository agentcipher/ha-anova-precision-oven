"""Climate platform for Anova Precision Oven."""
from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ATTR_CURRENT_STAGE,
    ATTR_OVEN_VERSION,
    ATTR_RECIPE_NAME,
    ATTR_STAGES,
    DOMAIN,
    MODE_DRY,
    MODE_WET,
    STATE_COOKING,
    STATE_IDLE,
    STATE_PREHEATING,
    TEMP_MAX,
    TEMP_MIN,
)
from .coordinator import AnovaOvenCoordinator
from .entity import AnovaOvenEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Anova Oven climate entities."""
    coordinator: AnovaOvenCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for device_id in coordinator.data:
        entities.append(AnovaOvenClimate(coordinator, device_id))

    async_add_entities(entities)


class AnovaOvenClimate(AnovaOvenEntity, ClimateEntity):
    """Climate entity for Anova Precision Oven."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
    _attr_min_temp = TEMP_MIN
    _attr_max_temp = TEMP_MAX
    _attr_target_temperature_step = 1.0

    def __init__(self, coordinator: AnovaOvenCoordinator, device_id: str) -> None:
        """Initialize the climate entity."""
        super().__init__(coordinator, device_id, "climate")
        self._attr_name = "Oven"

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode."""
        device = self.coordinator.get_device(self._device_id)
        if not device:
            return HVACMode.OFF

        if device.is_cooking:
            return HVACMode.HEAT
        return HVACMode.OFF

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        device = self.coordinator.get_device(self._device_id)
        if not device:
            return None

        # Use simple current_temperature if available
        if device.current_temperature is not None:
            return device.current_temperature

        # Try detailed state
        if device.nodes.temperature_bulbs.mode == "dry":
            return device.nodes.temperature_bulbs.dry.current.value
        return device.nodes.temperature_bulbs.wet.current.value

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        device = self.coordinator.get_device(self._device_id)
        if not device:
            return None

        # Use simple target_temperature if available
        if device.target_temperature is not None:
            return device.target_temperature

        # Try detailed state
        if device.nodes.temperature_bulbs.mode == "dry":
            return device.nodes.temperature_bulbs.dry.setpoint.value
        return device.nodes.temperature_bulbs.wet.setpoint.value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        device = self.coordinator.get_device(self._device_id)
        if not device:
            return {}

        attrs = {
            ATTR_OVEN_VERSION: device.oven_version.value,
        }

        # Add cooking information if available
        if hasattr(device.state, 'cook') and device.state.cook:
            cook = device.state.cook
            attrs[ATTR_RECIPE_NAME] = cook.name or "Manual Cook"
            if hasattr(cook, 'stages') and cook.stages:
                attrs[ATTR_STAGES] = len(cook.stages)
                attrs[ATTR_CURRENT_STAGE] = getattr(cook, 'current_stage', 0) or 0

        # Add probe temperature if available
        if device.nodes.probe.connected or device.nodes.probe.current.value is not None:
            attrs["probe_temperature"] = device.nodes.probe.current.value
            attrs["probe_target"] = device.nodes.probe.setpoint.value

        # Add steam information if in wet mode
        if device.nodes.temperature_bulbs.mode == "wet":
            attrs["steam_mode"] = device.nodes.steam_generators.mode
            attrs["steam_percentage"] = device.nodes.steam_generators.percentage

        # Add timer information
        if device.nodes.timer.is_running:
            attrs["timer_mode"] = device.nodes.timer.mode
            attrs["timer_initial"] = device.nodes.timer.initial
            attrs["timer_current"] = device.nodes.timer.current

        return attrs

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        # Determine duration from timer if currently cooking
        duration = None
        device = self.coordinator.get_device(self._device_id)
        if device and device.nodes.timer.is_running:
            duration = device.nodes.timer.initial

        await self.coordinator.async_start_cook(
            self._device_id,
            temperature=temperature,
            temperature_unit="C",
            duration=duration,
        )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode."""
        if hvac_mode == HVACMode.OFF:
            await self.coordinator.async_stop_cook(self._device_id)
        elif hvac_mode == HVACMode.HEAT:
            # Start with default temperature if not already set
            target = self.target_temperature or 180.0
            await self.coordinator.async_start_cook(
                self._device_id, temperature=target, temperature_unit="C"
            )