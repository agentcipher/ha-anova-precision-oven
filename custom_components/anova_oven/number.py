"""Number platform for Anova Precision Oven."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, PROBE_TEMP_MAX, PROBE_TEMP_MIN
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
        entities.append(AnovaOvenProbeTarget(coordinator, device_id))

    async_add_entities(entities)


class AnovaOvenProbeTarget(AnovaOvenEntity, NumberEntity):
    """Number entity for probe target temperature."""

    _attr_icon = "mdi:thermometer-probe"
    _attr_native_min_value = PROBE_TEMP_MIN
    _attr_native_max_value = PROBE_TEMP_MAX
    _attr_native_step = 0.5
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: AnovaOvenCoordinator, device_id: str) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, device_id, "probe_target")
        self._attr_name = "Probe Target"

    @property
    def native_value(self) -> float | None:
        """Return the probe target temperature."""
        device = self.coordinator.get_device(self._device_id)
        if not device:
            return None

        return device.nodes.probe.setpoint.value

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not super().available:
            return False

        device = self.coordinator.get_device(self._device_id)
        if not device:
            return False

        return device.nodes.probe.connected or device.nodes.probe.current.value is not None

    async def async_set_native_value(self, value: float) -> None:
        """Set probe target temperature."""
        await self.coordinator.async_set_probe(
            self._device_id, target=value, temperature_unit="C"
        )