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
    setpoint: Optional[Temperature] = None
    overheated: Optional[bool] = None  # For dryTop/dryBottom
    dosed: Optional[bool] = None  # For wet bulb
    dose_failed: Optional[bool] = Field(None, alias="doseFailed")  # For wet bulb

class TemperatureBulbs(BaseModel):
    """Temperature bulbs configuration."""
    model_config = ConfigDict(frozen=False, extra='ignore')
    mode: str = Field(..., description="Mode: dry or wet")
    dry: TemperatureState
    wet: TemperatureState
    dry_top: Optional[TemperatureState] = Field(None, alias="dryTop")
    dry_bottom: Optional[TemperatureState] = Field(None, alias="dryBottom")

class TemperatureProbeNode(BaseModel):
    """Temperature probe node - API uses 'temperatureProbe' not 'probe'."""
    model_config = ConfigDict(frozen=False, extra='ignore')
    connected: bool
    current: Optional[Temperature] = None
    setpoint: Optional[Temperature] = None

class RelativeHumidity(BaseModel):
    """Relative humidity."""
    model_config = ConfigDict(frozen=False, extra='ignore')
    current: int

class SteamComponent(BaseModel):
    """Steam component (evaporator or boiler)."""
    model_config = ConfigDict(frozen=False, extra='ignore')
    failed: bool
    overheated: bool
    celsius: float
    watts: int
    dosed: Optional[bool] = None  # Only for boiler
    descale_required: Optional[bool] = Field(None, alias="descaleRequired")  # Only for boiler

class SteamGenerators(BaseModel):
    """Steam generators - API structure."""
    model_config = ConfigDict(frozen=False, extra='ignore')
    mode: str
    relative_humidity: Optional[RelativeHumidity] = Field(None, alias="relativeHumidity")
    evaporator: Optional[SteamComponent] = None
    boiler: Optional[SteamComponent] = None

class TimerNode(BaseModel):
    """Timer node."""
    model_config = ConfigDict(frozen=False, extra='ignore')
    mode: str
    initial: int
    current: int

    @property
    def is_running(self) -> bool:
        return self.mode == "running"

class HeatingElement(BaseModel):
    """Individual heating element."""
    model_config = ConfigDict(frozen=False, extra='ignore')
    on: bool
    failed: bool
    watts: int

class HeatingElements(BaseModel):
    """All heating elements."""
    model_config = ConfigDict(frozen=False, extra='ignore')
    top: HeatingElement
    bottom: HeatingElement
    rear: HeatingElement

class FanNode(BaseModel):
    """Fan node."""
    model_config = ConfigDict(frozen=False, extra='ignore')
    speed: int
    failed: Optional[bool] = None

class VentNode(BaseModel):
    """Vent node - API uses 'vent' not 'exhaustVent'."""
    model_config = ConfigDict(frozen=False, extra='ignore')
    open: bool

class WaterTankNode(BaseModel):
    """Water tank node."""
    model_config = ConfigDict(frozen=False, extra='ignore')
    empty: bool

class DoorNode(BaseModel):
    """Door node."""
    model_config = ConfigDict(frozen=False, extra='ignore')
    closed: bool

class LampNode(BaseModel):
    """Lamp node."""
    model_config = ConfigDict(frozen=False, extra='ignore')
    on: bool
    failed: bool
    preference: Optional[str] = None

class UserInterfaceCircuit(BaseModel):
    """User interface circuit node."""
    model_config = ConfigDict(frozen=False, extra='ignore')
    communication_failed: bool = Field(..., alias="communicationFailed")

class Nodes(BaseModel):
    """Device nodes - matching actual API structure."""
    model_config = ConfigDict(frozen=False, extra='ignore')

    temperature_bulbs: TemperatureBulbs = Field(..., alias="temperatureBulbs")
    temperature_probe: Optional[TemperatureProbeNode] = Field(None, alias="temperatureProbe")
    steam_generators: SteamGenerators = Field(..., alias="steamGenerators")
    timer: TimerNode
    fan: FanNode
    vent: Optional[VentNode] = None
    heating_elements: Optional[HeatingElements] = Field(None, alias="heatingElements")
    water_tank: Optional[WaterTankNode] = Field(None, alias="waterTank")
    door: Optional[DoorNode] = None
    lamp: Optional[LampNode] = None
    user_interface_circuit: Optional[UserInterfaceCircuit] = Field(None, alias="userInterfaceCircuit")

class SystemInfo(BaseModel):
    """System information."""
    model_config = ConfigDict(frozen=False, extra='ignore')
    online: bool
    hardware_version: Optional[str] = Field(None, alias="hardwareVersion")
    power_mains: Optional[int] = Field(None, alias="powerMains")
    power_hertz: Optional[int] = Field(None, alias="powerHertz")
    firmware_version: Optional[str] = Field(None, alias="firmwareVersion")
    ui_hardware_version: Optional[str] = Field(None, alias="uiHardwareVersion")
    ui_firmware_version: Optional[str] = Field(None, alias="uiFirmwareVersion")
    firmware_updated_timestamp: Optional[str] = Field(None, alias="firmwareUpdatedTimestamp")
    last_connected_timestamp: Optional[str] = Field(None, alias="lastConnectedTimestamp")
    last_disconnected_timestamp: Optional[str] = Field(None, alias="lastDisconnectedTimestamp")
    triacs_failed: Optional[bool] = Field(None, alias="triacsFailed")

class State(BaseModel):
    """Device state - contains temperatureUnit and mode."""
    model_config = ConfigDict(frozen=False, extra='ignore')
    mode: str
    temperature_unit: Optional[str] = Field(None, alias="temperatureUnit")
    processed_command_ids: Optional[list[str]] = Field(None, alias="processedCommandIds")

class CookStatus(BaseModel):
    """Cook status."""
    model_config = ConfigDict(frozen=False, extra='ignore')
    name: Optional[str] = None
    stages: Optional[list] = None
    current_stage: Optional[int] = Field(None, alias="currentStage")

class AnovaOvenDevice(SDKDevice):
    """Extended Device model with nodes and state."""
    nodes: Optional[Nodes] = None
    state: Optional[State] = None
    cook: Optional[CookStatus] = None
    system_info: Optional[SystemInfo] = Field(None, alias="systemInfo")
    version: Optional[int] = None
    updated_timestamp: Optional[str] = Field(None, alias="updatedTimestamp")

AnovaOvenDevice.model_rebuild()