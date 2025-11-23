"""DataUpdateCoordinator for Anova Precision Oven."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Dict

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_TOKEN, CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from anova_oven_sdk import AnovaOven
from anova_oven_sdk.settings import settings
from anova_oven_sdk.models import RecipeLibrary, DeviceState, Device
from anova_oven_sdk.exceptions import AnovaError

from .const import DOMAIN, CONF_RECIPES_PATH, RECIPES_FILE

_LOGGER = logging.getLogger(__name__)


class AnovaOvenCoordinator(DataUpdateCoordinator[dict[str, Device]]):
    """Class to manage fetching Anova Oven data.

    Primarily uses WebSocket for real-time updates.
    Polls infrequently (5 minutes) only to verify connection health.
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize global Anova Oven data updater."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            # Very infrequent polling - only for connection health checks
            # WebSocket provides real-time updates
            update_interval=timedelta(minutes=5),
        )
        self.entry = entry
        self._initial_setup_done = False

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

        self.anova_oven = AnovaOven()

        # Add callback to trigger coordinator updates when SDK receives state updates
        self.anova_oven.client.add_callback(self._handle_state_update_callback)

    def _handle_state_update_callback(self, data: dict[str, Any]) -> None:
        """Callback to trigger coordinator update when SDK receives state updates."""
        command = data.get('command')
        if command == 'EVENT_APO_STATE':
            _LOGGER.debug("Received state update, triggering coordinator refresh")
            self.async_set_updated_data(self.anova_oven._devices)

    async def _async_update_data(self) -> dict[str, Device]:
        """Connection health check and initial setup.

        Initial run: Connect, discover devices, load recipes
        Subsequent runs: Just verify WebSocket is still connected
        """
        try:
            # Initial setup on first run
            if not self._initial_setup_done:
                _LOGGER.info("Performing initial setup (connect, discover, load recipes)")

                # Connect WebSocket
                if not self.anova_oven.client.is_connected:
                    await self.anova_oven.connect()

                # Initial device discovery
                await self.anova_oven.discover_devices()

                # Load recipes
                if not self.recipe_library:
                    await self._load_recipes()

                self._initial_setup_done = True
                _LOGGER.info("Initial setup complete - WebSocket active for real-time updates")
            else:
                # Just verify connection health
                if not self.anova_oven.client.is_connected:
                    _LOGGER.warning("WebSocket disconnected, reconnecting...")
                    await self.anova_oven.connect()
                    # Rediscover devices after reconnection
                    await self.anova_oven.discover_devices()
                else:
                    _LOGGER.debug("WebSocket connection healthy")

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

    def get_device(self, device_id: str) -> Device | None:
        """Get device by ID."""
        return self.data.get(device_id)

    def get_available_recipes(self) -> list[str]:
        """Get list of available recipe IDs."""
        if not self.recipe_library:
            return []
        return self.recipe_library.list_recipes()

    def get_recipe_info(self, recipe_id: str) -> dict[str, Any] | None:
        """Get recipe information."""
        if not self.recipe_library:
            return None
        try:
            recipe = self.recipe_library.get_recipe(recipe_id)
            return {
                "name": recipe.name,
                "description": recipe.description,
                "stages": len(recipe.stages),
                "oven_version": recipe.oven_version.value if recipe.oven_version else None,
            }
        except ValueError:
            return None

    async def async_start_recipe(self, device_id: str, recipe_id: str) -> None:
        """Start cooking with a recipe."""
        if not self.recipe_library:
            raise ValueError("No recipe library loaded")

        recipe = self.recipe_library.get_recipe(recipe_id)
        device = self.get_device(device_id)

        if not device:
            raise ValueError(f"Device {device_id} not found")

        # Validate recipe for oven version
        recipe.validate_for_oven(device.oven_version)

        # Convert recipe to cook stages
        stages = recipe.to_cook_stages()

        # Start cook with stages
        await self.anova_oven.start_cook(device_id, stages=stages)
        await self.async_request_refresh()

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