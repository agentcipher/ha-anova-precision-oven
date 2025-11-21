"""Test the Anova Oven services."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.anova_oven.const import (
    DOMAIN,
    SERVICE_START_COOK,
    SERVICE_STOP_COOK,
    SERVICE_START_RECIPE,
    SERVICE_SET_PROBE,
    SERVICE_SET_TEMPERATURE_UNIT,
    ATTR_TEMPERATURE_UNIT,
    ATTR_RECIPE_ID,
    ATTR_DURATION,
    ATTR_FAN_SPEED,
)

from homeassistant.components.climate import (
    ATTR_TEMPERATURE,
)


async def test_setup_services(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test services are registered."""
    from custom_components.anova_oven.services import async_setup_services

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        await async_setup_services(hass)

    # Verify services are registered
    assert hass.services.has_service(DOMAIN, SERVICE_START_COOK)
    assert hass.services.has_service(DOMAIN, SERVICE_STOP_COOK)
    assert hass.services.has_service(DOMAIN, SERVICE_START_RECIPE)
    assert hass.services.has_service(DOMAIN, SERVICE_SET_PROBE)
    assert hass.services.has_service(DOMAIN, SERVICE_SET_TEMPERATURE_UNIT)


async def test_service_start_cook(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test start_cook service."""
    from custom_components.anova_oven.services import async_setup_services

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        await async_setup_services(hass)

        # Mock entity state with device_id attribute
        hass.states.async_set(
            "climate.test_oven_oven",
            "idle",
            {"device_id": "test-device-123"}
        )

        # Call service
        await hass.services.async_call(
            DOMAIN,
            SERVICE_START_COOK,
            {
                "entity_id": "climate.test_oven_oven",
                ATTR_TEMPERATURE: 200.0,
                ATTR_TEMPERATURE_UNIT: "C",
                ATTR_DURATION: 3600,
                ATTR_FAN_SPEED: 75,
            },
            blocking=True,
        )

    # Verify coordinator method was called
    mock_anova_oven.start_cook.assert_called()


async def test_service_stop_cook(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test stop_cook service."""
    from custom_components.anova_oven.services import async_setup_services

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        await async_setup_services(hass)

        hass.states.async_set(
            "climate.test_oven_oven",
            "cooking",
            {"device_id": "test-device-123"}
        )

        await hass.services.async_call(
            DOMAIN,
            SERVICE_STOP_COOK,
            {"entity_id": "climate.test_oven_oven"},
            blocking=True,
        )

    mock_anova_oven.stop_cook.assert_called()


async def test_service_start_recipe(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
    mock_recipe_library,
):
    """Test start_recipe service."""
    from custom_components.anova_oven.services import async_setup_services

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

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
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        await async_setup_services(hass)

        hass.states.async_set(
            "climate.test_oven_oven",
            "idle",
            {"device_id": "test-device-123"}
        )

        await hass.services.async_call(
            DOMAIN,
            SERVICE_START_RECIPE,
            {
                "entity_id": "climate.test_oven_oven",
                ATTR_RECIPE_ID: "roast_chicken",
            },
            blocking=True,
        )

    mock_anova_oven.start_cook.assert_called()


async def test_service_set_probe(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_probe_device,
):
    """Test set_probe service."""
    from custom_components.anova_oven.services import async_setup_services

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_probe_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        await async_setup_services(hass)

        hass.states.async_set(
            "climate.test_oven_oven",
            "idle",
            {"device_id": "test-device-123"}
        )

        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_PROBE,
            {
                "entity_id": "climate.test_oven_oven",
                "target": 75.0,
                ATTR_TEMPERATURE_UNIT: "C",
            },
            blocking=True,
        )

    mock_anova_oven.set_probe.assert_called()


