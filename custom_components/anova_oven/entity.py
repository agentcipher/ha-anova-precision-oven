"""Base entity for Anova Precision Oven."""
from __future__ import annotations

import logging

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AnovaOvenCoordinator

_LOGGER = logging.getLogger(__name__)


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

    @callback
    def _handle_coordinator_update(self) -> None:
        """Diagnostic only: confirms HA's own listener-notification
        mechanism (coordinator.async_update_listeners()) actually reaches
        this entity, closing the last unverified link in the chain from
        SDK message -> coordinator callback -> entity re-render."""
        _LOGGER.info(
            "[%s] _handle_coordinator_update fired for %s",
            self.coordinator._instance_id,
            self._attr_unique_id,
        )
        super()._handle_coordinator_update()

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
            sw_version=device.system_info.firmware_version if device.system_info else None,
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        device = self.coordinator.get_device(self._device_id)
        return (
            self.coordinator.last_update_success
            and device is not None
            and device.nodes is not None
        )