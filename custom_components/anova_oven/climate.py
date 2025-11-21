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

        # Handle both simple DeviceState enum and detailed state
        if hasattr(device.state, 'value'):
            # It's a DeviceState enum
            state = device.state.value.lower()
        else:
            # It's a detailed state object, state might be elsewhere
            return HVACMode.OFF if not device.is_cooking else HVACMode.HEAT

        if state in [STATE_COOKING, STATE_PREHEATING]:
            return HVACMode.HEAT
        return HVACMode.OFF

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        device = self.coordinator.get_device(self._device_id)
        if not device:
            return None

        # Use simple current_temperature if available
        if hasattr(device, 'current_temperature') and device.current_temperature is not None:
            return device.current_temperature

        # Try detailed state if available
        if hasattr(device, 'state') and hasattr(device.state, 'nodes'):
            temp_bulbs = device.state.nodes.get("temperatureBulbs", {})
            mode = temp_bulbs.get("mode", MODE_DRY)

            if mode in temp_bulbs:
                current = temp_bulbs[mode].get("current", {})
                return current.get("celsius")

        return None

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        device = self.coordinator.get_device(self._device_id)
        if not device:
            return None

        # Use simple target_temperature if available
        if hasattr(device, 'target_temperature') and device.target_temperature is not None:
            return device.target_temperature

        # Try detailed state if available
        if hasattr(device, 'state') and hasattr(device.state, 'nodes'):
            temp_bulbs = device.state.nodes.get("temperatureBulbs", {})
            mode = temp_bulbs.get("mode", MODE_DRY)

            if mode in temp_bulbs:
                setpoint = temp_bulbs[mode].get("setpoint", {})
                return setpoint.get("celsius")

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

        # Only try to access detailed state if it exists
        if not hasattr(device, 'state') or not hasattr(device.state, 'nodes'):
            return attrs

        # Add cooking information if available
        if hasattr(device.state, 'cook') and device.state.cook:
            cook = device.state.cook
            attrs[ATTR_RECIPE_NAME] = cook.name or "Manual Cook"
            if hasattr(cook, 'stages') and cook.stages:
                attrs[ATTR_STAGES] = len(cook.stages)
                attrs[ATTR_CURRENT_STAGE] = getattr(cook, 'current_stage', 0) or 0

        # Add probe temperature if available
        probe_node = device.state.nodes.get("probe", {})
        if probe_node:
            probe_temp = probe_node.get("current", {}).get("celsius")
            if probe_temp is not None:
                attrs["probe_temperature"] = probe_temp
            probe_setpoint = probe_node.get("setpoint", {}).get("celsius")
            if probe_setpoint is not None:
                attrs["probe_target"] = probe_setpoint

        # Add steam information if in wet mode
        temp_bulbs = device.state.nodes.get("temperatureBulbs", {})
        if temp_bulbs.get("mode") == MODE_WET:
            steam = device.state.nodes.get("steamGenerators", {})
            if steam:
                attrs["steam_mode"] = steam.get("mode")
                attrs["steam_percentage"] = steam.get("relativeOutput", {}).get("percentage")

        # Add timer information
        timer_node = device.state.nodes.get("timer", {})
        if timer_node:
            attrs["timer_mode"] = timer_node.get("mode")
            attrs["timer_initial"] = timer_node.get("initial")
            attrs["timer_current"] = timer_node.get("current")

        return attrs

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        # Determine duration from timer if currently cooking
        duration = None
        device = self.coordinator.get_device(self._device_id)
        if device and hasattr(device, 'state') and hasattr(device.state, 'nodes'):
            timer_node = device.state.nodes.get("timer", {})
            if timer_node and timer_node.get("mode") != "idle":
                duration = timer_node.get("initial")

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