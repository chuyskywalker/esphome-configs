import sys
import re

target = '/config/energy-monitor.yaml'

print(f"Generating to: {target}")

# open file and setup sys.stdout, so all print()'s, go to the file
sys.stdout = open(target, "w", encoding="utf-8")

def to_esphome_id(text: str) -> str:
    # 1. Strip edge spaces and lowercase
    text = text.strip().lower()

    # 2. Replace internal spaces and hyphens with a single underscore
    text = re.sub(r'[\s\-]+', '_', text)

    # 3. Remove all non-alphanumeric characters except internal underscores
    text = re.sub(r'[^a-z0-9_]', '', text)

    # 4. Trim leading/trailing underscores created by removed symbols
    text = text.strip('_')

    # 5. Safety catch: If it starts with a number, prepend an underscore
    if text and text[0].isdigit():
        text = f"sensor_{text}"

    return text

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

  # This block delays initial sensor data publishing on boot
  on_boot:
    priority: -100.0  # Runs after WiFi, MQTT, and API connections are ready
    then:
      - delay: 15s     # Wait 15 seconds for energy ICs to stabilize
      - logger.log: "Boot delay finished. Allowing sensor publishing."

esp32:
  board: esp32-s3-devkitc-1
  framework:
    type: arduino

# Enable logging
logger:
  level: INFO
  # level: VERBOSE
  # logs:
  #   modbus: VERBOSE
  #   modbus_controller: VERBOSE
  #   # Turn down everything else so your log screen doesn't fly by too fast:
  #   sensor: DEBUG
  #   component: DEBUG
  #   i2c.idf: NONE

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

font:
  - file: "gfonts://Roboto"
    id: roboto
    size: 15

i2c:
  sda: 18
  scl: 17

# TODO: seems like we could do something way more fun with this than just IP address
#       maybe keep a running tally of kwh, or current amps/watts, etc.
#       a cool running graph of the last 15 minutes or something? I dunno!
display:
  - platform: ssd1306_i2c
    model: "SSD1306 128x64"
    address: 0x3C
    lambda: |-
      it.printf(0, 15, id(roboto), "IP: %s", id(eth_ip).state.c_str());

modbus:
  id: modbus_to_arm32
  turnaround_time: 200ms

# In theory, it would make sense to poll watts/amps quicker than kWh (since the later changes slowly)
# However, because of the optimized modbus polling, getting the kWh values just as frequently
# doesn't cost any extra.
modbus_controller:
  - id: modbod
    address: 1
    # I have measured the full response (all 6 banks) taking around 3 seconds.
    update_interval: 5s
    # update_interval: 60s

