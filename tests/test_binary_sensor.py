"""Test the Anova Oven binary_sensor platform."""
from unittest.mock import AsyncMock, patch

from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant


async def test_binary_sensor_setup(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test binary sensor setup."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]
    
    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
    
    # Check all binary sensors exist
    assert hass.states.get("binary_sensor.test_oven_cooking") is not None
    assert hass.states.get("binary_sensor.test_oven_preheating") is not None
    assert hass.states.get("binary_sensor.test_oven_door") is not None
    assert hass.states.get("binary_sensor.test_oven_water_low") is not None
    assert hass.states.get("binary_sensor.test_oven_probe_connected") is not None
    assert hass.states.get("binary_sensor.test_oven_vent") is not None


async def test_cooking_binary_sensor_idle(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test cooking binary sensor when idle."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]
    
    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
    
    state = hass.states.get("binary_sensor.test_oven_cooking")
    assert state.state == STATE_OFF


async def test_cooking_binary_sensor_cooking(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_cooking_device,
):
    """Test cooking binary sensor when cooking."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_cooking_device]
    
    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
    
    state = hass.states.get("binary_sensor.test_oven_cooking")
    assert state.state == STATE_ON


async def test_preheating_binary_sensor(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test preheating binary sensor."""
    mock_device.state.state = "preheating"
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]
    
    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
    
    state = hass.states.get("binary_sensor.test_oven_preheating")
    assert state.state == STATE_ON
    
    # Cooking sensor should also be on during preheat
    cooking_state = hass.states.get("binary_sensor.test_oven_cooking")
    assert cooking_state.state == STATE_ON


async def test_door_binary_sensor_closed(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test door binary sensor when closed."""
    mock_device.state.nodes["door"]["open"] = False
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]
    
    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
    
    state = hass.states.get("binary_sensor.test_oven_door")
    assert state.state == STATE_OFF


async def test_door_binary_sensor_open(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test door binary sensor when open."""
    mock_device.state.nodes["door"]["open"] = True
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]
    
    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
    
    state = hass.states.get("binary_sensor.test_oven_door")
    assert state.state == STATE_ON


async def test_water_low_binary_sensor(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test water low binary sensor."""
    mock_device.state.nodes["waterTank"]["low"] = True
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]
    
    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
    
    state = hass.states.get("binary_sensor.test_oven_water_low")
    assert state.state == STATE_ON


async def test_probe_connected_binary_sensor(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_probe_device,
):
    """Test probe connected binary sensor."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_probe_device]
    
    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
    
    state = hass.states.get("binary_sensor.test_oven_probe_connected")
    assert state.state == STATE_ON


async def test_vent_binary_sensor_open(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test vent binary sensor when open."""
    mock_device.state.nodes["exhaustVent"]["state"] = "open"
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]
    
    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
    
    state = hass.states.get("binary_sensor.test_oven_vent")
    assert state.state == STATE_ON


async def test_binary_sensor_unavailable_no_state(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test binary sensors unavailable when device has no state."""
    mock_device.state = None
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]
    
    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
    
    state = hass.states.get("binary_sensor.test_oven_cooking")
    assert state.state == STATE_OFF  # Should return False when no state


async def test_binary_sensor_vent_closed(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_device,
):
    """Test vent binary sensor when closed (binary_sensor.py line 130)."""
    mock_device.state.nodes["exhaustVent"]["state"] = "closed"
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("binary_sensor.test_oven_vent")
    assert state.state == "off"

async def test_binary_sensor_vent_no_state_in_node(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test vent binary sensor when exhaustVent state key missing (line 130)."""
    # Remove the state key to test the else branch
    mock_device.state.nodes["exhaustVent"] = {}
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("binary_sensor.test_oven_vent")
    # When state key is missing, should return False
    assert state.state == "off"


async def test_binary_sensor_is_on_no_is_on_fn(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_device,
):
    """Test binary sensor is_on when is_on_fn is None (binary_sensor.py line 130)."""
    from custom_components.anova_oven.binary_sensor import AnovaOvenBinarySensor, AnovaOvenBinarySensorEntityDescription
    from homeassistant.components.binary_sensor import BinarySensorDeviceClass
    from custom_components.anova_oven.coordinator import AnovaOvenCoordinator

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        coordinator = AnovaOvenCoordinator(hass, mock_config_entry)
        await coordinator.async_refresh()

        # Create entity description with is_on_fn = None
        description = AnovaOvenBinarySensorEntityDescription(
            key="test",
            name="Test",
            device_class=BinarySensorDeviceClass.RUNNING,
            is_on_fn=None,  # This triggers line 130
        )

        entity = AnovaOvenBinarySensor(coordinator, "test-device-123", description)

        # Should return False when is_on_fn is None
        assert entity.is_on is False