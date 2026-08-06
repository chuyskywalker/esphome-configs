import sys

target = 'energy-monitor'

print(f"Generating to: {target}.yaml")

# Open your log file (use 'w' to overwrite, or 'a' to append)
sys.stdout = open(f"/app/device-yamls/{target}.yaml", "w", encoding="utf-8")

# All the preamble

print('''
substitutions:
  name: energy-meter
  friendly_name: Energy Meter
  static_ip: 192.168.0.6
  gateway: 192.168.0.1
  subnet: 255.255.254.0
  api_key: !secret energy_monitor_api_encryption_key
  ota_pass: !secret energy_monitor_ota_password

esphome:
  name: ${name}
  friendly_name: ${friendly_name}

esp32:
  board: esp32-s3-devkitc-1
  framework:
    type: arduino

# Enable logging
logger:
  # baud_rate: 0

# Enable Home Assistant API
api:
  encryption:
    key: ${api_key}

# allow for remote updates
ota:
  - platform: esphome
    password: ${ota_pass}

ethernet:
  type: W5500
  clk_pin: GPIO42
  mosi_pin: GPIO43
  miso_pin: GPIO44
  cs_pin: GPIO41
  interrupt_pin: GPIO2
  reset_pin: GPIO1
  manual_ip:
    static_ip: ${static_ip}
    gateway: ${gateway}
    subnet: ${subnet}

uart:
  rx_pin: 9
  tx_pin: 10
  baud_rate: 115200
  stop_bits: 1
  data_bits: 8
  parity: NONE

web_server:
  port: 80
  ota: False
  version: 3
  local: True

text_sensor:
  - platform: ethernet_info
    ip_address:
      name: ESP IP Address
      id: eth_ip
      address_0:
        name: ESP IP Address 0
      address_1:
        name: ESP IP Address 1
      address_2:
        name: ESP IP Address 2
      address_3:
        name: ESP IP Address 3
      address_4:
        name: ESP IP Address 4
    dns_address:
      name: ESP DNS Address
    mac_address:
      name: ESP MAC Address

font:
  - file: "gfonts://Roboto"
    id: roboto
    size: 15

i2c:
  sda: 18
  scl: 17

display:
  - platform: ssd1306_i2c
    model: "SSD1306 128x64"
    address: 0x3C
    lambda: |-
      it.printf(0, 15, id(roboto), "IP: %s", id(eth_ip).state.c_str());

modbus:

modbus_controller:
  - address: 1
    update_interval: 5s

sensor:
''')

# inc, exc
for bank_id in range(1,7):

    # current (amps) per pin
    for pin_id in range(1,11):
        print(f'''
  - platform: modbus_controller
    id: n60_{bank_id}_{pin_id}_current
    name: bl0910_{bank_id}_{pin_id}_current
    address: {(bank_id * 100) + (pin_id * 2) - 2 }
    register_type: holding
    value_type: U_DWORD_R
    unit_of_measurement: A
    device_class: current
    accuracy_decimals: 3
    filters:
    - multiply: 0.001''')

    # power (watts) per pin
    for pin_id in range(1,11):
        print(f'''
  - platform: modbus_controller
    id: n60_{bank_id}_{pin_id}_power
    name: bl0910_{bank_id}_{pin_id}_power
    address: {(bank_id * 100) + (pin_id * 2) - 2 + 20}
    register_type: holding
    value_type: U_DWORD_R
    unit_of_measurement: W
    device_class: power
    accuracy_decimals: 1
    filters:
    - multiply: 0.1''')

    # energy (kWh) per pin
    for pin_id in range(1,11):
        print(f'''    
  - platform: modbus_controller
    id: n60_{bank_id}_{pin_id}_energy
    name: bl0910_{bank_id}_{pin_id}_energy
    address: {(bank_id * 100) + (pin_id * 2) - 2 + 40}
    register_type: holding
    value_type: U_DWORD_R
    unit_of_measurement: kWh
    state_class: total_increasing
    device_class: energy
    accuracy_decimals: 1''')

    # now back in the bank loop, the per-bank sum items
    print(f'''
  - platform: modbus_controller
    id: n60_{bank_id}_energy_sum
    name: bl0910_{bank_id}_energy_sum
    address: {bank_id}60
    register_type: holding
    value_type: U_DWORD_R
    unit_of_measurement: kWh
    state_class: total_increasing
    device_class: energy
    accuracy_decimals: 1

  - platform: modbus_controller
    id: n60_{bank_id}_voltage
    name: bl0910_{bank_id}_voltage
    address: {bank_id}62
    register_type: holding
    value_type: U_WORD
    unit_of_measurement: V
    device_class: voltage
    accuracy_decimals: 1
    filters:
    - multiply: 0.01

  - platform: modbus_controller
    id: n60_{bank_id}_frequency
    name: bl0910_{bank_id}_frequency
    address: {bank_id}63
    register_type: holding
    value_type: U_WORD
    unit_of_measurement: Hz
    device_class: frequency
    accuracy_decimals: 1
    filters:
    - multiply: 0.01

  - platform: modbus_controller
    id: n60_{bank_id}_temp
    name: bl0910_{bank_id}_temp
    address: {bank_id}64
    register_type: holding
    value_type: FP32_R
    unit_of_measurement: "°C"
    device_class: temperature
    accuracy_decimals: 1''')