sensor:
''')

# build up a quick map of every CT pin id => bank_id, pin_in_bank_id, modbus_address_offset value
internal_maps = {}
ct_counter = 0
for bank_id in range(1,7):  # reminder, range is (inclusive,exclusive)
    for pin_id in range(1,11):
        ct_counter += 1
        # ct: [bank, pin, base_addr)
        addr_offset = (bank_id * 100) + (pin_id * 2) - 2
        internal_maps[ct_counter] = [bank_id, pin_id, addr_offset]

# Mapping is a label to group-of-ct-ids which should be combined into the labeled value
#
# The two typical scenarios would be 1) labeling single CT items and 2) combining double pole breakers for items on 240v
# However, it would be perfectly reasonable to use these entries to summarize a set of loads, for example,
# you could tag 5 individual CT's as "Lights" if you have multiple circuits for lights, but want them all
# grouped together because tracking each circuit holds no value to you. The caveat to this, which the script
# will catch, is that you can't define a CT twice, otherwise it would (potentially) be double counted.
#
# You *MIGHT* have good reason to re-use CT numbers in multiple groups, though (maybe you want individual
# circuits for monitoring, but for display purposes, having an aggregate is easier to work with). If that's
# the case, you'll need to disable the logic which detects CT reuse.
mapping = {

    # Panel 1; Left
    "Microwave (P1B1)": [1],
    "Fridge & Hood (P1B3)": [31],
    "Kitchen Outlets (P1B5)": [2],
    "Disposal (P1B7)": [32],
    "Garage Outlets 1 (P1B9)": [3],
    "Garage Outlets 2 (P1B11)": [33],
    "Outside Outlets (P1B13)": [4],
    "ERV (P1B15)": [34],
    "Crawl: Dehum, LED, Cond.Pump, Moen Flo (P1B17)": [5],
    "Oven (30A) (P1B19-21)": [6, 35],
    "Cooktop (50A) (P1B23-25)": [7, 36],
    # 8, 37, 38 -- not connected

    # Panel 1; Right
    "Smoke Alarms (P1B2)": [9],
    "Garage Int&Ext Lights (P1B4)": [39],
    "(Old) TV Nook Lights (P1B6)": [10],
    "Living Outlets (P1B8)": [40],
    "Primary Bed Lights (P1B10)": [11],
    "Hallway Lights (P1B12)": [41],
    "Big Room Lights (P1B14)": [12],
    "Lights: Entrance, Porch, Front  (P1B16)": [42],
    "Primary Bath Lights (P1B18)": [13],
    "Kitchen Island Oulets (P1B20)": [43],
    "AC (40A) (P1B22-24)": [14, 44],

    # Panel 2; Left
    "EV Charger 1 (40A) (P2B1-3)": [15, 45],
    "EV Charger 2 (40A) (P2B5-7)": [16, 46],
    "Back Yard Porch Lights (P2B9)": [17],
    "Desk Outlets (P2B11)": [47],
    "Laundry Lights (P2B13)": [18],
    "Bedroom 1 Lights (P2B15)": [48],
    "Hallway Bath Lights (P2B17)": [19],
    "Bedroom 1 Outlets (P2B19)": [49],
    "Primary Bed Outlets (P2B21)": [20],
    "Bedroom 2 Lights (P2B23)": [50],
    "Bedroom 2 Outlets (P2B25)": [21],
    # 22, 51, 52 -- not connected

    # Panel 2; Right
    "Water Heater (30A) (P2B2-4)": [23, 53],
    "Primary Bath Outlets (P2B6)": [24],
    "Data (P2B8)": [54],
    "Laundry Outlets (P2B10)": [25],
    "Washer Outlet (P2B12)": [55],
    "Hallway Bath Outlets (P2B14)": [26],
    "Shower Valves (MOEN; in wall) (P2B16)": [56],
    "Fire Alarm (P2B18)": [27],
    # 26, 55, 56 -- not connected

}

is_valid = True
seen_numerical_ids = set()
seen_esphome_ids = {}

for name, id_list in mapping.items():
    esp_id = to_esphome_id(name)
    if esp_id in seen_esphome_ids:
        print(f"❌ Duplicate ESPHome ID: '{name}' and '{seen_esphome_ids[esp_id]}' both make '{esp_id}'", file=sys.stderr)
        is_valid = False
    seen_esphome_ids[esp_id] = name

    for num_id in id_list:
        # 2. Verify bounds (1-60)
        if not (1 <= num_id <= 60):
            print(f"❌ Range Error: ID {num_id} in '{name}' falls outside 1-60", file=sys.stderr)
            is_valid = False

        # 3. Verify numerical ID uniqueness <-- if re-using CT's is on purpose, comment out this block.
        if num_id in seen_numerical_ids:
            print(f"❌ Duplicate ID Error: ID {num_id} in '{name}' is referenced twice", file=sys.stderr)
            is_valid = False
        seen_numerical_ids.add(num_id)

if not is_valid:
    sys.exit(1)

# This will pull all details from all banks. Why? It's actually more efficient. For example,
# the data from bank 1 is in registers 100 - 166; a total of 68bytes to fetch. If you pull
# all of those fields, the modbus protocol can batch it into a single long request/response.
# If you choose to only pull a few of those registers, though, then the modbus client
# will make multiple, smaller requests. This causes a longer turn around time.
#
# So, instead, we just pull EVERYTHING from each bank (6 requests) and then "hide" that
# data internally. Then we create exposed sensors that represent the data as desired.

# you can change this to "true" or "false" to hide/show all these values
internal = 'true'

for ct_num, (bank_id, pin_id, addr_offset) in internal_maps.items():
    print(f'''
  # ct {ct_num:02d}, bank {bank_id}, pin {pin_id}, addr_offset {addr_offset}
  
  # current (amps)
  - platform: modbus_controller
    id: ct_{ct_num:02d}_current
    name: ct_{ct_num:02d}_current
    internal: {internal}
    address: {addr_offset}
    register_type: holding
    value_type: U_DWORD_R
    unit_of_measurement: A
    device_class: current
    state_class: measurement
    accuracy_decimals: 3
    filters:
    - multiply: 0.001

  # power (watts)
  - platform: modbus_controller
    id: ct_{ct_num:02d}_power
    name: ct_{ct_num:02d}_power
    internal: {internal}
    address: {addr_offset + 20}
    register_type: holding
    value_type: S_DWORD_R
    unit_of_measurement: W
    device_class: power
    state_class: measurement
    accuracy_decimals: 1
    filters:
    - multiply: 0.1

  # energy (kWh)
  - platform: modbus_controller
    id: ct_{ct_num:02d}_energy
    name: ct_{ct_num:02d}_energy
    internal: {internal}
    address: {addr_offset + 40}
    register_type: holding
    value_type: FP32_R
    unit_of_measurement: kWh
    device_class: energy
    state_class: total_increasing
    accuracy_decimals: 3''')

# There are also some "per bank" values that can be collected and referenced later as well
for bank_id in range(1,7):

    print(f'''
  # bank: {bank_id}, ct start: {(bank_id*10)-9}, ct end: {(bank_id*10)}
  - platform: modbus_controller
    id: bank_{bank_id}_energy_sum
    name: bank_{bank_id}_energy_sum
    internal: {internal}
    address: {bank_id}60
    register_type: holding
    value_type: FP32_R
    unit_of_measurement: kWh
    state_class: total_increasing
    device_class: energy
    accuracy_decimals: 3

  - platform: modbus_controller
    id: bank_{bank_id}_voltage
    name: bank_{bank_id}_voltage
    internal: {internal}
    address: {bank_id}62
    register_type: holding
    value_type: U_WORD
    unit_of_measurement: V
    device_class: voltage
    state_class: measurement
    accuracy_decimals: 1
    filters:
    - multiply: 0.01

  - platform: modbus_controller
    id: bank_{bank_id}_frequency
    name: bank_{bank_id}_frequency
    internal: {internal}
    address: {bank_id}63
    register_type: holding
    value_type: U_WORD
    unit_of_measurement: Hz
    device_class: frequency
    state_class: measurement
    accuracy_decimals: 1
    filters:
    - multiply: 0.01
    
  - platform: modbus_controller
    id: bank_{bank_id}_temp
    name: bank_{bank_id}_temp
    #internal: {internal}
    internal: false  # specifically override because per-bank temp is (mildly) useful
    address: {bank_id}64
    register_type: holding
    value_type: FP32_R
    unit_of_measurement: "°C"
    device_class: temperature
    state_class: measurement
    accuracy_decimals: 1
    
  - platform: modbus_controller
    id: bank_{bank_id}_powerfactor
    name: bank_{bank_id}_powerfactor
    internal: {internal}
    address: {bank_id}66
    register_type: holding
    value_type: FP32_R
    unit_of_measurement: ""
    device_class: power_factor
    state_class: measurement
    accuracy_decimals: 2
