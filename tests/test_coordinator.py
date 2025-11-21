"""Test the Anova Oven coordinator."""
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.anova_oven.coordinator import AnovaOvenCoordinator
from custom_components.anova_oven.anova_sdk.exceptions import AnovaError

from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_coordinator_setup_success(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test coordinator setup success."""
    mock_anova_oven.discover_devices.return_value = [mock_device]

    # Add config entry to hass
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        coordinator = AnovaOvenCoordinator(hass, mock_config_entry)
        await coordinator.async_refresh()

    assert coordinator.data is not None
    assert "test-device-123" in coordinator.data
    assert coordinator.data["test-device-123"] == mock_device
    mock_anova_oven.connect.assert_called_once()


async def test_coordinator_setup_connection_failed(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_anova_oven: AsyncMock,
):
    """Test coordinator handles connection failure."""
    # Make connect fail to trigger error during setup
    mock_anova_oven.connect.side_effect = AnovaError("Failed to connect")

    # Add config entry to hass
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        coordinator = AnovaOvenCoordinator(hass, mock_config_entry)

        # The error should be wrapped in UpdateFailed by the coordinator
        with pytest.raises(UpdateFailed, match="Failed to connect"):
            await coordinator._async_update_data()


async def test_coordinator_update_data(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test coordinator data updates."""
    mock_anova_oven.discover_devices.return_value = [mock_device]

    # Add config entry to hass
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        coordinator = AnovaOvenCoordinator(hass, mock_config_entry)
        await coordinator.async_refresh()

        # Update with different state
        mock_device.state.state = "cooking"
        await coordinator.async_refresh()

    assert coordinator.data["test-device-123"].state.state == "cooking"
    assert mock_anova_oven.discover_devices.call_count >= 2


async def test_coordinator_update_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test coordinator handles update errors."""
    mock_anova_oven.discover_devices.return_value = [mock_device]

    # Add config entry to hass
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        coordinator = AnovaOvenCoordinator(hass, mock_config_entry)
        # First update should succeed
        await coordinator._async_update_data()

        # Cause error on next update
        mock_anova_oven.discover_devices.side_effect = AnovaError("Update failed")

        with pytest.raises(UpdateFailed, match="Update failed"):
            await coordinator._async_update_data()


async def test_coordinator_start_cook(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test coordinator start_cook."""
    mock_anova_oven.discover_devices.return_value = [mock_device]

    # Add config entry to hass
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        coordinator = AnovaOvenCoordinator(hass, mock_config_entry)
        await coordinator.async_refresh()

        # Patch async_request_refresh to avoid debouncer
        with patch.object(coordinator, 'async_request_refresh', new_callable=AsyncMock):
            await coordinator.async_start_cook(
                "test-device-123",
                temperature=180.0,
                temperature_unit="C",
                duration=3600,
            )

    mock_anova_oven.start_cook.assert_called_once_with(
        device_id="test-device-123",
        temperature=180.0,
        temperature_unit="C",
        duration=3600,
    )


async def test_coordinator_stop_cook(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test coordinator stop_cook."""
    mock_anova_oven.discover_devices.return_value = [mock_device]

    # Add config entry to hass
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        coordinator = AnovaOvenCoordinator(hass, mock_config_entry)
        await coordinator.async_refresh()

        # Patch async_request_refresh to avoid debouncer
        with patch.object(coordinator, 'async_request_refresh', new_callable=AsyncMock):
            await coordinator.async_stop_cook("test-device-123")

    mock_anova_oven.stop_cook.assert_called_once_with("test-device-123")


async def test_coordinator_set_probe(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test coordinator set_probe."""
    mock_anova_oven.discover_devices.return_value = [mock_device]

    # Add config entry to hass
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        coordinator = AnovaOvenCoordinator(hass, mock_config_entry)
        await coordinator.async_refresh()

        # Patch async_request_refresh to avoid debouncer
        with patch.object(coordinator, 'async_request_refresh', new_callable=AsyncMock):
            await coordinator.async_set_probe("test-device-123", target=70.0)

    mock_anova_oven.set_probe.assert_called_once_with("test-device-123", 70.0, "C")


async def test_coordinator_set_temperature_unit(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test coordinator set_temperature_unit."""
    mock_anova_oven.discover_devices.return_value = [mock_device]

    # Add config entry to hass
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        coordinator = AnovaOvenCoordinator(hass, mock_config_entry)
        await coordinator.async_refresh()

        # Patch async_request_refresh to avoid debouncer
        with patch.object(coordinator, 'async_request_refresh', new_callable=AsyncMock):
            await coordinator.async_set_temperature_unit("test-device-123", "F")

    mock_anova_oven.set_temperature_unit.assert_called_once_with("test-device-123", "F")


async def test_coordinator_get_device(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test coordinator get_device."""
    mock_anova_oven.discover_devices.return_value = [mock_device]

    # Add config entry to hass
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        coordinator = AnovaOvenCoordinator(hass, mock_config_entry)
        await coordinator.async_refresh()

        device = coordinator.get_device("test-device-123")
        assert device == mock_device

        # Test non-existent device
        assert coordinator.get_device("nonexistent") is None


async def test_coordinator_load_recipes(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_anova_oven: AsyncMock,
    mock_device,
    mock_recipe_library,
):
    """Test coordinator loads recipes."""
    mock_anova_oven.discover_devices.return_value = [mock_device]

    # Add config entry to hass
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ), patch(
        "custom_components.anova_oven.coordinator.RecipeLibrary.from_yaml_file",
        return_value=mock_recipe_library,
    ):
        coordinator = AnovaOvenCoordinator(hass, mock_config_entry)
        await coordinator.async_refresh()

        recipes = coordinator.get_available_recipes()
        assert len(recipes) == 2
        assert "roast_chicken" in recipes
        assert "sourdough" in recipes


async def test_coordinator_start_recipe(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_anova_oven: AsyncMock,
    mock_device,
    mock_recipe_library,
):
    """Test coordinator start_recipe."""
    mock_anova_oven.discover_devices.return_value = [mock_device]

    # Add config entry to hass
    mock_config_entry.add_to_hass(hass)

    # Setup recipe mock
    recipe_mock = mock_recipe_library.recipes["roast_chicken"]
    recipe_mock.validate_for_oven = MagicMock()
    recipe_mock.to_cook_stages = MagicMock(return_value=[])

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ), patch(
        "custom_components.anova_oven.coordinator.RecipeLibrary.from_yaml_file",
        return_value=mock_recipe_library,
    ):
        coordinator = AnovaOvenCoordinator(hass, mock_config_entry)
        await coordinator.async_refresh()

        # Patch async_request_refresh to avoid debouncer
        with patch.object(coordinator, 'async_request_refresh', new_callable=AsyncMock):
            await coordinator.async_start_recipe("test-device-123", "roast_chicken")

    recipe_mock.validate_for_oven.assert_called_once()
    recipe_mock.to_cook_stages.assert_called_once()
    mock_anova_oven.start_cook.assert_called_once()


async def test_coordinator_start_recipe_not_found(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_anova_oven: AsyncMock,
    mock_device,
    mock_recipe_library,
):
    """Test coordinator handles recipe not found."""
    mock_anova_oven.discover_devices.return_value = [mock_device]
    mock_recipe_library.get_recipe.side_effect = ValueError("Recipe not found")

    # Add config entry to hass
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ), patch(
        "custom_components.anova_oven.coordinator.RecipeLibrary.from_yaml_file",
        return_value=mock_recipe_library,
    ):
        coordinator = AnovaOvenCoordinator(hass, mock_config_entry)
        await coordinator.async_refresh()

        with pytest.raises(UpdateFailed, match="Recipe validation failed"):
            await coordinator.async_start_recipe("test-device-123", "nonexistent")


