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
    model_config = ConfigDict(frozen=False, extra='ignore')
    current: Temperature
    setpoint: Optional[Temperature] = None  # Make optional - not always present

class TemperatureBulbs(BaseModel):
    """Temperature bulbs configuration."""
    model_config = ConfigDict(frozen=False, extra='ignore')
    mode: Optional[str] = Field(None, description="Mode: dry or wet")
    dry: Optional[TemperatureState] = None
    wet: Optional[TemperatureState] = None

class ProbeNode(BaseModel):
    """Probe node."""
    model_config = ConfigDict(frozen=False, extra='ignore')
    connected: bool = False
    current: Optional[Temperature] = None
    setpoint: Optional[Temperature] = None

class SteamOutput(BaseModel):
    """Steam output."""
    model_config = ConfigDict(frozen=False, extra='ignore')
    percentage: int = 0

class SteamGenerators(BaseModel):
    """Steam generators."""
    model_config = ConfigDict(frozen=False, extra='ignore')
    mode: str = "idle"
    relative_output: Optional[SteamOutput] = Field(None, alias="relativeOutput")

class TimerNode(BaseModel):
    """Timer node."""
    model_config = ConfigDict(frozen=False, extra='ignore')
    mode: str = "stopped"
    initial: int = 0
    current: int = 0

    @property
    def is_running(self) -> bool:
        return self.mode == "running"

class FanNode(BaseModel):
    """Fan node."""
    model_config = ConfigDict(frozen=False, extra='ignore')
    speed: int = 0

class ExhaustVentNode(BaseModel):
    """Exhaust vent node."""
    model_config = ConfigDict(frozen=False, extra='ignore')
    state: str = "closed"

class Nodes(BaseModel):
    """Device nodes."""
    model_config = ConfigDict(frozen=False, extra='ignore')

    temperature_bulbs: Optional[TemperatureBulbs] = Field(None, alias="temperatureBulbs")
    probe: Optional[ProbeNode] = None
    steam_generators: Optional[SteamGenerators] = Field(None, alias="steamGenerators")
    timer: Optional[TimerNode] = None
    fan: Optional[FanNode] = None
    exhaust_vent: Optional[ExhaustVentNode] = Field(None, alias="exhaustVent")

class CookStatus(BaseModel):
    """Cook status."""
    model_config = ConfigDict(frozen=False, extra='ignore')
    name: Optional[str] = None
    stages: Optional[list] = None
    current_stage: Optional[int] = Field(None, alias="currentStage")

class AnovaOvenDevice(SDKDevice):
    """Extended Device model with nodes."""
    model_config = ConfigDict(extra='ignore')
    nodes: Optional[Nodes] = None
    cook: Optional[CookStatus] = None

AnovaOvenDevice.model_rebuild()