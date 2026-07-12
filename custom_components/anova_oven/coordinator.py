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
            config_entry=entry,
            name=DOMAIN,
            # WebSocket callbacks are the primary update path; this is a
            # cheap safety-net poll (is_connected is a local check with no
            # network call when already connected, so this adds no load on
            # Anova's API) in case a push update is ever missed.
            update_interval=timedelta(seconds=20),
        )
        self.entry = entry
        self._instance_id = format(id(self), 'x')[-6:]
        self._initial_setup_done = False
        # Maps device_id -> (cook_id, recipe_id). Storing cook_id alongside
        # the recipe name lets us detect when the oven's actual active cook
        # session no longer matches what we last started (e.g. it finished
        # and a different cook was started from the Anova app directly),
        # rather than assuming any truthy device.cook still means "ours".
        self._active_recipes: dict[str, tuple[str | None, str]] = {}

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

        # As of SDK 2026.07.1+, the SDK follows the standard library-logging
        # convention (logging.getLogger(__name__) + no self-configured
        # level/handlers), rooted at the "anova_oven_sdk" logger name. It
        # naturally respects whatever this integration's own `logger:`
        # config sets for "anova_oven_sdk" - no manual mirroring or handler
        # cleanup needed here.

        # Add callback to trigger coordinator updates when SDK receives state updates
        self.anova_oven.client.add_callback(self._handle_state_update_callback)

    def _handle_state_update_callback(self, data: dict[str, Any]) -> None:
        """Callback to trigger coordinator update when SDK receives state updates."""
        command = data.get('command')
        _LOGGER.debug("WebSocket callback received command: %s", command)

        if command == 'EVENT_APO_STATE':
            self.async_set_updated_data(self.anova_oven._devices)
        elif command == 'ERROR':
            _LOGGER.error("Received ERROR from Anova API: %s", data)
        elif command == 'RESPONSE':
            payload = data.get('payload', {})
            if payload.get('status') != 'success':
                 _LOGGER.warning("Received non-success RESPONSE: %s", data)
            else:
                 _LOGGER.debug("Received success RESPONSE: %s", data)
        else:
            _LOGGER.debug("Received unhandled command: %s Payload: %s", command, data)

    async def _async_update_data(self) -> dict[str, Device]:
        """Connection health check and initial setup.

        Initial run: Connect, discover devices, load recipes
        Subsequent runs: Just verify WebSocket is still connected
        """
        try:
            # Initial setup on first run
            if not self._initial_setup_done:
                _LOGGER.info("[%s] Performing initial setup (connect, discover, load recipes)", self._instance_id)

                # Connect WebSocket
                if not self.anova_oven.client.is_connected:
                    await self.anova_oven.connect()

                # Initial device discovery
                await self.anova_oven.discover_devices()

                # Load recipes
                if not self.recipe_library:
                    await self._load_recipes()

                self._initial_setup_done = True
                _LOGGER.info("[%s] Initial setup complete - WebSocket active for real-time updates", self._instance_id)
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
        if not self.data:
            return None
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
                "id": recipe_id,
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
            raise UpdateFailed("Recipe library not loaded")

        device = self.get_device(device_id)
        if not device:
            raise UpdateFailed(f"Device {device_id} not found")

        try:
            recipe = self.recipe_library.get_recipe(recipe_id)
            recipe.validate_for_oven(device.oven_version)
            stages = recipe.to_cook_stages()
        except ValueError as err:
            raise UpdateFailed(f"Recipe validation failed: {err}") from err

        try:
            cook_id = await self.anova_oven.start_cook(device_id, stages=stages)
        except AnovaError as err:
            raise UpdateFailed(f"Failed to start recipe: {err}") from err

        self._active_recipes[device_id] = (cook_id, recipe_id)
        await self.async_request_refresh()

    async def async_start_cook(self, device_id: str, **kwargs) -> None:
        """Start cooking."""
        self._active_recipes.pop(device_id, None)
        try:
            await self.anova_oven.start_cook(device_id=device_id, **kwargs)
        except AnovaError as err:
            raise UpdateFailed(f"Failed to start cook: {err}") from err
        await self.async_request_refresh()

    async def async_stop_cook(self, device_id: str) -> None:
        """Stop cooking."""
        self._active_recipes.pop(device_id, None)
        try:
            await self.anova_oven.stop_cook(device_id)
        except AnovaError as err:
            raise UpdateFailed(f"Failed to stop cook: {err}") from err
        await self.async_request_refresh()

    def get_active_recipe_id(self, device_id: str) -> str | None:
        """Get the recipe ID currently cooking on a device, if any.

        Lazily clears (or ignores) the tracked recipe once the device's
        cook session has ended, OR once the oven reports a different
        cook_id than the one we started - e.g. it finished naturally, or
        a new cook was started from the Anova app directly rather than
        through this integration.

        A tracked cook_id of None means "unconfirmed" (restored from a
        previous HA session without knowing the real cook_id - see
        select.py's async_added_to_hass). In that case, adopt whatever
        cook_id the oven currently reports rather than treating it as a
        mismatch, so the restored selection survives its first refresh.
        """
        device = self.get_device(device_id)
        if not device or not device.cook:
            # Deliberately NOT popping _active_recipes here: this branch is
            # also hit in the brief window right after starting a cook,
            # before the oven has sent back any state update confirming it
            # (device.cook is still None from before the cook started, not
            # because it ended). Popping unconditionally on every "no
            # device.cook" read destroyed the tracked entry moments after
            # async_start_recipe() set it - the tracked recipe never had a
            # chance to be confirmed against a real cook_id. Simply
            # returning None here already reflects "no active cook right
            # now" correctly; the entry gets cleared for real once a cook_id
            # mismatch is actually observed below, or via
            # async_start_cook()/async_stop_cook().
            return None
        tracked = self._active_recipes.get(device_id)
        if not tracked:
            return None
        tracked_cook_id, recipe_id = tracked
        if tracked_cook_id is None:
            self._active_recipes[device_id] = (device.cook.cook_id, recipe_id)
            return recipe_id
        if tracked_cook_id != device.cook.cook_id:
            self._active_recipes.pop(device_id, None)
            return None
        return recipe_id

    async def async_set_probe(self, device_id: str, target: float, temperature_unit: str = "C") -> None:
        """Set probe temperature."""
        try:
            await self.anova_oven.set_probe(device_id, target, temperature_unit)
        except AnovaError as err:
            raise UpdateFailed(f"Failed to set probe: {err}") from err
        await self.async_request_refresh()

    async def async_set_temperature_unit(self, device_id: str, unit: str) -> None:
        """Set temperature unit."""
        try:
            await self.anova_oven.set_temperature_unit(device_id, unit)
        except AnovaError as err:
            raise UpdateFailed(f"Failed to set temperature unit: {err}") from err
        await self.async_request_refresh()

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator."""
        await self.anova_oven.disconnect()
        await super().async_shutdown()