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
from anova_oven_sdk.models import RecipeLibrary, DeviceState
from anova_oven_sdk.exceptions import AnovaError

from .const import DOMAIN, CONF_RECIPES_PATH, RECIPES_FILE
from .models import AnovaOvenDevice

_LOGGER = logging.getLogger(__name__)


class HAAnovaOven(AnovaOven):
    """Home Assistant specific Anova Oven wrapper."""

    def __init__(self, update_callback, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._update_callback = update_callback
        # Add our callback after SDK's built-in handler
        self.client.add_callback(self._handle_ha_updates)

    def _handle_ha_updates(self, data: dict[str, Any]) -> None:
        """Handle updates for Home Assistant - runs after SDK's handler."""
        command = data.get('command')

        if command == 'EVENT_APO_WIFI_LIST':
            # Convert SDK Device objects to AnovaOvenDevice objects
            for device_id, device in list(self._devices.items()):
                if not isinstance(device, AnovaOvenDevice):
                    try:
                        # Convert to AnovaOvenDevice with all SDK fields
                        ha_device = AnovaOvenDevice.model_validate(device.model_dump())
                        self._devices[device_id] = ha_device
                        _LOGGER.debug("Converted device %s to AnovaOvenDevice", device_id)
                    except Exception as e:
                        _LOGGER.error("Failed to convert device %s: %s", device_id, e)

        elif command == 'EVENT_APO_STATE':
            self._handle_state_update(data)

    def _handle_state_update(self, data: dict[str, Any]) -> None:
        """Handle real-time state updates from WebSocket."""
        command = data.get('command')
        _LOGGER.debug("Received WebSocket event: %s", command)

        if command != 'EVENT_APO_STATE':
            return

        try:
            from anova_oven_sdk.response_models import ApoStateResponse

            # Validate the full response structure using SDK model
            response = ApoStateResponse.model_validate(data)
            payload = response.payload

            device_id = payload.cooker_id
            if not device_id:
                _LOGGER.warning("Received EVENT_APO_STATE without device ID")
                return

            if device_id not in self._devices:
                _LOGGER.debug("Received state update for unknown device: %s", device_id)
                return

            device = self._devices[device_id]
            updated = False

            # Update nodes if present
            if payload.nodes:
                device.nodes = payload.nodes

                # Update convenience fields from nodes
                if device.nodes.temperature_bulbs:
                    if device.nodes.temperature_bulbs.mode == "dry":
                        device.current_temperature = device.nodes.temperature_bulbs.dry.current.get('celsius')
                        if device.nodes.temperature_bulbs.dry.setpoint:
                            device.target_temperature = device.nodes.temperature_bulbs.dry.setpoint.get('celsius')
                    else:
                        device.current_temperature = device.nodes.temperature_bulbs.wet.current.get('celsius')
                        if device.nodes.temperature_bulbs.wet.setpoint:
                            device.target_temperature = device.nodes.temperature_bulbs.wet.setpoint.get('celsius')

                updated = True
                _LOGGER.debug("Updated nodes for device %s (temp: %s°C -> %s°C)",
                            device_id, device.current_temperature, device.target_temperature)

            # Update state if present
            if payload.state and hasattr(payload.state, 'mode'):
                device.state_info = payload.state

                # Map state.mode to device.state (DeviceState enum)
                mode = payload.state.mode.lower()
                state_mapping = {
                    "cook": DeviceState.COOKING,
                    "cooking": DeviceState.COOKING,
                    "preheat": DeviceState.PREHEATING,
                    "preheating": DeviceState.PREHEATING,
                    "idle": DeviceState.IDLE,
                    "paused": DeviceState.PAUSED,
                    "completed": DeviceState.COMPLETED,
                    "error": DeviceState.ERROR,
                }

                device.state = state_mapping.get(mode, DeviceState.IDLE)
                if mode not in state_mapping:
                    _LOGGER.warning("Unknown state mode '%s', defaulting to IDLE", mode)

                updated = True
                _LOGGER.debug("Updated state for device %s: mode=%s -> state=%s, unit=%s",
                            device_id, payload.state.mode, device.state,
                            payload.state.temperature_unit if hasattr(payload.state, 'temperature_unit') else None)

            # Update system info if present
            if payload.system_info:
                device.system_info = payload.system_info
                updated = True
                _LOGGER.debug("Updated system info for device %s", device_id)

            # Update version and timestamp if present
            if payload.version:
                device.version = payload.version
                updated = True

            if payload.updated_timestamp:
                device.updated_timestamp = payload.updated_timestamp
                updated = True

            # Trigger coordinator update if we updated anything
            if updated:
                self._update_callback()
            else:
                _LOGGER.debug("Received state update but nothing changed")

        except Exception as e:
            _LOGGER.error("Failed to process state update: %s", e, exc_info=True)
            _LOGGER.debug("Payload: %s", data.get('payload'))


class AnovaOvenCoordinator(DataUpdateCoordinator[dict[str, AnovaOvenDevice]]):
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

        self.anova_oven = HAAnovaOven(self.async_set_updated_data_from_callback)

    def async_set_updated_data_from_callback(self):
        """Trigger update from callback."""
        self.async_set_updated_data(self.anova_oven._devices)

    async def _async_update_data(self) -> dict[str, AnovaOvenDevice]:
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