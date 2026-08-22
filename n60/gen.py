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
    # none of this gets used; commenting out
    #   address_0:
    #     name: ESP IP Address 0
    #   address_1:
    #     name: ESP IP Address 1
    #   address_2:
    #     name: ESP IP Address 2
    #   address_3:
    #     name: ESP IP Address 3
    #   address_4:
    #     name: ESP IP Address 4
    # dns_address:
    #   name: ESP DNS Address
    # mac_address:
    #   name: ESP MAC Address

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

modbus_controller:
  - address: 1
    update_interval: 5s

sensor:
''')

# build up a quick map of every CT pin id => bank_id, pin_in_bank_id, modbus_address_offset value
internal_maps = {}
ct_counter = 0
for bank_id in range(1,7):
    for pin_id in range(1,11):
        ct_counter += 1
        # ct: [bank, pin, base_addr)
        addr_offset = (bank_id * 100) + (pin_id * 2) - 2
        internal_maps[ct_counter] = [bank_id, pin_id, addr_offset]

# Label -> group of ct ids which should be combined into the labeled value
#
# The two typical scenarios would be 1) labeling single CT items and 2) combining double pole breakers for items on 240v
# However, it would be perfectly reasonable to use these entries to summarized a set of loads, for example,
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

for (power_name, ct_ids) in mapping.items():
    print(f'''
  ##############   {power_name}   ##############
  ''')

    # first, dump out the raw modbus fetching ct sensors; these will populate the labeled nice values later
    for ct_num in ct_ids:
        bank_id = internal_maps[ct_num][0]
        pin_id = internal_maps[ct_num][1]
        addr_offset = internal_maps[ct_num][2]
        print(f'''
  ### bank: {bank_id}, pin: {pin_id}, ct: {ct_num}
  
  
  

  


  # current (amps)
  - platform: modbus_controller
    id: ct_{ct_num}_current
    internal: true
    address: {addr_offset}
    register_type: holding
    value_type: U_DWORD_R
    unit_of_measurement: A
    device_class: current
    accuracy_decimals: 3
    filters:
    - multiply: 0.001

  # power (watts)
  - platform: modbus_controller
    id: ct_{ct_num}_power
    internal: true
    address: {addr_offset + 20}
    register_type: holding
    value_type: S_DWORD_R  # WAS: U_DWORD_R
    unit_of_measurement: W
    device_class: power
    accuracy_decimals: 1
    filters:
    - multiply: 0.1
    
  # energy (kWh)
  - platform: modbus_controller
    id: ct_{ct_num}_energy
    internal: true
    address: {addr_offset + 40}
    register_type: holding
    value_type: FP32_R  # WAS: U_DWORD_R
    unit_of_measurement: kWh
    state_class: total_increasing
    device_class: energy
    accuracy_decimals: 3''')

    # Now that the raw modbus values are being collected, let's setup the "combination"
    # helpers which will show up. Sometimes the combination is, uh, just a single source
    # other times, we're combining sources that have mupltiple power legs
    current_sources = "\n".join(f"      - source: ct_{num}_current" for num in ct_ids)
    power_sources   = "\n".join(f"      - source: ct_{num}_power"   for num in ct_ids)
    energy_sources  = "\n".join(f"      - source: ct_{num}_energy"  for num in ct_ids)

    print(f'''
  - platform: combination
    type: sum
    name: "{power_name} Load"
    id: {to_esphome_id(power_name)}_current
    sources:
{current_sources}

  - platform: combination
    type: sum
    name: "{power_name} Power"
    id: {to_esphome_id(power_name)}_power
    sources:
{power_sources}

  - platform: combination
    type: sum
    name: "{power_name} Energy"
    id: {to_esphome_id(power_name)}_energy
    # this specific stateclasss must be defined
    state_class: total_increasing
    sources:
{energy_sources}''')

print('''
##########################################################################################
''')

# Each bank has its own summation; the kwh summation is...kinda silly, the random grouping of ct's
# likely doesn't really relate to anything. The voltage & frequence measure are repeated several times
# because, based on how I wired things, L1 == L2 == L3 and L4 == L5 == L6 (since I'm in NA and we have
# two leg 120/240 split phase power). Even for 3 phase monitoring, it's likely that some of the banks
# legs are doubled up there too. Especialy on the N60.
#
# The temp per-bank is semi-useful, or at least it's not redundant.
#
# I may well come back in here, hide these, and re-label them to make more sense for my particular
# setup, like:
#
# - L1 Voltage
# - L1 Frequency
# - L2 Voltage
# - L2 Frequency
# - Internal Temp 1
# - Internal Temp 2
# - Internal Temp 3
# - Internal Temp 4
# - Internal Temp 5
# - Internal Temp 6
#
# Just leave off the kWh sums entirely and ignore some of the repeat volt/freq
for bank_id in range(1,7):

    print(f'''
  # bank: {bank_id}, ct start: {(bank_id*10)-9}, ct end: {(bank_id*10)}
  - platform: modbus_controller
    id: bank_{bank_id}_energy_sum
    name: Bank {bank_id} (CT {(bank_id*10)-9}-{(bank_id*10)}) Energy Sum
    address: {bank_id}60
    register_type: holding
    value_type: U_DWORD_R
    unit_of_measurement: kWh
    state_class: total_increasing
    device_class: energy
    accuracy_decimals: 1

  - platform: modbus_controller
    id: bank_{bank_id}_voltage
    name: Bank {bank_id} (CT {(bank_id*10)-9}-{(bank_id*10)}) Voltage
    address: {bank_id}62
    register_type: holding
    value_type: U_WORD
    unit_of_measurement: V
    device_class: voltage
    accuracy_decimals: 1
    filters:
    - multiply: 0.01

  - platform: modbus_controller
    id: bank_{bank_id}_frequency
    name: Bank {bank_id} (CT {(bank_id*10)-9}-{(bank_id*10)}) Frequency
    address: {bank_id}63
    register_type: holding
    value_type: U_WORD
    unit_of_measurement: Hz
    device_class: frequency
    accuracy_decimals: 1
    filters:
    - multiply: 0.01

  - platform: modbus_controller
    id: bank_{bank_id}_temp
    name: Bank {bank_id} (CT {(bank_id*10)-9}-{(bank_id*10)}) Temperature
    address: {bank_id}64
    register_type: holding
    value_type: FP32_R
    unit_of_measurement: "°C"
    device_class: temperature
    accuracy_decimals: 1''')
