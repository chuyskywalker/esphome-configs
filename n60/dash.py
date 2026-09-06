import re

import slugify as unicode_slug


print('''
views:
''')


###
def slugify(text: str | None, *, separator: str = "_") -> str:
  """Slugify a given text."""
  if text == "" or text is None:
    return ""
  slug = unicode_slug.slugify(text, separator=separator)
  return "unknown" if slug == "" else slug

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

p1l = {

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
}

p1r = {
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
}

p2l = {
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
}

p2r = {
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

print(f'''
  - type: sections
    max_columns: 2
    title: Loads
    path: loads
    sections:''')

for panel_name, panel_set in {'Panel 1, Left': p1l, 'Panel 1, Right': p1r, 'Panel 2, Left': p2l, 'Panel 2, Right': p2r}.items():
  print(f'''
      - type: grid
        cards:
          - type: heading
            icon: ''
            heading: "{panel_name}"
            heading_style: title
          - type: entities
            entities:''')

  ct = 0
  for mapping_name in panel_set.keys():
    energy_key = slugify(mapping_name)
    ct += 1
    print(f'''
              - entity: sensor.energy_meter_{energy_key}_energy
                name: "{mapping_name}"
                state_header: "{'kWh' if ct == 1 else ' '}"
                type: custom:multiple-entity-row
                styles:
                  width: 40px
                hide: true
                unit: false
                entities:
                  - entity: sensor.energy_meter_{energy_key}_current
                    name: "{'Amps' if ct == 1 else ' '}"
                    unit: false
                    styles:
                      width: 40px
                  - entity: sensor.energy_meter_{energy_key}_power
                    name: "{'Watts' if ct == 1 else ' '}"
                    unit: false
                    styles:
                      width: 40px''')














###
print(f'''
  - type: sections
    max_columns: 3
    title: Raw CT Vals
    path: raw-ct
    sections:''')

for bank in range(1, 7):
  print(f'''
      - type: grid
        cards:
          - type: heading
            icon: ''
            heading: BANK{bank}
            heading_style: title
          - type: entities
            entities:''')

  for ct in range(1, 11):
    ctid = (bank * 10) - 10 + ct
    print(f'''
              - entity: sensor.energy_meter_ct_{ctid:02d}_energy
                name: CT{ctid:02d}
                state_header: "{'kWh' if ct == 1 else ' '}"
                type: custom:multiple-entity-row
                styles:
                  width: 40px
                hide: true
                unit: false
                entities:
                  - entity: sensor.energy_meter_ct_{ctid:02d}_current
                    name: "{'Amps' if ct == 1 else ' '}"
                    unit: false
                    styles:
                      width: 40px
                  - entity: sensor.energy_meter_ct_{ctid:02d}_power
                    name: "{'Watts' if ct == 1 else ' '}"
                    unit: false
                    styles:
                      width: 40px''')



print('''
  - type: sections
    path: sankey
    title: Sankey
    cards: []
    sections:
      - type: grid
        cards:
          - type: energy-date-selection
            vertical_opening_direction: auto
            opening_direction: auto
          - type: energy-sankey
            layout: horizontal
            group_by_floor: false
            group_by_area: false
            grid_options:
              columns: full
              rows: 12
          - type: power-sankey
            layout: auto
            group_by_floor: false
            group_by_area: false
            grid_options:
              columns: full
              rows: 12
        column_span: 4''')



  # - type: sections
  #   max_columns: 4
  #   title: Circuits
  #   path: circuits
  #   sections:
  #     - type: grid
  #       cards:
  #         - type: heading
  #           heading: Watts
  #           heading_style: title
  #         - type: entities
  #           entities:
  #             - entity: sensor.energy_meter_disposal_p1b7_energy
  #             - entity: sensor.energy_meter_ac_40a_p1b22_24_energy
  #     - type: grid
  #       cards:
  #         - type: heading
  #           heading: Amps
  #           heading_style: title
  #         - type: entities
  #           entities:
  #             - entity: sensor.energy_meter_disposal_p1b7_load
  #             - entity: sensor.energy_meter_disposal_p1b7_load
  #     - type: grid
  #       cards:
  #         - type: heading
  #           heading: kWh
  #           heading_style: title
  #         - type: entities
  #           entities:
  #             - entity: sensor.energy_meter_erv_p1b15_power
  #             - entity: sensor.energy_meter_ac_40a_p1b22_24_power
  # - type: sections
  #
  #
  #

#   - type: sections
#     sections:
#       - type: grid
#         cards:
#           - type: heading
#             heading: New section
#           - type: history-graph
#             grid_options:
#               columns: full
#             entities:
#               - sensor.energy_meter_ct_01_energy
#               - sensor.energy_meter_ct_02_energy
#               - sensor.energy_meter_ct_03_energy
#               - sensor.energy_meter_ct_04_energy
#               - sensor.energy_meter_ct_05_energy
#               - sensor.energy_meter_ct_06_energy
#               - sensor.energy_meter_ct_07_energy
#               - sensor.energy_meter_ct_08_energy
#               - sensor.energy_meter_ct_09_energy
#               - sensor.energy_meter_ct_10_energy
#               - sensor.energy_meter_ct_11_energy
#               - sensor.energy_meter_ct_12_energy
#               - sensor.energy_meter_ct_13_energy
#               - sensor.energy_meter_ct_14_energy
#               - sensor.energy_meter_ct_15_energy
#               - sensor.energy_meter_ct_16_energy
#               - sensor.energy_meter_ct_17_energy
#               - sensor.energy_meter_ct_18_energy
#               - sensor.energy_meter_ct_19_energy
#               - sensor.energy_meter_ct_20_energy
#               - sensor.energy_meter_ct_21_energy
#               - sensor.energy_meter_ct_22_energy
#               - sensor.energy_meter_ct_23_energy
#               - sensor.energy_meter_ct_24_energy
#               - sensor.energy_meter_ct_25_energy
#               - sensor.energy_meter_ct_26_energy
#               - sensor.energy_meter_ct_27_energy
#               - sensor.energy_meter_ct_28_energy
#               - sensor.energy_meter_ct_29_energy
#               - sensor.energy_meter_ct_30_energy
#               - sensor.energy_meter_ct_31_energy
#               - sensor.energy_meter_ct_32_energy
#               - sensor.energy_meter_ct_33_energy
#               - sensor.energy_meter_ct_34_energy
#               - sensor.energy_meter_ct_35_energy
#               - sensor.energy_meter_ct_36_energy
#               - sensor.energy_meter_ct_37_energy
#               - sensor.energy_meter_ct_38_energy
#               - sensor.energy_meter_ct_39_energy
#               - sensor.energy_meter_ct_40_energy
#               - sensor.energy_meter_ct_41_energy
#               - sensor.energy_meter_ct_42_energy
#               - sensor.energy_meter_ct_43_energy
#               - sensor.energy_meter_ct_44_energy
#               - sensor.energy_meter_ct_45_energy
#               - sensor.energy_meter_ct_46_energy
#               - sensor.energy_meter_ct_47_energy
#               - sensor.energy_meter_ct_48_energy
#               - sensor.energy_meter_ct_49_energy
#               - sensor.energy_meter_ct_50_energy
#               - sensor.energy_meter_ct_51_energy
#               - sensor.energy_meter_ct_52_energy
#               - sensor.energy_meter_ct_53_energy
#               - sensor.energy_meter_ct_54_energy
#               - sensor.energy_meter_ct_55_energy
#               - sensor.energy_meter_ct_56_energy
#               - sensor.energy_meter_ct_57_energy
#               - sensor.energy_meter_ct_58_energy
#               - sensor.energy_meter_ct_59_energy
#               - sensor.energy_meter_ct_60_energy
#             hours_to_show: 1
#           - type: tile
#             entity: sensor.energy_meter_esp_ip_address
#           - type: entities
#             entities:
#               - entity: sensor.energy_meter_ct_01_energy
#               - entity: sensor.energy_meter_ct_02_energy
#         column_span: 4