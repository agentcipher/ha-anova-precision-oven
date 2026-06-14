"""Working example of sensor tests for Anova Oven."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_TOKEN

from custom_components.anova_oven.const import DOMAIN, CONF_WS_URL, DEFAULT_WS_URL
from anova_oven_sdk.response_models import SteamGenerators


async def test_sensors_created_with_device(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test that sensor entities are created when device is discovered."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    all_entities = hass.states.async_entity_ids()
    sensor_entities = [e for e in all_entities if e.startswith("sensor.")]
    assert len(sensor_entities) > 0, f"No sensors created. All entities: {all_entities}"


async def test_temperature_sensor_reads_state(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test temperature sensor reads from device state."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("sensor.test_oven_current_temperature")
    assert state is not None
    assert state.state == "25.0"


async def test_wet_mode_temperature(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test temperature with wet mode."""
    mock_device.nodes.temperature_bulbs.mode = "wet"
    mock_device.nodes.temperature_bulbs.wet.current["celsius"] = 95.0

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("sensor.test_oven_current_temperature")
    assert state is not None
    assert state.state == "95.0"


async def test_sensor_availability_function_returns_false(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_device,
):
    """Test sensor unavailable when available_fn returns False."""
    # Probe is disconnected by default, so probe sensors should be unavailable
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    # Probe temperature sensor should be unavailable when probe.current is None
    state = hass.states.get("sensor.test_oven_probe_temperature")
    assert state.state == "unavailable"


async def test_sensor_availability_no_available_fn(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_device,
):
    """Test sensor with no available_fn defaults to available."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    # Fan speed sensor has no available_fn, so should be available (line 252)
    state = hass.states.get("sensor.test_oven_fan_speed")
    assert state is not None
    assert state.state != "unavailable"


async def test_sensor_current_stage_unavailable_when_idle(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_device,
):
    """Test current_stage sensor unavailable when idle."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("sensor.test_oven_current_stage")
    assert state.state == "unavailable"


async def test_sensor_total_stages_unavailable_when_idle(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_device,
):
    """Test total_stages sensor unavailable when idle."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("sensor.test_oven_total_stages")
    assert state.state == "unavailable"


async def test_sensor_recipe_name_unavailable_when_idle(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_device,
):
    """Test recipe_name sensor unavailable when idle."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("sensor.test_oven_recipe_name")
    assert state.state == "unavailable"


async def test_sensor_cook_session_sensors_while_cooking(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_cooking_device,
):
    """Test current_stage/total_stages/rack_position/recipe_name while cooking."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_cooking_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    # mock_cooking_device's registered plan has "stage-1" as stages[0],
    # so current_stage_index resolves to 1 of total_stage_count 2.
    assert hass.states.get("sensor.test_oven_current_stage").state == "1"
    assert hass.states.get("sensor.test_oven_total_stages").state == "2"
    assert hass.states.get("sensor.test_oven_rack_position").state == "3"
    # No recipe tracked via async_start_recipe, so falls back to "Manual Cook".
    assert hass.states.get("sensor.test_oven_recipe_name").state == "Manual Cook"


async def test_sensor_cook_session_sensors_v1_active_stage_index(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_cooking_device,
):
    """Test current_stage/total_stages resolve via cook.active_stage_index on V1 ovens.

    Confirmed against a real V1 EVENT_APO_STATE capture: the live `cook`
    object reports `activeStageIndex`/`activeStageId` directly, so stage
    tracking works even for cooks started outside this SDK (e.g. the Anova
    app), without a registered plan.
    """
    mock_cooking_device.cook.active_stage_index = 1
    mock_cooking_device.cook.active_stage_id = "stage-2"

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_cooking_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert hass.states.get("sensor.test_oven_current_stage").state == "2"
    assert hass.states.get("sensor.test_oven_total_stages").state == "2"


async def test_sensor_timer_unavailable_when_idle(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_device,
):
    """Test timer sensors unavailable when timer mode is idle."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("sensor.test_oven_timer_remaining")
    assert state.state == "unavailable"

    state = hass.states.get("sensor.test_oven_timer_initial")
    assert state.state == "unavailable"


