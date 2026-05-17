[![HACS validation](https://img.shields.io/github/actions/workflow/status/KingKongKent/VRM-API/validate.yml?label=HACS%20Validation)](https://github.com/KingKongKent/VRM-API/actions?query=workflow%3Avalidate)
[![hacs_badge](https://img.shields.io/badge/HACS-Default%20✔-brightgreen.svg)](https://github.com/hacs/integration)
[![GitHub release](https://img.shields.io/github/release/KingKongKent/VRM-API?include_prereleases=&sort=semver&color=blue)](https://github.com/KingKongKent/VRM-API/releases/)
[![GH-code-size](https://img.shields.io/github/languages/code-size/KingKongKent/VRM-API?color=blue)](https://github.com/KingKongKent/VRM-API)
![stars](https://img.shields.io/github/stars/KingKongKent/VRM-API)

# Victron VRM API 
Victron VRM API Integration for Home Assistant

This integration uses the [Victron VRM Portal](https://vrm.victronenergy.com/) to get data from the API. All you need for setup are some numbers from your VRM Portal.
It reads data from Battery, MultiPlus, PV Inverter, Tank, and Solar Charger. You also get Overall Stats for the Day, Week, Month, and Year, plus System Overview information and Diagnostics for all detected devices.

### Key Features (v1.6.1)
- **134+ sensors** — Battery, MultiPlus, PV Inverter, Tank, Solar Charger, Overall Stats, System Overview, Diagnostics
- **Instance auto-remap** — If VRM reassigns a device instance ID (e.g., after Cerbo restart), the integration detects this automatically and queries the correct live instance. Your dashboards stay stable.
- **Reliable enum values** — Charge State, VE.Bus State, and similar status sensors always show the correct value, even when VRM's server-side cache is stale.
- **Tank diagnostics discovery** — Fresh water and other tank sensors can be discovered from diagnostics when VRM does not list them in System Overview.
- **Smart sensor creation** — Only creates sensor entities when the VRM API actually returns data for them.

> 📖 **[Full Documentation](docs/documentation.md)** — Detailed API reference, architecture guide, troubleshooting, and development instructions.
> 📋 **[Inventory](INVENTORY.md)** — Complete file inventory, sensor catalog, and API endpoint map.
> 🧭 **[Architecture](docs/architecture.md)** — Runtime flow, boundaries, and Mermaid diagram.
> 🔒 **[Security & Pitfalls](docs/security.md)** — Secret handling, repeated mistakes, and risk register.

<details>
   <summary> <b>VRM API supported Devices and Sensors</b></summary> 

### Overview Devices
| Device Type | Number of Sensors |
| :--- | :---: |
| **Battery** | 35 |
| **MultiPlus** | 29 |
| **PV Inverter** | 16 |
| **Tank** | 6 |
| **Solar Charger** | 11 |
| **Overall Stats** | 16 |
| **System Overview** | 10 per device |
| **Total** | 134+ |

### Sensor Details
| Device Type | Sensor Name | VRM ID / Key | Unit | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Battery** | State of charge | `51` | % | State of Charge (SOC) |
| **Battery** | Voltage | `47` | V | Battery Voltage |
| **Battery** | Starter Battery Voltage | `48` | V | Starter Battery Voltage |
| **Battery** | Current | `49` | A | Battery Current |
| **Battery** | Consumed Amphours | `50` | Ah | Consumed Amphours |
| **Battery** | Time to go | `52` | h | Time to go until empty |
| **Battery** | Battery Temperature | `115` | °C | Battery Temperature |
| **Battery** | Minimum Cell Voltage | `173` | V | Minimum Cell Voltage (BMS) |
| **Battery** | Maximum Cell Voltage | `174` | V | Maximum Cell Voltage (BMS) |
| **Battery** | Mid Voltage | `64` | V | Mid Point Voltage |
| **Battery** | Battery Power | *(Calculated)* | W | Current Power (V*A) |
| **Battery** | Battery Charge Cycles | `58` | - | Full Charge Cycles |
| **Battery** | Battery to Consumers (Today) | `Bc` | kWh | Energy to Load (Today) |
| **Battery** | Battery to Grid (Today) | `Bg` | kWh | Energy to Grid (Today) |
| **Battery** | Low voltage alarm | `119` | - | Low voltage alarm |
| **Battery** | High voltage alarm | `120` | - | High voltage alarm |
| **Battery** | Low starter-voltage alarm | `121` | - | Low starter-voltage alarm |
| **Battery** | High starter-voltage alarm | `122` | - | High starter-voltage alarm |
| **Battery** | Low state-of-charge alarm | `123` | - | Low state of charge |
| **Battery** | Low battery temperature alarm | `124` | - | Battery temperature too low |
| **Battery** | High battery temperature alarm | `125` | - | Battery temperature too high |
| **Battery** | Mid-voltage alarm | `126` | - | Mid-voltage anomaly |
| **Battery** | Low fused-voltage alarm | `155` | - | Low fused voltage |
| **Battery** | High fused-voltage alarm | `156` | - | High fused voltage |
| **Battery** | Fuse blown alarm | `157` | - | Fuse blown |
| **Battery** | High internal-temperature alarm | `158` | - | Internal temperature alarm |
| **Battery** | Cell imbalance alarm | `286` | - | Cell imbalance detected |
| **Battery** | High charge current alarm | `287` | - | Charge current too high |
| **Battery** | High discharge current alarm | `288` | - | Discharge current too high |
| **Battery** | Internal failure | `289` | - | Internal failure detected |
| **Battery** | High charge temperature alarm | `459` | - | Charge temperature too high |
| **Battery** | Low charge temperature alarm | `460` | - | Charge temperature too low |
| **Battery** | Low cell voltage | `522` | - | Low cell voltage |
| **Battery** | Charge blocked | `739` | - | Charging blocked (BMS) |
| **Battery** | Discharge blocked | `740` | - | Discharging blocked (BMS) |
| --- | --- | --- | --- | --- |
| **MultiPlus** | AC Input Frequency | `6` | Hz | AC Input Frequency |
| **MultiPlus** | AC Input Voltage L1 | `8` | V | AC Input Voltage Phase 1 |
| **MultiPlus** | AC Input Voltage L2 | `9` | V | AC Input Voltage Phase 2 |
| **MultiPlus** | AC Input Voltage L3 | `10` | V | AC Input Voltage Phase 3 |
| **MultiPlus** | AC Input Current L1 | `11` | A | AC Input Current Phase 1 |
| **MultiPlus** | AC Input Current L2 | `12` | A | AC Input Current Phase 2 |
| **MultiPlus** | AC Input Current L3 | `13` | A | AC Input Current Phase 3 |
| **MultiPlus** | AC Input Power L1 | `17` | W | AC Input Power Phase 1 |
| **MultiPlus** | AC Input Power L2 | `18` | W | AC Input Power Phase 2 |
| **MultiPlus** | AC Input Power L3 | `19` | W | AC Input Power Phase 3 |
| **MultiPlus** | AC Output Voltage L1 | `20` | V | AC Output Voltage Phase 1 |
| **MultiPlus** | AC Output Voltage L2 | `21` | V | AC Output Voltage Phase 2 |
| **MultiPlus** | AC Output Voltage L3 | `22` | V | AC Output Voltage Phase 3 |
| **MultiPlus** | AC Output Frequency | `23` | Hz | AC Output Frequency |
| **MultiPlus** | AC Output Current L1 | `14` | A | AC Output Current Phase 1 |
| **MultiPlus** | AC Output Current L2 | `15` | A | AC Output Current Phase 2 |
| **MultiPlus** | AC Output Current L3 | `16` | A | AC Output Current Phase 3 |
| **MultiPlus** | AC Output Power L1 | `29` | W | AC Output Power Phase 1 |
| **MultiPlus** | AC Output Power L2 | `30` | W | AC Output Power Phase 2 |
| **MultiPlus** | AC Output Power L3 | `31` | W | AC Output Power Phase 3 |
| **MultiPlus** | DC Bus Voltage | `32` | V | DC Bus Voltage |
| **MultiPlus** | DC Bus Current | `33` | A | DC Bus Current |
| **MultiPlus** | Active Input Source | `35` | - | Active AC Input (Grid/Generator/Shore) |
| **MultiPlus** | VE.Bus State | `40` | - | Operating State (e.g., Inverting) |
| **MultiPlus** | Switch Position | `44` | - | Charger/Inverter/On/Off |
| **MultiPlus** | Grid Setpoint | `242` | W | ESS Grid Setpoint Target |
| **MultiPlus** | SOC Limit | `243` | % | ESS Minimum SOC Limit |
| **MultiPlus** | Active SOC Limit | `244` | % | ESS Active SOC Limit |
| **MultiPlus** | MultiPlus Temperature | `521` | °C | Device Temperature |
| **MultiPlus** | DC Bus Power | *(Calculated)* | W | Current DC Power (V*A) |
| **MultiPlus** | Grid to Consumers (Today) | `Gc` | kWh | Energy from Grid to Load (Today) |
| **MultiPlus** | Grid to Battery (Today) | `Gb` | kWh | Energy from Grid to Battery (Today) |
| --- | --- | --- | --- | --- |
| **PV Inverter** | L1 Voltage | `203` | V | Voltage Phase 1 |
| **PV Inverter** | L1 Current | `204` | A | Current Phase 1 |
| **PV Inverter** | L1 Power | `205` | W | Power Phase 1 |
| **PV Inverter** | L1 Energy | `206` | kWh | Energy Yield Phase 1 (Total) |
| **PV Inverter** | L2 Voltage | `207` | V | Voltage Phase 2 |
| **PV Inverter** | L2 Current | `208` | A | Current Phase 2 |
| **PV Inverter** | L2 Power | `209` | W | Power Phase 2 |
| **PV Inverter** | L2 Energy | `210` | kWh | Energy Yield Phase 2 (Total) |
| **PV Inverter** | L3 Voltage | `211` | V | Voltage Phase 3 |
| **PV Inverter** | L3 Current | `212` | A | Current Phase 3 |
| **PV Inverter** | L3 Power | `213` | W | Power Phase 3 |
| **PV Inverter** | L3 Energy | `214` | kWh | Energy Yield Phase 3 (Total) |
| **PV Inverter** | Status | `246` | - | Status Code |
| **PV Inverter** | PV to Consumers (Today) | `Pc` | kWh | Energy from PV to Load (Today) |
| **PV Inverter** | PV to Battery (Today) | `Pb` | kWh | Energy from PV to Battery (Today) |
| **PV Inverter** | PV to Grid (Today) | `Pg` | kWh | Energy from PV to Grid (Today) |
| **PV Inverter** | PV Total Today | *(Calculated)* | kWh | Total PV Yield Today (Pc+Pb+Pg) |
| --- | --- | --- | --- | --- |
| **Tank** | Capacity | `328` | m³ | Tank Capacity |
| **Tank** | Type | `329` | - | Fluid Type |
| **Tank** | Level | `330` | % | Fluid Level in Percent |
| **Tank** | Remaining | `331` | m³ | Remaining Fluid Volume |
| **Tank** | Status | `443` | - | Tank Status (e.g., OK) |
| **Tank** | Custom Name | `638` | - | User Defined Name |
| --- | --- | --- | --- | --- |
| **Solar Charger** | Battery Voltage | `81` | V | Battery Voltage |
| **Solar Charger** | PV Voltage | `82` | V | Solar Panel Voltage |
| **Solar Charger** | Battery Temperature | `83` | °C | Battery Temperature (external) |
| **Solar Charger** | PV Current | `84` | A | Solar Panel Current |
| **Solar Charger** | Charge State | `85` | - | Charger State (e.g., Bulk, Float) |
| **Solar Charger** | Error Code | `88` | - | Error Code (if any) |
| **Solar Charger** | Relay Status | `90` | - | Relay State |
| **Solar Charger** | Yield Today | `94` | kWh | Energy Yield Today |
| **Solar Charger** | Max Power Today | `95` | W | Maximum Power Today |
| **Solar Charger** | Yield Yesterday | `96` | kWh | Energy Yield Yesterday |
| **Solar Charger** | Battery Watts | `107` | W | Charging Power to Battery |
| --- | --- | --- | --- | --- |
| **Overall Stats** | * Total Solar Yield | `total_solar_yield` | kWh | Total PV Yield (for selected period) |
| **Overall Stats** | * Total Consumption | `total_consumption` | kWh | Total Consumption (for selected period) |
| **Overall Stats** | * Grid Energy In | `grid_history_from` | kWh | Energy from Grid (for selected period) |
| **Overall Stats** | * Grid Energy Out | `grid_history_to` | kWh | Energy to Grid (for selected period) |
| --- | --- | --- | --- | --- |
| **System Overview** | Firmware | `firmwareVersion` | - | Device firmware version |
| **System Overview** | Last Connection | `lastConnection` | - | Last connection timestamp |
| **System Overview** | Product Name | `productName` | - | Device product name |
| **System Overview** | Remote IP | `remoteOnLan` | - | Remote IP address |
| **System Overview** | Connection Info | `connectionInformation` | - | Connection details |
| **System Overview** | Auto Update | `autoUpdate` | - | Auto-update status |
| **System Overview** | Battery Family | `batteryFamily` | - | Battery family type |
| **System Overview** | Battery Manufacturer | `batteryManufacturer` | - | Battery manufacturer |
| **System Overview** | Serial Number | `machineSerialNumber` | - | Device serial number |
| **System Overview** | Instance ID | `instance` | - | Device instance ID |

*(The **Overall Stats** Entities are build for Periods **Today, Week, Month and Year**.)*
*(The **System Overview** provides device information for all detected devices in your VRM installation.)*

</details>

## ✔️ Prerequisites 
- VRM access token (keep this secret!). Create one in the VRM Portal under Preferences > Integrations > Access tokens or use [this link.](https://vrm.victronenergy.com/access-tokens)
- your SiteID (VRM-Installations-ID)
- Instance Number from Battery, Multiplus and PV Inverter

  <details>
   <summary> <b>"How to" - Site_ID, Instance Number, Token</b></summary>  
   <img width="3161" height="1111" alt="vrm-api-Erklärung" src="https://github.com/KingKongKent/VRM-API/blob/main/docs/vrm-api-description.png" />
  </details>

## 📥 Installing the Integration

### ➡️ HACS

- Simply follow the Link to integrate this repository to HACS
  
 [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=KingKongKent&repository=VRM-API&category=integration)
- go to `Settings -> Devices and Services -> Integration`
- click on `Add Integration`
- search for `victron vrm api` or short `vrm`
- fill in your Site_ID, Token and Instance_ID for Battery, Multiplus and PV Inverter

#
### ➡️ Manual

- Download the [latest Release](https://github.com/KingKongKent/VRM-API/releases)
- Copy the folder `custom_components/victron_vrm_api/` into your Home Assistant `config/custom_components/` directory
- Restart Home Assistant
- go to `Settings -> Devices and Services -> Integration`
- click on `Add Integration`
- search for `victron vrm api` or short `vrm`
- fill in your Site_ID, Token and Instance_ID for Battery, Multiplus and PV Inverter

## ✅ How it looks in HA

<img width="1084" height="513" alt="baaf71fc1a0bd487e77f43b7fb7b184def05f512" src="https://github.com/KingKongKent/VRM-API/blob/main/docs/victron-vrm-api.png" />

  <details>
   <summary> <b>Pictures of Devices inside the Ingration</b></summary>  
   <img width="320" height="500" alt="vrm-api-Erklärung" src="https://github.com/KingKongKent/VRM-API/blob/main/docs/Config_Menu.png" />
   <img width="320" height="500" alt="vrm-api-Erklärung" src="https://github.com/KingKongKent/VRM-API/blob/main/docs/Battery.png" />
   <img width="320" height="500" alt="vrm-api-Erklärung" src="https://github.com/KingKongKent/VRM-API/blob/main/docs/Multiplus.png" />
   <img width="320" height="500" alt="vrm-api-Erklärung" src="https://github.com/KingKongKent/VRM-API/blob/main/docs/PV_Inverter.png" />
   <img width="320" height="500" alt="vrm-api-Erklärung" src="https://github.com/KingKongKent/VRM-API/blob/main/docs/Overall.png" />
  </details>

  <details>
   <summary> <b>Q&A</b></summary> 
    
  - Configuration Menu, if the instance number for Battery, Multiplus or PV Inverter is set to 0, then no device will be added!
    (Example, if you have no Battery, then you don`t need the empty Device in HA.)
  - You can add more instance ids separated by comma (100, 101, 102)
  - You get the Temperature value with a 1PH Multiplus Setup. With 3Ph Multiplus Setup you dont get this Sensor.
  - You get Data from your 1Ph or 3Ph PV-Inverter. With 3Ph you get some more Sensors.
  </details>

## 📋 Changelog

| Version | Changes |
| :--- | :--- |
| **v1.6.1** | Discover tank instances from diagnostics and use diagnostics fallback for Fresh water tank values |
| **v1.6.0** | Auto-remap instance IDs when VRM reassigns them; fix stale enum values (Charge State, VE.Bus State) |
| **v1.5.9** | Fix aiohttp session/timeout compatibility with HA 2026.2.x |
| **v1.5.8** | Fix diagnostics endpoint + decimal precision display |
| **v1.5.6** | Smart sensor creation — only create sensors when data is available |
| **v1.5.5** | Add MultiPlus ESS sensors (Grid Setpoint, SOC Limits, Switch Position) |
| **v1.5.4** | Add MultiPlus L2/L3 phases, Solar Charger PV voltage/current, Battery mid-voltage |
| **v1.5.3** | Add Starter Battery Voltage, System Overview device |
| **v1.5.2** | HACS default repository registration |

See [docs/documentation.md](docs/documentation.md) for the full changelog with details.

## 🔧 Troubleshooting

If sensors show as **Unavailable**:
1. Verify your Site ID, Token and Instance IDs are correct
2. Check HA logs: `Settings → System → Logs` and filter for `victron_vrm_api`
3. Enable debug logging in `configuration.yaml`:
   ```yaml
   logger:
     logs:
       custom_components.victron_vrm_api: debug
   ```
4. See the [Full Documentation](docs/documentation.md#troubleshooting) for more solutions.

## 📖 Documentation

- **[Full Documentation](docs/documentation.md)** — Complete reference including API details, architecture, development guide
- **[Architecture](docs/architecture.md)** — Runtime flow, shipped-code boundary, and diagram
- **[Security & Pitfalls](docs/security.md)** — Secret handling, deployment boundaries, and risk register
- **[Developer Instructions](docs/Instructions.md)** — Code architecture and contribution guide
- **[Inventory](INVENTORY.md)** — File inventory, sensor catalog, API endpoints
