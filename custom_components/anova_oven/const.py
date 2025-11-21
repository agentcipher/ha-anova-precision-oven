"""Constants for the Anova Precision Oven integration."""
from typing import Final

DOMAIN: Final = "anova_oven"

# Configuration
CONF_WS_URL: Final = "ws_url"
CONF_ENVIRONMENT: Final = "environment"

# Default values
DEFAULT_WS_URL: Final = "wss://devices.anovaculinary.io"
DEFAULT_TIMEOUT: Final = 30.0
DEFAULT_COMMAND_TIMEOUT: Final = 10.0
DEFAULT_SCAN_INTERVAL: Final = 30

# Device attributes
ATTR_DEVICE_ID: Final = "device_id"
ATTR_OVEN_VERSION: Final = "oven_version"
ATTR_COOKER_ID: Final = "cooker_id"
ATTR_RECIPE_ID: Final = "recipe_id"
ATTR_RECIPE_NAME: Final = "recipe_name"
ATTR_STAGES: Final = "stages"
ATTR_CURRENT_STAGE: Final = "current_stage"
ATTR_TEMPERATURE_UNIT: Final = "temperature_unit"
ATTR_DURATION: Final = "duration"
ATTR_FAN_SPEED: Final = "fan_speed"

# Services
SERVICE_START_COOK: Final = "start_cook"
SERVICE_STOP_COOK: Final = "stop_cook"
SERVICE_SET_PROBE: Final = "set_probe"
SERVICE_START_RECIPE: Final = "start_recipe"
SERVICE_SET_TEMPERATURE_UNIT: Final = "set_temperature_unit"

# State attributes
STATE_IDLE: Final = "idle"
STATE_PREHEATING: Final = "preheating"
STATE_COOKING: Final = "cooking"
STATE_PAUSED: Final = "paused"
STATE_COMPLETED: Final = "completed"
STATE_ERROR: Final = "error"

# Oven modes
MODE_DRY: Final = "dry"
MODE_WET: Final = "wet"

# Temperature limits (Celsius)
TEMP_MIN: Final = 25.0
TEMP_MAX: Final = 250.0
PROBE_TEMP_MIN: Final = 1.0
PROBE_TEMP_MAX: Final = 100.0

# Recipe configuration
RECIPES_FILE: Final = "recipes.yml"
CONF_RECIPES_PATH: Final = "recipes_path"