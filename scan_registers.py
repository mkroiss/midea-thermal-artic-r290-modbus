#!/usr/bin/env python3
"""Scan and dump all Modbus registers from Midea M-Thermal Arctic R290 heat pump.

Reads all known registers (0-22, 100-199, 200-290), formats values with
proper scaling, and outputs a complete register dump with descriptions.
Output goes to both console and register_dump.txt.

Usage: python scan_registers.py

Connection: EW11-A gateway at 192.168.178.121:8899 (change to 10.10.100.254
after AP mode hardening), Modbus slave address 2.

Note: Registers 200-290 must be read individually (bulk read returns
exception code 2). This makes the scan slower for that range.

Requires: pip install pymodbus
"""
from pymodbus.client import ModbusTcpClient

# Midea Modbus Register Scanner
# =============================
#
# Register Map:
#   0-22    Control registers (R/W) - power, mode, setpoints, zone control
#   23-99   Not implemented (gap in protocol)
#   100-199 Operating parameters (R) - temperatures, pressures, status, energy
#   200-290 Configuration parameters (R/W) - limits, curves, timings
#
# Bulk Read Behavior:
#   0-22    Bulk read works
#   100-199 Bulk read works
#   200-290 Bulk read FAILS (Exception code 2), must read individually
#
# Value Encoding:
#   - Some registers pack two values: Zone1 in low 8 bits, Zone2 in high 8 bits
#   - Negative temperatures use 16-bit two's complement (e.g., 65531 = -5)
#   - 32-bit values split across two registers (high/low), scaled by 0.01
#   - 65535 (0xFFFF) and 255 (0xFF) typically mean "not available" or "no sensor"
#