''')


# Now that the raw modbus values are being collected, let's setup the "combination"
# helpers which will show up. Sometimes the combination is, uh, just a single source
# other times, we're combining sources that have mupltiple power legs
for (power_name, ct_ids) in mapping.items():

    current_sources = "\n".join(f"      - source: ct_{num:02d}_current" for num in ct_ids)
    power_sources   = "\n".join(f"      - source: ct_{num:02d}_power"   for num in ct_ids)
    energy_sources  = "\n".join(f"      - source: ct_{num:02d}_energy"  for num in ct_ids)

    print(f'''
  ##############   {power_name}   ##############
 
  - platform: combination
    type: sum
    name: "{power_name} Current"
    id: {to_esphome_id(power_name)}_current
    device_class: current
    state_class: measurement
    sources:
{current_sources}

  - platform: combination
    type: sum
    name: "{power_name} Power"
    id: {to_esphome_id(power_name)}_power
    device_class: power
    state_class: measurement
    sources:
{power_sources}

  - platform: combination
    type: sum
    name: "{power_name} Energy"
    id: {to_esphome_id(power_name)}_energy
    device_class: energy
    state_class: total_increasing
    sources:
{energy_sources}''')

print('''

### Useful combinations soley based on MY wiring configuration
### I have L1 hooked up to bank 1, 2, 3 and L2 on bank 4,5,6
### If you have a different setup, season to taste

  - platform: combination
    type: mean
    name: "L1 Voltage"
    id: l1_voltage
    sources:
    - source: bank_1_voltage
    - source: bank_2_voltage
    - source: bank_3_voltage
    accuracy_decimals: 2
    unit_of_measurement: V
    device_class: voltage
    state_class: measurement

  - platform: combination
    type: mean
    name: "L1 Frequency"
    id: l1_frequency
    sources:
    - source: bank_1_frequency
    - source: bank_2_frequency
    - source: bank_3_frequency
    accuracy_decimals: 2
    unit_of_measurement: Hz
    device_class: frequency
    state_class: measurement

  - platform: combination
    type: mean
    name: "L2 Voltage"
    id: l2_voltage
    sources:
    - source: bank_4_voltage
    - source: bank_5_voltage
    - source: bank_6_voltage
    accuracy_decimals: 2
    unit_of_measurement: V
    device_class: voltage
    state_class: measurement

  - platform: combination
    type: mean
    name: "L2 Frequency"
    id: l2_frequency
    sources:
    - source: bank_4_frequency
    - source: bank_5_frequency
    - source: bank_6_frequency
    accuracy_decimals: 2
    unit_of_measurement: Hz
    device_class: frequency
    state_class: measurement

