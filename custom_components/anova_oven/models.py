"""Local models for Anova Precision Oven."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, ConfigDict

from anova_oven_sdk.models import (
    Device as SDKDevice,
    Temperature,
    Timer as SDKTimer,
)

class TemperatureState(BaseModel):
    """Temperature state."""
    model_config = ConfigDict(frozen=False)
    current: Temperature
    setpoint: Temperature

class TemperatureBulbs(BaseModel):
    """Temperature bulbs configuration."""
    model_config = ConfigDict(frozen=False)
    mode: str = Field(..., description="Mode: dry or wet")
    dry: TemperatureState
    wet: TemperatureState

class ProbeNode(BaseModel):
    """Probe node."""
    model_config = ConfigDict(frozen=False)
    connected: bool
    current: Temperature
    setpoint: Temperature

class SteamOutput(BaseModel):
    """Steam output."""
    model_config = ConfigDict(frozen=False)
    percentage: int

class SteamGenerators(BaseModel):
    """Steam generators."""
    model_config = ConfigDict(frozen=False)
    mode: str
    relative_output: SteamOutput = Field(..., alias="relativeOutput")

class TimerNode(BaseModel):
    """Timer node."""
    model_config = ConfigDict(frozen=False)
    mode: str
    initial: int
    current: int
    
    @property
    def is_running(self) -> bool:
        return self.mode == "running"

class FanNode(BaseModel):
    """Fan node."""
    model_config = ConfigDict(frozen=False)
    speed: int

class ExhaustVentNode(BaseModel):
    """Exhaust vent node."""
    model_config = ConfigDict(frozen=False)
    state: str

class Nodes(BaseModel):
    """Device nodes."""
    model_config = ConfigDict(frozen=False)
    
    temperature_bulbs: TemperatureBulbs = Field(..., alias="temperatureBulbs")
    probe: ProbeNode
    steam_generators: SteamGenerators = Field(..., alias="steamGenerators")
    timer: TimerNode
    fan: FanNode
    exhaust_vent: ExhaustVentNode = Field(..., alias="exhaustVent")

class CookStatus(BaseModel):
    """Cook status."""
    model_config = ConfigDict(frozen=False)
    name: Optional[str] = None
    stages: Optional[list] = None
    current_stage: Optional[int] = Field(None, alias="currentStage")

class AnovaOvenDevice(SDKDevice):
    """Extended Device model with nodes."""
    nodes: Optional[Nodes] = None
    cook: Optional[CookStatus] = None

AnovaOvenDevice.model_rebuild()
