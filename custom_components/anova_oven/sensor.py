"""Sensor platform for Anova Precision Oven."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import DOMAIN, MODE_DRY, STATE_IDLE
from .coordinator import AnovaOvenCoordinator
from .entity import AnovaOvenEntity
from .anova_sdk.models import Device


@dataclass(frozen=True)
class AnovaOvenSensorEntityDescription(SensorEntityDescription):
    """Describes Anova Oven sensor entity."""

    value_fn: Callable[[Device], StateType] | None = None
    available_fn: Callable[[Device], bool] | None = None


SENSORS: tuple[AnovaOvenSensorEntityDescription, ...] = (
    AnovaOvenSensorEntityDescription(
        key="current_temperature",
        name="Current Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda device: (
            device.current_temperature
            if device.current_temperature is not None
            else (
                device.nodes.temperature_bulbs.dry.current.value
                if device.nodes.temperature_bulbs.mode == "dry"
                else device.nodes.temperature_bulbs.wet.current.value
            )
        ),
    ),
    AnovaOvenSensorEntityDescription(
        key="target_temperature",
        name="Target Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda device: (
            device.target_temperature
            if device.target_temperature is not None
            else (
                device.nodes.temperature_bulbs.dry.setpoint.value
                if device.nodes.temperature_bulbs.mode == "dry"
                else device.nodes.temperature_bulbs.wet.setpoint.value
            )
        ),
    ),
    AnovaOvenSensorEntityDescription(
        key="probe_temperature",
        name="Probe Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda device: device.nodes.probe.current.value,
        available_fn=lambda device: device.nodes.probe.connected or device.nodes.probe.current.value is not None,
    ),
    AnovaOvenSensorEntityDescription(
        key="probe_target",
        name="Probe Target",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda device: device.nodes.probe.setpoint.value,
        available_fn=lambda device: device.nodes.probe.connected or device.nodes.probe.setpoint.value is not None,
    ),
    AnovaOvenSensorEntityDescription(
        key="timer_remaining",
        name="Timer Remaining",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        value_fn=lambda device: device.nodes.timer.current,
        available_fn=lambda device: device.nodes.timer.is_running,
    ),
    AnovaOvenSensorEntityDescription(
        key="timer_initial",
        name="Timer Initial",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        value_fn=lambda device: device.nodes.timer.initial,
        available_fn=lambda device: device.nodes.timer.is_running,
    ),
    AnovaOvenSensorEntityDescription(
        key="steam_percentage",
        name="Steam Percentage",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda device: device.nodes.steam_generators.percentage,
        available_fn=lambda device: device.nodes.steam_generators.mode != "idle",
    ),
    AnovaOvenSensorEntityDescription(
        key="fan_speed",
        name="Fan Speed",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda device: device.nodes.fan.speed,
    ),
    AnovaOvenSensorEntityDescription(
        key="current_stage",
        name="Current Stage",
        value_fn=lambda device: (
            device.state.cook.current_stage
            if hasattr(device.state, 'cook') and device.state.cook
            else None
        ),
        available_fn=lambda device: device.is_cooking,
    ),
    AnovaOvenSensorEntityDescription(
        key="total_stages",
        name="Total Stages",
        value_fn=lambda device: (
            len(device.state.cook.stages)
            if hasattr(device.state, 'cook') and device.state.cook and hasattr(device.state.cook, 'stages') and device.state.cook.stages
            else None
        ),
        available_fn=lambda device: device.is_cooking,
    ),
    AnovaOvenSensorEntityDescription(
        key="recipe_name",
        name="Recipe Name",
        value_fn=lambda device: (
            device.state.cook.name
            if hasattr(device.state, 'cook') and device.state.cook
            else None
        ),
        available_fn=lambda device: device.is_cooking,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Anova Oven sensor entities."""
    coordinator: AnovaOvenCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for device_id in coordinator.data:
        for description in SENSORS:
            entities.append(AnovaOvenSensor(coordinator, device_id, description))

    async_add_entities(entities)


class AnovaOvenSensor(AnovaOvenEntity, SensorEntity):
    """Sensor entity for Anova Precision Oven."""

    entity_description: AnovaOvenSensorEntityDescription

    def __init__(
        self,
        coordinator: AnovaOvenCoordinator,
        device_id: str,
        description: AnovaOvenSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id, description.key)
        self.entity_description = description
        self._attr_name = description.name

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        device = self.coordinator.get_device(self._device_id)
        if not device or not self.entity_description.value_fn:
            return None
        return self.entity_description.value_fn(device)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not super().available:
            return False

        device = self.coordinator.get_device(self._device_id)
        if not device:
            return False

        if self.entity_description.available_fn:
            return self.entity_description.available_fn(device)

        return True