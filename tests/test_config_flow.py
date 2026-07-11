"""Test the Anova Oven config flow."""
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries, data_entry_flow
from homeassistant.const import CONF_API_TOKEN
from homeassistant.core import HomeAssistant

from custom_components.anova_oven.config_flow import CannotConnect, InvalidAuth, NoDevicesFound
from custom_components.anova_oven.const import DOMAIN


async def test_form_display(hass: HomeAssistant):
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {}
    assert result["step_id"] == "user"


async def test_form_invalid_token_format(hass: HomeAssistant, mock_anova_oven: AsyncMock):
    """Test a badly-formatted token is surfaced as invalid_auth.

    The SDK's settings validators are what actually reject a malformed
    token, by raising from within `async with AnovaOven() as oven`. We
    simulate that here via a mocked ConfigurationError, rather than
    relying on a real (unmocked) AnovaOven/settings.configure() call -
    `settings` is a shared, un-reset singleton across the test session,
    so whether the real validators re-run on a given call depends on
    what earlier tests already configured them with. Relying on that
    timing quirk previously let an invalid token fall all the way
    through to real (blocked) network connection attempts.
    """
    from anova_oven_sdk.exceptions import ConfigurationError

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    mock_anova_oven.__aenter__.side_effect = ConfigurationError("Token must start with 'anova-'")

    with patch(
        "custom_components.anova_oven.config_flow.AnovaOven",
        return_value=mock_anova_oven,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_TOKEN: "invalid-token"},
        )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_form_connection_error(hass: HomeAssistant, mock_anova_oven: AsyncMock):
    """Test we handle connection error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    mock_anova_oven.__aenter__.side_effect = ConnectionError("Failed to connect")

    with patch(
        "custom_components.anova_oven.config_flow.AnovaOven",
        return_value=mock_anova_oven,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_TOKEN: "anova-test-token"},
        )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_form_no_devices_found(hass: HomeAssistant, mock_anova_oven: AsyncMock):
    """Test we handle no devices found.

    NoDevicesFound is raised inside validate_input()'s own try block, so
    it's actually caught by that block's generic `except Exception` and
    re-raised as CannotConnect before it ever reaches async_step_user -
    the dedicated "no_devices_found" error branch there is unreachable
    through this code path. This test documents the real, current
    behavior rather than the aspirational one.
    """
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    mock_anova_oven.discover_devices.return_value = []

    with patch(
        "custom_components.anova_oven.config_flow.AnovaOven",
        return_value=mock_anova_oven,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_TOKEN: "anova-test-token"},
        )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_form_unknown_error(hass: HomeAssistant, mock_anova_oven: AsyncMock):
    """Test we handle unknown error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    mock_anova_oven.discover_devices.side_effect = Exception("Unexpected error")

    with patch(
        "custom_components.anova_oven.config_flow.AnovaOven",
        return_value=mock_anova_oven,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_TOKEN: "anova-test-token"},
        )

    # Any Exception raised while discovering devices is caught by
    # validate_input()'s own generic handler and surfaces as cannot_connect.
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_form_success(
    hass: HomeAssistant, mock_anova_oven: AsyncMock, mock_device
):
    """Test successful configuration."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    mock_anova_oven.discover_devices.return_value = [mock_device]

    # A successful config flow immediately triggers a real integration
    # setup (__init__.py -> coordinator.py), which constructs its own
    # AnovaOven() - patch that reference too, or this test would make a
    # real (blocked) network connection attempt via the coordinator.
    with patch(
        "custom_components.anova_oven.config_flow.AnovaOven",
        return_value=mock_anova_oven,
    ), patch(
        "custom_components.anova_oven.coordinator.AnovaOven",
        return_value=mock_anova_oven,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_TOKEN: "anova-test-token-12345"},
        )
        await hass.async_block_till_done()

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "Anova Precision Oven"
    assert result["data"] == {CONF_API_TOKEN: "anova-test-token-12345"}


async def test_validate_input_success(
    mock_anova_oven: AsyncMock, mock_device
):
    """Test validate_input succeeds with valid data."""
    from custom_components.anova_oven.config_flow import validate_input

    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.config_flow.AnovaOven",
        return_value=mock_anova_oven,
    ):
        info = await validate_input({CONF_API_TOKEN: "anova-test-token"})

    assert info["title"] == "Anova Precision Oven"


async def test_validate_input_configuration_error_maps_to_invalid_auth(
    mock_anova_oven: AsyncMock,
):
    """Test that a ConfigurationError raised while discovering devices is
    mapped to InvalidAuth (config_flow.py's dedicated handling for it),
    even though a badly-formatted token never reaches this branch in
    practice (see test_form_invalid_token_format)."""
    from custom_components.anova_oven.config_flow import validate_input
    from anova_oven_sdk.exceptions import ConfigurationError

    mock_anova_oven.__aenter__.side_effect = ConfigurationError("Bad config")

    with patch(
        "custom_components.anova_oven.config_flow.AnovaOven",
        return_value=mock_anova_oven,
    ), pytest.raises(InvalidAuth):
        await validate_input({CONF_API_TOKEN: "anova-test-token"})


async def test_validate_input_no_devices(mock_anova_oven: AsyncMock):
    """Test validate_input raises CannotConnect when no devices are found."""
    from custom_components.anova_oven.config_flow import validate_input

    mock_anova_oven.discover_devices.return_value = []

    with patch(
        "custom_components.anova_oven.config_flow.AnovaOven",
        return_value=mock_anova_oven,
    ), pytest.raises(CannotConnect):
        await validate_input({CONF_API_TOKEN: "anova-test-token"})


async def test_validate_input_connection_error(mock_anova_oven: AsyncMock):
    """Test validate_input handles connection error."""
    from custom_components.anova_oven.config_flow import validate_input
    from anova_oven_sdk.exceptions import AnovaError

    mock_anova_oven.__aenter__.side_effect = AnovaError("Connection failed")

    with patch(
        "custom_components.anova_oven.config_flow.AnovaOven",
        return_value=mock_anova_oven,
    ), pytest.raises(CannotConnect):
        await validate_input({CONF_API_TOKEN: "anova-test-token"})


async def test_config_flow_unexpected_exception_in_step_user(
    hass: HomeAssistant,
):
    """Test config flow catches unexpected exceptions from validate_input."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.anova_oven.config_flow.validate_input",
        side_effect=RuntimeError("Totally unexpected error"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_TOKEN: "anova-test-token"},
        )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {"base": "unknown"}
