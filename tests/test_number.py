"""Test the Anova Oven number platform."""
from unittest.mock import AsyncMock, patch

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant


async def test_number_setup(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test number setup."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]
    
    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
    
    assert hass.states.get("number.test_oven_probe_target") is not None


async def test_probe_target_unavailable_no_probe(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test probe target unavailable when probe not connected."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]
    
    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
    
    state = hass.states.get("number.test_oven_probe_target")
    assert state.state == "unavailable"


async def test_probe_target_available_with_probe(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_probe_device,
):
    """Test probe target available when probe connected."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_probe_device]
    
    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
    
    state = hass.states.get("number.test_oven_probe_target")
    assert state.state == "70.0"
    assert state.attributes["min"] == 1.0
    assert state.attributes["max"] == 100.0
    assert state.attributes["step"] == 0.5


async def test_probe_target_set_value(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_probe_device,
):
    """Test setting probe target value."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_probe_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        await hass.services.async_call(
            "number",
            "set_value",
            {
                ATTR_ENTITY_ID: "number.test_oven_probe_target",
                "value": 75.0,
            },
            blocking=True,
        )

    mock_anova_oven.set_probe.assert_called_once_with("test-device-123", 75.0, "C")


async def test_probe_target_properties(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_probe_device,
):
    """Test probe target properties."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_probe_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("number.test_oven_probe_target")
    assert state.attributes["unit_of_measurement"] == "°C"
    assert state.attributes["mode"] == "box"


async def test_probe_target_no_state(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test probe target when device has no state."""
    mock_device.state = None
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("number.test_oven_probe_target")
    assert state.state == "unavailable"


async def test_number_native_value_none(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_device,
):
    """Test number entity when probe setpoint is None (number.py line 50)."""
    # Set probe setpoint to empty dict to return None
    mock_device.state.nodes["probe"]["setpoint"] = {}
    mock_device.state.nodes["probe"]["connected"] = True

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("number.test_oven_probe_target")
    # Probe is connected but has no setpoint value
    assert state.state in ["unknown", "unavailable"]


async def test_number_native_value_none_probe_setpoint(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_probe_device,
):
    """Test number native_value when probe setpoint is None (line 50)."""
    # Set probe setpoint to empty dict
    mock_probe_device.state.nodes["probe"]["setpoint"] = {}

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_probe_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("number.test_oven_probe_target")
    assert state.state in ["unknown", "unavailable"]


async def test_number_native_value_no_device(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
):
    """Test native_value returns None when device not found (line 50)."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = []

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Manually add a probe target entity for non-existent device
        from custom_components.anova_oven.number import AnovaOvenProbeTarget
        from custom_components.anova_oven.const import DOMAIN

        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]
        entity = AnovaOvenProbeTarget(coordinator, "nonexistent-device")

        # Should return None (line 50)
        assert entity.native_value is None