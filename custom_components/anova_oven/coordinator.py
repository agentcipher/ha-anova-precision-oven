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


class HAAnovaOven(AnovaOven):
    """Home Assistant specific Anova Oven wrapper."""

    def __init__(self, update_callback, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._update_callback = update_callback
        # Store additional state data separately from SDK Device objects
        self._device_state_data: Dict[str, Dict[str, Any]] = {}
        # Add our callback after SDK's built-in handler
        self.client.add_callback(self._handle_ha_state_updates)

    def _handle_ha_state_updates(self, data: dict[str, Any]) -> None:
        """Handle state updates for Home Assistant - runs after SDK's handler."""
        command = data.get('command')

        if command == 'EVENT_APO_STATE':
            try:
                # Get raw payload to handle nested structure
                raw_payload = data.get('payload', {})

                device_id = raw_payload.get('cookerId')
                if not device_id:
                    _LOGGER.warning("Received EVENT_APO_STATE without device ID")
                    return

                if device_id not in self._devices:
                    _LOGGER.warning("Received state for unknown device: %s", device_id)
                    return

                # Initialize state data for this device if needed
                if device_id not in self._device_state_data:
                    self._device_state_data[device_id] = {}
                    _LOGGER.debug("Initialized state data storage for device %s", device_id)

                state_data = self._device_state_data[device_id]
                updated = False

                # For v1 ovens, data is nested under 'state' key
                nested_state = raw_payload.get('state', {})

                # Store nodes - they're in the nested state for v1
                if 'nodes' in nested_state:
                    from anova_oven_sdk.response_models import Nodes
                    state_data['nodes'] = Nodes.model_validate(nested_state['nodes'])
                    updated = True
                    _LOGGER.info("Stored nodes for device %s", device_id)
                elif 'nodes' in raw_payload:
                    # v2 might have nodes at top level
                    from anova_oven_sdk.response_models import Nodes
                    state_data['nodes'] = Nodes.model_validate(raw_payload['nodes'])
                    updated = True
                    _LOGGER.info("Stored nodes for device %s (top-level)", device_id)

                # Store state info (mode, temperatureUnit, etc.)
                # This is in nested_state.state for v1
                if 'state' in nested_state:
                    from anova_oven_sdk.response_models import OvenState
                    state_data['state_info'] = OvenState.model_validate(nested_state['state'])

                    # Update SDK device state enum based on mode
                    mode_str = nested_state['state'].get('mode')
                    if mode_str:
                        device = self._devices[device_id]
                        mode = mode_str.lower()
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
                        _LOGGER.debug("Updated device %s state to %s (from mode: %s)", device_id, device.state, mode)

                    updated = True

                # Store system info - in nested state for v1
                if 'systemInfo' in nested_state:
                    from anova_oven_sdk.response_models import SystemInfo
                    state_data['system_info'] = SystemInfo.model_validate(nested_state['systemInfo'])
                    updated = True

                # Store version and timestamp - in nested state for v1
                if 'version' in nested_state:
                    state_data['version'] = nested_state['version']
                    updated = True

                if 'updatedTimestamp' in nested_state:
                    state_data['updated_timestamp'] = nested_state['updatedTimestamp']
                    updated = True

                # Trigger coordinator update if we updated anything
                if updated:
                    _LOGGER.info("Updated state data for device %s, triggering coordinator refresh", device_id)
                    self._update_callback()

            except Exception as e:
                _LOGGER.error("Failed to process state update: %s", e, exc_info=True)

    def get_state_data(self, device_id: str) -> Dict[str, Any]:
        """Get additional state data for a device."""
        return self._device_state_data.get(device_id, {})


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

        self.anova_oven = HAAnovaOven(self.async_set_updated_data_from_callback)

    def async_set_updated_data_from_callback(self):
        """Trigger update from callback."""
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

    def get_device_nodes(self, device_id: str):
        """Get device nodes (detailed state)."""
        state_data = self.anova_oven.get_state_data(device_id)
        nodes = state_data.get('nodes')
        if nodes:
            _LOGGER.debug("get_device_nodes(%s) returning nodes: %s", device_id, type(nodes))
        else:
            _LOGGER.warning("get_device_nodes(%s) returning None - state_data keys: %s", device_id, list(state_data.keys()) if state_data else "empty")
        return nodes

    def get_device_state_info(self, device_id: str):
        """Get device state info (mode, temperature unit)."""
        state_data = self.anova_oven.get_state_data(device_id)
        return state_data.get('state_info')

    def get_device_system_info(self, device_id: str):
        """Get device system info."""
        state_data = self.anova_oven.get_state_data(device_id)
        return state_data.get('system_info')

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