from pymodbus.client import ModbusTcpClient
import time

client = ModbusTcpClient('192.168.178.121', port=8899, timeout=5)
if client.connect():
    # Read key control and status registers
    print('=== Current State ===')
    regs = [
        (0, 'Power cmd'), (1, 'Mode'), (2, 'Set temp'),
        (14, 'Zone2 pwr'), (15, 'DHW pwr'), (16, 'Zone1 pwr'),
        (100, 'Comp freq'), (101, 'Op state'), (199, 'Op mode'),
    ]
    for addr, name in regs:
        result = client.read_holding_registers(address=addr, count=1, device_id=2)
        if not result.isError():
            print(f'  Reg {addr:3d} ({name:12s}): {result.registers[0]}')
        else:
            print(f'  Reg {addr:3d} ({name:12s}): ERROR')

    # Try sequence: Zone1 on, then mode=heating, then main power
    print('\n=== Turning ON ===')

    print('  Write reg 16 (Zone1) = 1')
    r = client.write_register(address=16, value=1, device_id=2)
    print(f'    Result: {r}')
    time.sleep(1)

    print('  Write reg 1 (Mode) = 3 (Heating)')
    r = client.write_register(address=1, value=3, device_id=2)
    print(f'    Result: {r}')
    time.sleep(1)

    print('  Write reg 0 (Power) = 1')
    r = client.write_register(address=0, value=1, device_id=2)
    print(f'    Result: {r}')
    time.sleep(2)

    print('\n=== After Write ===')
    for addr, name in regs:
        result = client.read_holding_registers(address=addr, count=1, device_id=2)
        if not result.isError():
            print(f'  Reg {addr:3d} ({name:12s}): {result.registers[0]}')

    client.close()
