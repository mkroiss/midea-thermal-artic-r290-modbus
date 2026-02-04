#!/usr/bin/env python3
"""Write target temp to Midea heat pump register 2, preserving Zone2 byte."""
import sys
from pymodbus.client import ModbusTcpClient

target = int(float(sys.argv[1]))
client = ModbusTcpClient('192.168.178.121', port=8899, timeout=5)
if client.connect():
    result = client.read_holding_registers(address=2, count=1, device_id=2)
    if not result.isError():
        zone2 = (result.registers[0] >> 8) & 0xFF
        new_raw = (zone2 << 8) | target
        client.write_register(address=2, value=new_raw, device_id=2)
    client.close()