async def test_coordinator_get_recipe_info(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_anova_oven: AsyncMock,
    mock_device,
    mock_recipe_library,
):
    """Test coordinator get_recipe_info."""
    mock_anova_oven.discover_devices.return_value = [mock_device]

    # Add config entry to hass
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ), patch(
        "custom_components.anova_oven.coordinator.RecipeLibrary.from_yaml_file",
        return_value=mock_recipe_library,
    ):
        coordinator = AnovaOvenCoordinator(hass, mock_config_entry)
        await coordinator.async_refresh()

        info = coordinator.get_recipe_info("roast_chicken")
        assert info is not None
        assert info["id"] == "roast_chicken"
        assert info["name"] == "Roast Chicken"
        assert info["description"] == "Perfect roast chicken"

        # Test non-existent recipe - mock should return None for missing keys
        mock_recipe_library.get_recipe.side_effect = ValueError("Not found")
        assert coordinator.get_recipe_info("nonexistent") is None


async def test_coordinator_shutdown(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test coordinator shutdown."""
    mock_anova_oven.discover_devices.return_value = [mock_device]

    # Add config entry to hass
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        coordinator = AnovaOvenCoordinator(hass, mock_config_entry)
        await coordinator.async_refresh()

        await coordinator.async_shutdown()

    mock_anova_oven.disconnect.assert_called_once()


async def test_coordinator_custom_ws_url(
    hass: HomeAssistant,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test coordinator with custom WebSocket URL."""
    from custom_components.anova_oven.const import CONF_WS_URL

    custom_config = MockConfigEntry(
        domain="anova_oven",
        data={
            "token": "anova-test",
            CONF_WS_URL: "wss://custom.anovaculinary.io",
        },
    )

    # Add config entry to hass
    custom_config.add_to_hass(hass)

    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        coordinator = AnovaOvenCoordinator(hass, custom_config)
        await coordinator.async_refresh()

    assert mock_anova_oven.client.ws_url == "wss://custom.anovaculinary.io"



async def test_coordinator_load_recipes_custom_path(
        hass: HomeAssistant,
        mock_anova_oven: AsyncMock,
        mock_device,
        mock_recipe_library,
        tmp_path,
):
    """Test coordinator loads recipes from custom path."""
    from custom_components.anova_oven.const import CONF_RECIPES_PATH, CONF_WS_URL, DEFAULT_WS_URL, CONF_ENVIRONMENT
    from homeassistant.const import CONF_TOKEN
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    custom_recipes_path = str(tmp_path / "custom_recipes.yml")

    # Create MockConfigEntry with all data upfront - do NOT modify .data after
    custom_config = MockConfigEntry(
        domain="anova_oven",
        data={
            CONF_TOKEN: "anova-test",
            CONF_WS_URL: DEFAULT_WS_URL,
            CONF_ENVIRONMENT: "production",
            CONF_RECIPES_PATH: custom_recipes_path,
        },
        entry_id="test_custom_recipes",
    )
    custom_config.add_to_hass(hass)

    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ), patch(
        "custom_components.anova_oven.coordinator.RecipeLibrary.from_yaml_file",
        return_value=mock_recipe_library,
    ) as mock_from_yaml:
        coordinator = AnovaOvenCoordinator(hass, custom_config)
        await coordinator.async_refresh()

        # Verify it tried to load from custom path
        mock_from_yaml.assert_called_with(custom_recipes_path)


