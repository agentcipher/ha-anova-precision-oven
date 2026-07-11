"""Fixtures for Anova Oven integration tests."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# ============================================================================
# CRITICAL: Set up environment for SDK tests BEFORE any imports
# ============================================================================
os.environ.setdefault("ANOVA_TOKEN", "anova-test-token-for-unit-tests")
os.environ.setdefault("ANOVA_ENV", "testing")
os.environ.setdefault("ANOVA_WS_URL", "wss://test.anovaculinary.io")
os.environ.setdefault("ANOVA_CONNECTION_TIMEOUT", "30.0")
os.environ.setdefault("ANOVA_COMMAND_TIMEOUT", "10.0")
os.environ.setdefault("ANOVA_LOG_LEVEL", "INFO")
os.environ.setdefault("ANOVA_MAX_RETRIES", "3")

# Now safe to import
from homeassistant.const import CONF_TOKEN
from homeassistant.core import HomeAssistant

from custom_components.anova_oven.const import (
    CONF_ENVIRONMENT,
    CONF_RECIPES_PATH,
    CONF_WS_URL,
    DEFAULT_WS_URL,
    DOMAIN,
)
from anova_oven_sdk.models import Device, DeviceState, OvenVersion
from anova_oven_sdk.response_models import CookSessionState, ProbeState

from pytest_homeassistant_custom_component.common import MockConfigEntry


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests."""
    yield


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_TOKEN: "anova-test-token-12345",
            CONF_WS_URL: DEFAULT_WS_URL,
            CONF_ENVIRONMENT: "production",
        },
        entry_id="test_entry_id",
        title="Anova Oven (1 device(s))",
    )


def _default_nodes_payload() -> dict:
    """Return a realistic, fully-populated idle "nodes" payload."""
    return {
        "temperatureBulbs": {
            "mode": "dry",
            "wet": {
                "current": {"celsius": 25.0, "fahrenheit": 77.0},
                "setpoint": {"celsius": 180.0, "fahrenheit": 356.0},
            },
            "dry": {
                "current": {"celsius": 25.0, "fahrenheit": 77.0},
                "setpoint": {"celsius": 180.0, "fahrenheit": 356.0},
            },
            "dryTop": {"current": {"celsius": 25.0, "fahrenheit": 77.0}},
            "dryBottom": {"current": {"celsius": 25.0, "fahrenheit": 77.0}},
        },
        "timer": {"mode": "idle", "initial": 0, "current": 0},
        "temperatureProbe": {"connected": False, "current": None, "setpoint": None},
        "steamGenerators": {"mode": "idle", "evaporator": {}, "boiler": {}},
        "heatingElements": {
            "top": {"on": False, "failed": False, "watts": 0},
            "bottom": {"on": False, "failed": False, "watts": 0},
            "rear": {"on": False, "failed": False, "watts": 0},
        },
        "fan": {"speed": 50, "failed": False},
        "vent": {"open": False},
        "waterTank": {"empty": False},
        "door": {"closed": True},
        "lamp": {"on": False, "failed": False, "preference": "off"},
        "userInterfaceCircuit": {"communicationFailed": False},
    }


def _make_device(**overrides) -> Device:
    """Build a real Device instance from a realistic API payload."""
    payload = {
        "cookerId": "test-device-123",
        "name": "Test Oven",
        "pairedAt": "2024-01-01T00:00:00Z",
        "type": OvenVersion.V2.value,
        "state": DeviceState.IDLE.value,
        "nodes": _default_nodes_payload(),
        "state_info": {"mode": "idle", "temperatureUnit": "C"},
        "system_info": {
            "online": True,
            "hardwareVersion": "120V1",
            "powerMains": 120,
            "powerHertz": 60,
            "firmwareVersion": "2.1.0",
            "uiHardwareVersion": "UI_ORIGINAL_2",
            "uiFirmwareVersion": "0.0.0",
            "triacsFailed": False,
        },
        "cook": None,
    }
    payload.update(overrides)
    return Device.model_validate(payload)


@pytest.fixture
def mock_device() -> Device:
    """Return a real Device instance representing an idle oven."""
    return _make_device()


@pytest.fixture
def make_device():
    """Return a factory for building additional real Device instances."""
    return _make_device


