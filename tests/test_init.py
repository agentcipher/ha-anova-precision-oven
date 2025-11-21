"""Test the Anova Oven __init__ module."""
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from custom_components.anova_oven.const import DOMAIN

from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_setup_entry_success(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test successful setup of config entry."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state == ConfigEntryState.LOADED
    assert DOMAIN in hass.data
    assert mock_config_entry.entry_id in hass.data[DOMAIN]


async def test_setup_entry_connection_failed(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_anova_oven: AsyncMock,
):
    """Test setup fails when connection fails."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.connect.side_effect = ConnectionError("Connection failed")

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        assert not await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state == ConfigEntryState.SETUP_RETRY


async def test_setup_entry_discovery_failed(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_anova_oven: AsyncMock,
):
    """Test setup fails when discovery fails."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.side_effect = Exception("Discovery failed")

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        assert not await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state == ConfigEntryState.SETUP_RETRY


async def test_unload_entry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test successful unload of a config entry."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state == ConfigEntryState.NOT_LOADED
    assert mock_config_entry.entry_id not in hass.data[DOMAIN]
    # disconnect may be called multiple times during cleanup
    assert mock_anova_oven.disconnect.called


async def test_reload_entry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test successful reload of a config entry."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        assert await hass.config_entries.async_reload(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state == ConfigEntryState.LOADED
    assert DOMAIN in hass.data
    assert mock_config_entry.entry_id in hass.data[DOMAIN]


async def test_setup_entry_with_multiple_devices(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test setup with multiple devices."""
    # Create a second device with different ID
    from unittest.mock import MagicMock
    device2 = MagicMock()
    device2.cooker_id = "test-device-456"
    device2.display_name = "Test Oven 2"
    device2.name = "Test Oven 2"
    device2.oven_version = mock_device.oven_version
    device2.device_type = mock_device.device_type
    device2.model = mock_device.model
    device2.firmware_version = mock_device.firmware_version
    device2.wifi_ssid = mock_device.wifi_ssid
    device2.wifi_strength = mock_device.wifi_strength
    device2.state = mock_device.state

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device, device2]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]
    assert len(coordinator.data) == 2
    assert "test-device-123" in coordinator.data
    assert "test-device-456" in coordinator.data


async def test_setup_entry_no_devices(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_anova_oven: AsyncMock,
):
    """Test setup with no devices found."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = []

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        # Should still load successfully
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state == ConfigEntryState.LOADED
    coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]
    assert len(coordinator.data) == 0


async def test_async_reload_entry(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_device,
):
    """Test reloading a config entry."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        # Initial setup
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Import the reload function
        from custom_components.anova_oven import async_reload_entry

        # Reload the entry
        await async_reload_entry(hass, mock_config_entry)
        await hass.async_block_till_done()

    # Verify disconnect was called during unload
    mock_anova_oven.disconnect.assert_called()
    # Verify connect was called during reload
    assert mock_anova_oven.connect.call_count >= 2  # Once for setup, once for reload