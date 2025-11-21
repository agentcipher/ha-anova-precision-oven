"""Base entity for Anova Precision Oven."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AnovaOvenCoordinator


class AnovaOvenEntity(CoordinatorEntity[AnovaOvenCoordinator]):
    """Base entity for Anova Oven."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: AnovaOvenCoordinator, device_id: str, entity_type: str | None = None
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._device_id = device_id
        if entity_type:
            self._attr_unique_id = f"{device_id}_{entity_type}"
        else:
            self._attr_unique_id = device_id

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        device = self.coordinator.get_device(self._device_id)
        if not device:
            return DeviceInfo(
                identifiers={(DOMAIN, self._device_id)},
                name=f"Anova Oven {self._device_id}",
            )

        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=device.name or f"Anova Oven {self._device_id}",
            manufacturer="Anova",
            model=f"Precision Oven {device.oven_version.value}",
            sw_version=device.firmware_version,
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            super().available
            and self.coordinator.get_device(self._device_id) is not None
        )