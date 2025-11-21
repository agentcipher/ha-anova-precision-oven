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
from custom_components.anova_oven.anova_sdk.models import OvenVersion

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


@pytest.fixture
def mock_device() -> MagicMock:
    """Return a mock device."""
    device = MagicMock()
    device.cooker_id = "test-device-123"
    device.display_name = "Test Oven"
    device.name = "Test Oven"

    # ✅ FIXED: Use OvenVersion Enum - device.oven_version returns the enum
    device.oven_version = OvenVersion.V2  # This is an Enum
    device.device_type = OvenVersion.V2

    # The model property should return "Precision Oven APO" for display
    # This is what Home Assistant uses in device_info
    device.model = "Precision Oven APO"

    device.firmware_version = "2.1.0"
    device.wifi_ssid = "TestWiFi"
    device.wifi_strength = 85

    # Mock state
    state = MagicMock()
    state.state = "idle"
    state.temperature_unit = "C"
    state.cook = None

    # Mock nodes
    state.nodes = {
        "temperatureBulbs": {
            "mode": "dry",
            "dry": {
                "current": {"celsius": 25.0, "fahrenheit": 77.0},
                "setpoint": {"celsius": 180.0, "fahrenheit": 356.0},
            },
            "wet": {
                "current": {"celsius": 25.0, "fahrenheit": 77.0},
                "setpoint": {"celsius": 180.0, "fahrenheit": 356.0},
            },
        },
        "door": {"open": False},
        "waterTank": {"low": False},
        "probe": {
            "connected": False,
            "current": {},  # Empty dict instead of None
            "setpoint": {},  # Empty dict instead of None
        },
        "exhaustVent": {"state": "closed"},
        "timer": {"mode": "idle", "current": None, "initial": None},
        "steamGenerators": {
            "mode": "idle",
            "relativeOutput": {"percentage": 0},
        },
        "fan": {"speed": 50},
    }

    device.state = state
    return device


@pytest.fixture
def mock_cooking_device(mock_device) -> MagicMock:
    """Return a mock device that is cooking."""
    mock_device.state.state = "cooking"

    # Add cook info
    cook = MagicMock()
    cook.name = "Roast Chicken"
    cook.current_stage = 1
    cook.stages = [
        {"temperature": 180, "duration": 3600},
        {"temperature": 200, "duration": 1800},
    ]
    mock_device.state.cook = cook

    # Update nodes for cooking
    mock_device.state.nodes["temperatureBulbs"]["dry"]["current"]["celsius"] = 175.0
    mock_device.state.nodes["timer"]["mode"] = "countdown"
    mock_device.state.nodes["timer"]["current"] = 1800
    mock_device.state.nodes["timer"]["initial"] = 3600

    return mock_device


@pytest.fixture
def mock_probe_device(mock_device) -> MagicMock:
    """Return a mock device with probe connected."""
    mock_device.state.nodes["probe"] = {
        "connected": True,
        "current": {"celsius": 65.0, "fahrenheit": 149.0},
        "setpoint": {"celsius": 70.0, "fahrenheit": 158.0},
    }
    return mock_device


@pytest.fixture
def mock_anova_oven() -> AsyncMock:
    """Return a mock AnovaOven instance (NOT patched - tests do their own patching).

    ✅ FIXED: Returns AsyncMock directly, tests handle patching themselves.
    """
    mock_oven = AsyncMock()

    # Setup async context manager
    mock_oven.__aenter__ = AsyncMock(return_value=mock_oven)
    mock_oven.__aexit__ = AsyncMock(return_value=None)

    # Setup methods
    mock_oven.connect = AsyncMock()
    mock_oven.disconnect = AsyncMock()
    mock_oven.discover_devices = AsyncMock(return_value=[])
    mock_oven.start_cook = AsyncMock()
    mock_oven.stop_cook = AsyncMock()
    mock_oven.set_probe = AsyncMock()
    mock_oven.set_temperature_unit = AsyncMock()

    # Mock client
    mock_oven.client = MagicMock()
    mock_oven.client.ws_url = DEFAULT_WS_URL

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
    mock_device: MagicMock,
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