''')


# 6. Energy Clearing Functions (Function Code 0x05)
# --------------------------------------------------
#
# The following registers clear energy consumption data when written with function code 0x05:
#
# 6.1 Clear All Channels on a Chip
# ---------------------------------
#
# +----------+--------------------------------+
# | Register | Function                       |
# +----------+--------------------------------+
# | 520      | Clear all energy on Chip 1     |
# | 521      | Clear all energy on Chip 2     |
# | 522      | Clear all energy on Chip 3     |
# | 523      | Clear all energy on Chip 4     |
# | 524      | Clear all energy on Chip 5     |
# | 525      | Clear all energy on Chip 6     |
# +----------+--------------------------------+
#
# 6.2 Clear Individual Channels
# ------------------------------
#
# +----------------+------------------------------------------------+
# | Register Range | Function                                       |
# +----------------+------------------------------------------------+
# | 526-535        | Clear energy on Chip 1, channels 1-10          |
# | 536-545        | Clear energy on Chip 2, channels 1-10          |
# | 546-555        | Clear energy on Chip 3, channels 1-10          |
# | 556-565        | Clear energy on Chip 4, channels 1-10          |
# | 566-575        | Clear energy on Chip 5, channels 1-10          |
# | 576-585        | Clear energy on Chip 6, channels 1-10          |
# | 586            | Clear sum energy on Chip 1                     |
# | 587            | Clear sum energy on Chip 2                     |
# | 588            | Clear sum energy on Chip 3                     |
# | 589            | Clear sum energy on Chip 4                     |
# | 590            | Clear sum energy on Chip 5                     |
# | 591            | Clear sum energy on Chip 6                     |
# +----------------+------------------------------------------------+
#
# print('''
#
# button:
#
#   - platform: template
#     name: "Warm Reset"
#     icon: "mdi:refresh"
#     id: clear_btn_chip_500
#     on_press:
#       - modbus_client.write_single_coil:
#           address: 0x01
#           start_address: 500
#           value: true
#
#   - platform: template
#     name: "Factory Reset"
#     icon: "mdi:refresh"
#     id: clear_btn_chip_510
#     on_press:
#       - modbus_client.write_single_coil:
#           address: 0x01
#           start_address: 510
#           value: true''')


print('''
switch:
  - platform: modbus_controller
    id: bidirectional
    name: "Bidirectional CT mode"
    register_type: holding
    address: 30
''')

for chip in range(1, 7):
  print(f'''
  - platform: modbus_controller
    id: clear_btn_chip_{chip}
    name: "Clear Energy, Chip {chip}"
    register_type: coil
    address: {520+chip-1}
''')

# - platform: template
#   name: "CLEAR ALL ENERGY REGISTERS"
#   icon: "mdi:refresh"
#   id: clear_btn_chip_1
#   on_press:
#
# for addr in range(520,592):
#     print(f'''      - modbus_client.write_single_coil:
#           address: 0x01
#           start_address: {addr}
#           value: true
#       - delay: 500ms''')
#