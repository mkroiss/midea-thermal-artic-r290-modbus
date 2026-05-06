# EW11-A Settings (Current — STA Mode on Pi AP)

EW11-A connects as a WiFi client to the Pi's isolated "leni" access point.

## System Settings

### Authentication
| Setting | Value |
|---------|-------|
| User Name | admin |
| Password | (strong password) |

Web UI is only reachable via SSH tunnel through the Pi — not exposed to the home network.

### Basic Settings
| Setting | Value |
|---------|-------|
| Host Name | EW11 |

### WAN Settings
| Setting | Value |
|---------|-------|
| DHCP | ON |
| DNS | 223.5.5.5 |

Gets IP from Pi's dnsmasq via DHCP reservation → always `10.10.100.131`.
DNS is factory default (Alibaba) — irrelevant since EW11 doesn't use DNS.

### LAN Settings
| Setting | Value |
|---------|-------|
| LAN IP | 10.10.100.254 |
| Mask | 255.255.255.0 |
| DHCP Server | OFF |

LAN settings are for AP mode only (unused in STA mode). DHCP Server OFF.

### WiFi Settings
| Setting | Value |
|---------|-------|
| WiFi Mode | STA |
| STA SSID | leni |
| STA KEY | (AP password) |

Connects to the Pi's isolated AP. Only the Pi is on this network.

### Telnet Settings
| Setting | Value |
|---------|-------|
| Enable | OFF |

Off. Telnet is unencrypted.

### Web Settings
| Setting | Value |
|---------|-------|
| Enable | ON |
| Web Port | 80 |

Accessible only from within the 10.10.100.x network. From a PC, access via SSH tunnel:
```bash
ssh -L 8080:10.10.100.131:80 -f -N makro@192.168.178.107
```
Then open http://localhost:8080.

### NTP Settings
| Setting | Value |
|---------|-------|
| Enable | OFF |

Not needed — no time-dependent features.

### Modbus TimeOut Settings
| Setting | Value |
|---------|-------|
| Automatic | ON |

Calculates timeout from baud rate (9600). Leave as is.

## Serial Port Settings

### Basic Settings
| Setting | Value |
|---------|-------|
| Baud Rate | 9600 |
| Data Bit | 8 |
| Stop Bit | 1 |
| Parity | None |

Must match Midea heat pump spec: 9600/8/N/1.

### Buffer Settings
| Setting | Value |
|---------|-------|
| Buffer Size | 512 |
| Gap Time | 50 |

Buffer covers max Modbus frame (256 bytes). Gap time (50ms) handles inter-frame silence.

### Flow Control Settings
| Setting | Value |
|---------|-------|
| Flow Control | Half Duplex |

Correct for 2-wire RS-485. EW11 handles TX/RX direction switching automatically.

### Cli Settings
| Setting | Value |
|---------|-------|
| Cli | None |

Disabled. The `+++` AT escape sequence is not needed and is an unnecessary attack surface.

### Protocol Settings
| Setting | Value |
|---------|-------|
| Protocol | Modbus |

Modbus TCP to RTU gateway mode. Converts TCP frames to RS-485 RTU, passes slave address through transparently.