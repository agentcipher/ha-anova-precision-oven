"""DataUpdateCoordinator for Anova Precision Oven."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .anova_sdk.oven import AnovaOven
from .anova_sdk.models import Device, RecipeLibrary
from .anova_sdk.exceptions import AnovaError
from .const import (
    CONF_ENVIRONMENT,
    CONF_RECIPES_PATH,
    CONF_WS_URL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_WS_URL,
    RECIPES_FILE,
)

_LOGGER = logging.getLogger(__name__)


class AnovaOvenCoordinator(DataUpdateCoordinator[dict[str, Device]]):
    """Class to manage fetching Anova Oven data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Anova Oven",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
            config_entry=entry,
        )

        self.entry = entry
        self.oven: AnovaOven | None = None
        self.recipe_library: RecipeLibrary | None = None
        self._setup_complete = False

    async def _async_setup(self) -> None:
        """Set up the coordinator."""
        if self._setup_complete:
            return

        # Initialize SDK with token from config
        token = self.entry.data.get(CONF_TOKEN)
        environment = self.entry.data.get(CONF_ENVIRONMENT, "production")
        self.oven = AnovaOven(token=token, environment=environment)

        # Override WebSocket URL if provided
        ws_url = self.entry.data.get(CONF_WS_URL, DEFAULT_WS_URL)
        if ws_url != DEFAULT_WS_URL:
            self.oven.client.ws_url = ws_url

        # Connect to Anova servers
        await self.oven.connect()

        # Load recipe library
        await self._load_recipes()

        # Do initial discovery
        _LOGGER.debug("Performing initial device discovery...")
        await self.oven.discover_devices(timeout=10.0)

        # Register callback for real-time updates
        self.oven.client.add_callback(self._on_data_update)

        self._setup_complete = True

    def _on_data_update(self, data: dict[str, Any]) -> None:
        """Handle real-time updates from WebSocket."""
        # Only trigger update if we have devices
        if not self.oven._devices:
            return

        # Update the coordinator data
        device_dict = {device_id: device for device_id, device in self.oven._devices.items()}
        self.async_set_updated_data(device_dict)

    async def _load_recipes(self) -> None:
        """Load recipe library from YAML file."""
        try:
            # Try custom path first
            recipes_path = self.entry.data.get(CONF_RECIPES_PATH)
            if recipes_path:
                self.recipe_library = await self.hass.async_add_executor_job(
                    RecipeLibrary.from_yaml_file, recipes_path
                )
                _LOGGER.info("Loaded %d recipes from %s", len(self.recipe_library.recipes), recipes_path)
            else:
                # Try default location in config directory
                config_path = self.hass.config.path(RECIPES_FILE)
                try:
                    self.recipe_library = await self.hass.async_add_executor_job(
                        RecipeLibrary.from_yaml_file, config_path
                    )
                    _LOGGER.info("Loaded %d recipes from config directory", len(self.recipe_library.recipes))
                except FileNotFoundError:
                    # Create empty library
                    self.recipe_library = RecipeLibrary(recipes={})
                    _LOGGER.info("No recipes file found, using empty library")
        except Exception as err:
            _LOGGER.error("Failed to load recipes: %s", err)
            self.recipe_library = RecipeLibrary(recipes={})

    async def _async_update_data(self) -> dict[str, Device]:
        """Fetch data from Anova."""
        try:
            if not self._setup_complete:
                await self._async_setup()

            # Return cached devices from the SDK
            # The WebSocket is already updating the oven._devices dict in real-time
            device_dict = {device_id: device for device_id, device in self.oven._devices.items()}

            return device_dict

        except AnovaError as err:
            raise UpdateFailed(f"Error communicating with Anova: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}") from err

    async def async_shutdown(self) -> None:
        """Shutdown coordinator and disconnect."""
        if self.oven:
            await self.oven.disconnect()

    async def async_start_cook(
        self,
        device_id: str,
        temperature: float,
        temperature_unit: str = "C",
        duration: int | None = None,
        **kwargs: Any,
    ) -> None:
        """Start cooking on a device."""
        try:
            await self.oven.start_cook(
                device_id=device_id,
                temperature=temperature,
                temperature_unit=temperature_unit,
                duration=duration,
                **kwargs,
            )
            await self.async_request_refresh()
        except AnovaError as err:
            raise UpdateFailed(f"Failed to start cook: {err}") from err

    async def async_stop_cook(self, device_id: str) -> None:
        """Stop cooking on a device."""
        try:
            await self.oven.stop_cook(device_id)
            await self.async_request_refresh()
        except AnovaError as err:
            raise UpdateFailed(f"Failed to stop cook: {err}") from err

    async def async_set_probe(
        self, device_id: str, target: float, temperature_unit: str = "C"
    ) -> None:
        """Set probe temperature."""
        try:
            await self.oven.set_probe(device_id, target, temperature_unit)
            await self.async_request_refresh()
        except AnovaError as err:
            raise UpdateFailed(f"Failed to set probe: {err}") from err

    async def async_start_recipe(self, device_id: str, recipe_id: str) -> None:
        """Start a recipe from the library."""
        if not self.recipe_library:
            raise UpdateFailed("Recipe library not loaded")

        try:
            recipe = self.recipe_library.get_recipe(recipe_id)
            device = self.data.get(device_id)

            if not device:
                raise UpdateFailed(f"Device {device_id} not found")

            # Validate recipe for oven version
            recipe.validate_for_oven(device.oven_version)

            # Convert to cook stages and start
            stages = recipe.to_cook_stages()
            await self.oven.start_cook(device_id, stages=stages)
            await self.async_request_refresh()

        except ValueError as err:
            raise UpdateFailed(f"Recipe validation failed: {err}") from err
        except AnovaError as err:
            raise UpdateFailed(f"Failed to start recipe: {err}") from err

    async def async_set_temperature_unit(self, device_id: str, unit: str) -> None:
        """Set temperature unit on device."""
        try:
            await self.oven.set_temperature_unit(device_id, unit)
            await self.async_request_refresh()
        except AnovaError as err:
            raise UpdateFailed(f"Failed to set temperature unit: {err}") from err

    def get_device(self, device_id: str) -> Device | None:
        """Get device by ID."""
        return self.data.get(device_id) if self.data else None

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
                "id": recipe.recipe_id,
                "name": recipe.name,
                "description": recipe.description,
                "stages": len(recipe.stages),
                "oven_version": recipe.oven_version.value if recipe.oven_version else "any",
            }
        except ValueError:
            return None