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

from anova_oven_sdk.models import DeviceState, Device

from .const import DOMAIN
from .coordinator import AnovaOvenCoordinator
from .entity import AnovaOvenEntity


@dataclass(frozen=True)
class AnovaOvenSensorEntityDescription(SensorEntityDescription):
    """Describes Anova Oven sensor entity."""

    value_fn: Callable[[AnovaOvenCoordinator, str], StateType] | None = None
    available_fn: Callable[[AnovaOvenCoordinator, str], bool] | None = None


SENSORS: tuple[AnovaOvenSensorEntityDescription, ...] = (
    AnovaOvenSensorEntityDescription(
        key="current_temperature",
        name="Current Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda coord, device_id: (
            lambda device: (
                device.nodes.temperature_bulbs.dry.current.get('celsius')
                if device.nodes.temperature_bulbs.mode == "dry"
                else device.nodes.temperature_bulbs.wet.current.get('celsius')
            ) if device and device.nodes and device.nodes.temperature_bulbs else None
        )(coord.get_device(device_id)),
    ),
    AnovaOvenSensorEntityDescription(
        key="target_temperature",
        name="Target Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda coord, device_id: (
            lambda device: (
                device.nodes.temperature_bulbs.dry.setpoint.get('celsius')
                if device.nodes.temperature_bulbs.mode == "dry" and device.nodes.temperature_bulbs.dry.setpoint
                else (device.nodes.temperature_bulbs.wet.setpoint.get('celsius') if device.nodes.temperature_bulbs.wet.setpoint else None)
            ) if device and device.nodes and device.nodes.temperature_bulbs else None
        )(coord.get_device(device_id)),
    ),
    AnovaOvenSensorEntityDescription(
        key="probe_temperature",
        name="Probe Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda coord, device_id: (
            lambda device: device.nodes.temperature_probe.current.get('celsius') if device.nodes.temperature_probe and hasattr(device.nodes.temperature_probe, 'current') and device.nodes.temperature_probe.current else None
        )(coord.get_device(device_id)),
        available_fn=lambda coord, device_id: (
            lambda device: device.nodes.temperature_probe.connected if device and device.nodes and device.nodes.temperature_probe else False
        )(coord.get_device(device_id)),
    ),
    AnovaOvenSensorEntityDescription(
        key="probe_target",
        name="Probe Target",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda coord, device_id: (
            lambda device: device.nodes.temperature_probe.setpoint.get('celsius') if device.nodes.temperature_probe and hasattr(device.nodes.temperature_probe, 'setpoint') and device.nodes.temperature_probe.setpoint else None
        )(coord.get_device(device_id)),
        available_fn=lambda coord, device_id: (
            lambda device: device.nodes.temperature_probe.connected if device and device.nodes and device.nodes.temperature_probe else False
        )(coord.get_device(device_id)),
    ),
    AnovaOvenSensorEntityDescription(
        key="timer_remaining",
        name="Timer Remaining",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        value_fn=lambda coord, device_id: (
            lambda device: device.nodes.timer.current if device.nodes.timer else None
        )(coord.get_device(device_id)),
        available_fn=lambda coord, device_id: (
            lambda device: device.nodes.timer.mode != "idle" if device and device.nodes and device.nodes.timer else False
        )(coord.get_device(device_id)),
    ),
    AnovaOvenSensorEntityDescription(
        key="timer_initial",
        name="Timer Initial",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        value_fn=lambda coord, device_id: (
            lambda device: device.nodes.timer.initial if device.nodes.timer else None
        )(coord.get_device(device_id)),
        available_fn=lambda coord, device_id: (
            lambda device: device.nodes.timer.mode != "idle" if device and device.nodes and device.nodes.timer else False
        )(coord.get_device(device_id)),
    ),
    AnovaOvenSensorEntityDescription(
        key="steam_percentage",
        name="Steam Percentage",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda coord, device_id: (
            lambda device: device.nodes.steam_generators.relative_humidity.current if device.nodes.steam_generators and device.nodes.steam_generators.relative_humidity else None
        )(coord.get_device(device_id)),
        available_fn=lambda coord, device_id: (
            lambda device: device.nodes.steam_generators.mode != "idle" if device and device.nodes and device.nodes.steam_generators else False
        )(coord.get_device(device_id)),
    ),
    AnovaOvenSensorEntityDescription(
        key="fan_speed",
        name="Fan Speed",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda coord, device_id: (
            lambda device: device.nodes.fan.speed if device.nodes.fan else None
        )(coord.get_device(device_id)),
    ),
    AnovaOvenSensorEntityDescription(
        key="current_stage",
        name="Current Stage",
        value_fn=lambda coord, device_id: None,  # TODO: Implement when cook data is available
        available_fn=lambda coord, device_id: coord.get_device(device_id).state == DeviceState.COOKING if coord.get_device(device_id) else False,
    ),
    AnovaOvenSensorEntityDescription(
        key="total_stages",
        name="Total Stages",
        value_fn=lambda coord, device_id: None,  # TODO: Implement when cook data is available
        available_fn=lambda coord, device_id: coord.get_device(device_id).state == DeviceState.COOKING if coord.get_device(device_id) else False,
    ),
    AnovaOvenSensorEntityDescription(
        key="recipe_name",
        name="Recipe Name",
        value_fn=lambda coord, device_id: None,  # TODO: Implement when cook data is available
        available_fn=lambda coord, device_id: coord.get_device(device_id).state == DeviceState.COOKING if coord.get_device(device_id) else False,
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
        if not self.entity_description.value_fn:
            return None
        return self.entity_description.value_fn(self.coordinator, self._device_id)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not super().available:
            return False

        if self.entity_description.available_fn:
            return self.entity_description.available_fn(self.coordinator, self._device_id)

        return True