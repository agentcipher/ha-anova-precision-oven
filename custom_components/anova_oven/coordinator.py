"""DataUpdateCoordinator for Anova Precision Oven."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_TOKEN, CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from anova_oven_sdk import AnovaOven
from anova_oven_sdk.settings import settings
from anova_oven_sdk.models import RecipeLibrary
from anova_oven_sdk.exceptions import AnovaError

from .const import DOMAIN, CONF_RECIPES_PATH, RECIPES_FILE
from .models import AnovaOvenDevice, Nodes, State, SystemInfo

_LOGGER = logging.getLogger(__name__)


class HAAnovaOven(AnovaOven):
    """Home Assistant specific Anova Oven wrapper."""

    def __init__(self, update_callback, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._update_callback = update_callback
        # Register our custom handler for state updates
        self.client.add_callback(self._handle_state_update)

    def _handle_state_update(self, data: dict[str, Any]) -> None:
        """Handle real-time state updates from WebSocket.

        Expected payload structure:
        {
            "command": "EVENT_APO_STATE",
            "payload": {
                "id": "device_id",  # or "cookerId"
                "version": 1,
                "updatedTimestamp": "...",
                "systemInfo": {...},
                "state": {
                    "mode": "idle",
                    "temperatureUnit": "F",
                    "processedCommandIds": [...]
                },
                "nodes": {
                    "temperatureBulbs": {...},
                    "timer": {...},
                    ...
                }
            }
        }
        """
        if data.get('command') != 'EVENT_APO_STATE':
            return

        payload = data.get('payload', {})
        device_id = payload.get('id') or payload.get('cookerId')

        if not device_id:
            _LOGGER.warning("Received EVENT_APO_STATE without device ID: %s", payload.keys())
            return

        if device_id not in self._devices:
            _LOGGER.debug("Received state update for unknown device: %s", device_id)
            return

        try:
            device = self._devices[device_id]
            updated = False

            # Update nodes if present
            if "nodes" in payload:
                try:
                    device.nodes = Nodes.model_validate(payload["nodes"])
                    updated = True
                    _LOGGER.debug("Updated nodes for device %s", device_id)
                except Exception as e:
                    _LOGGER.warning("Failed to validate nodes data: %s", e)
                    _LOGGER.debug("Nodes data: %s", payload["nodes"])

            # Update state if present
            if "state" in payload:
                try:
                    device.state = State.model_validate(payload["state"])
                    updated = True
                    _LOGGER.debug("Updated state for device %s: mode=%s, unit=%s",
                                device_id, device.state.mode, device.state.temperature_unit)
                except Exception as e:
                    _LOGGER.warning("Failed to validate state data: %s", e)
                    _LOGGER.debug("State data: %s", payload["state"])

            # Update system info if present
            if "systemInfo" in payload:
                try:
                    device.system_info = SystemInfo.model_validate(payload["systemInfo"])
                    updated = True
                    _LOGGER.debug("Updated system info for device %s", device_id)
                except Exception as e:
                    _LOGGER.warning("Failed to validate system info: %s", e)

            # Update version and timestamp if present
            if "version" in payload:
                device.version = payload["version"]
                updated = True

            if "updatedTimestamp" in payload:
                device.updated_timestamp = payload["updatedTimestamp"]
                updated = True

            # Trigger coordinator update if we updated anything
            if updated:
                self._update_callback()
            else:
                _LOGGER.debug("Received state update but found nothing to update. Payload keys: %s",
                            payload.keys())

        except Exception as e:
            _LOGGER.error("Failed to process state update for device %s: %s", device_id, e, exc_info=True)

    def _handle_device_list(self, data: dict[str, Any]) -> None:
        """Handle device discovery messages."""
        if data.get('command') == 'EVENT_APO_WIFI_LIST':
            payload = data.get('payload', [])
            for device_data in payload:
                try:
                    device = AnovaOvenDevice.model_validate(device_data)
                    self._devices[device.cooker_id] = device
                    _LOGGER.debug("Discovered device: %s", device.cooker_id)
                except Exception as e:
                    _LOGGER.error("Device validation error: %s", e)


class AnovaOvenCoordinator(DataUpdateCoordinator[dict[str, AnovaOvenDevice]]):
    """Class to manage fetching Anova Oven data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize global Anova Oven data updater."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )
        self.entry = entry

        # Try to find the token in various keys
        self.api_token = entry.data.get(CONF_API_TOKEN)
        if not self.api_token:
            self.api_token = entry.data.get(CONF_TOKEN)
        if not self.api_token:
            self.api_token = entry.data.get("access_token")

        if not self.api_token:
            _LOGGER.error("API token not found in config entry data: %s", entry.data.keys())
            raise ConfigEntryAuthFailed("API token missing")

        self.recipe_library: RecipeLibrary | None = None

        # Configure settings
        settings.configure(TOKEN=self.api_token)

        self.anova_oven = HAAnovaOven(self.async_set_updated_data_from_callback)

    def async_set_updated_data_from_callback(self):
        """Trigger update from callback."""
        self.async_set_updated_data(self.anova_oven._devices)

    async def _async_update_data(self) -> dict[str, AnovaOvenDevice]:
        """Fetch data from API endpoint."""
        try:
            if not self.anova_oven.client.is_connected:
                await self.anova_oven.connect()

            # Discovery updates the devices list
            await self.anova_oven.discover_devices()

            # Load recipes if not loaded
            if not self.recipe_library:
                await self._load_recipes()

            return self.anova_oven._devices
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    async def _load_recipes(self) -> None:
        """Load recipe library."""
        try:
            recipes_path = self.entry.data.get(CONF_RECIPES_PATH)
            if recipes_path:
                self.recipe_library = await self.hass.async_add_executor_job(
                    RecipeLibrary.from_yaml_file, recipes_path
                )
            else:
                # Try default location
                config_path = self.hass.config.path(RECIPES_FILE)
                try:
                    self.recipe_library = await self.hass.async_add_executor_job(
                        RecipeLibrary.from_yaml_file, config_path
                    )
                except FileNotFoundError:
                    self.recipe_library = RecipeLibrary(recipes={})
        except Exception as err:
            _LOGGER.warning("Failed to load recipes: %s", err)
            self.recipe_library = RecipeLibrary(recipes={})

    def get_device(self, device_id: str) -> AnovaOvenDevice | None:
        """Get device by ID."""
        return self.data.get(device_id)

    def get_available_recipes(self) -> list[str]:
        """Get list of available recipe IDs."""
        if not self.recipe_library:
            return []
        return self.recipe_library.list_recipes()

    async def async_start_cook(self, device_id: str, **kwargs) -> None:
        """Start cooking."""
        await self.anova_oven.start_cook(device_id, **kwargs)
        await self.async_request_refresh()

    async def async_stop_cook(self, device_id: str) -> None:
        """Stop cooking."""
        await self.anova_oven.stop_cook(device_id)
        await self.async_request_refresh()

    async def async_set_probe(self, device_id: str, target: float, temperature_unit: str = "C") -> None:
        """Set probe temperature."""
        await self.anova_oven.set_probe(device_id, target, temperature_unit)
        await self.async_request_refresh()

    async def async_set_temperature_unit(self, device_id: str, unit: str) -> None:
        """Set temperature unit."""
        await self.anova_oven.set_temperature_unit(device_id, unit)
        await self.async_request_refresh()

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator."""
        await self.anova_oven.disconnect()
        await super().async_shutdown()