async def test_service_set_temperature_unit(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test set_temperature_unit service."""
    from custom_components.anova_oven.services import async_setup_services

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        await async_setup_services(hass)

        hass.states.async_set(
            "climate.test_oven_oven",
            "idle",
            {"device_id": "test-device-123"}
        )

        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_TEMPERATURE_UNIT,
            {
                "entity_id": "climate.test_oven_oven",
                "unit": "F",
            },
            blocking=True,
        )

    mock_anova_oven.set_temperature_unit.assert_called()


async def test_unload_services(hass: HomeAssistant):
    """Test services are unloaded."""
    from custom_components.anova_oven.services import (
        async_setup_services,
        async_unload_services,
    )

    await async_setup_services(hass)

    assert hass.services.has_service(DOMAIN, SERVICE_START_COOK)

    await async_unload_services(hass)

    assert not hass.services.has_service(DOMAIN, SERVICE_START_COOK)
    assert not hass.services.has_service(DOMAIN, SERVICE_STOP_COOK)
    assert not hass.services.has_service(DOMAIN, SERVICE_START_RECIPE)
    assert not hass.services.has_service(DOMAIN, SERVICE_SET_PROBE)
    assert not hass.services.has_service(DOMAIN, SERVICE_SET_TEMPERATURE_UNIT)


async def test_service_with_invalid_entity(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test service with invalid entity_id."""
    from custom_components.anova_oven.services import async_setup_services

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        await async_setup_services(hass)

        # Call with non-existent entity
        await hass.services.async_call(
            DOMAIN,
            SERVICE_STOP_COOK,
            {"entity_id": "climate.nonexistent"},
            blocking=True,
        )

    # Should not crash, just skip


async def test_service_error_handling(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test service error handling."""
    from custom_components.anova_oven.services import async_setup_services
    from custom_components.anova_oven.anova_sdk.exceptions import AnovaError

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]
    mock_anova_oven.start_cook.side_effect = AnovaError("Failed")

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        await async_setup_services(hass)

        hass.states.async_set(
            "climate.test_oven_oven",
            "idle",
            {"device_id": "test-device-123"}
        )

        # Should handle error gracefully
        await hass.services.async_call(
            DOMAIN,
            SERVICE_START_COOK,
            {
                "entity_id": "climate.test_oven_oven",
                ATTR_TEMPERATURE: 200.0,
            },
            blocking=True,
        )


async def test_service_no_device_id_in_state(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test services when entity has no device_id in state (lines 79, 108, 124, etc)."""
    from custom_components.anova_oven.services import async_setup_services

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        await async_setup_services(hass)

        # Set entity state WITHOUT device_id attribute
        hass.states.async_set("climate.test_oven_oven", "idle", {})

        # Call service - should skip since no device_id
        await hass.services.async_call(
            "anova_oven",
            "start_cook",
            {
                "entity_id": "climate.test_oven_oven",
                "temperature": 200.0,
            },
            blocking=True,
        )

    # Should not have called start_cook since device_id was None
    mock_anova_oven.start_cook.assert_not_called()


async def test_service_no_coordinator_found(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test services when coordinator not found (lines 83, 113, 128, etc)."""
    from custom_components.anova_oven.services import async_setup_services

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        await async_setup_services(hass)

        # Set device_id that doesn't exist in any coordinator
        hass.states.async_set(
            "climate.test_oven_oven",
            "idle",
            {"device_id": "nonexistent-device-999"}
        )

        # Call service - should skip since no coordinator found
        await hass.services.async_call(
            "anova_oven",
            "stop_cook",
            {"entity_id": "climate.test_oven_oven"},
            blocking=True,
        )

    # Should not have called stop_cook
    mock_anova_oven.stop_cook.assert_not_called()


async def test_service_exception_handling_all_services(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test exception handling in all service handlers (lines 114, 134, 152, 162, 175, 183)."""
    from custom_components.anova_oven.services import async_setup_services

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    # Make all coordinator methods raise exceptions
    mock_anova_oven.start_cook.side_effect = Exception("Failed")
    mock_anova_oven.stop_cook.side_effect = Exception("Failed")
    mock_anova_oven.set_probe.side_effect = Exception("Failed")
    mock_anova_oven.set_temperature_unit.side_effect = Exception("Failed")

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        await async_setup_services(hass)

        hass.states.async_set(
            "climate.test_oven_oven",
            "idle",
            {"device_id": "test-device-123"}
        )

        # Test start_cook exception (line 114)
        await hass.services.async_call(
            "anova_oven",
            "start_cook",
            {
                "entity_id": "climate.test_oven_oven",
                "temperature": 200.0,
            },
            blocking=True,
        )

        # Test stop_cook exception (line 134)
        await hass.services.async_call(
            "anova_oven",
            "stop_cook",
            {"entity_id": "climate.test_oven_oven"},
            blocking=True,
        )

        # Test set_probe exception (line 162)
        await hass.services.async_call(
            "anova_oven",
            "set_probe",
            {
                "entity_id": "climate.test_oven_oven",
                "target": 70.0,
            },
            blocking=True,
        )

        # Test set_temperature_unit exception (line 183)
        await hass.services.async_call(
            "anova_oven",
            "set_temperature_unit",
            {
                "entity_id": "climate.test_oven_oven",
                "unit": "F",
            },
            blocking=True,
        )


async def test_get_coordinator_for_device_returns_none(
    hass: HomeAssistant,
):
    """Test _get_coordinator_for_device returns None (line 251)."""
    from custom_components.anova_oven.services import _get_coordinator_for_device

    # No data in hass.data[DOMAIN]
    result = await _get_coordinator_for_device(hass, "test-device")
    assert result is None


async def test_service_start_cook_exception_handling(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_device,
):
    """Test start_cook service handles exceptions (services.py line 83)."""
    from custom_components.anova_oven.services import async_setup_services

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Setup services
        await async_setup_services(hass)

        # Make start_cook raise an exception
        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]
        coordinator.async_start_cook = AsyncMock(
            side_effect=Exception("Start cook failed")
        )

        # Call service - should catch exception and log error (line 83)
        await hass.services.async_call(
            DOMAIN,
            SERVICE_START_COOK,
            {
                "entity_id": "climate.test_oven_oven",
                "temperature": 180.0,
            },
            blocking=True,
        )

        # Should not raise, just log the error
        await hass.async_block_till_done()


async def test_service_stop_cook_exception_handling(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_device,
):
    """Test stop_cook service handles exceptions (services.py line 101)."""
    from custom_components.anova_oven.services import async_setup_services

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Setup services
        await async_setup_services(hass)

        # Make stop_cook raise an exception
        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]
        coordinator.async_stop_cook = AsyncMock(
            side_effect=Exception("Stop cook failed")
        )

        # Call service - should catch exception
        await hass.services.async_call(
            DOMAIN,
            SERVICE_STOP_COOK,
            {"entity_id": "climate.test_oven_oven"},
            blocking=True,
        )

        await hass.async_block_till_done()


async def test_service_start_recipe_exception_handling(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_device,
):
    """Test start_recipe service handles exceptions (services.py lines 124, 128)."""
    from custom_components.anova_oven.services import async_setup_services

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Setup services
        await async_setup_services(hass)

        # Make start_recipe raise an exception
        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]
        coordinator.async_start_recipe = AsyncMock(
            side_effect=Exception("Start recipe failed")
        )

        # Call service - should catch exception (lines 124, 128)
        await hass.services.async_call(
            DOMAIN,
            SERVICE_START_RECIPE,
            {
                "entity_id": "climate.test_oven_oven",
                "recipe_id": "test_recipe",
            },
            blocking=True,
        )

        await hass.async_block_till_done()


