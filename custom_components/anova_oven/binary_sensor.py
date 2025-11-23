"""Binary sensor platform for Anova Precision Oven."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from anova_oven_sdk.models import DeviceState

from .coordinator import AnovaOvenCoordinator
from .entity import AnovaOvenEntity
from .const import DOMAIN


@dataclass(frozen=True)
class AnovaOvenBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes Anova Oven binary sensor entity."""

    is_on_fn: Callable[[AnovaOvenCoordinator, str], bool] | None = None


BINARY_SENSORS: tuple[AnovaOvenBinarySensorEntityDescription, ...] = (
    AnovaOvenBinarySensorEntityDescription(
        key="cooking",
        name="Cooking",
        device_class=BinarySensorDeviceClass.RUNNING,
        is_on_fn=lambda coord, device_id: (
            coord.get_device(device_id).state in (DeviceState.COOKING, DeviceState.PREHEATING)
            if coord.get_device(device_id) else False
        ),
    ),
    AnovaOvenBinarySensorEntityDescription(
        key="preheating",
        name="Preheating",
        device_class=BinarySensorDeviceClass.HEAT,
        is_on_fn=lambda coord, device_id: (
            coord.get_device(device_id).state == DeviceState.PREHEATING
            if coord.get_device(device_id) else False
        ),
    ),
    AnovaOvenBinarySensorEntityDescription(
        key="probe_connected",
        name="Probe Connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        is_on_fn=lambda coord, device_id: (
            lambda device: device.nodes.temperature_probe.connected if device and device.nodes and device.nodes.temperature_probe else False
        )(coord.get_device(device_id)),
    ),
    AnovaOvenBinarySensorEntityDescription(
        key="vent_open",
        name="Vent",
        device_class=BinarySensorDeviceClass.OPENING,
        is_on_fn=lambda coord, device_id: (
            lambda device: device.nodes.vent.open if device and device.nodes and device.nodes.vent else False
        )(coord.get_device(device_id)),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Anova Oven binary sensor entities."""
    coordinator: AnovaOvenCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for device_id in coordinator.data:
        for description in BINARY_SENSORS:
            entities.append(
                AnovaOvenBinarySensor(coordinator, device_id, description)
            )

    async_add_entities(entities)


class AnovaOvenBinarySensor(AnovaOvenEntity, BinarySensorEntity):
    """Binary sensor entity for Anova Precision Oven."""

    entity_description: AnovaOvenBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: AnovaOvenCoordinator,
        device_id: str,
        description: AnovaOvenBinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, device_id, description.key)
        self.entity_description = description
        self._attr_name = description.name

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        if not self.entity_description.is_on_fn:
            return False
        return self.entity_description.is_on_fn(self.coordinator, self._device_id)