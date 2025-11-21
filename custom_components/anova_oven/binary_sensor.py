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

from .const import DOMAIN, STATE_COOKING, STATE_PREHEATING
from .coordinator import AnovaOvenCoordinator
from .entity import AnovaOvenEntity
from .anova_sdk.models import Device


@dataclass(frozen=True)
class AnovaOvenBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes Anova Oven binary sensor entity."""

    is_on_fn: Callable[[Device], bool] | None = None


BINARY_SENSORS: tuple[AnovaOvenBinarySensorEntityDescription, ...] = (
    AnovaOvenBinarySensorEntityDescription(
        key="cooking",
        name="Cooking",
        device_class=BinarySensorDeviceClass.RUNNING,
        is_on_fn=lambda device: (
            device.is_cooking
            if hasattr(device, 'is_cooking')
            else (
                device.state.value.lower() in [STATE_COOKING, STATE_PREHEATING]
                if hasattr(device.state, 'value')
                else (
                    device.state.state.lower() in [STATE_COOKING, STATE_PREHEATING]
                    if hasattr(device.state, 'state')
                    else False
                )
            )
        ),
    ),
    AnovaOvenBinarySensorEntityDescription(
        key="preheating",
        name="Preheating",
        device_class=BinarySensorDeviceClass.HEAT,
        is_on_fn=lambda device: (
            device.state.value.lower() == STATE_PREHEATING
            if hasattr(device.state, 'value')
            else (
                device.state.state.lower() == STATE_PREHEATING
                if hasattr(device.state, 'state')
                else False
            )
        ),
    ),
    AnovaOvenBinarySensorEntityDescription(
        key="door_open",
        name="Door",
        device_class=BinarySensorDeviceClass.DOOR,
        is_on_fn=lambda device: (
            device.state.nodes.get("door", {}).get("open", False)
            if hasattr(device, 'state') and hasattr(device.state, 'nodes')
            else False
        ),
    ),
    AnovaOvenBinarySensorEntityDescription(
        key="water_low",
        name="Water Low",
        device_class=BinarySensorDeviceClass.PROBLEM,
        is_on_fn=lambda device: (
            device.state.nodes.get("waterTank", {}).get("low", False)
            if hasattr(device, 'state') and hasattr(device.state, 'nodes')
            else False
        ),
    ),
    AnovaOvenBinarySensorEntityDescription(
        key="probe_connected",
        name="Probe Connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        is_on_fn=lambda device: (
            device.state.nodes.get("probe", {}).get("connected", False)
            if hasattr(device, 'state') and hasattr(device.state, 'nodes')
            else False
        ),
    ),
    AnovaOvenBinarySensorEntityDescription(
        key="vent_open",
        name="Vent",
        device_class=BinarySensorDeviceClass.OPENING,
        is_on_fn=lambda device: (
            device.state.nodes.get("exhaustVent", {}).get("state") == "open"
            if hasattr(device, 'state') and hasattr(device.state, 'nodes')
            else False
        ),
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
        device = self.coordinator.get_device(self._device_id)
        if not device or not self.entity_description.is_on_fn:
            return False
        return self.entity_description.is_on_fn(device)