from pymodbus.client import ModbusTcpClient

client = ModbusTcpClient('192.168.178.121', port=8899, timeout=5)
if client.connect():
    print('Connected!')
    for dev_id in [1, 2, 3]:
        try:
            result = client.read_holding_registers(address=110, count=1, device_id=dev_id)
            print(f'  Device {dev_id}, Reg 110: {result.registers[0]}')
        except Exception as e:
            print(f'  Device {dev_id}: no response')
    client.close()
else:
    print('Connection failed')
