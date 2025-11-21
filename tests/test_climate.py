"""Test the Anova Oven climate platform."""
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components.climate import (
    ATTR_HVAC_MODE,
    ATTR_TEMPERATURE,
    DOMAIN as CLIMATE_DOMAIN,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_TEMPERATURE,
    HVACMode,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant

from custom_components.anova_oven.const import DOMAIN


async def test_climate_entity_setup(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test climate entity setup."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]
    
    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        # Give platforms additional time to load
        await hass.async_block_till_done()

    state = hass.states.get("climate.test_oven_oven")
    assert state is not None, "Climate entity was not created"
    assert state.state == HVACMode.OFF


async def test_climate_properties_idle(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test climate properties when idle."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        await hass.async_block_till_done()

    state = hass.states.get("climate.test_oven_oven")
    assert state is not None, "Climate entity was not created"
    assert state.state == HVACMode.OFF
    assert state.attributes["current_temperature"] == 25.0
    assert state.attributes["temperature"] == 180.0
    assert state.attributes["min_temp"] == 25.0
    assert state.attributes["max_temp"] == 250.0  # Celsius (482°F)


async def test_climate_properties_cooking(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_cooking_device,
):
    """Test climate properties when cooking."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_cooking_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        await hass.async_block_till_done()

    state = hass.states.get("climate.test_oven_oven")
    assert state is not None, "Climate entity was not created"
    assert state.state == HVACMode.HEAT
    assert state.attributes["current_temperature"] == 175.0


async def test_climate_set_temperature(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test setting target temperature."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        await hass.async_block_till_done()

        # Verify entity exists
        state = hass.states.get("climate.test_oven_oven")
        assert state is not None, "Climate entity was not created"

        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            {
                ATTR_ENTITY_ID: "climate.test_oven_oven",
                ATTR_TEMPERATURE: 200.0,
            },
            blocking=True,
        )
        await hass.async_block_till_done()

    mock_anova_oven.start_cook.assert_called_once()


async def test_climate_set_hvac_mode_heat(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test setting HVAC mode to heat."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        await hass.async_block_till_done()

        # Verify entity exists
        state = hass.states.get("climate.test_oven_oven")
        assert state is not None, "Climate entity was not created"

        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_HVAC_MODE,
            {
                ATTR_ENTITY_ID: "climate.test_oven_oven",
                ATTR_HVAC_MODE: HVACMode.HEAT,
            },
            blocking=True,
        )
        await hass.async_block_till_done()

    mock_anova_oven.start_cook.assert_called_once()


async def test_climate_set_hvac_mode_off(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_cooking_device,
):
    """Test setting HVAC mode to off."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_cooking_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        await hass.async_block_till_done()

        # Verify entity exists
        state = hass.states.get("climate.test_oven_oven")
        assert state is not None, "Climate entity was not created"

        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_HVAC_MODE,
            {
                ATTR_ENTITY_ID: "climate.test_oven_oven",
                ATTR_HVAC_MODE: HVACMode.OFF,
            },
            blocking=True,
        )
        await hass.async_block_till_done()

    mock_anova_oven.stop_cook.assert_called_once()


async def test_climate_extra_attributes_idle(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test extra attributes when idle."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        await hass.async_block_till_done()

    state = hass.states.get("climate.test_oven_oven")
    assert state is not None, "Climate entity was not created"
    assert "current_stage" not in state.attributes
    assert "recipe_name" not in state.attributes


async def test_climate_extra_attributes_cooking(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_cooking_device,
):
    """Test extra attributes when cooking."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_cooking_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        await hass.async_block_till_done()

    state = hass.states.get("climate.test_oven_oven")
    assert state is not None, "Climate entity was not created"
    assert state.attributes["current_stage"] == 1
    assert state.attributes["recipe_name"] == "Roast Chicken"
    assert state.attributes["stages"] == 2


async def test_climate_unavailable_no_state(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test climate unavailable when device has no state."""
    mock_device.state = None
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        await hass.async_block_till_done()

    state = hass.states.get("climate.test_oven_oven")
    assert state is not None, "Climate entity was not created"
    # When device.state is None, the entity should show unavailable or off depending on implementation
    # Check both possibilities
    assert state.state in ("unavailable", "off"), f"Expected unavailable or off, got {state.state}"


async def test_climate_temperature_with_wet_mode(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_device,
):
    """Test temperature reading with wet mode."""
    mock_device.state.nodes["temperatureBulbs"]["mode"] = "wet"
    mock_device.state.nodes["temperatureBulbs"]["wet"]["current"]["celsius"] = 100.0

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        await hass.async_block_till_done()

    state = hass.states.get("climate.test_oven_oven")
    assert state is not None, "Climate entity was not created"
    assert state.attributes["current_temperature"] == 100.0


async def test_climate_current_temperature_no_mode_in_bulbs(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_device,
):
    """Test current temperature when mode key is missing from temperatureBulbs."""
    # Remove the mode from the temperature bulbs to test line 95
    mock_device.state.nodes["temperatureBulbs"]["mode"] = "nonexistent_mode"

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        await hass.async_block_till_done()

    state = hass.states.get("climate.test_oven_oven")
    # When mode is not in bulbs, current_temperature should be None
    assert state.attributes.get("current_temperature") is None


async def test_climate_target_temperature_no_mode_in_bulbs(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_device,
):
    """Test target temperature when mode key is missing from temperatureBulbs."""
    # Remove the mode from the temperature bulbs to test line 111
    mock_device.state.nodes["temperatureBulbs"]["mode"] = "nonexistent_mode"

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        await hass.async_block_till_done()

    state = hass.states.get("climate.test_oven_oven")
    # When mode is not in bulbs, target_temperature should be None
    assert state.attributes.get("temperature") is None


async def test_climate_set_temperature_with_timer(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_cooking_device,
):
    """Test setting temperature preserves timer duration."""
    # Set up a cooking device with active timer to test line 163
    mock_cooking_device.state.nodes["timer"]["mode"] = "countdown"
    mock_cooking_device.state.nodes["timer"]["initial"] = 3600
    mock_cooking_device.state.nodes["timer"]["current"] = 1800

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_cooking_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        await hass.async_block_till_done()

        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            {
                ATTR_ENTITY_ID: "climate.test_oven_oven",
                ATTR_TEMPERATURE: 200.0,
            },
            blocking=True,
        )

    # Verify duration was passed from timer
    call_args = mock_anova_oven.start_cook.call_args
    assert call_args[1]["duration"] == 3600


async def test_climate_set_hvac_heat_with_no_target(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_device,
):
    """Test setting HVAC to heat when no target temperature exists."""
    # Remove setpoint to test line 171 (default 180.0)
    mock_device.state.nodes["temperatureBulbs"]["dry"]["setpoint"] = {}

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        await hass.async_block_till_done()

        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_HVAC_MODE,
            {
                ATTR_ENTITY_ID: "climate.test_oven_oven",
                ATTR_HVAC_MODE: HVACMode.HEAT,
            },
            blocking=True,
        )

    # Verify default temperature 180.0 was used
    call_args = mock_anova_oven.start_cook.call_args
    assert call_args[1]["temperature"] == 180.0

async def test_climate_set_temperature_preserves_timer_duration(
    hass: HomeAssistant,
    mock_config_entry,
    mock_anova_oven: AsyncMock,
    mock_cooking_device,
):
    """Test that set_temperature preserves timer duration when cooking (line 163)."""
    # Set up active timer
    mock_cooking_device.state.nodes["timer"]["mode"] = "countdown"
    mock_cooking_device.state.nodes["timer"]["initial"] = 3600
    mock_cooking_device.state.nodes["timer"]["current"] = 1800

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_cooking_device]

    with patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        from homeassistant.components.climate import (
            DOMAIN as CLIMATE_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            ATTR_TEMPERATURE,
        )
        from homeassistant.const import ATTR_ENTITY_ID

        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            {
                ATTR_ENTITY_ID: "climate.test_oven_oven",
                ATTR_TEMPERATURE: 200.0,
            },
            blocking=True,
        )

    # Verify duration was passed through
    call_kwargs = mock_anova_oven.start_cook.call_args[1]
    assert call_kwargs.get("duration") == 3600

    async def test_climate_set_hvac_mode_heat_no_target_temperature(
            hass: HomeAssistant,
            mock_config_entry,
            mock_anova_oven: AsyncMock,
            mock_device,
    ):
        """Test setting HVAC mode to HEAT when target temperature is None (climate.py line 163)."""
        # Set target temperature to None
        mock_device.state.nodes["temperatureBulbs"]["dry"]["setpoint"] = {}

        mock_config_entry.add_to_hass(hass)
        mock_anova_oven.discover_devices.return_value = [mock_device]

        with patch(
                "custom_components.anova_oven.coordinator.AnovaOven",
                return_value=mock_anova_oven,
        ):
            await hass.config_entries.async_setup(mock_config_entry.entry_id)
            await hass.async_block_till_done()

            # Set HVAC mode to HEAT when target is None
            await hass.services.async_call(
                "climate",
                "set_hvac_mode",
                {
                    ATTR_ENTITY_ID: "climate.test_oven_oven",
                    "hvac_mode": HVACMode.HEAT,
                },
                blocking=True,
            )

        # Should call start_cook with default temperature of 180.0
        mock_anova_oven.start_cook.assert_called_once()
        call_args = mock_anova_oven.start_cook.call_args
        assert call_args[1]["temperature"] == 180.0


