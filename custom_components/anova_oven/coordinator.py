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
from .models import AnovaOvenDevice, Nodes

_LOGGER = logging.getLogger(__name__)


class HAAnovaOven(AnovaOven):
    """Home Assistant specific Anova Oven wrapper."""

    def __init__(self, update_callback, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._update_callback = update_callback
        # Register our custom handler for state updates
        self.client.add_callback(self._handle_state_update)

    def _handle_state_update(self, data: dict[str, Any]) -> None:
        """Handle real-time state updates."""
        if data.get('command') == 'EVENT_APO_STATE':
            payload = data.get('payload', {})
            device_id = payload.get('id') or payload.get('cookerId')
            if device_id and device_id in self._devices:
                try:
                    device = self._devices[device_id]
                    # The payload 'state' contains the nodes data
                    state_data = payload.get('state')
                    if state_data and "temperatureBulbs" in state_data:
                        device.nodes = Nodes.model_validate(state_data)
                        self._update_callback()
                    elif state_data:
                        _LOGGER.debug("Received state update without nodes data: %s", state_data.keys())
                except Exception as e:
                    _LOGGER.debug("Failed to process state update: %s", e)

    def _handle_device_list(self, data: dict[str, Any]) -> None:
        """Handle device discovery messages."""
        if data.get('command') == 'EVENT_APO_WIFI_LIST':
            payload = data.get('payload', [])
            for device_data in payload:
                try:
                    device = AnovaOvenDevice.model_validate(device_data)
                    self._devices[device.cooker_id] = device
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