@pytest.fixture
def mock_cooking_device(mock_device: Device) -> Device:
    """Return a real Device instance representing an oven mid-cook."""
    mock_device.state = DeviceState.COOKING
    mock_device.nodes.temperature_bulbs.dry.current["celsius"] = 175.0
    mock_device.nodes.timer.mode = "countdown"
    mock_device.nodes.timer.initial = 3600
    mock_device.nodes.timer.current = 1800
    mock_device.cook = CookSessionState.model_validate(
        {
            "cookId": "cook-123",
            "originSource": "app",
            "type": "manual",
            "rackPosition": 3,
            "stages": [
                {
                    "id": "stage-1",
                    "stepType": "cook",
                    "title": "Roast",
                    "description": "Roast the chicken",
                    "rackPosition": 3,
                },
                {
                    "id": "stage-2",
                    "stepType": "cook",
                    "title": "Rest",
                    "description": "Let it rest",
                    "rackPosition": 3,
                },
            ],
        }
    )
    # Mirrors what AnovaOven.start_cook() records via register_cook_plan(),
    # so current_stage_index/total_stage_count resolve to real values.
    mock_device.register_cook_plan("cook-123", ["stage-1", "stage-2"])
    return mock_device


@pytest.fixture
def mock_probe_device(mock_device: Device) -> Device:
    """Return a real Device instance with a connected temperature probe."""
    mock_device.nodes.temperature_probe = ProbeState.model_validate(
        {
            "connected": True,
            "current": {"celsius": 65.0, "fahrenheit": 149.0},
            "setpoint": {"celsius": 70.0, "fahrenheit": 158.0},
        }
    )
    return mock_device


@pytest.fixture
def mock_anova_oven() -> AsyncMock:
    """Return a mock AnovaOven instance (NOT patched - tests do their own patching).

    ``discover_devices`` populates ``_devices`` from its own ``return_value``
    so ``coordinator._async_update_data`` (which returns
    ``self.anova_oven._devices``) yields a real dict keyed by cooker_id,
    matching how tests configure ``mock_anova_oven.discover_devices.return_value``.
    """
    mock_oven = AsyncMock()

    # Setup async context manager
    mock_oven.__aenter__ = AsyncMock(return_value=mock_oven)
    mock_oven.__aexit__ = AsyncMock(return_value=None)

    async def _discover_devices_side_effect():
        devices = mock_oven.discover_devices.return_value
        mock_oven._devices = {device.cooker_id: device for device in devices}
        return devices

    # Setup methods
    mock_oven.connect = AsyncMock()
    mock_oven.disconnect = AsyncMock()
    mock_oven.discover_devices = AsyncMock(side_effect=_discover_devices_side_effect)
    mock_oven.discover_devices.return_value = []
    mock_oven._devices = {}
    mock_oven.start_cook = AsyncMock()
    mock_oven.stop_cook = AsyncMock()
    mock_oven.set_probe = AsyncMock()
    mock_oven.set_temperature_unit = AsyncMock()

    # Mock client
    mock_oven.client = MagicMock()
    mock_oven.client.ws_url = DEFAULT_WS_URL
    mock_oven.client.is_connected = False

    return mock_oven


@pytest.fixture
def mock_recipe_library() -> MagicMock:
    """Return a mock recipe library."""
    library = MagicMock()

    # Create recipe mocks with actual string values, not nested MagicMocks
    roast_chicken = MagicMock()
    roast_chicken.recipe_id = "roast_chicken"
    roast_chicken.name = "Roast Chicken"  # Actual string
    roast_chicken.description = "Perfect roast chicken"  # Actual string
    roast_chicken.stages = []
    roast_chicken.oven_version = None

    sourdough = MagicMock()
    sourdough.recipe_id = "sourdough"
    sourdough.name = "Sourdough Bread"  # Actual string
    sourdough.description = "Artisan sourdough"  # Actual string
    sourdough.stages = []
    sourdough.oven_version = None

    library.recipes = {
        "roast_chicken": roast_chicken,
        "sourdough": sourdough,
    }

    library.list_recipes = MagicMock(return_value=["roast_chicken", "sourdough"])
    library.get_recipe = MagicMock(
        side_effect=lambda recipe_id: library.recipes.get(recipe_id)
    )

    return library


# Helper fixtures for common test setups
@pytest.fixture
async def setup_integration(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_anova_oven: AsyncMock
) -> AsyncMock:
    """Setup integration with no devices - for tests that add devices later."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = []

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    return mock_anova_oven


@pytest.fixture
async def setup_integration_with_device(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_anova_oven: AsyncMock,
    mock_device: Device,
) -> AsyncMock:
    """Setup integration with a single device."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    return mock_anova_oven


# ============================================================================
# SDK Test Fixtures (from SDK's conftest.py)
# ============================================================================

@pytest.fixture(autouse=True)
def reset_settings():
    """Reset settings before each test - from SDK conftest."""
    yield


@pytest.fixture
def temp_log_file(tmp_path):
    """Provide a temporary log file path - from SDK conftest."""
    return tmp_path / "test.log"


# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)
