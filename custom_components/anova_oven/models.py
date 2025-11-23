"""Local models for Anova Precision Oven."""
from __future__ import annotations

from typing import Optional

from pydantic import Field, ConfigDict

from anova_oven_sdk.models import Device as SDKDevice
from anova_oven_sdk.response_models import (
    Nodes,
    SystemInfo as SDKSystemInfo,
    OvenState,
)


class AnovaOvenDevice(SDKDevice):
    """Extended Device model with additional state tracking."""
    model_config = ConfigDict(populate_by_name=True)

    nodes: Optional[Nodes] = None
    state_info: Optional[OvenState] = Field(None, alias="state")
    system_info: Optional[SDKSystemInfo] = Field(None, alias="systemInfo")
    version: Optional[int] = None
    updated_timestamp: Optional[str] = Field(None, alias="updatedTimestamp")

AnovaOvenDevice.model_rebuild()