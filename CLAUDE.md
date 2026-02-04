# Midea Modbus Integration Project

## Goal
Integrate Midea Thermal Arctic R290 10kW heat pump with Home Assistant via Modbus RTU.

## Hardware Setup
- **Heat Pump**: Midea Thermal Arctic R290 10kW
- **Home Assistant**: Running on Raspberry Pi 5 (Docker image)
- **Modbus Gateway**: Elfin EW11-A (WiFi to RS-485 converter)

### Architecture
```
Heat Pump (RS-485 H1/H2) → EW11-A → WiFi → Home Assistant (Modbus TCP)
```

### EW11-A to Wired Controller Wiring
- EW11-A A (+) → H1
- EW11-A B (-) → H2
- No ground connection needed (short cable)
- Connected to wired controller, NOT outdoor unit

### EW11-A Configuration
- Baud Rate: 9600
- Data Bits: 8
- Parity: None
- Stop Bits: 1
- Mode: Modbus TCP to RTU gateway (must be "Modbus" mode, not transparent TCP)

### Home Assistant Configuration
- **Pi IP**: 192.168.178.107 (user: makro)
- **EW11-A IP**: 192.168.178.121, TCP port 8899
- **Modbus slave address**: 2
- Config file: `/root/homeassistant/config/configuration.yaml`
- Docker: `ghcr.io/home-assistant/home-assistant:stable`

### System Configuration
- Zone 1 only (no Zone 2)
- No DHW (domestic hot water)
- No TBH (tank booster heater)
- No IBH (inline booster heater)

## Modbus Specifications
- **Port**: RS-485 (H1"-", H2"+")
- **Baud Rate**: 9600
- **Data Bits**: 8
- **Parity**: None
- **Stop Bits**: 1
- **Protocol**: Modbus RTU (ASCII not supported)
- **Function Codes**: 03H (read), 06H (write single), 10H (write multiple)

## Reference Documentation
- `resources/120L-modbus-0052003044313-V-E.pdf` - Modbus mapping table

## Project Files
- `configuration.yaml` - HA config: modbus sensors, template sensors, switch, packages
- `heat_pump_dashboard.yaml` - HA dashboard (lovelace)
- `heat_pump_package.yaml` - Target temp input_number, automations for read/write sync
- `set_target.py` - Python script to write target temp to heat pump via Modbus
- `midea_esp32.yaml` - Old ESPHome config (abandoned, SparkFun board had design flaw)

## Key Registers Summary

### Control Registers (Read/Write)
| Address | PLC | Description | Values |
|---------|-----|-------------|--------|
| 0 | 40001 | Power on/off | Bit field (see docs) |
| 1 | 40002 | Mode setting | 1=Auto, 2=Cooling, 3=Heating |
| 2 | 40003 | Set water temp T1s | Zone1 (low 8 bits), Zone2 (high 8 bits) |
| 16 | 40017 | Power Zone 1 | 0=off, 1=on |

### Sensor Registers (Read Only)
| Address | PLC | Description | Unit |
|---------|-----|-------------|------|
| 100 | 40101 | Compressor frequency | Hz |
| 101 | 40102 | Operating state | 0=off, 2=cooling, 3=heating |
| 104 | 40105 | Tw_in (water inlet) | °C |
| 105 | 40106 | Tw_out (water outlet) | °C |
| 106 | 40107 | T3 (condenser) | °C |
| 107 | 40108 | T4 (outdoor ambient) | °C |
| 108 | 40109 | Discharge temp | °C |
| 109 | 40110 | Suction temp | °C |
| 110 | 40111 | T1 (total outlet water) | °C |
| 116 | 40117 | P1 (high pressure) | kPa |
| 117 | 40118 | P2 (low pressure) | kPa |
| 118 | 40119 | ODU current | A (x0.1) |
| 119 | 40120 | ODU voltage | V |
| 124 | 40125 | Current error | Error code |
| 138 | 40139 | Water flow | m³/h (x0.01) |
| 150 | 40151 | Power consumption | kW (x0.01) |
| 151 | 40152 | COP | x0.01 |
| 199 | 40200 | Operation mode | 0=Off, 2=Cooling, 3=Heating, 5=DHW |

### Template Sensors
- **HP Mode Text** - Operating mode as text (Off/Cool/Heat/DHW)
- **HP State Text** - Operating state as text (Idle/Cool/Heat)
- **HP Current Target** - Zone 1 target extracted from packed register 2
- **HP Power Consumption** - Power raw / 100 in kW
- **HP ODU Power** - ODU current × voltage in W
- **HP Delta T** - T1 outlet minus Tw_in inlet
- **HP COP Filtered** - COP capped at 10 (raw register gives unrealistic spikes)

## TODO
- [x] Determine RS-485 adapter for Raspberry Pi → EW11-A
- [x] Configure Home Assistant Modbus integration
- [x] Create sensors
- [x] Test communication - working!
- [x] Add power switch and target temperature control
- [x] Create HA dashboard
- [ ] Add mode control (auto/heating/cooling)
- [ ] Improve EW11-A WiFi signal (-96 dBm is marginal)
