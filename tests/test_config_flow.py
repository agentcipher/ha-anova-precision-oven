"""Test the Anova Oven config flow."""
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries, data_entry_flow
from homeassistant.const import CONF_TOKEN
from homeassistant.core import HomeAssistant

from custom_components.anova_oven.config_flow import CannotConnect, InvalidToken
from custom_components.anova_oven.const import (
    CONF_ENVIRONMENT,
    CONF_RECIPES_PATH,
    CONF_WS_URL,
    DEFAULT_WS_URL,
    DOMAIN,
)


async def test_form_display(hass: HomeAssistant):
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {}
    assert result["step_id"] == "user"


async def test_form_invalid_token_format(hass: HomeAssistant, mock_anova_oven: AsyncMock):
    """Test invalid token format."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    
    with patch(
        "custom_components.anova_oven.anova_sdk.oven.AnovaOven",
        return_value=mock_anova_oven,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_TOKEN: "invalid-token"},
        )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_token"}


async def test_form_connection_error(hass: HomeAssistant, mock_anova_oven: AsyncMock):
    """Test we handle connection error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    mock_anova_oven.__aenter__.side_effect = ConnectionError("Failed to connect")

    with patch(
        "custom_components.anova_oven.anova_sdk.oven.AnovaOven",
        return_value=mock_anova_oven,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_TOKEN: "anova-test-token"},
        )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_form_no_devices_found(hass: HomeAssistant, mock_anova_oven: AsyncMock):
    """Test we handle no devices found."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    mock_anova_oven.discover_devices.return_value = []

    with patch(
        "custom_components.anova_oven.anova_sdk.oven.AnovaOven",
        return_value=mock_anova_oven,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_TOKEN: "anova-test-token"},
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
        "custom_components.anova_oven.anova_sdk.oven.AnovaOven",
        return_value=mock_anova_oven,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_TOKEN: "anova-test-token"},
        )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_form_success_single_device(
    hass: HomeAssistant, mock_anova_oven: AsyncMock, mock_device
):
    """Test successful configuration with one device."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.anova_sdk.oven.AnovaOven",
        return_value=mock_anova_oven,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_TOKEN: "anova-test-token-12345"},
        )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "Anova Oven (1 device(s))"
    assert result["data"] == {
        CONF_TOKEN: "anova-test-token-12345",
        CONF_WS_URL: DEFAULT_WS_URL,
        CONF_ENVIRONMENT: "production",
        CONF_RECIPES_PATH: "",
    }


async def test_form_success_multiple_devices(
    hass: HomeAssistant, mock_anova_oven: AsyncMock, mock_device
):
    """Test successful configuration with multiple devices."""
    device2 = mock_device
    device2.cooker_id = "test-device-456"

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    mock_anova_oven.discover_devices.return_value = [mock_device, device2]

    with patch(
        "custom_components.anova_oven.anova_sdk.oven.AnovaOven",
        return_value=mock_anova_oven,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_TOKEN: "anova-test-token-12345"},
        )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "Anova Oven (2 device(s))"