async def test_sensor_steam_unavailable_when_idle(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_device,
):
    """Test steam sensor unavailable when steam mode is idle."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("sensor.test_oven_steam_percentage")
    assert state.state == "unavailable"


async def test_sensor_steam_percentage_mode(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_device,
):
    """Test steam sensor reads steamPercentage.current when mode is steam-percentage."""
    mock_device.nodes.steam_generators = SteamGenerators.model_validate({
        "mode": "steam-percentage",
        "steamPercentage": {"current": 42.0, "setpoint": 100.0},
        "evaporator": {},
        "boiler": {},
    })

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("sensor.test_oven_steam_percentage")
    assert state.state == "42.0"


async def test_sensor_steam_relative_humidity_mode(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_device,
):
    """Test steam sensor reads relativeHumidity.current when mode is relative-humidity."""
    mock_device.nodes.steam_generators = SteamGenerators.model_validate({
        "mode": "relative-humidity",
        "relativeHumidity": {"current": 55.0, "setpoint": 60.0},
        "evaporator": {},
        "boiler": {},
    })

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("sensor.test_oven_steam_percentage")
    assert state.state == "55.0"


async def test_sensor_native_value_when_value_fn_none(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_device,
):
    """Test sensor native_value when value_fn returns None (line 241)."""
    # Clear device nodes to make value_fn return None
    mock_device.nodes = None

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("sensor.test_oven_current_temperature")
    assert state.state in ["unknown", "unavailable"]

async def test_sensor_available_no_available_fn(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test sensor available when no available_fn defined (line 252)."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    # Fan speed sensor has no available_fn, so should default to True
    state = hass.states.get("sensor.test_oven_fan_speed")
    assert state is not None
    assert state.state != "unavailable"


async def test_sensor_native_value_no_value_fn(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_device,
):
    """Test native_value returns None when value_fn is None (line 241)."""
    from custom_components.anova_oven.sensor import AnovaOvenSensor, AnovaOvenSensorEntityDescription
    from custom_components.anova_oven.coordinator import AnovaOvenCoordinator

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        coordinator = AnovaOvenCoordinator(hass, mock_config_entry)
        await coordinator.async_refresh()

        # Create sensor with value_fn=None
        description = AnovaOvenSensorEntityDescription(
            key="test",
            name="Test",
            value_fn=None,
        )

        sensor = AnovaOvenSensor(coordinator, "test-device-123", description)

        # Should return None (line 241)
        assert sensor.native_value is None


async def test_sensor_available_no_device(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
):
    """Test available returns False when device not found (line 252)."""
    from custom_components.anova_oven.sensor import AnovaOvenSensor, AnovaOvenSensorEntityDescription
    from custom_components.anova_oven.coordinator import AnovaOvenCoordinator

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = []

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        coordinator = AnovaOvenCoordinator(hass, mock_config_entry)
        await coordinator.async_refresh()

        # Create sensor for non-existent device
        description = AnovaOvenSensorEntityDescription(
            key="test",
            name="Test",
            value_fn=lambda d: "test",
        )

        sensor = AnovaOvenSensor(coordinator, "nonexistent-device", description)

        # Should return False (line 252)
        assert sensor.available is False


async def test_sensor_available_device_none_line_252(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
):
    """Test sensor.available returns False when device is None (line 252)."""
    from custom_components.anova_oven.sensor import AnovaOvenSensor, AnovaOvenSensorEntityDescription
    from custom_components.anova_oven.coordinator import AnovaOvenCoordinator

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = []

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        coordinator = AnovaOvenCoordinator(hass, mock_config_entry)
        await coordinator.async_refresh()

        description = AnovaOvenSensorEntityDescription(
            key="test",
            name="Test",
            value_fn=lambda d: "value",
            available_fn=lambda d: True,  # Has available_fn but device is None
        )

        sensor = AnovaOvenSensor(coordinator, "nonexistent-device-id", description)

        # Line 252: should return False because device is None
        assert sensor.available is False


async def test_sensor_available_returns_false_when_device_is_none(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
):
    """Test sensor.available returns False when get_device returns None (line 252).

    This tests the specific case where:
    - super().available returns True (coordinator is working)
    - coordinator.get_device() returns None (device not found)
    - The function should return False at line 252
    """
    from custom_components.anova_oven.sensor import AnovaOvenSensor, AnovaOvenSensorEntityDescription
    from custom_components.anova_oven.coordinator import AnovaOvenCoordinator

    mock_config_entry.add_to_hass(hass)
    # Empty device list - no devices discovered
    mock_anova_oven.discover_devices.return_value = []

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        coordinator = AnovaOvenCoordinator(hass, mock_config_entry)
        # This makes super().available return True
        await coordinator.async_refresh()

        # Verify coordinator is available (super().available will be True)
        assert coordinator.last_update_success is True

        # Create a sensor with a device_id that doesn't exist
        description = AnovaOvenSensorEntityDescription(
            key="current_temperature",
            name="Current Temperature",
            value_fn=lambda d: 25.0,
        )

        sensor = AnovaOvenSensor(coordinator, "device-does-not-exist", description)

        # coordinator.get_device("device-does-not-exist") returns None
        assert coordinator.get_device("device-does-not-exist") is None

        # Line 252: should return False because device is None
        assert sensor.available is False


async def test_sensor_available_line_252_with_real_integration_setup(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_device,
):
    """Test line 252 using actual integration setup to ensure super().available is True."""
    from custom_components.anova_oven.const import DOMAIN

    mock_config_entry.add_to_hass(hass)
    # Setup with one device
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        # Setup the integration
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Get the coordinator
        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]

        # Create sensor for a non-existent device
        from custom_components.anova_oven.sensor import AnovaOvenSensor, AnovaOvenSensorEntityDescription

        description = AnovaOvenSensorEntityDescription(
            key="test",
            name="Test",
            value_fn=lambda d: "value",
        )

        # Use a device_id that doesn't exist in coordinator
        sensor = AnovaOvenSensor(coordinator, "nonexistent-device-id-12345", description)

        # This should hit line 252 and return False
        assert sensor.available is False


async def test_sensor_line_252_device_none_super_available_true(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_device,
):
    """Test line 252: device is None but super().available is True.

    The key is that we need:
    1. Coordinator to have last_update_success = True (makes super().available = True)
    2. Device to NOT be in coordinator.data (makes get_device return None)
    3. Then line 252 will execute and return False
    """
    from custom_components.anova_oven.sensor import AnovaOvenSensor, AnovaOvenSensorEntityDescription
    from custom_components.anova_oven.coordinator import AnovaOvenCoordinator
    from custom_components.anova_oven.const import DOMAIN

    mock_config_entry.add_to_hass(hass)

    # Discover one device so coordinator has success
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        # Create coordinator and do initial refresh
        coordinator = AnovaOvenCoordinator(hass, mock_config_entry)
        await coordinator.async_refresh()

        # Verify coordinator has successful state (super().available will be True)
        assert coordinator.last_update_success is True

        # Verify the actual device exists in coordinator
        assert "test-device-123" in coordinator.data

        # Now create a sensor with a DIFFERENT device_id that's not in coordinator.data
        description = AnovaOvenSensorEntityDescription(
            key="current_temperature",
            name="Current Temperature",
            value_fn=lambda d: 25.0,
        )

        sensor = AnovaOvenSensor(coordinator, "different-device-id-999", description)

        # Verify get_device returns None for our fake device
        assert coordinator.get_device("different-device-id-999") is None

        # Now check available - this should hit line 252
        # Line 247: super().available is True (passes)
        # Line 250-251: device is None
        # Line 252: return False  <- THIS LINE
        result = sensor.available
        assert result is False


async def test_sensor_line_252_mock_coordinator_get_device(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_device,
):
    """Test line 252 by mocking coordinator.get_device to return None."""
    from custom_components.anova_oven.sensor import AnovaOvenSensor, AnovaOvenSensorEntityDescription
    from custom_components.anova_oven.coordinator import AnovaOvenCoordinator

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        coordinator = AnovaOvenCoordinator(hass, mock_config_entry)
        await coordinator.async_refresh()

        # Ensure coordinator is available
        assert coordinator.last_update_success is True

        description = AnovaOvenSensorEntityDescription(
            key="test",
            name="Test",
            value_fn=lambda d: "value",
        )

        sensor = AnovaOvenSensor(coordinator, "test-device-123", description)

        # Temporarily mock get_device to return None
        original_get_device = coordinator.get_device
        coordinator.get_device = MagicMock(return_value=None)

        # This should hit line 252
        result = sensor.available

        # Restore
        coordinator.get_device = original_get_device

        assert result is False


async def test_sensor_line_252_direct_property_access(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_device,
):
    """Test line 252 by directly manipulating coordinator data after sensor creation."""
    from custom_components.anova_oven.sensor import AnovaOvenSensor, AnovaOvenSensorEntityDescription
    from custom_components.anova_oven.coordinator import AnovaOvenCoordinator
    from custom_components.anova_oven.const import DOMAIN

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]

        # Verify device exists
        assert "test-device-123" in coordinator.data
        assert coordinator.last_update_success is True

        # Create sensor
        description = AnovaOvenSensorEntityDescription(
            key="test",
            name="Test",
            value_fn=lambda d: "value",
        )

        sensor = AnovaOvenSensor(coordinator, "test-device-123", description)

        # Sensor should be available initially
        assert sensor.available is True

        # Now remove the device from coordinator.data
        del coordinator.data["test-device-123"]

        # Keep coordinator "available"
        coordinator.last_update_success = True

        # Now accessing available should hit line 252
        # super().available = True (coordinator still successful)
        # get_device returns None (device removed from data)
        # Line 252: return False
        result = sensor.available
        assert result is False


async def test_sensor_line_252_integration_then_disconnect(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_device,
):
    """Test line 252: setup integration, then simulate device disconnect."""
    from custom_components.anova_oven.const import DOMAIN

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        # Initial setup
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Get all sensor entities
        sensor_entities = [e for e in hass.states.async_entity_ids() if e.startswith("sensor.")]
        assert len(sensor_entities) > 0

        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]

        # Clear all devices but keep coordinator "successful"
        coordinator.data.clear()
        coordinator.last_update_success = True

        # Manually trigger update on all sensors
        from custom_components.anova_oven.sensor import AnovaOvenSensor

        for entity_id in sensor_entities:
            entity = hass.data["entity_components"]["sensor"].get_entity(entity_id)
            if isinstance(entity, AnovaOvenSensor):
                # This should hit line 252
                available = entity.available
                # Should be False since device is gone but coordinator is "available"
                assert available is False
                break  # Just need one to hit the line


async def test_sensor_line_252_via_entity_registry(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_device,
):
    """Test line 252 by setting up sensors and then removing device from coordinator."""
    from custom_components.anova_oven.const import DOMAIN

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        # Setup integration with device
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]

        # Manually remove device from coordinator data to simulate disconnection
        original_data = coordinator.data.copy()
        coordinator.data = {}  # Empty the data

        # Force coordinator to still be "available" (last_update_success = True)
        coordinator.last_update_success = True

        # Now create a sensor manually for the removed device
        from custom_components.anova_oven.sensor import AnovaOvenSensor, AnovaOvenSensorEntityDescription

        description = AnovaOvenSensorEntityDescription(
            key="test",
            name="Test",
            value_fn=lambda d: "value",
        )

        sensor = AnovaOvenSensor(coordinator, "test-device-123", description)

        # This should hit line 252
        assert sensor.available is False