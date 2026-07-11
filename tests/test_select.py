"""Test the Anova Oven select platform."""
from unittest.mock import AsyncMock, patch, MagicMock

from homeassistant.const import ATTR_ENTITY_ID, ATTR_OPTION
from homeassistant.core import HomeAssistant, State

from pytest_homeassistant_custom_component.common import mock_restore_cache

from custom_components.anova_oven.const import DOMAIN


async def test_select_setup(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test select setup."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]
    
    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
    
    assert hass.states.get("select.test_oven_recipe") is not None
    assert hass.states.get("select.test_oven_temperature_unit") is not None


async def test_recipe_select_no_recipes(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test recipe select with no recipes loaded."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]
    
    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
    
    state = hass.states.get("select.test_oven_recipe")
    assert state.state == "None"
    assert state.attributes["options"] == ["None"]


async def test_recipe_select_with_recipes(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
    mock_recipe_library,
):
    """Test recipe select with recipes loaded."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]
    
    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ), patch(
        "custom_components.anova_oven.coordinator.RecipeLibrary.from_yaml_file",
        return_value=mock_recipe_library,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
    
    state = hass.states.get("select.test_oven_recipe")
    assert state.state == "None"
    assert "None" in state.attributes["options"]
    assert "roast_chicken" in state.attributes["options"]
    assert "sourdough" in state.attributes["options"]


async def test_recipe_select_current_cooking(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_cooking_device,
    mock_recipe_library,
):
    """Test recipe select shows current recipe when cooking."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_cooking_device]
    # Must match mock_cooking_device.cook.cook_id so get_active_recipe_id()
    # recognizes the started cook as the one now reported by the device.
    mock_anova_oven.start_cook.return_value = mock_cooking_device.cook.cook_id

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ), patch(
        "custom_components.anova_oven.coordinator.RecipeLibrary.from_yaml_file",
        return_value=mock_recipe_library,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]
        await coordinator.async_start_recipe("test-device-123", "roast_chicken")
        await hass.async_block_till_done()

    state = hass.states.get("select.test_oven_recipe")
    assert state.state == "roast_chicken"


async def test_recipe_select_restores_state_while_cooking(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_cooking_device,
    mock_recipe_library,
):
    """A restored recipe selection should reappear (and get confirmed
    against the oven's real cook_id) if a cook is still genuinely active
    across a HA restart/reload, instead of flashing back to "None"."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_cooking_device]

    mock_restore_cache(
        hass,
        [State("select.test_oven_recipe", "roast_chicken")],
    )

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ), patch(
        "custom_components.anova_oven.coordinator.RecipeLibrary.from_yaml_file",
        return_value=mock_recipe_library,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("select.test_oven_recipe")
    assert state.state == "roast_chicken"

    coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]
    # The restored (cook_id=None, recipe_id) entry should have been
    # confirmed/adopted against the device's real cook_id by now.
    assert coordinator._active_recipes["test-device-123"] == ("cook-123", "roast_chicken")


async def test_recipe_select_restore_ignored_when_not_cooking(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
    mock_recipe_library,
):
    """A restored recipe selection should be dropped if the device isn't
    actually cooking - it shouldn't get stuck showing a stale recipe."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    mock_restore_cache(
        hass,
        [State("select.test_oven_recipe", "roast_chicken")],
    )

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ), patch(
        "custom_components.anova_oven.coordinator.RecipeLibrary.from_yaml_file",
        return_value=mock_recipe_library,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("select.test_oven_recipe")
    assert state.state == "None"


async def test_recipe_select_start_recipe(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
    mock_recipe_library,
):
    """Test selecting a recipe starts it."""
    # Setup recipe mock
    recipe_mock = mock_recipe_library.recipes["roast_chicken"]
    recipe_mock.validate_for_oven = AsyncMock()
    recipe_mock.to_cook_stages = AsyncMock(return_value=[])
    
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]
    
    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ), patch(
        "custom_components.anova_oven.coordinator.RecipeLibrary.from_yaml_file",
        return_value=mock_recipe_library,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        
        await hass.services.async_call(
            "select",
            "select_option",
            {
                ATTR_ENTITY_ID: "select.test_oven_recipe",
                ATTR_OPTION: "roast_chicken",
            },
            blocking=True,
        )
    
    mock_anova_oven.start_cook.assert_called_once()


async def test_recipe_select_none_stops_cook(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_cooking_device,
    mock_recipe_library,
):
    """Test selecting None stops cooking."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_cooking_device]
    
    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ), patch(
        "custom_components.anova_oven.coordinator.RecipeLibrary.from_yaml_file",
        return_value=mock_recipe_library,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        
        await hass.services.async_call(
            "select",
            "select_option",
            {
                ATTR_ENTITY_ID: "select.test_oven_recipe",
                ATTR_OPTION: "None",
            },
            blocking=True,
        )
    
    mock_anova_oven.stop_cook.assert_called_once_with("test-device-123")


async def test_recipe_select_extra_attributes(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_cooking_device,
    mock_recipe_library,
):
    """Test recipe select extra attributes."""
    # Create detailed recipe info
    recipe_mock = mock_recipe_library.recipes["roast_chicken"]
    recipe_mock.description = "Perfect roast chicken"
    recipe_mock.stages = [{"temp": 180}, {"temp": 200}]
    recipe_mock.oven_version = None

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_cooking_device]
    # Must match mock_cooking_device.cook.cook_id so get_active_recipe_id()
    # recognizes the started cook as the one now reported by the device.
    mock_anova_oven.start_cook.return_value = mock_cooking_device.cook.cook_id

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ), patch(
        "custom_components.anova_oven.coordinator.RecipeLibrary.from_yaml_file",
        return_value=mock_recipe_library,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]
        await coordinator.async_start_recipe("test-device-123", "roast_chicken")
        await hass.async_block_till_done()

    state = hass.states.get("select.test_oven_recipe")
    assert "recipe_description" in state.attributes
    assert "recipe_stages" in state.attributes


async def test_temperature_unit_select(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test temperature unit select."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]
    
    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
    
    state = hass.states.get("select.test_oven_temperature_unit")
    assert state.state == "C"
    assert state.attributes["options"] == ["C", "F"]


async def test_temperature_unit_select_change(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test changing temperature unit."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]
    
    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        
        await hass.services.async_call(
            "select",
            "select_option",
            {
                ATTR_ENTITY_ID: "select.test_oven_temperature_unit",
                ATTR_OPTION: "F",
            },
            blocking=True,
        )
    
    mock_anova_oven.set_temperature_unit.assert_called_once_with("test-device-123", "F")


async def test_temperature_unit_fahrenheit(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test temperature unit select shows Fahrenheit."""
    mock_device.state_info.temperature_unit = "F"
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]
    
    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
    
    state = hass.states.get("select.test_oven_temperature_unit")
    assert state.state == "F"