async def test_service_set_probe_exception_handling(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_device,
):
    """Test set_probe service handles exceptions (services.py lines 148, 152)."""
    from custom_components.anova_oven.services import async_setup_services

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Setup services
        await async_setup_services(hass)

        # Make set_probe raise an exception
        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]
        coordinator.async_set_probe = AsyncMock(
            side_effect=Exception("Set probe failed")
        )

        # Call service - should catch exception (lines 148, 152)
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_PROBE,
            {
                "entity_id": "climate.test_oven_oven",
                "target": 70.0,
            },
            blocking=True,
        )

        await hass.async_block_till_done()


async def test_service_set_temperature_unit_exception_handling(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_device,
):
    """Test set_temperature_unit service handles exceptions (services.py lines 171, 175)."""
    from custom_components.anova_oven.services import async_setup_services

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Setup services
        await async_setup_services(hass)

        # Make set_temperature_unit raise an exception
        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]
        coordinator.async_set_temperature_unit = AsyncMock(
            side_effect=Exception("Set temperature unit failed")
        )

        # Call service - should catch exception (lines 171, 175)
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_TEMPERATURE_UNIT,
            {
                "entity_id": "climate.test_oven_oven",
                "unit": "F",
            },
            blocking=True,
        )

        await hass.async_block_till_done()


