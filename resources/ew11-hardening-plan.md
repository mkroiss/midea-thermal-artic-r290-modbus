# EW11-A Hardening Plan

## Architecture Change

Switch from EW11 on FritzBox WiFi to isolated AP mode:

```
Heat Pump → EW11 (AP: 10.10.100.x) → WiFi → Pi (WiFi) → Ethernet → FritzBox
```

- Pi connects to FritzBox via **ethernet** (more stable for HA)
- Pi connects to EW11 via **WiFi** (isolated Modbus network)
- EW11 is no longer on the home network

## Settings

See [ew11-sta-settings.md](ew11-sta-settings.md) (before) and [ew11-ap-settings.md](ew11-ap-settings.md) (after).

## Pi Configuration

1. Connect ethernet cable to FritzBox
2. Configure WiFi to join EW11's AP SSID
3. Verify Pi gets `10.10.100.x` address on WiFi interface

## Home Assistant Changes

Update Modbus host in `configuration.yaml`:
```yaml
host: 10.10.100.254  # was: 192.168.178.121
```

Update Python scripts (`set_target.py`, `scan_registers.py`):
```python
client = ModbusTcpClient('10.10.100.254', port=8899, timeout=5)
```

## Accessing EW11 Config Page

The EW11 web UI is only reachable from the Pi's network. To access from your PC:

```bash
ssh -L 8080:10.10.100.254:80 makro@192.168.178.107
```

Then open `http://localhost:8080` in your browser.

## Security Benefits

- EW11 is **not on the home network** (no one on FritzBox WiFi can reach it)
- Modbus traffic is **isolated** on a separate 10.10.100.x network
- Web UI only reachable via **SSH tunnel** through the Pi
- CLI escape sequence disabled (no AT command backdoor)
- Two separate passwords: AP KEY (WiFi access) and Authentication (config access)
- Factory reset button on EW11 as physical fallback

## Fallback

If anything goes wrong, hold the EW11 reset button for ~5 seconds to factory reset. It returns to AP mode with default settings (admin/admin, 10.10.100.254).