# Known registers from Midea Modbus mapping table
# Format: (name, short_desc, used_in_setup, detailed_description)
# used_in_setup: True = used in our Zone1-only heating setup, False = not used
REGISTERS = {
    # ==========================================================================
    # CONTROL REGISTERS (0-22) - Read/Write
    # ==========================================================================

    0: ("Power on/off", "Bit field", True,
        "Bit0: Zone1/2 room temp control (0=off,1=on), "
        "Bit1: Zone1 water temp control (0=off,1=on), "
        "Bit2: DHW power (0=off,1=on), "
        "Bit3: Zone2 water temp control. "
        "Prefer using registers 14-17 for individual control."),

    1: ("Mode setting", "1=Auto, 2=Cooling, 3=Heating", True,
        "Operating mode selection. 1=Auto (switches heating/cooling based on outdoor temp), "
        "2=Cooling mode, 3=Heating mode. Other values invalid."),

    2: ("Set water temp T1s", "Zone1 (low 8), Zone2 (high 8)", True,
        "Water temperature setpoint. Low byte = Zone1 temp, High byte = Zone2 temp. "
        "Example: 7708 = 0x1E1C = Zone1=28C, Zone2=30C. "
        "Prefer using registers 11-12 for individual zone control."),

    3: ("Set air temp Tas", "Room temp control", False,
        "Room air temperature setpoint for room thermostat control mode. "
        "Typically 16-30C. Only used when room temp control is enabled (reg 17)."),

    4: ("Set DHW temp T5s", "DHW tank temp", False,
        "Domestic hot water tank temperature setpoint. Typically 40-60C. "
        "Only relevant when DHW function is enabled."),

    5: ("Function setting", "Bit field", True,
        "Bit0: Refrigerant leak detection, Bit4: Disinfection timer, "
        "Bit5: Holiday away (RO), Bit6: Silent mode on/off, Bit7: Silent level (0=L1,1=L2), "
        "Bit8: Holiday home (RO), Bit10: ECO mode, Bit11: DHW circ pump, "
        "Bit12: Climate curve Zone1, Bit13: Climate curve Zone2, Bit14: C2 fault restore."),

    6: ("Temp curve selection", "Zone1 (low 8), Zone2 (high 8)", False,
        "Weather compensation curve selection (1-9) for each zone. "
        "Low byte = Zone1 curve, High byte = Zone2 curve. "
        "Prefer using registers 18-19 for individual zone control."),

    7: ("Forced DHW", "0=Invalid, 1=On, 2=Off", False,
        "Force DHW heating on or off regardless of schedule/thermostat. "
        "0=Normal operation, 1=Force ON, 2=Force OFF."),

    8: ("Forced TBH", "0=Invalid, 1=On, 2=Off", False,
        "Force Tank Booster Heater (electric heater in DHW tank). "
        "0=Normal, 1=Force ON, 2=Force OFF. Cannot run with IBH simultaneously."),

    9: ("Forced IBH", "0=Invalid, 1=On, 2=Off", False,
        "Force Inline Booster Heater (electric heater in water circuit). "
        "0=Normal, 1=Force ON, 2=Force OFF. IBH1 and IBH2 can run together."),

    10: ("Special function", "Bit field", False,
        "Bit1: Third-party SG1 signal (smart grid), "
        "Bit2: Third-party SG2/EVU signal (utility control). "
        "Used for demand response and electricity pricing signals."),

    11: ("T1s Zone 1", "Water temp Zone 1", True,
        "Zone 1 water temperature setpoint in C. Recommended register for "
        "setting Zone 1 target temperature instead of packed register 2."),

    12: ("T1s2 Zone 2", "Water temp Zone 2", False,
        "Zone 2 water temperature setpoint in C. Only used when dual-zone "
        "system is configured."),

    13: ("t_antilock", "SV antilock time, 0-60s", False,
        "Solenoid valve (SV1, SV4) anti-lock action time in seconds. "
        "Prevents valves from seizing due to inactivity."),

    14: ("Power Zone 2", "0=off, 1=on", False,
        "Zone 2 water flow temperature control power switch. "
        "Independent on/off control for Zone 2 heating/cooling."),

    15: ("Power DHW", "0=off, 1=on", False,
        "Domestic hot water function power switch. "
        "Enables/disables DHW tank heating."),

    16: ("Power Zone 1", "0=off, 1=on", True,
        "Zone 1 water flow temperature control power switch. "
        "Main on/off control for Zone 1 heating/cooling. "
        "This is the primary power control for single-zone systems."),

    17: ("Power Zone 1/2 room", "Room temp control, 0=off, 1=on", False,
        "Room temperature control mode power switch for both zones. "
        "When enabled, uses room thermostat (Ta) instead of water temp (T1s)."),

    18: ("Temp curve Zone 1", "Curves 1-9", False,
        "Weather compensation curve selection for Zone 1 (values 1-9). "
        "Each curve defines water temp vs outdoor temp relationship. "
        "Curve 9 is typically custom/user-defined."),

    19: ("Temp curve Zone 2", "Curves 1-9", False,
        "Weather compensation curve selection for Zone 2 (values 1-9). "
        "Only used when dual-zone system is configured."),

    20: ("Silent mode level", "0=Level1, 1=Level2, 2=Boost", True,
        "Noise reduction mode. 0=Silent Level 1 (moderate), "
        "1=Silent Level 2 (maximum noise reduction, reduced capacity), "
        "2=Boost mode (maximum capacity, only on specific units)."),

    21: ("Function inquiry", "Bit field", True,
        "Read-only status bits. Bit4: Disinfection status (0=off, 1=running). "
        "Used to query current function states."),

    22: ("Reserved/Unknown", "", False,
        "Reserved register. Purpose unknown, typically reads 0."),

    # ==========================================================================
    # OPERATING PARAMETERS (100-199) - Read Only
    # ==========================================================================

    100: ("Compressor frequency", "Hz", True,
        "Current compressor operating frequency in Hz. 0 = compressor off. "
        "Higher frequency = more heating/cooling capacity but more power consumption."),

    101: ("Operating mode", "0=off, 2=cooling, 3=heating", True,
        "Current operating mode (not setpoint). 0=Off/Standby, "
        "2=Cooling active, 3=Heating active. Compare with reg 199 for detailed mode."),

    102: ("Fan speed", "r/min", True,
        "Outdoor unit fan motor speed in RPM. Varies with load and ambient conditions."),

    103: ("EXV1 openness", "P", True,
        "Electronic expansion valve 1 opening in pulses (P). "
        "Controls refrigerant flow. Higher = more flow."),

    104: ("Tw_in", "Water inlet temp", True,
        "Plate heat exchanger water inlet temperature. "
        "This is the return water temperature from the heating system."),

    105: ("Tw_out", "Water outlet temp", True,
        "Plate heat exchanger water outlet temperature. "
        "This is the supply water temperature to the heating system."),

    106: ("T3", "Condenser temp", True,
        "Condenser/heat exchanger refrigerant temperature. "
        "65535 (0xFFFF) = sensor not available or fault."),

    107: ("T4", "Outdoor ambient temp", True,
        "Outdoor ambient air temperature. Used for weather compensation "
        "and defrost control. Critical for COP optimization."),

    108: ("Tp", "Discharge temp", True,
        "Compressor discharge (hot gas) temperature. High values trigger "
        "protection. Typically 50-90C during operation."),

    109: ("Th", "Suction temp", True,
        "Compressor suction temperature. Used for superheat calculation. "
        "Low values may indicate liquid refrigerant (dangerous)."),

    110: ("T1", "Total outlet water temp", True,
        "Final outlet water temperature after mixing (if applicable). "
        "In single-zone systems, typically equals Tw_out."),

    111: ("Tw2", "Zone 2 water temp", False,
        "Zone 2 water circuit temperature. Returns 25 if Zone 2 not configured "
        "or sensor not installed."),

    112: ("T2", "Refrigerant liquid side temp", True,
        "Refrigerant liquid line temperature (before expansion valve). "
        "Used for subcooling calculation."),

    113: ("T2B", "Refrigerant gas side temp", True,
        "Refrigerant gas line temperature (suction line). "
        "Used for superheat calculation together with Th."),

    114: ("Ta", "Room temp", False,
        "Room air temperature from wired controller or external sensor. "
        "Returns 25 if no room sensor connected."),

    115: ("T5", "DHW tank temp", False,
        "Domestic hot water tank temperature. Returns 25 if no DHW tank "
        "or sensor not installed."),

    116: ("P1", "High pressure, kPa", True,
        "High-side refrigerant pressure in kPa. Normal range varies by refrigerant "
        "and conditions. High values trigger safety cutoff (typically >4000 kPa)."),

    117: ("P2", "Low pressure, kPa", True,
        "Low-side refrigerant pressure in kPa. Very low values indicate "
        "refrigerant leak or restriction. Used for defrost detection."),

    118: ("ODU current", "A (x0.1)", True,
        "Outdoor unit total current consumption. Value is actual current x10, "
        "so divide by 10 for Amps. Example: 30 = 3.0A."),

    119: ("ODU voltage", "V", True,
        "Outdoor unit supply voltage in Volts. Should be stable 220-240V (EU). "
        "Low voltage can cause compressor issues."),

    120: ("Tbt1", "Buffer tank top temp", False,
        "Buffer tank top temperature (if installed). Returns 255 if not installed. "
        "Used for thermal storage systems."),

    121: ("Tbt2", "Buffer tank bottom temp", False,
        "Buffer tank bottom temperature (if installed). Returns 255 if not installed."),

    122: ("Compressor time", "hours", True,
        "Total compressor operating hours. Useful for maintenance scheduling "
        "and warranty tracking."),

    123: ("Unit capacity", "kW", True,
        "Nominal unit heating/cooling capacity in kW. Example: 10 = 10kW unit."),

    124: ("Current error", "Error code", True,
        "Current active error code. 0 = no error. See error code table: "
        "E0(1)=Water flow, E1(2)=Phase, E2(3)=Comm, E8(9)=Flow fault, "
        "P0(20)=Low press, P1(21)=High press, P4(24)=High discharge temp."),

    125: ("Reserved", "", False, "Reserved for future use."),
    126: ("Reserved", "", False, "Reserved for future use."),
    127: ("Reserved", "", False, "Reserved for future use."),

    128: ("Status bit 1", "Bit field", True,
        "Bit1: Defrosting, Bit2: Anti-freeze active, Bit3: Oil return, "
        "Bit4: Remote on/off valid, Bit6: HT room thermostat, Bit7: CL room thermostat, "
        "Bit8: Solar thermal signal, Bit9: DHW anti-freeze, Bit10: SG status, Bit11: EVU status."),

    129: ("Load output", "Bit field", True,
        "Active outputs status. Bit0: IBH1, Bit1: IBH2, Bit2: TBH, Bit3: Pump_i, "
        "Bit4: SV1, Bit5: SV2, Bit6: Pump_o, Bit7: Pump_d, Bit8: Pump_c, "
        "Bit9: SV3, Bit10: Crankcase heater, Bit11: Pump_s, Bit12: Alarm, Bit14: AHS."),

    130: ("IDU software version", "1-99", True,
        "Indoor/hydraulic unit controller software version. E.g., 19 = version 19."),

    131: ("HMI software version", "Reserved", True,
        "Wired controller (HMI) software version. May show same as IDU version."),

    132: ("Unit target frequency", "Hz", True,
        "Target compressor frequency requested by controller. "
        "May differ from actual (reg 100) during ramp-up/down."),

    133: ("DC bus current", "A (x10)", True,
        "Inverter DC bus current. Value is actual x10, divide by 10 for Amps. "
        "Example: 40 = 4.0A."),

    134: ("DC bus voltage", "V (/10)", True,
        "Inverter DC bus voltage. Value is actual /10, multiply by 10 for Volts. "
        "Example: 37 = 370V DC (after rectification)."),

    135: ("TF", "PCB module temp", True,
        "Power module / PCB temperature. High values indicate cooling issues "
        "or high ambient temperature in outdoor unit."),

    136: ("Temp curve T1s calc 1", "calculated", False,
        "Calculated target water temp from weather curve for Zone 1. "
        "255 = curve not active or calculation not available."),

    137: ("Temp curve T1s calc 2", "calculated", False,
        "Calculated target water temp from weather curve for Zone 2. "
        "255 = curve not active or calculation not available."),

    138: ("Water flow", "m3/h (x0.01)", True,
        "Water flow rate through heat exchanger. Value x0.01 = m3/h. "
        "Example: 106 = 1.06 m3/h. Low flow triggers E8 error."),

    139: ("ODU current limit", "Code", True,
        "Current limitation code/level active on outdoor unit. "
        "Indicates if power is being limited due to grid or settings."),

    140: ("Hydraulic module capacity", "kW (x0.01)", True,
        "Real-time thermal capacity of hydraulic module. Value x0.01 = kW. "
        "Example: 349 = 3.49 kW."),

    141: ("Tsolar", "Solar panel temp", False,
        "Solar thermal panel temperature (if solar kit installed). "
        "Returns 255 if not installed."),

    142: ("Slave unit status", "Bit field", False,
        "Status of slave units in cascade/parallel systems. "
        "0 if single unit installation."),

    143: ("Energy consumption high", "kWh (x0.01, high 16 bits)", True,
        "Cumulative electricity consumption, high 16 bits. "
        "Combine with reg 144: total = (143 * 65536 + 144) / 100 kWh."),

    144: ("Energy consumption low", "kWh (x0.01, low 16 bits)", True,
        "Cumulative electricity consumption, low 16 bits. "
        "This is the electrical energy input to the heat pump."),

    145: ("Power output high", "kWh (x0.01)", True,
        "Cumulative thermal energy output, high 16 bits. "
        "Combine with reg 146: total = (145 * 65536 + 146) / 100 kWh."),

    146: ("Power output low", "kWh (x0.01)", True,
        "Cumulative thermal energy output, low 16 bits. "
        "This is the heat delivered to the water circuit."),

    147: ("Reserved", "", False, "Reserved for future use."),

    148: ("Real-time heating capacity", "kW (x0.01)", True,
        "Current heating capacity being delivered. Value x0.01 = kW. "
        "Calculated from water flow and delta-T."),

    149: ("Real-time renewable heating", "kW (x0.01)", True,
        "Current renewable (ambient) energy contribution. Value x0.01 = kW. "
        "This is the 'free' energy extracted from outdoor air."),

    150: ("Real-time heating power", "kW (x0.01)", True,
        "Current electrical power consumption for heating. Value x0.01 = kW. "
        "COP = reg148 / reg150."),

    151: ("Real-time heating COP", "x0.01", True,
        "Current coefficient of performance. Value x0.01 = actual COP. "
        "Example: 414 = COP 4.14. Higher is better, typically 2.5-5.0."),

    152: ("Cum system heating high", "kWh (x0.01)", True,
        "Cumulative system heating energy, high 16 bits."),

    153: ("Cum system heating low", "kWh (x0.01)", True,
        "Cumulative system heating energy, low 16 bits."),

    154: ("Cum renewable heating high", "kWh (x0.01)", True,
        "Cumulative renewable heating energy, high 16 bits."),

    155: ("Cum renewable heating low", "kWh (x0.01)", True,
        "Cumulative renewable heating energy, low 16 bits."),

    156: ("Cum system power high", "kWh (x0.01)", True,
        "Cumulative system power consumption, high 16 bits."),

    157: ("Cum system power low", "kWh (x0.01)", True,
        "Cumulative system power consumption, low 16 bits."),

    158: ("Cum heating energy high", "kWh (x0.01)", True,
        "Cumulative heating mode energy output, high 16 bits."),

    159: ("Cum heating energy low", "kWh (x0.01)", True,
        "Cumulative heating mode energy output, low 16 bits."),

    160: ("Cum renewable energy high", "kWh (x0.01)", True,
        "Cumulative renewable energy contribution, high 16 bits."),

    161: ("Cum renewable energy low", "kWh (x0.01)", True,
        "Cumulative renewable energy contribution, low 16 bits."),

    162: ("Cum heating power high", "kWh (x0.01)", True,
        "Cumulative heating mode power consumption, high 16 bits."),

    163: ("Cum heating power low", "kWh (x0.01)", True,
        "Cumulative heating mode power consumption, low 16 bits."),

    164: ("Cum heating efficiency", "x0.01", True,
        "Cumulative/seasonal heating efficiency (SCOP). Value x0.01. "
        "Example: 362 = SCOP 3.62 over lifetime."),

    165: ("Cum cooling energy high", "kWh (x0.01)", False,
        "Cumulative cooling mode energy output, high 16 bits."),

    166: ("Cum cooling energy low", "kWh (x0.01)", False,
        "Cumulative cooling mode energy output, low 16 bits."),

    167: ("Cum renewable cooling high", "kWh (x0.01)", False,
        "Cumulative cooling renewable energy, high 16 bits."),

    168: ("Cum renewable cooling low", "kWh (x0.01)", False,
        "Cumulative cooling renewable energy, low 16 bits."),

    169: ("Cum cooling power high", "kWh (x0.01)", False,
        "Cumulative cooling power consumption, high 16 bits."),

    170: ("Cum cooling power low", "kWh (x0.01)", False,
        "Cumulative cooling power consumption, low 16 bits."),

    171: ("Cum cooling efficiency", "x0.01", False,
        "Cumulative cooling efficiency (SEER). Value x0.01."),

    172: ("Cum DHW energy high", "kWh (x0.01)", False,
        "Cumulative DHW energy output, high 16 bits."),

    173: ("Cum DHW energy low", "kWh (x0.01)", False,
        "Cumulative DHW energy output, low 16 bits."),

    174: ("Cum DHW renewable high", "kWh (x0.01)", False,
        "Cumulative DHW renewable energy, high 16 bits."),

    175: ("Cum DHW renewable low", "kWh (x0.01)", False,
        "Cumulative DHW renewable energy, low 16 bits."),

    176: ("Cum DHW power high", "kWh (x0.01)", False,
        "Cumulative DHW power consumption, high 16 bits."),

    177: ("Cum DHW power low", "kWh (x0.01)", False,
        "Cumulative DHW power consumption, low 16 bits."),

    178: ("Cum DHW COP", "x0.01", False,
        "Cumulative DHW efficiency. Value x0.01."),

    179: ("Real-time cooling capacity", "kW (x0.01)", False,
        "Current cooling capacity. Only valid in cooling mode."),

    180: ("Real-time renewable cooling", "kW (x0.01)", False,
        "Current cooling renewable contribution."),

    181: ("Real-time cooling power", "kW (x0.01)", False,
        "Current cooling power consumption."),

    182: ("Real-time cooling EER", "x0.01", False,
        "Current cooling energy efficiency ratio."),

    183: ("Real-time DHW capacity", "kW (x0.01)", False,
        "Current DHW heating capacity."),

    184: ("Real-time DHW renewable", "kW (x0.01)", False,
        "Current DHW renewable contribution."),

    185: ("Real-time DHW power", "kW (x0.01)", False,
        "Current DHW power consumption."),

    186: ("Real-time DHW COP", "x0.01", False,
        "Current DHW coefficient of performance."),

    187: ("Modbus protocol version", "e.g. 46=V4.6", True,
        "Modbus protocol version. Example: 46 = Version 4.6. "
        "Newer versions may have additional registers."),

    188: ("Error code 2", "See table 2", True,
        "Secondary error code register. 0=no error. "
        "Used for additional error information."),

    189: ("Status bit 2", "Bit field", True,
        "Bit7: Power type (0=1-phase, 1=3-phase), "
        "Bit8: Temp resolution (0=1C, 1=0.1C). "
        "Check bit8 to determine temperature scaling."),

    190: ("Hydraulic module sub-model", "0-10", True,
        "Hydraulic module type: 0=R32-P, 1=Aqua, 2=C-R32-P, 3=R290-A, "
        "4=R290-N, 5=C-R290-A, 6=C-R290-N, 7=R32-A, 8=C-R32-A, 9=R290-M, 10=R32-H."),

    191: ("TL", "ODU refrigerant pipe temp", True,
        "Outdoor unit refrigerant pipe temperature. "
        "65535 = sensor not available."),

    192: ("Pump_i PWM", "x10", True,
        "Internal circulation pump PWM duty cycle. Value /10 = percentage. "
        "Example: 200 = 20.0% duty cycle."),

    193: ("T9i", "2nd PHE inlet temp (x10)", False,
        "Secondary plate heat exchanger inlet temp. Only for cascade systems."),

    194: ("T9o", "2nd PHE outlet temp (x10)", False,
        "Secondary plate heat exchanger outlet temp. Only for cascade systems."),

    195: ("EXV2 openness", "P", False,
        "Electronic expansion valve 2 opening (pulses). Only for dual-circuit systems."),

    196: ("EXV3 openness", "P", False,
        "Electronic expansion valve 3 opening (pulses). Only for specific models."),

    197: ("Fan2 speed", "r/min", False,
        "Second fan motor speed (RPM). Only for dual-fan outdoor units."),

    198: ("Status bit 3", "Bit field", True,
        "Bit3: Cooling active, Bit4: Heating active, Bit5: DHW active, "
        "Bit8: Energy metering enabled, Bit9: T1 enabled, Bit10: IBH enabled, "
        "Bit11: AHS mode (0=Heat only, 1=Heat+DHW), Bit14: AHS enabled, Bit15: TBH enabled."),

    199: ("Heat pump operation mode", "0=Off, 2=Cool, 3=Heat, 5=DHW", True,
        "Current heat pump operation mode. 0=Off/Standby, 2=Cooling, "
        "3=Heating, 5=DHW heating. More detailed than reg 101."),

    # ==========================================================================
    # PARAMETER SETTINGS (200-290) - Read/Write (209+ writable)
    # Note: Registers 200-208 are read-only, 209+ support write
    # ==========================================================================

    200: ("Reserved", "", False,
        "Reserved/unknown. May contain packed configuration data."),

    201: ("T1s cooling upper limit", "Zone1 (low 8), Zone2 (high 8)", False,
        "Maximum water temperature setpoint allowed for cooling mode. "
        "Low byte = Zone1 limit, High byte = Zone2 limit."),

    202: ("T1s cooling lower limit", "Zone1 (low 8), Zone2 (high 8)", False,
        "Minimum water temperature setpoint allowed for cooling mode. "
        "Low byte = Zone1 limit, High byte = Zone2 limit."),

    203: ("T1s heating upper limit", "Zone1 (low 8), Zone2 (high 8)", True,
        "Maximum water temperature setpoint allowed for heating mode. "
        "Low byte = Zone1 limit (e.g., 55C), High byte = Zone2 limit."),

    204: ("T1s heating lower limit", "Zone1 (low 8), Zone2 (high 8)", True,
        "Minimum water temperature setpoint allowed for heating mode. "
        "Low byte = Zone1 limit (e.g., 25C), High byte = Zone2 limit."),

    205: ("Tas upper limit", "x2", False,
        "Maximum room temperature setpoint. Value = actual x 2. "
        "Example: 60 = 30C max room setpoint."),

    206: ("Tas lower limit", "x2", False,
        "Minimum room temperature setpoint. Value = actual x 2. "
        "Example: 34 = 17C min room setpoint."),

    207: ("T5s upper limit", "DHW", False,
        "Maximum DHW tank temperature setpoint allowed."),

    208: ("T5s lower limit", "DHW", False,
        "Minimum DHW tank temperature setpoint allowed."),

    209: ("Pump_D running time", "5-120 min", False,
        "DHW circulation pump (Pump_D) running duration per cycle. "
        "Range: 5-120 minutes, 1 minute steps. Default: 5 min."),

    210: ("Parameter setting 1", "Bit field", True,
        "Bit0: DHW priority, Bit1: Room thermostat dual zone, Bit2: RT mode set, "
        "Bit3: RT function enable, Bit4: Room temp function, Bit5: Pump_i silent, "
        "Bit7: Heating enable, Bit9: Cooling enable, Bit10: Pump_d disinfect, "
        "Bit11: DHW priority func, Bit12: Pump_d func, Bit13: Disinfect func, Bit15: DHW func."),

    211: ("Parameter setting 2", "Bit field", True,
        "Bit1: Tbt function, Bit3: Double zone, Bit7: Smart grid, "
        "Bit8: M1M2 setting (0=Remote,1=TBH), Bit9: Solar kit, Bit10: Solar control, "
        "Bit11: F-pipe length (1=>=10m), Bit12: Tbt1 func, Bit13: T1T2 setting, "
        "Bit14: M1M2 AHS enable, Bit15: ACS status (RO)."),

    212: ("dT5_On", "DHW start differential", False,
        "Temperature differential to start DHW heating. "
        "DHW starts when T5 drops this many degrees below setpoint."),

    213: ("dT1S5", "DHW/Zone temp diff", False,
        "Temperature differential between DHW and zone setpoint."),

    214: ("Unknown 214", "", False,
        "Undocumented register. Typically reads small value (e.g., 5)."),

    215: ("T4DHWmax", "DHW outdoor max temp", False,
        "Maximum outdoor temperature for DHW operation. "
        "Above this temp, DHW heating is disabled."),

    216: ("T4DHWmin", "DHW outdoor min temp", False,
        "Minimum outdoor temperature for DHW heat pump operation. "
        "Below this, electric backup (TBH) may be needed. "
        "Negative values stored as 2's complement (65526 = -10C)."),

    217: ("t_TBH_delay", "TBH delay, min", False,
        "Delay time before Tank Booster Heater activates. "
        "Allows heat pump time to reach setpoint first."),

    218: ("dT5_TBH_off", "TBH off differential", False,
        "Temperature differential to turn off TBH. "
        "TBH stops when tank temp reaches setpoint minus this value."),

    219: ("T4_TBH_on", "TBH enable outdoor temp", False,
        "Outdoor temperature threshold to enable TBH. "
        "TBH can activate when outdoor temp drops below this."),

    220: ("T5s_DI", "Disinfection temp", False,
        "Legionella disinfection temperature setpoint (typically 60-65C). "
        "Tank is heated to this temp periodically to kill bacteria."),

    221: ("t_DI_max", "Disinfection max time, min", False,
        "Maximum time allowed for disinfection cycle. "
        "Cycle aborts if this time exceeded without reaching temp."),

    222: ("t_DI_hightemp", "High temp hold time, min", False,
        "Time to hold disinfection temperature once reached. "
        "Ensures bacteria are killed."),

    223: ("Unknown 223", "", False,
        "Undocumented register."),

    224: ("dT1SC", "Cooling curve delta", False,
        "Temperature differential/deadband for cooling weather curve."),

    225: ("dTSC", "Cooling setback", False,
        "Cooling mode temperature setback value."),

    226: ("T4cmax", "Cooling outdoor max", False,
        "Maximum outdoor temperature for cooling operation. "
        "Above this, unit may reduce capacity or stop."),

    227: ("T4cmin", "Cooling outdoor min", False,
        "Minimum outdoor temperature for cooling operation. "
        "Below this, cooling is disabled."),

    228: ("Unknown 228", "", False,
        "Undocumented register."),

    229: ("dT1SH", "Heating curve delta", True,
        "Temperature differential/deadband for heating weather curve. "
        "Affects how quickly system responds to temperature changes."),

    230: ("dTSH", "Heating setback", True,
        "Heating mode temperature setback value. "
        "Used for night setback or eco mode reduction."),

    231: ("T4hmax", "Heating outdoor max", True,
        "Maximum outdoor temperature for heating operation. "
        "Above this (e.g., 25C), heating is disabled (summer cutoff)."),

    232: ("T4hmin", "Heating outdoor min", True,
        "Minimum outdoor temperature for heat pump heating. "
        "Below this (e.g., -15C), backup heaters may be needed. "
        "Stored as 2's complement (65521 = -15C)."),

    233: ("T4_IBH_on", "IBH enable temp", False,
        "Outdoor temperature to enable Inline Booster Heater. "
        "IBH can activate when outdoor temp drops below this. "
        "Stored as 2's complement (65531 = -5C)."),

    234: ("dT1_IBH_on", "IBH delta", False,
        "Temperature differential to activate IBH. "
        "IBH starts if water temp is this far below setpoint."),

    235: ("t_IBH_delay", "IBH delay, min", False,
        "Delay time before IBH activates after conditions are met."),

    236: ("Unknown 236", "", False,
        "Undocumented register (gap in addressing)."),

    237: ("T4_AHS_on", "AHS enable temp", False,
        "Outdoor temperature to enable Auxiliary Heat Source. "
        "Stored as 2's complement (65531 = -5C)."),

    238: ("dT1_AHS_on", "AHS delta", False,
        "Temperature differential to activate AHS."),

    239: ("Unknown 239", "", False,
        "Undocumented register (gap in addressing)."),

    240: ("t_AHS_delay", "AHS delay, min", False,
        "Delay time before AHS activates after conditions are met."),

    241: ("t_DHWHP_max", "DHW HP max time, min", False,
        "Maximum continuous DHW heat pump operation time. "
        "After this, DHW heating pauses to allow space heating."),

    242: ("t_DHWHP_restrict", "DHW HP restrict time, min", False,
        "Minimum pause between DHW heating cycles."),

    243: ("T4autocmin", "Auto cooling min outdoor", False,
        "Minimum outdoor temperature for auto mode to switch to cooling."),

    244: ("T4autohmax", "Auto heating max outdoor", False,
        "Maximum outdoor temperature for auto mode to stay in heating."),

    245: ("T1S_H.A_H", "Holiday heating T1", False,
        "Water temperature setpoint during holiday/away mode for heating."),

    246: ("T5S_H.A_DHW", "Holiday DHW T5", False,
        "DHW temperature setpoint during holiday/away mode."),

    247: ("Unknown 247", "", False, "Undocumented register."),
    248: ("Unknown 248", "", False, "Undocumented register."),
    249: ("Unknown 249", "", False, "Undocumented register."),

    250: ("IBH1 power", "x100 W", False,
        "Inline Booster Heater 1 power rating. Value x 100 = Watts. "
        "Example: 20 = 2000W = 2kW heater."),

    251: ("IBH2 power", "x100 W", False,
        "Inline Booster Heater 2 power rating. Value x 100 = Watts."),

    252: ("TBH power", "x100 W", False,
        "Tank Booster Heater power rating. Value x 100 = Watts."),

    253: ("Unknown 253", "", False, "Undocumented register."),
    254: ("Unknown 254", "", False, "Undocumented register."),

    255: ("t_DRYUP", "Floor dry up days", False,
        "Floor drying function - ramp up phase duration in days."),

    256: ("t_HIGHPEAK", "Floor dry peak days", False,
        "Floor drying function - peak temperature phase duration in days."),

    257: ("t_DRYDOWN", "Floor dry down days", False,
        "Floor drying function - ramp down phase duration in days."),

    258: ("t_DRYPEAK", "Floor dry peak temp", False,
        "Floor drying function - peak water temperature."),

    259: ("t_ARSTH", "Anti-freeze reset time, hrs", False,
        "Hours after anti-freeze event before normal operation resumes."),

    260: ("T1S preheating", "Floor preheat temp", False,
        "Water temperature for floor preheating function."),

    261: ("T1SetC1", "Custom curve cooling T1 point 1", False,
        "Custom cooling curve - water temp at outdoor temp T4C1."),

    262: ("T1SetC2", "Custom curve cooling T1 point 2", False,
        "Custom cooling curve - water temp at outdoor temp T4C2."),

    263: ("T4C1", "Custom curve cooling T4 point 1", False,
        "Custom cooling curve - outdoor temp for point 1 (higher outdoor)."),

    264: ("T4C2", "Custom curve cooling T4 point 2", False,
        "Custom cooling curve - outdoor temp for point 2 (lower outdoor)."),

    265: ("T1SetH1", "Custom curve heating T1 point 1", True,
        "Custom heating curve - water temp at outdoor temp T4H1. "
        "Higher outdoor temp = lower water temp needed."),

    266: ("T1SetH2", "Custom curve heating T1 point 2", True,
        "Custom heating curve - water temp at outdoor temp T4H2. "
        "Lower outdoor temp = higher water temp needed."),

    267: ("T4H1", "Custom curve heating T4 point 1", True,
        "Custom heating curve - outdoor temp for point 1 (colder). "
        "Stored as 2's complement (65531 = -5C)."),

    268: ("T4H2", "Custom curve heating T4 point 2", True,
        "Custom heating curve - outdoor temp for point 2 (warmer). "
        "Example: T4H1=-5C/T1=35C, T4H2=7C/T1=28C defines curve slope."),

    269: ("Power input limitation", "Level", True,
        "Power/capacity limitation level. Limits compressor frequency "
        "and thus maximum power consumption and capacity."),

    270: ("T4_Fresh", "Hi=Cooling, Lo=Heating", False,
        "Fresh air temperature thresholds. High byte = cooling, Low byte = heating."),

    271: ("t_Delay pump", "pump delay", True,
        "Circulation pump delay time after compressor stops."),

    272: ("Emission type", "Zone H/C emission type", True,
        "Heat emitter types per zone. Bits 0-3: Zone1 H, Bits 4-7: Zone2 H, "
        "Bits 8-11: Zone1 C, Bits 12-15: Zone2 C. "
        "Values: 0=FLH (underfloor), 1=FCU (fan coil), 2=RAD (radiator)."),

    273: ("Deltatsol / Solar function", "Hi=deltatsol, Lo=solar func", False,
        "Solar thermal settings. Low byte: 0=No solar, 1=Solar+HP, 2=Solar only. "
        "High byte: Solar differential temperature."),

    274: ("AHS_PDC", "Bit field", False,
        "Auxiliary heat source and power demand control settings."),

    275: ("GAS-COST", "x100", False,
        "Gas cost per unit for hybrid system efficiency calculation. "
        "Value / 100 = cost."),

    276: ("ELE-COST", "x100", False,
        "Electricity cost per unit for efficiency calculation. "
        "Value / 100 = cost."),

    277: ("SETHEATER", "Hi=max, Lo=min", False,
        "External heater temperature setpoints. High byte = max, Low byte = min."),

    278: ("SIGHEATER", "Hi=max, Lo=min, V", False,
        "External heater signal voltage range in Volts."),

    279: ("t2_Antilock SV run", "s", False,
        "Solenoid valve anti-lock run time in seconds."),

    280: ("Unknown 280", "", False, "Undocumented - may mirror custom curve."),
    281: ("Unknown 281", "", False, "Undocumented - may mirror custom curve."),
    282: ("Unknown 282", "", False, "Undocumented - may mirror custom curve."),
    283: ("Unknown 283", "", False, "Undocumented - may mirror custom curve."),
    284: ("Unknown 284", "", False, "Undocumented - may mirror custom curve."),
    285: ("Unknown 285", "", False, "Undocumented - may mirror custom curve."),
    286: ("Unknown 286", "", False, "Undocumented - may mirror custom curve."),
    287: ("Unknown 287", "", False, "Undocumented - may mirror custom curve."),

    288: ("Ta_adj", "Room temp adjustment", False,
        "Room temperature sensor calibration offset."),

    289: ("TBHEnFunc", "TBH enable", False,
        "Tank Booster Heater enable function. 0=Disabled, 1=Enabled."),

    290: ("High price compressor limit", "x10, kW", False,
        "Compressor power limit during high electricity price periods. "
        "Value / 10 = kW limit. For smart grid integration."),
}