async def test_service_get_device_id_returns_none(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_device,
):
    """Test service when _get_device_id_from_entity returns None."""
    from custom_components.anova_oven.services import async_setup_services

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Setup services
        await async_setup_services(hass)

        # Call service with non-existent entity
        await hass.services.async_call(
            DOMAIN,
            SERVICE_START_COOK,
            {
                "entity_id": "climate.nonexistent_oven",
                "temperature": 180.0,
            },
            blocking=True,
        )

        # Should not call start_cook since device_id is None
        mock_anova_oven.start_cook.assert_not_called()


async def test_service_get_coordinator_returns_none(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_device,
):
    """Test service when _get_coordinator_for_device returns None."""
    from custom_components.anova_oven.services import async_setup_services

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ), patch(
        "custom_components.anova_oven.services._get_coordinator_for_device",
        return_value=None,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Setup services
        await async_setup_services(hass)

        # Call service - coordinator lookup returns None
        await hass.services.async_call(
            DOMAIN,
            SERVICE_START_COOK,
            {
                "entity_id": "climate.test_oven_oven",
                "temperature": 180.0,
            },
            blocking=True,
        )

        # Should not call start_cook since coordinator is None
        mock_anova_oven.start_cook.assert_not_called()


async def test_services_exception_in_start_cook(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_device,
):
    """Test start_cook exception handling (services.py line 83)."""
    from custom_components.anova_oven.services import async_setup_services
    from custom_components.anova_oven.const import SERVICE_START_COOK, DOMAIN

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        await async_setup_services(hass)

        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]
        coordinator.async_start_cook = AsyncMock(side_effect=Exception("Failed"))

        # Line 83: except Exception
        await hass.services.async_call(
            DOMAIN,
            SERVICE_START_COOK,
            {"entity_id": "climate.test_oven_oven", "temperature": 180.0},
            blocking=True,
        )


async def test_services_exception_in_start_recipe(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_device,
):
    """Test start_recipe exception handling (services.py line 128)."""
    from custom_components.anova_oven.services import async_setup_services
    from custom_components.anova_oven.const import SERVICE_START_RECIPE, DOMAIN

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        await async_setup_services(hass)

        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]
        coordinator.async_start_recipe = AsyncMock(side_effect=Exception("Failed"))

        # Line 128: except Exception
        await hass.services.async_call(
            DOMAIN,
            SERVICE_START_RECIPE,
            {"entity_id": "climate.test_oven_oven", "recipe_id": "test"},
            blocking=True,
        )


async def test_services_exception_in_set_probe(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_device,
):
    """Test set_probe exception handling (services.py line 152)."""
    from custom_components.anova_oven.services import async_setup_services
    from custom_components.anova_oven.const import SERVICE_SET_PROBE, DOMAIN

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        await async_setup_services(hass)

        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]
        coordinator.async_set_probe = AsyncMock(side_effect=Exception("Failed"))

        # Line 152: except Exception
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_PROBE,
            {"entity_id": "climate.test_oven_oven", "target": 70.0},
            blocking=True,
        )