async def test_coordinator_load_recipes_config_directory(
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_anova_oven: AsyncMock,
        mock_device,
        mock_recipe_library,
):
    """Test coordinator loads recipes from config directory."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ), patch(
        "custom_components.anova_oven.coordinator.RecipeLibrary.from_yaml_file",
        return_value=mock_recipe_library,
    ) as mock_from_yaml:
        coordinator = AnovaOvenCoordinator(hass, mock_config_entry)
        await coordinator.async_refresh()

        # Should have tried to load from config directory
        assert mock_from_yaml.called


async def test_coordinator_load_recipes_file_not_found(
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_anova_oven: AsyncMock,
        mock_device,
):
    """Test coordinator handles missing recipe file gracefully."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ), patch(
        "custom_components.anova_oven.coordinator.RecipeLibrary.from_yaml_file",
        side_effect=FileNotFoundError("Recipe file not found"),
    ):
        coordinator = AnovaOvenCoordinator(hass, mock_config_entry)
        await coordinator.async_refresh()

        # Should have empty recipe library
        assert coordinator.recipe_library is not None
        assert len(coordinator.recipe_library.recipes) == 0


async def test_coordinator_load_recipes_generic_error(
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_anova_oven: AsyncMock,
        mock_device,
):
    """Test coordinator handles recipe loading errors."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ), patch(
        "custom_components.anova_oven.coordinator.RecipeLibrary.from_yaml_file",
        side_effect=Exception("Generic error"),
    ):
        coordinator = AnovaOvenCoordinator(hass, mock_config_entry)
        await coordinator.async_refresh()

        # Should have empty recipe library
        assert coordinator.recipe_library is not None
        assert len(coordinator.recipe_library.recipes) == 0


async def test_coordinator_start_cook_error(
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_anova_oven: AsyncMock,
        mock_device,
):
    """Test coordinator handles start_cook errors."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]
    mock_anova_oven.start_cook.side_effect = AnovaError("Start cook failed")

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        coordinator = AnovaOvenCoordinator(hass, mock_config_entry)
        await coordinator.async_refresh()

        with pytest.raises(UpdateFailed, match="Failed to start cook"):
            await coordinator.async_start_cook("test-device-123", temperature=180.0)