async def test_select_recipe_info_none(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_device,
        mock_recipe_library,
):
    """Test select extra attributes when recipe_info returns None (select.py line 93)."""
    # Create a device with a recipe name that doesn't exist
    mock_device.state.cook = MagicMock()
    mock_device.state.cook.name = "nonexistent_recipe"

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ), patch(
        "custom_components.anova_oven.coordinator.RecipeLibrary.from_yaml_file",
        return_value=mock_recipe_library,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("select.test_oven_recipe")
    # Recipe info should be empty when recipe not found
    assert "recipe_description" not in state.attributes


async def test_select_extra_attributes_recipe_info_none(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_device,
        mock_recipe_library,
):
    """Test select extra attributes when recipe_info returns None (line 93)."""
    # Set cook name to a recipe that doesn't exist
    mock_device.state.cook = MagicMock()
    mock_device.state.cook.name = "nonexistent_recipe"

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ), patch(
        "custom_components.anova_oven.coordinator.RecipeLibrary.from_yaml_file",
        return_value=mock_recipe_library,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("select.test_oven_recipe")
    # Should not have recipe attributes when recipe_info is None
    assert "recipe_description" not in state.attributes


async def test_select_extra_attributes_recipe_not_found(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_cooking_device,
        mock_recipe_library,
):
    """Test extra_state_attributes returns {} when recipe_info is None (line 93)."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_cooking_device]

    # Make the active recipe resolvable but get_recipe_info return None
    mock_recipe_library.recipes["existing_recipe"] = mock_recipe_library.recipes["roast_chicken"]
    mock_recipe_library.list_recipes.return_value = ["existing_recipe"]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ), patch(
        "custom_components.anova_oven.coordinator.RecipeLibrary.from_yaml_file",
        return_value=mock_recipe_library,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]
        await coordinator.async_start_recipe("test-device-123", "existing_recipe")
        await hass.async_block_till_done()

        # Make get_recipe_info return None
        coordinator.get_recipe_info = lambda x: None

        # Trigger state update
        coordinator.async_set_updated_data(coordinator.data)
        await hass.async_block_till_done()

        state = hass.states.get("select.test_oven_recipe")
        # Should return {} (line 93)
        assert "recipe_description" not in state.attributes