async def test_form_with_custom_settings(
    hass: HomeAssistant, mock_anova_oven: AsyncMock, mock_device
):
    """Test configuration with custom settings."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    mock_anova_oven.discover_devices.return_value = [mock_device]
    custom_ws_url = "wss://custom.anovaculinary.io"

    with patch(
        "custom_components.anova_oven.anova_sdk.oven.AnovaOven",
        return_value=mock_anova_oven,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_TOKEN: "anova-test-token-12345",
                CONF_WS_URL: custom_ws_url,
                CONF_ENVIRONMENT: "dev",
                CONF_RECIPES_PATH: "/config/my_recipes.yml",
            },
        )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_WS_URL] == custom_ws_url
    assert result["data"][CONF_ENVIRONMENT] == "dev"
    assert result["data"][CONF_RECIPES_PATH] == "/config/my_recipes.yml"


async def test_validate_input_success(
    hass: HomeAssistant, mock_anova_oven: AsyncMock, mock_device
):
    """Test validate_input succeeds with valid data."""
    from custom_components.anova_oven.config_flow import validate_input

    mock_anova_oven.discover_devices.return_value = [mock_device]

    with patch(
        "custom_components.anova_oven.anova_sdk.oven.AnovaOven",
        return_value=mock_anova_oven,
    ):
        info = await validate_input(
            hass,
            {
                CONF_TOKEN: "anova-test-token",
                CONF_ENVIRONMENT: "production",
                CONF_WS_URL: DEFAULT_WS_URL,
            },
        )

    assert info["title"] == "Anova Oven (1 device(s))"
    assert info["device_count"] == 1


async def test_validate_input_invalid_token():
    """Test validate_input raises error for invalid token."""
    from custom_components.anova_oven.config_flow import validate_input

    with pytest.raises(InvalidToken):
        await validate_input(
            None,
            {
                CONF_TOKEN: "invalid-token",
                CONF_ENVIRONMENT: "production",
            },
        )


async def test_validate_input_no_devices(
    hass: HomeAssistant, mock_anova_oven: AsyncMock
):
    """Test validate_input raises error when no devices found."""
    from custom_components.anova_oven.config_flow import validate_input

    mock_anova_oven.discover_devices.return_value = []

    with patch(
        "custom_components.anova_oven.anova_sdk.oven.AnovaOven",
        return_value=mock_anova_oven,
    ), pytest.raises(CannotConnect):
        await validate_input(
            hass,
            {
                CONF_TOKEN: "anova-test-token",
                CONF_ENVIRONMENT: "production",
            },
        )


async def test_validate_input_connection_error(
    hass: HomeAssistant, mock_anova_oven: AsyncMock
):
    """Test validate_input handles connection error."""
    from custom_components.anova_oven.config_flow import validate_input
    from custom_components.anova_oven.anova_sdk.exceptions import AnovaError

    mock_anova_oven.__aenter__.side_effect = AnovaError("Connection failed")

    with patch(
        "custom_components.anova_oven.anova_sdk.oven.AnovaOven",
        return_value=mock_anova_oven,
    ), pytest.raises(CannotConnect):
        await validate_input(
            hass,
            {
                CONF_TOKEN: "anova-test-token",
                CONF_ENVIRONMENT: "production",
            },
        )


async def test_config_flow_exception_handler(hass: HomeAssistant, mock_anova_oven: AsyncMock):
    """Test config flow handles unexpected exceptions (config_flow.py lines 92-94)."""
    from homeassistant import config_entries

    result = await hass.config_entries.flow.async_init(
        "anova_oven", context={"source": config_entries.SOURCE_USER}
    )

    # Make it raise a generic exception
    mock_anova_oven.discover_devices.side_effect = RuntimeError("Unexpected error")

    with patch(
            "custom_components.anova_oven.anova_sdk.oven.AnovaOven",
            return_value=mock_anova_oven,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"token": "anova-test-token"},
        )

    # RuntimeError is wrapped in CannotConnect by validate_input(), so expect cannot_connect
    assert result["errors"] == {"base": "cannot_connect"}

async def test_config_flow_unexpected_exception(
    hass: HomeAssistant,
    mock_anova_oven: AsyncMock,
):
    """Test config flow handles unexpected exceptions (lines 92-94)."""
    from homeassistant import config_entries

    result = await hass.config_entries.flow.async_init(
        "anova_oven", context={"source": config_entries.SOURCE_USER}
    )

    # Cause an unexpected exception that's not CannotConnect or InvalidToken
    mock_anova_oven.discover_devices.side_effect = ValueError("Unexpected error")

    with patch(
        "custom_components.anova_oven.config_flow.AnovaOven",
        return_value=mock_anova_oven,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"token": "anova-test-token"},
        )

    assert result["type"] == "form"
    assert result["errors"] == {"base": "cannot_connect"}


async def test_config_flow_unexpected_exception_in_step_user(
        hass: HomeAssistant,
        mock_anova_oven: AsyncMock,
):
    """Test config flow catches unexpected exceptions (config_flow.py lines 93-95)."""
    from homeassistant import config_entries
    from homeassistant.const import CONF_TOKEN

    result = await hass.config_entries.flow.async_init(
        "anova_oven", context={"source": config_entries.SOURCE_USER}
    )

    # Make validate_input raise an unexpected exception
    with patch(
            "custom_components.anova_oven.config_flow.validate_input",
            side_effect=RuntimeError("Totally unexpected error"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_TOKEN: "anova-test-token"},
        )

    # Should catch and show "unknown" error (line 95)
    assert result["type"] == "form"
    assert result["errors"] == {"base": "unknown"}