async def test_coordinator_stop_cook_error(
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_anova_oven: AsyncMock,
        mock_device,
):
    """Test coordinator handles stop_cook errors."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]
    mock_anova_oven.stop_cook.side_effect = AnovaError("Stop cook failed")

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        coordinator = AnovaOvenCoordinator(hass, mock_config_entry)
        await coordinator.async_refresh()

        with pytest.raises(UpdateFailed, match="Failed to stop cook"):
            await coordinator.async_stop_cook("test-device-123")


async def test_coordinator_set_probe_error(
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_anova_oven: AsyncMock,
        mock_device,
):
    """Test coordinator handles set_probe errors."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]
    mock_anova_oven.set_probe.side_effect = AnovaError("Set probe failed")

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        coordinator = AnovaOvenCoordinator(hass, mock_config_entry)
        await coordinator.async_refresh()

        with pytest.raises(UpdateFailed, match="Failed to set probe"):
            await coordinator.async_set_probe("test-device-123", target=70.0)


async def test_coordinator_set_temperature_unit_error(
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_anova_oven: AsyncMock,
        mock_device,
):
    """Test coordinator handles set_temperature_unit errors."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]
    mock_anova_oven.set_temperature_unit.side_effect = AnovaError("Set unit failed")

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        coordinator = AnovaOvenCoordinator(hass, mock_config_entry)
        await coordinator.async_refresh()

        with pytest.raises(UpdateFailed, match="Failed to set temperature unit"):
            await coordinator.async_set_temperature_unit("test-device-123", "F")


async def test_coordinator_start_recipe_no_library(
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_anova_oven: AsyncMock,
        mock_device,
):
    """Test coordinator handles start_recipe when no library loaded."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ), patch(
        "custom_components.anova_oven.coordinator.RecipeLibrary.from_yaml_file",
        side_effect=FileNotFoundError(),
    ):
        coordinator = AnovaOvenCoordinator(hass, mock_config_entry)
        await coordinator.async_refresh()

        # Set recipe_library to None to test that branch
        coordinator.recipe_library = None

        with pytest.raises(UpdateFailed, match="Recipe library not loaded"):
            await coordinator.async_start_recipe("test-device-123", "some_recipe")


async def test_coordinator_start_recipe_device_not_found(
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_anova_oven: AsyncMock,
        mock_device,
        mock_recipe_library,
):
    """Test coordinator handles start_recipe when device not found."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ), patch(
        "custom_components.anova_oven.coordinator.RecipeLibrary.from_yaml_file",
        return_value=mock_recipe_library,
    ):
        coordinator = AnovaOvenCoordinator(hass, mock_config_entry)
        await coordinator.async_refresh()

        with pytest.raises(UpdateFailed, match="Device .* not found"):
            await coordinator.async_start_recipe("nonexistent-device", "roast_chicken")


async def test_coordinator_start_recipe_anova_error(
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_anova_oven: AsyncMock,
        mock_device,
        mock_recipe_library,
):
    """Test coordinator handles AnovaError during start_recipe."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]
    mock_anova_oven.start_cook.side_effect = AnovaError("Failed to start recipe")

    recipe_mock = mock_recipe_library.recipes["roast_chicken"]
    recipe_mock.validate_for_oven = MagicMock()
    recipe_mock.to_cook_stages = MagicMock(return_value=[])

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ), patch(
        "custom_components.anova_oven.coordinator.RecipeLibrary.from_yaml_file",
        return_value=mock_recipe_library,
    ):
        coordinator = AnovaOvenCoordinator(hass, mock_config_entry)
        await coordinator.async_refresh()

        with pytest.raises(UpdateFailed, match="Failed to start recipe"):
            await coordinator.async_start_recipe("test-device-123", "roast_chicken")