async def test_climate_set_hvac_heat_uses_default_temp(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_device,
):
    """Test HVAC HEAT mode uses default 180.0 when target is None (climate.py line 163)."""
    # Remove setpoint to make target_temperature None
    mock_device.state.nodes["temperatureBulbs"]["dry"]["setpoint"] = {}

    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        await hass.services.async_call(
            "climate",
            "set_hvac_mode",
            {
                "entity_id": "climate.test_oven_oven",
                "hvac_mode": "heat",
            },
            blocking=True,
        )

    # Verify it used 180.0 (the "or 180.0" part of line 163)
    assert mock_anova_oven.start_cook.called
    assert mock_anova_oven.start_cook.call_args[1]["temperature"] == 180.0


"""Test for climate.py line 163 - temperature is None"""
from unittest.mock import AsyncMock, patch
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er


async def test_climate_set_temperature_none(
        hass: HomeAssistant,
        mock_config_entry,
        mock_anova_oven: AsyncMock,
        mock_device,
):
    """Test async_set_temperature returns early when temperature is None (line 163)."""
    mock_config_entry.add_to_hass(hass)
    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
            "custom_components.anova_oven.coordinator.AnovaOven",
            return_value=mock_anova_oven,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Get the climate entity
        entity_reg = er.async_get(hass)
        entry = entity_reg.async_get("climate.test_oven_oven")

        # Get the actual entity object from hass.data
        from custom_components.anova_oven.const import DOMAIN
        climate_platform = hass.data["entity_components"]["climate"]
        climate_entity = None
        for entity in climate_platform.entities:
            if entity.entity_id == "climate.test_oven_oven":
                climate_entity = entity
                break

        assert climate_entity is not None

        # Call async_set_temperature with no temperature (line 163)
        await climate_entity.async_set_temperature()

    # Should not call start_cook since temperature is None
    mock_anova_oven.start_cook.assert_not_called()
