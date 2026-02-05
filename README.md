# Midea Heat Pump Modbus Integration for Home Assistant

Home Assistant integration for Midea M-Thermal Arctic R290 heat pumps via Modbus RTU over TCP.

## Hardware Setup

- **Heat Pump**: Midea Thermal Arctic R290 10kW
- **Modbus Gateway**: Elfin EW11-A (WiFi to RS-485 converter)
- **Home Assistant**: Running on Raspberry Pi 5 (Docker)

### Wiring

```
Heat Pump (Wired Controller) → EW11-A → WiFi → Home Assistant
         H1 (-) → A                              Modbus TCP
         H2 (+) → B
```

### EW11-A Configuration

- **Mode**: Modbus TCP to RTU gateway (NOT transparent TCP)
- **Baud Rate**: 9600
- **Data Bits**: 8
- **Parity**: None
- **Stop Bits**: 1
- **TCP Port**: 8899

### Modbus Settings

- **Slave Address**: Default is 1, this project uses 2 (configurable in HMI wired controller)
- **Protocol**: Modbus RTU

## Files

| File | Description |
|------|-------------|
| `configuration.yaml` | Home Assistant config with Modbus sensors, template sensors, utility meters |
| `heat_pump_dashboard.yaml` | Lovelace dashboard for heat pump monitoring |
| `heat_pump_package.yaml` | HA package with input_number, shell_command, automation for target temp |
| `set_target.py` | Python script to write target temperature (called by HA automation) |
| `scan_registers.py` | Modbus register scanner with full documentation |
| `register_dump.txt` | Complete register dump with values and descriptions |

## Installation

1. Copy files to your Home Assistant config directory (`/config/`)
2. Update IP address in `configuration.yaml` and Python scripts (default: 192.168.178.121)
3. Update Modbus slave address in configs if using default (1) instead of 2
4. Restart Home Assistant
5. Dashboard appears automatically in sidebar as "Heat Pump"

## Features

- Real-time monitoring: temperatures, pressures, compressor frequency, COP
- Power control via Modbus switch
- Target temperature adjustment with +/- buttons
- Energy tracking (daily/monthly/yearly)
- Historical graphs for temperatures, power, COP

## Register Documentation

See `register_dump.txt` for complete Modbus register documentation, or run:

```bash
python scan_registers.py
```

### Key Registers

| Address | Name | Description |
|---------|------|-------------|
| 0 | Power on/off | Bit field for zone/DHW power |
| 1 | Mode setting | 1=Auto, 2=Cooling, 3=Heating |
| 2 | Set water temp | Zone1 (low byte), Zone2 (high byte) |
| 16 | Power Zone 1 | 0=off, 1=on |
| 100 | Compressor freq | Current frequency in Hz |
| 104-105 | Tw_in/Tw_out | Water inlet/outlet temps |
| 107 | T4 | Outdoor ambient temp |
| 116-117 | P1/P2 | High/low pressure (kPa) |
| 143-144 | Energy consumption | 32-bit cumulative kWh (x0.01) |
| 151 | Real-time COP | Current COP (x0.01) |
| 199 | Operation mode | 0=Off, 2=Cool, 3=Heat, 5=DHW |

## Notes

- Bulk reads work for registers 0-22 and 100-199
- Registers 200-290 must be read individually (bulk read fails)
- Negative temperatures use 16-bit two's complement (e.g., 65531 = -5°C)
- 32-bit values split across two registers: `(high * 65536 + low) / 100`

## References

- [Midea Modbus Protocol Documentation](resources/120L-modbus-0052003044313-V-E.pdf)

## License

MIT