def format_value(addr, val):
    """Format value based on known scaling"""
    if addr in [118]:  # ODU current x0.1
        return f"{val} ({val * 0.1:.1f} A)"
    elif addr in [133]:  # DC bus current x10
        return f"{val} ({val * 0.1:.1f} A)"
    elif addr in [134]:  # DC bus voltage /10
        return f"{val} ({val * 0.1:.1f} V)"
    elif addr in [138]:  # Water flow x0.01
        return f"{val} ({val * 0.01:.2f} m3/h)"
    elif addr in [140, 148, 149, 150]:  # kW x0.01
        return f"{val} ({val * 0.01:.2f} kW)"
    elif addr in [143, 144, 145, 146, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163]:  # kWh x0.01
        return f"{val} ({val * 0.01:.2f} kWh)"
    elif addr in [151, 164]:  # COP x0.01
        return f"{val} ({val * 0.01:.2f})"
    elif addr in [192]:  # PWM x10
        return f"{val} ({val * 0.1:.1f}%)"
    return str(val)


def scan_registers():
    client = ModbusTcpClient('192.168.178.121', port=8899, timeout=5)
    if not client.connect():
        print('Connection failed')
        return

    print('Connected! Scanning registers...\n')
    print(f'{"Addr":<6} {"Name":<30} {"Value":<25} {"Description"}')
    print('-' * 100)

    all_values = {}

    # Bulk read: control (0-22) and operating (100-199) registers
    for start, count in [(0, 23), (100, 100)]:
        try:
            result = client.read_holding_registers(address=start, count=count, device_id=2)
            if not result.isError():
                for i, val in enumerate(result.registers):
                    addr = start + i
                    all_values[addr] = val
        except Exception as e:
            pass

    # Parameter registers (200-290) - bulk read fails, must read one-by-one
    param_addrs = list(range(200, 291))
    for addr in param_addrs:
        try:
            result = client.read_holding_registers(address=addr, count=1, device_id=2)
            if not result.isError():
                all_values[addr] = result.registers[0]
        except Exception as e:
            pass

    # Print all scanned registers (known and unknown)
    for addr in sorted(all_values.keys()):
        val = all_values[addr]
        if addr in REGISTERS:
            name, desc, used, detail = REGISTERS[addr]
            formatted = format_value(addr, val)
            marker = "  " if used else "* "
            print(f'{marker}{addr:<5} {name:<30} {formatted:<25} {desc}')
            if detail:
                # Wrap detailed description to ~90 chars per line
                indent = "        "
                words = detail.split()
                line = indent
                for word in words:
                    if len(line) + len(word) + 1 > 95:
                        print(line)
                        line = indent + word
                    else:
                        line = line + " " + word if line != indent else indent + word
                if line != indent:
                    print(line)
        elif val != 0 and val != 0x7FFF and val != 0x7F and val != 0xFFFF and val != 255:
            # Unknown register with non-zero value
            print(f'? {addr:<5} {"(unknown)":<30} {val:<25}')


    # Print 32-bit combined values
    print('\n' + '-' * 100)
    print('32-bit combined values (high<<16 + low) / 100:\n')
    pairs = [
        (143, 144, "Energy consumption"),
        (145, 146, "Power output"),
        (152, 153, "Cum system heating"),
        (154, 155, "Cum renewable heating"),
        (156, 157, "Cum system power"),
        (158, 159, "Cum heating energy"),
        (160, 161, "Cum renewable energy"),
        (162, 163, "Cum heating power"),
    ]
    for hi, lo, name in pairs:
        if hi in all_values and lo in all_values:
            combined = (all_values[hi] * 65536 + all_values[lo]) / 100
            print(f'{hi}/{lo:<4} {name:<30} {combined:.2f} kWh')

    client.close()


if __name__ == '__main__':
    import sys

    # Write to both console and file
    output_file = 'register_dump.txt'

    class Tee:
        def __init__(self, *files):
            self.files = files
        def write(self, text):
            for f in self.files:
                f.write(text)
        def flush(self):
            for f in self.files:
                f.flush()

    with open(output_file, 'w', encoding='utf-8') as f:
        old_stdout = sys.stdout
        sys.stdout = Tee(sys.stdout, f)
        scan_registers()
        sys.stdout = old_stdout

    print(f'\nOutput saved to {output_file}')
