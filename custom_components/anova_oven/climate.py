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
        nodes = self.coordinator.get_device_nodes(self._device_id)
        if not nodes or not nodes.temperature_bulbs:
            return None

        if nodes.temperature_bulbs.mode == "dry":
            return nodes.temperature_bulbs.dry.current.get('celsius')
        return nodes.temperature_bulbs.wet.current.get('celsius')

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        nodes = self.coordinator.get_device_nodes(self._device_id)
        if not nodes or not nodes.temperature_bulbs:
            return None

        if nodes.temperature_bulbs.mode == "dry" and nodes.temperature_bulbs.dry.setpoint:
            return nodes.temperature_bulbs.dry.setpoint.get('celsius')
        if nodes.temperature_bulbs.wet.setpoint:
            return nodes.temperature_bulbs.wet.setpoint.get('celsius')
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        device = self.coordinator.get_device(self._device_id)
        nodes = self.coordinator.get_device_nodes(self._device_id)

        if not device:
            return {}

        attrs = {
            ATTR_OVEN_VERSION: device.oven_version.value,
        }

        # TODO: Implement cook data when available
        # if device.cook:
        #     attrs[ATTR_RECIPE_NAME] = device.cook.name or "Manual Cook"
        #     if device.cook.stages:
        #         attrs[ATTR_STAGES] = len(device.cook.stages)
        #         attrs[ATTR_CURRENT_STAGE] = device.cook.current_stage or 0

        if nodes:
            if nodes.temperature_probe and nodes.temperature_probe.connected:
                if hasattr(nodes.temperature_probe, 'current') and nodes.temperature_probe.current:
                    attrs["probe_temperature"] = nodes.temperature_probe.current.get('celsius')
                if hasattr(nodes.temperature_probe, 'setpoint') and nodes.temperature_probe.setpoint:
                    attrs["probe_target"] = nodes.temperature_probe.setpoint.get('celsius')

            if nodes.temperature_bulbs and nodes.temperature_bulbs.mode == "wet":
                if nodes.steam_generators:
                    attrs["steam_mode"] = nodes.steam_generators.mode
                    if nodes.steam_generators.relative_humidity:
                        attrs["steam_percentage"] = nodes.steam_generators.relative_humidity.current

            if nodes.timer and nodes.timer.mode != "idle":
                attrs["timer_mode"] = nodes.timer.mode
                attrs["timer_initial"] = nodes.timer.initial
                attrs["timer_current"] = nodes.timer.current

        return attrs

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        duration = None
        nodes = self.coordinator.get_device_nodes(self._device_id)
        if nodes and nodes.timer and nodes.timer.mode != "idle":
            duration = nodes.timer.initial

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