# Anova Precision Oven Integration for Home Assistant

**⚠️ DISCLAIMER**

This software is provided "as is" without warranty of any kind, express or implied. The authors and contributors are not liable for any damages, losses, or issues arising from the use of this software, including but not limited to:
- Device malfunction or damage
- Property damage
- Food safety issues
- Data loss
- Service interruptions

Use at your own risk. Always supervise cooking operations and follow manufacturer guidelines for your Anova Precision Oven. This is unofficial software not endorsed by Anova Culinary.

---

The goal of this personal project is to allow Anova Precision Ovens to be used in a Home Assistant integration using the official Anova API ([https://developer.anovaculinary.com/docs/devices/wifi/oven-commands](https://developer.anovaculinary.com/docs/devices/wifi/oven-commands)).  The majority of this code was written using Anthropic Claude ([https://claude.ai](https://claude.ai))

## Features

### Core Functionality
- **Full Climate Control**: Temperature, mode, and HVAC control through Home Assistant
- **Recipe Library Support**: Load and execute recipes from YAML files
- **Real-time Monitoring**: Live temperature, probe, timer, and status updates
- **Multi-device Support**: Manage multiple Anova ovens simultaneously
- **Celsius & Fahrenheit**: Full support for both temperature units

### Entity Types

#### Climate Entity
- Main oven temperature control
- HVAC modes: Heat, Off
- Current and target temperature display
- Rich state attributes (stages, probe, steam, timer)

#### Sensors (11 total)
- Current Temperature
- Target Temperature
- Probe Temperature & Target
- Timer (Remaining & Initial)
- Steam Percentage
- Fan Speed
- Current Stage & Total Stages
- Recipe Name

#### Binary Sensors (6 total)
- Cooking Status
- Preheating Status
- Door Open/Closed
- Water Low Warning
- Probe Connected
- Vent Open/Closed

#### Controls
- **Button**: Stop Cook
- **Select**: Recipe selection, Temperature unit
- **Number**: Probe target temperature

### Services

#### `anova_oven.start_cook`
Start cooking with custom parameters.

#### `anova_oven.stop_cook`
Stop current cooking session.

#### `anova_oven.set_probe`
Set probe target temperature.

#### `anova_oven.start_recipe`
Start a recipe from the library.

#### `anova_oven.set_temperature_unit`
Set display temperature unit on oven.

## Installation

### Manual Installation
1. Copy the `custom_components/anova_oven` directory to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant
3. Configure via UI: Configuration → Integrations → Add Integration → Anova Precision Oven

## Recipe Configuration

Recipes are loaded from a YAML file. Place your `recipes.yml` in the Home Assistant config directory or specify a custom path during setup.

### Recipe Format
```yaml
recipes:
  - my_recipe:
      name: "My Recipe"
      description: "Recipe description"
      stages:
        - name: "Stage 1"
          temperature:
            value: 200
            temperature_unit: "C"
            mode: "DRY"
          timer:
            seconds: 1800
          fan_speed: 100
          heating_elements:
            top: true
            bottom: true
            rear: true
          rack_position: 3
```

## Credits

Inspired by ha_gehome([https://github.com/simbaja/ha_gehome]) integration patterns.
