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
#   - Negative temperatures use 16-bit two's complement (e.g., 65531 = -5°C)
#   - 32-bit values split across two registers (high/low), scaled by 0.01
#   - 65535 (0xFFFF) and 255 (0xFF) typically mean "not available" or "no sensor"
#

# Known registers from Midea Modbus mapping table
# Third element: True = used in our setup, False = not used (Zone2, DHW, Cooling, etc.)
REGISTERS = {
    # Control registers (R/W)
    0: ("Power on/off", "Bit field", True),
    1: ("Mode setting", "1=Auto, 2=Cooling, 3=Heating", True),
    2: ("Set water temp T1s", "Zone1 (low 8), Zone2 (high 8)", True),
    3: ("Set air temp Tas", "Room temp control, °C", False),
    4: ("Set DHW temp T5s", "DHW tank temp, °C", False),
    5: ("Function setting", "Bit field", True),
    6: ("Temp curve selection", "Zone1 (low 8), Zone2 (high 8)", False),
    7: ("Forced DHW", "0=Invalid, 1=On, 2=Off", False),
    8: ("Forced TBH", "0=Invalid, 1=On, 2=Off", False),
    9: ("Forced IBH", "0=Invalid, 1=On, 2=Off", False),
    10: ("Special function", "Bit field", False),
    11: ("T1s Zone 1", "Water temp Zone 1, °C", True),
    12: ("T1s2 Zone 2", "Water temp Zone 2, °C", False),
    13: ("t_antilock", "SV antilock time, 0-60s", False),
    14: ("Power Zone 2", "0=off, 1=on", False),
    15: ("Power DHW", "0=off, 1=on", False),
    16: ("Power Zone 1", "0=off, 1=on", True),
    17: ("Power Zone 1/2 room", "Room temp control, 0=off, 1=on", False),
    18: ("Temp curve Zone 1", "Curves 1-9", False),
    19: ("Temp curve Zone 2", "Curves 1-9", False),
    20: ("Silent mode level", "0=Level1, 1=Level2, 2=Boost", True),
    21: ("Function inquiry", "Bit field", True),
    22: ("Reserved/Unknown", "", False),

    # Operating parameters (R)
    100: ("Compressor frequency", "Hz", True),
    101: ("Operating mode", "0=off, 2=cooling, 3=heating", True),
    102: ("Fan speed", "r/min", True),
    103: ("EXV1 openness", "P", True),
    104: ("Tw_in", "Water inlet temp, °C", True),
    105: ("Tw_out", "Water outlet temp, °C", True),
    106: ("T3", "Condenser temp, °C", True),
    107: ("T4", "Outdoor ambient temp, °C", True),
    108: ("Tp", "Discharge temp, °C", True),
    109: ("Th", "Suction temp, °C", True),
    110: ("T1", "Total outlet water temp, °C", True),
    111: ("Tw2", "Zone 2 water temp, °C", False),
    112: ("T2", "Refrigerant liquid side temp, °C", True),
    113: ("T2B", "Refrigerant gas side temp, °C", True),
    114: ("Ta", "Room temp, °C", False),
    115: ("T5", "DHW tank temp, °C", False),
    116: ("P1", "High pressure, kPa", True),
    117: ("P2", "Low pressure, kPa", True),
    118: ("ODU current", "A (x0.1)", True),
    119: ("ODU voltage", "V", True),
    120: ("Tbt1", "Buffer tank top temp, °C", False),
    121: ("Tbt2", "Buffer tank bottom temp, °C", False),
    122: ("Compressor time", "hours", True),
    123: ("Unit capacity", "kW", True),
    124: ("Current error", "Error code", True),
    125: ("Reserved", "", False),
    126: ("Reserved", "", False),
    127: ("Reserved", "", False),
    128: ("Status bit 1", "Bit field", True),
    129: ("Load output", "Bit field", True),
    130: ("IDU software version", "1-99", True),
    131: ("HMI software version", "Reserved", True),
    132: ("Unit target frequency", "Hz", True),
    133: ("DC bus current", "A (x10)", True),
    134: ("DC bus voltage", "V (/10)", True),
    135: ("TF", "PCB module temp, °C", True),
    136: ("Temp curve T1s calc 1", "°C", False),
    137: ("Temp curve T1s calc 2", "°C", False),
    138: ("Water flow", "m³/h (x0.01)", True),
    139: ("ODU current limit", "Code", True),
    140: ("Hydraulic module capacity", "kW (x0.01)", True),
    141: ("Tsolar", "Solar panel temp, °C", False),
    142: ("Slave unit status", "Bit field", False),
    143: ("Energy consumption high", "kWh (x0.01, high 16 bits)", True),
    144: ("Energy consumption low", "kWh (x0.01, low 16 bits)", True),
    145: ("Power output high", "kWh (x0.01)", True),
    146: ("Power output low", "kWh (x0.01)", True),
    147: ("Reserved", "", False),
    148: ("Real-time heating capacity", "kW (x0.01)", True),
    149: ("Real-time renewable heating", "kW (x0.01)", True),
    150: ("Real-time heating power", "kW (x0.01)", True),
    151: ("Real-time heating COP", "x0.01", True),
    152: ("Cum system heating high", "kWh (x0.01)", True),
    153: ("Cum system heating low", "kWh (x0.01)", True),
    154: ("Cum renewable heating high", "kWh (x0.01)", True),
    155: ("Cum renewable heating low", "kWh (x0.01)", True),
    156: ("Cum system power high", "kWh (x0.01)", True),
    157: ("Cum system power low", "kWh (x0.01)", True),
    158: ("Cum heating energy high", "kWh (x0.01)", True),
    159: ("Cum heating energy low", "kWh (x0.01)", True),
    160: ("Cum renewable energy high", "kWh (x0.01)", True),
    161: ("Cum renewable energy low", "kWh (x0.01)", True),
    162: ("Cum heating power high", "kWh (x0.01)", True),
    163: ("Cum heating power low", "kWh (x0.01)", True),
    164: ("Cum heating efficiency", "x0.01", True),
    165: ("Cum cooling energy high", "kWh (x0.01)", False),
    166: ("Cum cooling energy low", "kWh (x0.01)", False),
    167: ("Cum renewable cooling high", "kWh (x0.01)", False),
    168: ("Cum renewable cooling low", "kWh (x0.01)", False),
    169: ("Cum cooling power high", "kWh (x0.01)", False),
    170: ("Cum cooling power low", "kWh (x0.01)", False),
    171: ("Cum cooling efficiency", "x0.01", False),
    172: ("Cum DHW energy high", "kWh (x0.01)", False),
    173: ("Cum DHW energy low", "kWh (x0.01)", False),
    174: ("Cum DHW renewable high", "kWh (x0.01)", False),
    175: ("Cum DHW renewable low", "kWh (x0.01)", False),
    176: ("Cum DHW power high", "kWh (x0.01)", False),
    177: ("Cum DHW power low", "kWh (x0.01)", False),
    178: ("Cum DHW COP", "x0.01", False),
    179: ("Real-time cooling capacity", "kW (x0.01)", False),
    180: ("Real-time renewable cooling", "kW (x0.01)", False),
    181: ("Real-time cooling power", "kW (x0.01)", False),
    182: ("Real-time cooling EER", "x0.01", False),
    183: ("Real-time DHW capacity", "kW (x0.01)", False),
    184: ("Real-time DHW renewable", "kW (x0.01)", False),
    185: ("Real-time DHW power", "kW (x0.01)", False),
    186: ("Real-time DHW COP", "x0.01", False),
    187: ("Modbus protocol version", "e.g. 46=V4.6", True),
    188: ("Error code 2", "See table 2", True),
    189: ("Status bit 2", "Bit field", True),
    190: ("Hydraulic module sub-model", "0-10", True),
    191: ("TL", "ODU refrigerant pipe temp, °C", True),
    192: ("Pump_i PWM", "x10", True),
    193: ("T9i", "2nd PHE inlet temp (x10), °C", False),
    194: ("T9o", "2nd PHE outlet temp (x10), °C", False),
    195: ("EXV2 openness", "P", False),
    196: ("EXV3 openness", "P", False),
    197: ("Fan2 speed", "r/min", False),
    198: ("Status bit 3", "Bit field", True),
    199: ("Heat pump operation mode", "0=Off, 2=Cool, 3=Heat, 5=DHW", True),

    # Parameter settings (R/W from 209+)
    200: ("Reserved", "", False),
    201: ("T1s cooling upper limit", "Zone1 (low 8), Zone2 (high 8), °C", False),
    202: ("T1s cooling lower limit", "Zone1 (low 8), Zone2 (high 8), °C", False),
    203: ("T1s heating upper limit", "Zone1 (low 8), Zone2 (high 8), °C", True),
    204: ("T1s heating lower limit", "Zone1 (low 8), Zone2 (high 8), °C", True),
    205: ("Tas upper limit", "x2, °C", False),
    206: ("Tas lower limit", "x2, °C", False),
    207: ("T5s upper limit", "DHW, °C", False),
    208: ("T5s lower limit", "DHW, °C", False),
    209: ("Pump_D running time", "5-120 min", False),
    210: ("Parameter setting 1", "Bit field", True),
    211: ("Parameter setting 2", "Bit field", True),
    212: ("dT5_On", "°C", False),
    213: ("dT1S5", "°C", False),
    215: ("T4DHWmax", "°C", False),
    216: ("T4DHWmin", "°C", False),
    217: ("t_TBH_delay", "min", False),
    218: ("dT5_TBH_off", "°C", False),
    219: ("T4_TBH_on", "°C", False),
    220: ("T5s_DI", "Disinfection temp, °C", False),
    221: ("t_DI_max", "Disinfection max time, min", False),
    222: ("t_DI_hightemp", "min", False),
    224: ("dT1SC", "Cooling delta, °C", False),
    225: ("dTSC", "°C", False),
    226: ("T4cmax", "Cooling outdoor max, °C", False),
    227: ("T4cmin", "Cooling outdoor min, °C", False),
    229: ("dT1SH", "Heating delta, °C", True),
    230: ("dTSH", "°C", True),
    231: ("T4hmax", "Heating outdoor max, °C", True),
    232: ("T4hmin", "Heating outdoor min, °C", True),
    233: ("T4_IBH_on", "IBH enable temp, °C", False),
    234: ("dT1_IBH_on", "IBH delta, °C", False),
    235: ("t_IBH_delay", "IBH delay, min", False),
    237: ("T4_AHS_on", "AHS enable temp, °C", False),
    238: ("dT1_AHS_on", "AHS delta, °C", False),
    240: ("t_AHS_delay", "AHS delay, min", False),
    241: ("t_DHWHP_max", "DHW HP max time, min", False),
    242: ("t_DHWHP_restrict", "DHW HP restrict time, min", False),
    243: ("T4autocmin", "Auto cooling min outdoor, °C", False),
    244: ("T4autohmax", "Auto heating max outdoor, °C", False),
    245: ("T1S_H.A_H", "Holiday heating T1, °C", False),
    246: ("T5S_H.A_DHW", "Holiday DHW T5, °C", False),
    250: ("IBH1 power", "x100 W", False),
    251: ("IBH2 power", "x100 W", False),
    252: ("TBH power", "x100 W", False),
    255: ("t_DRYUP", "Floor dry up days", False),
    256: ("t_HIGHPEAK", "Floor dry peak days", False),
    257: ("t_DRYDOWN", "Floor dry down days", False),
    258: ("t_DRYPEAK", "Floor dry peak temp, °C", False),
    259: ("t_ARSTH", "Anti-freeze reset time, hrs", False),
    260: ("T1S preheating", "Floor preheat temp, °C", False),
    261: ("T1SetC1", "Custom curve cooling T1, °C", False),
    262: ("T1SetC2", "Custom curve cooling T1, °C", False),
    263: ("T4C1", "Custom curve cooling T4, °C", False),
    264: ("T4C2", "Custom curve cooling T4, °C", False),
    265: ("T1SetH1", "Custom curve heating T1, °C", True),
    266: ("T1SetH2", "Custom curve heating T1, °C", True),
    267: ("T4H1", "Custom curve heating T4, °C", True),
    268: ("T4H2", "Custom curve heating T4, °C", True),
    269: ("Power input limitation", "Level", True),
    270: ("T4_Fresh", "Hi=Cooling, Lo=Heating, °C", False),
    271: ("t_Delay pump", "°C", True),
    272: ("Emission type", "Zone H/C emission type", True),
    273: ("Deltatsol / Solar function", "Hi=deltatsol, Lo=solar func", False),
    274: ("AHS_PDC", "Bit field", False),
    275: ("GAS-COST", "x100", False),
    276: ("ELE-COST", "x100", False),
    277: ("SETHEATER", "Hi=max, Lo=min, °C", False),
    278: ("SIGHEATER", "Hi=max, Lo=min, V", False),
    279: ("t2_Antilock SV run", "s", False),
    288: ("Ta_adj", "Room temp adjustment, °C", False),
    289: ("TBHEnFunc", "TBH enable, 0=disable, 1=enable", False),
    290: ("High price compressor limit", "x10, kW", False),
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
        return f"{val} ({val * 0.01:.2f} m³/h)"
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
            name, desc, used = REGISTERS[addr]
            formatted = format_value(addr, val)
            marker = "  " if used else "* "
            print(f'{marker}{addr:<5} {name:<30} {formatted:<25} {desc}')
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
