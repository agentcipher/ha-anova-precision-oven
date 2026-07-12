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

from anova_oven_sdk.models import DeviceState

from .const import (
    ATTR_CURRENT_STAGE,
    ATTR_OVEN_VERSION,
    ATTR_RACK_POSITION,
    ATTR_RECIPE_NAME,
    ATTR_STAGES,
    DOMAIN,
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

        if device.state in (DeviceState.COOKING, DeviceState.PREHEATING):
            return HVACMode.HEAT
        return HVACMode.OFF

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        device = self.coordinator.get_device(self._device_id)
        if not device or not device.nodes or not device.nodes.temperature_bulbs:
            return None

        if device.nodes.temperature_bulbs.mode == "dry":
            return device.nodes.temperature_bulbs.dry.current.get('celsius')
        if device.nodes.temperature_bulbs.mode == "wet":
            return device.nodes.temperature_bulbs.wet.current.get('celsius')
        return None

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        device = self.coordinator.get_device(self._device_id)
        if not device or not device.nodes or not device.nodes.temperature_bulbs:
            return None

        if device.nodes.temperature_bulbs.mode == "dry":
            return (
                device.nodes.temperature_bulbs.dry.setpoint.get('celsius')
                if device.nodes.temperature_bulbs.dry.setpoint
                else None
            )
        if device.nodes.temperature_bulbs.mode == "wet":
            return (
                device.nodes.temperature_bulbs.wet.setpoint.get('celsius')
                if device.nodes.temperature_bulbs.wet.setpoint
                else None
            )
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        device = self.coordinator.get_device(self._device_id)

        if not device:
            return {}

        attrs = {
            ATTR_OVEN_VERSION: device.oven_version.value,
        }

        if device.cook:
            # Captured before get_active_recipe_id(), since that call clears
            # _active_recipes[device_id] as a side effect when it detects a
            # cook_id mismatch - reading it after would lose exactly the
            # value we need for comparison in that case.
            tracked = self.coordinator._active_recipes.get(self._device_id)
            recipe_id = self.coordinator.get_active_recipe_id(self._device_id)
            attrs[ATTR_RECIPE_NAME] = (
                self.coordinator.get_recipe_info(recipe_id)["name"]
                if recipe_id
                else "Manual Cook"
            )
            attrs["cook_id"] = device.cook.cook_id
            if tracked:
                attrs["tracked_cook_id"] = tracked[0]
            if device.total_stage_count is not None:
                attrs[ATTR_STAGES] = device.total_stage_count
            if device.current_stage_index is not None:
                attrs[ATTR_CURRENT_STAGE] = device.current_stage_index
            if device.rack_position is not None:
                attrs[ATTR_RACK_POSITION] = device.rack_position

        if device.nodes:
            if device.nodes.temperature_probe and device.nodes.temperature_probe.connected:
                if hasattr(device.nodes.temperature_probe, 'current') and device.nodes.temperature_probe.current:
                    attrs["probe_temperature"] = device.nodes.temperature_probe.current.get('celsius')
                if hasattr(device.nodes.temperature_probe, 'setpoint') and device.nodes.temperature_probe.setpoint:
                    attrs["probe_target"] = device.nodes.temperature_probe.setpoint.get('celsius')

            if device.nodes.steam_generators and device.nodes.steam_generators.mode != "idle":
                steam = device.nodes.steam_generators
                attrs["steam_mode"] = steam.mode
                if steam.mode == "steam-percentage" and steam.steam_percentage:
                    attrs["steam_percentage"] = steam.steam_percentage.current
                elif steam.mode == "relative-humidity" and steam.relative_humidity:
                    attrs["steam_percentage"] = steam.relative_humidity.current

            if device.nodes.timer:
                attrs["timer_mode"] = device.nodes.timer.mode
                attrs["timer_initial"] = device.nodes.timer.initial
                attrs["timer_current"] = device.nodes.timer.current

        return attrs

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        duration = None
        device = self.coordinator.get_device(self._device_id)
        if device and device.nodes and device.nodes.timer and device.nodes.timer.mode != "idle":
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
            target = self.target_temperature or 180.0
            await self.coordinator.async_start_cook(
                self._device_id, temperature=target, temperature_unit="C"
            )