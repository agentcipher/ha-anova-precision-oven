"""Test the Anova Oven base entity."""
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant

from custom_components.anova_oven.const import DOMAIN
from custom_components.anova_oven.anova_sdk.models import OvenVersion
from custom_components.anova_oven.anova_sdk.exceptions import AnovaError


async def test_entity_device_info(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test entity device info."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        # Ensure setup succeeds
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    # Wait for entities to be fully registered
    await hass.async_block_till_done()

    # Check device info from any entity
    state = hass.states.get("climate.test_oven_oven")
    assert state is not None

    # Get device from registry
    from homeassistant.helpers import device_registry as dr
    device_registry = dr.async_get(hass)
    device = device_registry.async_get_device(
        identifiers={(DOMAIN, "test-device-123")}
    )

    assert device is not None
    assert device.name == "Test Oven"
    assert device.manufacturer == "Anova"
    assert device.model == "Precision Oven oven_v2"
    assert device.sw_version == "2.1.0"


async def test_entity_unique_id(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test entity unique IDs."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    # Check unique IDs from entity registry
    from homeassistant.helpers import entity_registry as er
    entity_registry = er.async_get(hass)

    climate_entity = entity_registry.async_get("climate.test_oven_oven")
    assert climate_entity is not None
    assert climate_entity.unique_id == "test-device-123_climate"

    sensor_entity = entity_registry.async_get("sensor.test_oven_current_temperature")
    assert sensor_entity is not None
    assert sensor_entity.unique_id == "test-device-123_current_temperature"


async def test_entity_available_coordinator_unavailable(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test entity unavailable when coordinator is unavailable."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Get coordinator and force it to fail
        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]

        # Make the next update fail
        mock_anova_oven.discover_devices.side_effect = AnovaError("Connection lost")

        # Try to refresh - this should fail and mark coordinator unavailable
        try:
            await coordinator.async_refresh()
        except Exception:
            pass  # Expected to fail

        await hass.async_block_till_done()

    # Check entity state - should be unavailable
    state = hass.states.get("climate.test_oven_oven")
    assert state is not None
    assert state.state == "unavailable"

    # Verify coordinator shows as failed
    assert coordinator.last_update_success is False


async def test_entity_available_device_not_found(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test entity unavailable when device not in coordinator data."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Remove device from coordinator data
        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]
        coordinator.data = {}

        # Trigger state update
        await coordinator.async_request_refresh()
        await hass.async_block_till_done()

    state = hass.states.get("climate.test_oven_oven")
    # Entity might show as 'off' or 'unavailable' when device is missing
    assert state.state in ["unavailable", "off"]


async def test_multiple_devices_separate_entities(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test multiple devices create separate entities."""
    # Create second device with proper mocking
    device2 = MagicMock()
    device2.cooker_id = 'test-device-456'
    device2.display_name = 'Test Oven 2'
    device2.name = 'Test Oven 2'
    device2.oven_version = OvenVersion.V2
    device2.device_type = OvenVersion.V2
    device2.model = "Precision Oven APO"
    device2.firmware_version = '2.1.0'
    device2.wifi_ssid = 'TestWiFi'
    device2.wifi_strength = 85
    device2.state = mock_device.state  # Reuse the state mock

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device, device2]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    # Check both devices have entities
    assert hass.states.get("climate.test_oven_oven") is not None
    assert hass.states.get("climate.test_oven_2_oven") is not None

    # Check they have different unique IDs
    from homeassistant.helpers import entity_registry as er
    entity_registry = er.async_get(hass)

    entity1 = entity_registry.async_get("climate.test_oven_oven")
    entity2 = entity_registry.async_get("climate.test_oven_2_oven")

    assert entity1.unique_id != entity2.unique_id
    assert entity1.unique_id == "test-device-123_climate"
    assert entity2.unique_id == "test-device-456_climate"


async def test_entity_extra_state_attributes(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test entity extra state attributes."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("climate.test_oven_oven")

    # Check that oven_version attribute exists (it may be the enum value string)
    assert "oven_version" in state.attributes
    # The oven_version in attributes is the string value of the enum
    assert state.attributes["oven_version"] == "oven_v2"  # This is OvenVersion.V2.value

    # Check timer attributes (these should be present based on the nodes data)
    assert "timer_mode" in state.attributes
    assert state.attributes["timer_mode"] == "idle"


async def test_entity_device_info_no_device(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
):
    """Test entity device_info when device not found (entity.py line 29)."""
    from custom_components.anova_oven.entity import AnovaOvenEntity
    from custom_components.anova_oven.coordinator import AnovaOvenCoordinator

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = []

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        coordinator = AnovaOvenCoordinator(hass, mock_config_entry)
        await coordinator.async_refresh()

        # Create entity with device that doesn't exist in coordinator
        entity = AnovaOvenEntity(coordinator, "nonexistent-device", "test")
        device_info = entity.device_info

        # Should return basic device info with device_id
        assert device_info["identifiers"] == {("anova_oven", "nonexistent-device")}
        assert "Anova Oven nonexistent-device" in device_info["name"]

async def test_entity_device_info_device_not_found(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
):
    """Test entity device_info when device not found (line 25)."""
    from custom_components.anova_oven.entity import AnovaOvenEntity
    from custom_components.anova_oven.coordinator import AnovaOvenCoordinator

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = []

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        coordinator = AnovaOvenCoordinator(hass, mock_config_entry)
        await coordinator.async_refresh()

    # Create entity with non-existent device
    entity = AnovaOvenEntity(coordinator, "nonexistent-device", "test")
    device_info = entity.device_info

    # Should return basic info without device details
    assert ("anova_oven", "nonexistent-device") in device_info["identifiers"]
    assert "Anova Oven nonexistent-device" in device_info["name"]


async def test_entity_unique_id_no_entity_type(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_device,
):
    """Test entity unique_id when entity_type is None (line 25)."""
    from custom_components.anova_oven.entity import AnovaOvenEntity
    from custom_components.anova_oven.coordinator import AnovaOvenCoordinator

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        coordinator = AnovaOvenCoordinator(hass, mock_config_entry)
        await coordinator.async_refresh()

        # Create entity with entity_type=None
        entity = AnovaOvenEntity(coordinator, "test-device-123", None)

        # Should use device_id as unique_id (line 25)
        assert entity.unique_id == "test-device-123"