"""Number platform for Anova Precision Oven."""
from __future__ import annotations

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from anova_oven_sdk.models import Device

from .const import DOMAIN, TEMP_MAX, TEMP_MIN
from .coordinator import AnovaOvenCoordinator
from .entity import AnovaOvenEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Anova Oven number entities."""
    coordinator: AnovaOvenCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for device_id in coordinator.data:
        entities.append(AnovaOvenProbeNumber(coordinator, device_id))

    async_add_entities(entities)


class AnovaOvenProbeNumber(AnovaOvenEntity, NumberEntity):
    """Number entity for Anova Precision Oven probe."""

    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_min_value = TEMP_MIN
    _attr_native_max_value = TEMP_MAX
    _attr_native_step = 1.0

    def __init__(self, coordinator: AnovaOvenCoordinator, device_id: str) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, device_id, "probe_target")
        self._attr_name = "Probe Target"

    @property
    def native_value(self) -> float | None:
        """Return the value reported by the number."""
        device = self.coordinator.get_device(self._device_id)
        if not device or not device.nodes or not device.nodes.temperature_probe or not device.nodes.temperature_probe.setpoint:
            return None
        return device.nodes.temperature_probe.setpoint.celsius

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        device = self.coordinator.get_device(self._device_id)
        return (
            super().available
            and device is not None
            and device.nodes is not None
            and device.nodes.temperature_probe is not None
            and device.nodes.temperature_probe.connected
        )

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        await self.coordinator.async_set_probe(self._device_id, value, "C")