async def test_services_exception_in_set_temperature_unit(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_device,
):
    """Test set_temperature_unit exception handling (services.py line 175)."""
    from custom_components.anova_oven.services import async_setup_services
    from custom_components.anova_oven.const import SERVICE_SET_TEMPERATURE_UNIT, DOMAIN

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        await async_setup_services(hass)

        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]
        coordinator.async_set_temperature_unit = AsyncMock(side_effect=Exception("Failed"))

        # Line 175: except Exception
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_TEMPERATURE_UNIT,
            {"entity_id": "climate.test_oven_oven", "unit": "F"},
            blocking=True,
        )

async def test_service_start_cook_no_coordinator(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test start_cook continues when coordinator not found (line 83)."""
    from custom_components.anova_oven.services import async_setup_services
    from custom_components.anova_oven.const import SERVICE_START_COOK, DOMAIN

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ), patch(
        "custom_components.anova_oven.services._get_coordinator_for_device",
        return_value=None,  # No coordinator found
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        await async_setup_services(hass)

        # Call service - should continue (line 83) when coordinator is None
        await hass.services.async_call(
            DOMAIN,
            SERVICE_START_COOK,
            {"entity_id": "climate.test_oven_oven", "temperature": 180.0},
            blocking=True,
        )

    # Should not crash, just skip
    mock_anova_oven.start_cook.assert_not_called()


async def test_service_start_cook_exception(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test start_cook exception handling (line 95)."""
    from custom_components.anova_oven.services import async_setup_services
    from custom_components.anova_oven.const import SERVICE_START_COOK, DOMAIN

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        await async_setup_services(hass)

        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]
        coordinator.async_start_cook = AsyncMock(side_effect=Exception("Failed"))

        # Should catch exception (line 95)
        await hass.services.async_call(
            DOMAIN,
            SERVICE_START_COOK,
            {"entity_id": "climate.test_oven_oven", "temperature": 180.0},
            blocking=True,
        )


async def test_service_start_recipe_exception(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test start_recipe exception handling (line 128)."""
    from custom_components.anova_oven.services import async_setup_services
    from custom_components.anova_oven.const import SERVICE_START_RECIPE, DOMAIN

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        await async_setup_services(hass)

        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]
        coordinator.async_start_recipe = AsyncMock(side_effect=Exception("Failed"))

        # Should catch exception (line 128)
        await hass.services.async_call(
            DOMAIN,
            SERVICE_START_RECIPE,
            {"entity_id": "climate.test_oven_oven", "recipe_id": "test"},
            blocking=True,
        )


async def test_service_set_probe_exception(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test set_probe exception handling (line 152)."""
    from custom_components.anova_oven.services import async_setup_services
    from custom_components.anova_oven.const import SERVICE_SET_PROBE, DOMAIN

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        await async_setup_services(hass)

        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]
        coordinator.async_set_probe = AsyncMock(side_effect=Exception("Failed"))

        # Should catch exception (line 152)
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_PROBE,
            {"entity_id": "climate.test_oven_oven", "target": 70.0},
            blocking=True,
        )


