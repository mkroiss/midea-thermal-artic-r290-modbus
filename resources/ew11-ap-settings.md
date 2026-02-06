# EW11-A Settings (AP Mode - Hardened)

Hardened settings - EW11 runs as isolated access point, only Pi connects.

## System Settings

### Authentication
| Setting | Value |
|---------|-------|
| User Name | admin |
| Password | **strong password** |

Web UI login. In AP mode, only the Pi can reach the config page. From a PC, access via SSH tunnel: `ssh -L 8080:10.10.100.254:80 makro@192.168.178.107` then open http://localhost:8080. Use a different password than the AP KEY.

### Basic Settings
| Setting | Value |
|---------|-------|
| Host Name | EW11 |

### WAN Settings
| Setting | Value |
|---------|-------|
| DHCP | OFF |
| DNS | - |

Unused in AP mode. The EW11 doesn't join any external network, so WAN DHCP and DNS are irrelevant.

### LAN Settings
| Setting | Value |
|---------|-------|
| LAN IP | 10.10.100.254 |
| Mask | 255.255.255.0 |
| DHCP Server | ON |

The EW11 is now the router on its own isolated 10.10.100.x network. DHCP Server must be ON to hand the Pi an IP address when it connects to the AP.

### WiFi Settings
| Setting | Value |
|---------|-------|
| WiFi Mode | AP |
| AP KEY | **strong password (different from Authentication)** |

AP = access point mode. The EW11 broadcasts its own WiFi network. Only the Pi should connect. The AP KEY protects WiFi access (who can connect), the Authentication password protects config access (who can change settings) - two separate layers.

### Telnet Settings
| Setting | Value |
|---------|-------|
| Enable | OFF |

Keep off. Telnet is unencrypted remote shell access.

### Web Settings
| Setting | Value |
|---------|-------|
| Enable | ON |
| Web Port | 80 |

Safe to leave on - only the Pi can reach it on the isolated network. Disabling it is optional since the factory reset button can always restore access.

### NTP Settings
| Setting | Value |
|---------|-------|
| Enable | OFF |

Not needed, and the EW11 has no internet access in AP mode anyway.

### Modbus TimeOut Settings
| Setting | Value |
|---------|-------|
| Automatic | ON |

No change needed. Automatic timeout calculation based on 9600 baud works fine.

## Serial Port Settings

### Basic Settings
| Setting | Value |
|---------|-------|
| Baud Rate | 9600 |
| Data Bit | 8 |
| Stop Bit | 1 |
| Parity | None |

Must match the Midea heat pump spec: 9600/8/N/1. No change from STA mode.

### Buffer Settings
| Setting | Value |
|---------|-------|
| Buffer Size | 512 |
| Gap Time | 50 |

No change needed. Buffer size covers Modbus frames, gap time handles inter-frame silence.

### Flow Control Settings
| Setting | Value |
|---------|-------|
| Flow Control | Half Duplex |

Correct for 2-wire RS-485. No change from STA mode.

### Cli Settings
| Setting | Value |
|---------|-------|
| Cli | None |

Disabled. The AT command escape sequence (`+++`) is not needed for a Modbus gateway and is an unnecessary attack surface. Removing it prevents anyone from dropping into the EW11's configuration CLI via the TCP port.

### Protocol Settings
| Setting | Value |
|---------|-------|
| Protocol | Modbus |

Must be Modbus. The EW11 converts Modbus TCP to RTU and passes the slave address through transparently. No change from STA mode.