async def test_coordinator_get_device_no_data(
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_anova_oven: AsyncMock,
):
    """Test get_device when coordinator has no data."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = []

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        coordinator = AnovaOvenCoordinator(hass, mock_config_entry)
        # Don't refresh, so data is None

        result = coordinator.get_device("any-device")
        assert result is None


async def test_coordinator_load_recipes_custom_path_exception(
        hass: HomeAssistant,
        mock_anova_oven: AsyncMock,
):
    """Test coordinator handles exception when loading recipes from custom path (line 50)."""
    from custom_components.anova_oven.coordinator import AnovaOvenCoordinator
    from custom_components.anova_oven.const import CONF_RECIPES_PATH, CONF_WS_URL, DEFAULT_WS_URL, DOMAIN
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    # Create config entry with custom recipes path
    mock_config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            'token': "anova-test-token",
            CONF_WS_URL: DEFAULT_WS_URL,
            CONF_RECIPES_PATH: "/invalid/path/recipes.yml",
        },
        entry_id="test_entry_id",
    )
    mock_config_entry.add_to_hass(hass)

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ), patch(
        "custom_components.anova_oven.coordinator.RecipeLibrary.from_yaml_file",
        side_effect=Exception("Failed to load recipes"),
    ):
        coordinator = AnovaOvenCoordinator(hass, mock_config_entry)

        # This should catch the exception and create empty library (line 50)
        await coordinator._load_recipes()

        # Should have empty recipe library
        assert coordinator.recipe_library is not None
        assert len(coordinator.recipe_library.recipes) == 0


async def test_coordinator_start_recipe_validation_error(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_device,
        mock_recipe_library,
):
    """Test coordinator handles recipe validation error (line 198)."""
    from custom_components.anova_oven.coordinator import AnovaOvenCoordinator

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ), patch(
        "custom_components.anova_oven.coordinator.RecipeLibrary.from_yaml_file",
        return_value=mock_recipe_library,
    ):
        coordinator = AnovaOvenCoordinator(hass, mock_config_entry)
        await coordinator.async_refresh()

        # Make recipe validation fail
        recipe_mock = mock_recipe_library.recipes["roast_chicken"]
        recipe_mock.validate_for_oven = MagicMock(
            side_effect=ValueError("Recipe not compatible with oven")
        )

        # Should raise UpdateFailed with validation error (line 198)
        with pytest.raises(UpdateFailed, match="Recipe validation failed"):
            await coordinator.async_start_recipe("test-device-123", "roast_chicken")


async def test_coordinator_get_recipe_info_value_error(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
):
    """Test coordinator get_recipe_info returns None on ValueError (line 204)."""
    from custom_components.anova_oven.coordinator import AnovaOvenCoordinator

    mock_config_entry.add_to_hass(hass)

    mock_recipe_library = MagicMock()
    mock_recipe_library.get_recipe = MagicMock(
        side_effect=ValueError("Recipe not found")
    )

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ), patch(
        "custom_components.anova_oven.coordinator.RecipeLibrary.from_yaml_file",
        return_value=mock_recipe_library,
    ):
        coordinator = AnovaOvenCoordinator(hass, mock_config_entry)
        coordinator.recipe_library = mock_recipe_library

        # Should return None when ValueError is raised (line 204)
        result = coordinator.get_recipe_info("nonexistent_recipe")
        assert result is None


async def test_coordinator_recipes_load_exception(
        hass: HomeAssistant,
        mock_anova_oven: AsyncMock,
):
    """Test recipe loading handles exceptions (coordinator.py line 50)."""
    from custom_components.anova_oven.coordinator import AnovaOvenCoordinator
    from custom_components.anova_oven.const import CONF_RECIPES_PATH, CONF_WS_URL, CONF_ENVIRONMENT, \
        DEFAULT_WS_URL, DOMAIN
    from homeassistant.const import CONF_TOKEN
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    mock_config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_TOKEN: "anova-test-token",
            CONF_WS_URL: DEFAULT_WS_URL,
            CONF_ENVIRONMENT: "production",
            CONF_RECIPES_PATH: "/custom/recipes.yml",
        },
    )
    mock_config_entry.add_to_hass(hass)

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ), patch(
        "custom_components.anova_oven.coordinator.RecipeLibrary.from_yaml_file",
        side_effect=IOError("Cannot read file"),
    ):
        coordinator = AnovaOvenCoordinator(hass, mock_config_entry)
        await coordinator._load_recipes()

        # Should catch exception and create empty library (line 50)
        assert coordinator.recipe_library is not None
        assert len(coordinator.recipe_library.recipes) == 0


async def test_coordinator_recipe_validation_fails(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_device,
        mock_recipe_library,
):
    """Test recipe validation error handling (coordinator.py line 198)."""
    from custom_components.anova_oven.coordinator import AnovaOvenCoordinator
    from homeassistant.helpers.update_coordinator import UpdateFailed

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ), patch(
        "custom_components.anova_oven.coordinator.RecipeLibrary.from_yaml_file",
        return_value=mock_recipe_library,
    ):
        coordinator = AnovaOvenCoordinator(hass, mock_config_entry)
        await coordinator.async_refresh()

        # Make validation raise ValueError
        recipe = mock_recipe_library.recipes["roast_chicken"]
        recipe.validate_for_oven = MagicMock(
            side_effect=ValueError("Incompatible oven version")
        )

        # Line 198 catches ValueError
        with pytest.raises(UpdateFailed, match="Recipe validation failed"):
            await coordinator.async_start_recipe("test-device-123", "roast_chicken")


async def test_coordinator_get_recipe_info_not_found(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
):
    """Test get_recipe_info returns None when recipe not found (coordinator.py line 204)."""
    from custom_components.anova_oven.coordinator import AnovaOvenCoordinator

    mock_config_entry.add_to_hass(hass)

    mock_recipe_library = MagicMock()
    mock_recipe_library.get_recipe = MagicMock(
        side_effect=ValueError("Recipe not found")
    )

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        coordinator = AnovaOvenCoordinator(hass, mock_config_entry)
        coordinator.recipe_library = mock_recipe_library

        # Line 204 catches ValueError and returns None
        result = coordinator.get_recipe_info("nonexistent")
        assert result is None


async def test_coordinator_async_setup_already_complete(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
):
    """Test _async_setup returns early when already complete (line 50)."""
    from custom_components.anova_oven.coordinator import AnovaOvenCoordinator

    mock_config_entry.add_to_hass(hass)

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        coordinator = AnovaOvenCoordinator(hass, mock_config_entry)

        # First setup
        await coordinator._async_setup()
        assert coordinator._setup_complete is True

        # Call again - should return early at line 50
        await coordinator._async_setup()

        # Verify connect was only called once (first setup)
        assert mock_anova_oven.connect.call_count == 1


async def test_coordinator_get_available_recipes_no_library(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
):
    """Test get_available_recipes returns empty list when no library (line 198)."""
    from custom_components.anova_oven.coordinator import AnovaOvenCoordinator

    mock_config_entry.add_to_hass(hass)

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        coordinator = AnovaOvenCoordinator(hass, mock_config_entry)
        coordinator.recipe_library = None

        # Should return empty list (line 198)
        result = coordinator.get_available_recipes()
        assert result == []


async def test_coordinator_get_recipe_info_no_library(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
):
    """Test get_recipe_info returns None when no library (line 204)."""
    from custom_components.anova_oven.coordinator import AnovaOvenCoordinator

    mock_config_entry.add_to_hass(hass)

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        coordinator = AnovaOvenCoordinator(hass, mock_config_entry)
        coordinator.recipe_library = None

        # Should return None (line 204)
        result = coordinator.get_recipe_info("any_recipe")
        assert result is None