async def test_service_set_temperature_unit_exception(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test set_temperature_unit exception handling (line 175)."""
    from custom_components.anova_oven.services import async_setup_services
    from custom_components.anova_oven.const import SERVICE_SET_TEMPERATURE_UNIT, DOMAIN

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        await async_setup_services(hass)

        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]
        coordinator.async_set_temperature_unit = AsyncMock(side_effect=Exception("Failed"))

        # Should catch exception (line 175)
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_TEMPERATURE_UNIT,
            {"entity_id": "climate.test_oven_oven", "unit": "F"},
            blocking=True,
        )

async def test_service_start_cook_no_coordinator_line_83(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test start_cook continues when coordinator is None (line 83)."""
    from custom_components.anova_oven.services import async_setup_services
    from custom_components.anova_oven.const import SERVICE_START_COOK, DOMAIN

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ), patch(
        "custom_components.anova_oven.services._get_coordinator_for_device",
        return_value=None,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        await async_setup_services(hass)

        hass.states.async_set(
            "climate.test_oven_oven", "idle", {"device_id": "test-device-123"}
        )

        # Line 83: should continue when coordinator is None
        await hass.services.async_call(
            DOMAIN,
            SERVICE_START_COOK,
            {"entity_id": "climate.test_oven_oven", ATTR_TEMPERATURE: 180.0},
            blocking=True,
        )

    mock_anova_oven.start_cook.assert_not_called()


# ============================================================================
# services.py line 128 - continue when coordinator is None (start_recipe)
# ============================================================================
async def test_service_start_recipe_no_coordinator_line_128(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test start_recipe continues when coordinator is None (line 128)."""
    from custom_components.anova_oven.services import async_setup_services
    from custom_components.anova_oven.const import SERVICE_START_RECIPE, DOMAIN, ATTR_RECIPE_ID

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ), patch(
        "custom_components.anova_oven.services._get_coordinator_for_device",
        return_value=None,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        await async_setup_services(hass)

        hass.states.async_set(
            "climate.test_oven_oven", "idle", {"device_id": "test-device-123"}
        )

        # Line 128: should continue when coordinator is None
        await hass.services.async_call(
            DOMAIN,
            SERVICE_START_RECIPE,
            {"entity_id": "climate.test_oven_oven", ATTR_RECIPE_ID: "test_recipe"},
            blocking=True,
        )

    mock_anova_oven.start_cook.assert_not_called()


# ============================================================================
# services.py lines 133-134 - exception handler log in start_recipe
# ============================================================================
async def test_service_start_recipe_exception_lines_133_134(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test start_recipe exception handler logs error (lines 133-134)."""
    from custom_components.anova_oven.services import async_setup_services
    from custom_components.anova_oven.const import SERVICE_START_RECIPE, DOMAIN, ATTR_RECIPE_ID

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        await async_setup_services(hass)

        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]
        coordinator.async_start_recipe = AsyncMock(side_effect=Exception("Recipe failed"))

        hass.states.async_set(
            "climate.test_oven_oven", "idle", {"device_id": "test-device-123"}
        )

        # Lines 133-134: should catch exception and log error
        await hass.services.async_call(
            DOMAIN,
            SERVICE_START_RECIPE,
            {"entity_id": "climate.test_oven_oven", ATTR_RECIPE_ID: "bad_recipe"},
            blocking=True,
        )


# ============================================================================
# services.py line 152 - continue when coordinator is None (set_probe)
# ============================================================================
async def test_service_set_probe_no_coordinator_line_152(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test set_probe continues when coordinator is None (line 152)."""
    from custom_components.anova_oven.services import async_setup_services
    from custom_components.anova_oven.const import SERVICE_SET_PROBE, DOMAIN

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ), patch(
        "custom_components.anova_oven.services._get_coordinator_for_device",
        return_value=None,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        await async_setup_services(hass)

        hass.states.async_set(
            "climate.test_oven_oven", "idle", {"device_id": "test-device-123"}
        )

        # Line 152: should continue when coordinator is None
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_PROBE,
            {"entity_id": "climate.test_oven_oven", "target": 70.0},
            blocking=True,
        )

    mock_anova_oven.set_probe.assert_not_called()


# ============================================================================
# services.py line 175 - continue when coordinator is None (set_temperature_unit)
# ============================================================================
async def test_service_set_temperature_unit_no_coordinator_line_175(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test set_temperature_unit continues when coordinator is None (line 175)."""
    from custom_components.anova_oven.services import async_setup_services
    from custom_components.anova_oven.const import SERVICE_SET_TEMPERATURE_UNIT, DOMAIN

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ), patch(
        "custom_components.anova_oven.services._get_coordinator_for_device",
        return_value=None,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        await async_setup_services(hass)

        hass.states.async_set(
            "climate.test_oven_oven", "idle", {"device_id": "test-device-123"}
        )

        # Line 175: should continue when coordinator is None
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_TEMPERATURE_UNIT,
            {"entity_id": "climate.test_oven_oven", "unit": "F"},
            blocking=True,
        )

    mock_anova_oven.set_temperature_unit.assert_not_called()