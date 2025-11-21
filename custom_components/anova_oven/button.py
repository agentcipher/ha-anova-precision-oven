from dataclasses import dataclass
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import AnovaOvenCoordinator
from .entity import AnovaOvenEntity


@dataclass(frozen=True)
class AnovaOvenButtonEntityDescription(ButtonEntityDescription):
    """Describes Anova Oven button entity."""


BUTTONS: tuple[AnovaOvenButtonEntityDescription, ...] = (
    AnovaOvenButtonEntityDescription(
        key="stop_cook",
        name="Stop Cook",
        icon="mdi:stop",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Anova Oven button entities."""
    coordinator: AnovaOvenCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for device_id in coordinator.data:
        for description in BUTTONS:
            entities.append(AnovaOvenButton(coordinator, device_id, description))

    async_add_entities(entities)


class AnovaOvenButton(AnovaOvenEntity, ButtonEntity):
    """Button entity for Anova Precision Oven."""

    entity_description: AnovaOvenButtonEntityDescription

    def __init__(
        self,
        coordinator: AnovaOvenCoordinator,
        device_id: str,
        description: AnovaOvenButtonEntityDescription,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator, device_id, description.key)
        self.entity_description = description
        self._attr_name = description.name

    async def async_press(self) -> None:
        """Handle button press."""
        if self.entity_description.key == "stop_cook":
            await self.coordinator.async_stop_cook(self._device_id)
