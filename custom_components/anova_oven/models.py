"""Local models for Anova Precision Oven."""
from __future__ import annotations

from typing import Optional, Union

from pydantic import BaseModel, Field, ConfigDict, field_validator, field_validator
from typing import Union

from anova_oven_sdk.models import (
    Device as SDKDevice,
    Temperature,
    Timer as SDKTimer,
)


class WebSocketPayload(BaseModel):
    """WebSocket EVENT_APO_STATE payload that handles both formats.

    Format 1: Direct structure with id, nodes, state at top level
    Format 2: Nested structure with cookerId and everything under 'state' key
    """
    model_config = ConfigDict(frozen=False, extra='ignore')

    # Device ID can be either field
    device_id: str = Field(alias="id", default=None)
    cooker_id: str = Field(alias="cookerId", default=None)

    # Top-level fields (Format 1) or nested under state (Format 2)
    version: Optional[int] = None
    updated_timestamp: Optional[str] = Field(None, alias="updatedTimestamp")
    system_info: Optional['SystemInfo'] = Field(None, alias="systemInfo")
    state: Optional[Union['State', dict]] = None  # Can be State object or wrapper dict
    nodes: Optional['Nodes'] = None

    # Format 2 specific
    type: Optional[str] = None

    @field_validator('device_id', mode='before')
    @classmethod
    def get_device_id(cls, v, info):
        """Extract device ID from either id or cookerId."""
        if v:
            return v
        # Try cookerId from the raw data
        return info.data.get('cookerId') or info.data.get('id')

    @field_validator('state', mode='before')
    @classmethod
    def unwrap_nested_state(cls, v, info):
        """Handle Format 2 where everything is nested under 'state'."""
        if not isinstance(v, dict):
            return v

        # Check if this is Format 2 (state contains nodes/systemInfo/version)
        if 'nodes' in v or 'systemInfo' in v or 'version' in v:
            # This is Format 2 - extract the actual state object
            actual_state = v.get('state', {})
            # Also populate the top-level fields from nested structure
            if 'version' in v:
                info.data['version'] = v['version']
            if 'updatedTimestamp' in v:
                info.data['updated_timestamp'] = v['updatedTimestamp']
            if 'systemInfo' in v:
                info.data['system_info'] = v['systemInfo']
            if 'nodes' in v:
                info.data['nodes'] = v['nodes']
            return actual_state

        # Format 1 - return as-is
        return v


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
WebSocketPayload.model_rebuild()