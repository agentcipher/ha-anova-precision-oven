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
            if hasattr(device, 'current_temperature') and device.current_temperature is not None
            else (
                device.state.nodes.get("temperatureBulbs", {})
                .get(device.state.nodes.get("temperatureBulbs", {}).get("mode", MODE_DRY), {})
                .get("current", {})
                .get("celsius")
                if hasattr(device, 'state') and hasattr(device.state, 'nodes')
                else None
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
            if hasattr(device, 'target_temperature') and device.target_temperature is not None
            else (
                device.state.nodes.get("temperatureBulbs", {})
                .get(device.state.nodes.get("temperatureBulbs", {}).get("mode", MODE_DRY), {})
                .get("setpoint", {})
                .get("celsius")
                if hasattr(device, 'state') and hasattr(device.state, 'nodes')
                else None
            )
        ),
    ),
    AnovaOvenSensorEntityDescription(
        key="probe_temperature",
        name="Probe Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda device: (
            device.state.nodes.get("probe", {}).get("current", {}).get("celsius")
            if hasattr(device, 'state') and hasattr(device.state, 'nodes')
            else None
        ),
        available_fn=lambda device: (
            hasattr(device, 'state')
            and hasattr(device.state, 'nodes')
            and device.state.nodes.get("probe") is not None
            and device.state.nodes.get("probe", {}).get("current") is not None
        ),
    ),
    AnovaOvenSensorEntityDescription(
        key="probe_target",
        name="Probe Target",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda device: (
            device.state.nodes.get("probe", {}).get("setpoint", {}).get("celsius")
            if hasattr(device, 'state') and hasattr(device.state, 'nodes')
            else None
        ),
        available_fn=lambda device: (
            hasattr(device, 'state')
            and hasattr(device.state, 'nodes')
            and device.state.nodes.get("probe") is not None
            and device.state.nodes.get("probe", {}).get("setpoint") is not None
        ),
    ),
    AnovaOvenSensorEntityDescription(
        key="timer_remaining",
        name="Timer Remaining",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        value_fn=lambda device: (
            device.state.nodes.get("timer", {}).get("current")
            if hasattr(device, 'state') and hasattr(device.state, 'nodes')
            else None
        ),
        available_fn=lambda device: (
            hasattr(device, 'state')
            and hasattr(device.state, 'nodes')
            and device.state.nodes.get("timer") is not None
            and device.state.nodes.get("timer", {}).get("mode") != "idle"
        ),
    ),
    AnovaOvenSensorEntityDescription(
        key="timer_initial",
        name="Timer Initial",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        value_fn=lambda device: (
            device.state.nodes.get("timer", {}).get("initial")
            if hasattr(device, 'state') and hasattr(device.state, 'nodes')
            else None
        ),
        available_fn=lambda device: (
            hasattr(device, 'state')
            and hasattr(device.state, 'nodes')
            and device.state.nodes.get("timer") is not None
            and device.state.nodes.get("timer", {}).get("mode") != "idle"
        ),
    ),
    AnovaOvenSensorEntityDescription(
        key="steam_percentage",
        name="Steam Percentage",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda device: (
            device.state.nodes.get("steamGenerators", {})
            .get("relativeOutput", {})
            .get("percentage")
            if hasattr(device, 'state') and hasattr(device.state, 'nodes')
            else None
        ),
        available_fn=lambda device: (
            hasattr(device, 'state')
            and hasattr(device.state, 'nodes')
            and device.state.nodes.get("steamGenerators") is not None
            and device.state.nodes.get("steamGenerators", {}).get("mode") != "idle"
        ),
    ),
    AnovaOvenSensorEntityDescription(
        key="fan_speed",
        name="Fan Speed",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda device: (
            device.state.nodes.get("fan", {}).get("speed")
            if hasattr(device, 'state') and hasattr(device.state, 'nodes')
            else None
        ),
    ),
    AnovaOvenSensorEntityDescription(
        key="current_stage",
        name="Current Stage",
        value_fn=lambda device: (
            device.state.cook.current_stage
            if hasattr(device, 'state') and hasattr(device.state, 'cook') and device.state.cook
            else None
        ),
        available_fn=lambda device: (
            hasattr(device, 'state')
            and hasattr(device.state, 'cook')
            and device.state.cook is not None
            and hasattr(device.state, 'state')
            and device.state.state.lower() != STATE_IDLE
        ),
    ),
    AnovaOvenSensorEntityDescription(
        key="total_stages",
        name="Total Stages",
        value_fn=lambda device: (
            len(device.state.cook.stages)
            if hasattr(device, 'state') and hasattr(device.state, 'cook') and device.state.cook and hasattr(device.state.cook, 'stages') and device.state.cook.stages
            else None
        ),
        available_fn=lambda device: (
            hasattr(device, 'state')
            and hasattr(device.state, 'cook')
            and device.state.cook is not None
            and hasattr(device.state, 'state')
            and device.state.state.lower() != STATE_IDLE
        ),
    ),
    AnovaOvenSensorEntityDescription(
        key="recipe_name",
        name="Recipe Name",
        value_fn=lambda device: (
            device.state.cook.name
            if hasattr(device, 'state') and hasattr(device.state, 'cook') and device.state.cook
            else None
        ),
        available_fn=lambda device: (
            hasattr(device, 'state')
            and hasattr(device.state, 'cook')
            and device.state.cook is not None
            and hasattr(device.state, 'state')
            and device.state.state.lower() != STATE_IDLE
        ),
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