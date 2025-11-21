"""Test the Anova Oven button platform."""
from unittest.mock import AsyncMock, patch

from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant


async def test_button_setup(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test button entity setup."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("button.test_oven_stop_cook")
    assert state is not None


async def test_button_press_stop_cook(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_cooking_device,
):
    """Test pressing the stop cook button."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_cooking_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        await hass.services.async_call(
            BUTTON_DOMAIN,
            "press",
            {ATTR_ENTITY_ID: "button.test_oven_stop_cook"},
            blocking=True,
        )

    mock_anova_oven.stop_cook.assert_called_once_with("test-device-123")


async def test_button_multiple_devices(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test buttons created for multiple devices."""
    from unittest.mock import MagicMock
    from custom_components.anova_oven.anova_sdk.models import OvenVersion

    # Create second device
    device2 = MagicMock()
    device2.cooker_id = "test-device-456"
    device2.display_name = "Test Oven 2"
    device2.name = "Test Oven 2"
    device2.oven_version = OvenVersion.V2
    device2.device_type = OvenVersion.V2
    device2.model = "Precision Oven APO"
    device2.firmware_version = "2.1.0"
    device2.state = mock_device.state

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device, device2]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    # Check both buttons exist
    assert hass.states.get("button.test_oven_stop_cook") is not None
    assert hass.states.get("button.test_oven_2_stop_cook") is not None