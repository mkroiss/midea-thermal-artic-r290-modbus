# EW11-A Settings (STA Mode)

Current settings - EW11 connects to FritzBox WiFi as a client.

## System Settings

### Authentication
| Setting | Value |
|---------|-------|
| User Name | admin |
| Password | ******* |

Web UI login. Anyone who can reach the EW11 on the network can access the config page. In STA mode, that's anyone on the FritzBox WiFi.

### Basic Settings
| Setting | Value |
|---------|-------|
| Host Name | EW11 |

### WAN Settings
| Setting | Value |
|---------|-------|
| DHCP | ON |
| DNS | 223.5.5.5 |

DHCP ON means the EW11 gets its IP from the FritzBox automatically. DNS 223.5.5.5 is Alibaba's public DNS (Chinese) - factory default. The EW11 doesn't actually use DNS since Modbus communication is IP-only.

### LAN Settings
| Setting | Value |
|---------|-------|
| LAN IP | 10.10.100.254 |
| Mask | 255.255.255.0 |
| DHCP Server | OFF |

LAN settings are for AP mode. The 10.10.100.254 address is only reachable when the EW11 broadcasts its own WiFi network. DHCP Server was turned OFF since in STA mode the FritzBox handles IP assignment - leaving it ON could hand out rogue IPs to other devices.

### WiFi Settings
| Setting | Value |
|---------|-------|
| WiFi Mode | STA |
| STA SSID | FRITZ!Box Fon WLAN 7360 |
| STA KEY | ******* |

STA = station mode, the EW11 joins the FritzBox as a client. The STA KEY is the FritzBox WiFi password. Modbus TCP port 8899 is open to anyone on the network with no authentication.

### Telnet Settings
| Setting | Value |
|---------|-------|
| Enable | OFF |

Good. Telnet is unencrypted remote shell access.

### Web Settings
| Setting | Value |
|---------|-------|
| Enable | ON |
| Web Port | 80 |

The config page (HTTP, unencrypted). In STA mode, reachable from any device on the FritzBox network at http://192.168.178.121.

### NTP Settings
| Setting | Value |
|---------|-------|
| Enable | OFF |

Network time sync. Not needed - the EW11 has no logs or schedules that depend on accurate time.

### Modbus TimeOut Settings
| Setting | Value |
|---------|-------|
| Automatic | ON |

How long the EW11 waits for a response from the heat pump on RS-485. Automatic calculates the timeout from the baud rate (9600). Leave as is unless there are communication issues.

## Serial Port Settings

### Basic Settings
| Setting | Value |
|---------|-------|
| Baud Rate | 9600 |
| Data Bit | 8 |
| Stop Bit | 1 |
| Parity | None |

Must match the Midea heat pump spec: 9600/8/N/1.

### Buffer Settings
| Setting | Value |
|---------|-------|
| Buffer Size | 512 |
| Gap Time | 50 |

Buffer size is fine (Modbus max frame is 256 bytes). Gap Time (50ms) is the inter-frame silence between Modbus messages.

### Flow Control Settings
| Setting | Value |
|---------|-------|
| Flow Control | Half Duplex |

Correct for 2-wire RS-485 (H1/H2). Half duplex means only one side talks at a time. The EW11 handles transmit/receive direction switching automatically. Other options (None, Hardware) are for RS-232 or 4-wire RS-485.

### Cli Settings
| Setting | Value |
|---------|-------|
| Cli | Serial String |
| Serial String | +++ |
| Waiting Time | 300 |

AT command escape sequence. Sending `+++` with 300ms silence before and after drops into the EW11's configuration CLI. In Modbus protocol mode this is likely ignored, but it's an unnecessary attack surface.

### Protocol Settings
| Setting | Value |
|---------|-------|
| Protocol | Modbus |

Must be Modbus (not transparent TCP). The EW11 acts as a Modbus TCP to RTU gateway - it converts TCP frames to RS-485 RTU frames and passes the slave address through transparently.
