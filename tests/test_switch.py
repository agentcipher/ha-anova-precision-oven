"""Test the Anova Oven switch platform."""
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, STATE_ON, STATE_OFF
from homeassistant.core import HomeAssistant


async def test_switch_setup(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test switch entity setup."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("switch.test_oven_cooking")
    assert state is not None
    assert state.state == STATE_OFF


async def test_switch_is_on_idle(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test switch is off when oven is idle."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("switch.test_oven_cooking")
    assert state.state == STATE_OFF


async def test_switch_is_on_cooking(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_cooking_device,
):
    """Test switch is on when oven is cooking."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_cooking_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("switch.test_oven_cooking")
    assert state.state == STATE_ON


async def test_switch_is_on_preheating(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test switch is on when oven is preheating."""
    mock_device.state.state = "preheating"
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("switch.test_oven_cooking")
    assert state.state == STATE_ON


async def test_switch_turn_on(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test turning on the switch."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        await hass.services.async_call(
            SWITCH_DOMAIN,
            "turn_on",
            {ATTR_ENTITY_ID: "switch.test_oven_cooking"},
            blocking=True,
        )

    mock_anova_oven.start_cook.assert_called_once()
    call_args = mock_anova_oven.start_cook.call_args
    assert call_args[1]["device_id"] == "test-device-123"
    assert call_args[1]["temperature"] == 180.0
    assert call_args[1]["temperature_unit"] == "C"


async def test_switch_turn_on_with_custom_temp(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test turning on the switch uses device's setpoint."""
    mock_device.state.nodes["temperatureBulbs"]["dry"]["setpoint"]["celsius"] = 200.0
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        await hass.services.async_call(
            SWITCH_DOMAIN,
            "turn_on",
            {ATTR_ENTITY_ID: "switch.test_oven_cooking"},
            blocking=True,
        )

    call_args = mock_anova_oven.start_cook.call_args
    assert call_args[1]["temperature"] == 200.0


async def test_switch_turn_off(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_cooking_device,
):
    """Test turning off the switch."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_cooking_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        await hass.services.async_call(
            SWITCH_DOMAIN,
            "turn_off",
            {ATTR_ENTITY_ID: "switch.test_oven_cooking"},
            blocking=True,
        )

    mock_anova_oven.stop_cook.assert_called_once_with("test-device-123")


async def test_switch_turn_on_error(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test switch handles turn on errors."""
    from custom_components.anova_oven.anova_sdk.exceptions import AnovaError

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]
    mock_anova_oven.start_cook.side_effect = AnovaError("Failed to start")

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        with pytest.raises(Exception):
            await hass.services.async_call(
                SWITCH_DOMAIN,
                "turn_on",
                {ATTR_ENTITY_ID: "switch.test_oven_cooking"},
                blocking=True,
            )


async def test_switch_turn_off_error(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_cooking_device,
):
    """Test switch handles turn off errors."""
    from custom_components.anova_oven.anova_sdk.exceptions import AnovaError

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_cooking_device]
    mock_anova_oven.stop_cook.side_effect = AnovaError("Failed to stop")

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        with pytest.raises(Exception):
            await hass.services.async_call(
                SWITCH_DOMAIN,
                "turn_off",
                {ATTR_ENTITY_ID: "switch.test_oven_cooking"},
                blocking=True,
            )


async def test_switch_no_state(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test switch when device has no state."""
    mock_device.state = None
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("switch.test_oven_cooking")
    assert state.state == STATE_OFF