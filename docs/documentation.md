# Victron VRM API — Full Documentation

> **Version**: 1.6.0 &nbsp;|&nbsp; **Minimum HA**: 2025.1 &nbsp;|&nbsp; **Domain**: `victron_vrm_api`

A Home Assistant custom integration that pulls real-time data from the [Victron VRM Portal](https://vrm.victronenergy.com/) API. Supports Battery, MultiPlus, PV Inverter, Tank, Solar Charger, Overall Stats, System Overview, and Diagnostics devices — creating **134+ sensors** from a single configuration.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Supported Devices & Sensors](#supported-devices--sensors)
- [Architecture](#architecture)
- [API Reference](#api-reference)
- [Scan Intervals](#scan-intervals)
- [Error Handling](#error-handling)
- [Troubleshooting](#troubleshooting)
- [Development Guide](#development-guide)
- [Deployment](#deployment)
- [Changelog](#changelog)
- [FAQ](#faq)
- [Contributing](#contributing)
- [License](#license)

---

## Prerequisites

1. **VRM Access Token** — Create at [VRM Portal → Preferences → Integrations → Access Tokens](https://vrm.victronenergy.com/access-tokens). Keep this secret.
2. **Site ID** — Your VRM Installation ID, visible in the VRM Portal URL (e.g., `https://vrm.victronenergy.com/installation/<SITE_ID>/dashboard`).
3. **Instance IDs** — Device instance numbers for your Battery, MultiPlus, PV Inverter, Tank, and/or Solar Charger. Found in the VRM Portal device list.

<details>
<summary><b>How to find your Site ID, Instance Number, and Token</b></summary>
<img width="3161" height="1111" alt="VRM API Setup Guide" src="https://github.com/KingKongKent/VRM-API/blob/main/docs/vrm-api-description.png" />
</details>

---

## Installation

### Via HACS (Recommended)

1. Click the button below to add this repository to HACS:

   [![Open HACS Repository](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=KingKongKent&repository=VRM-API&category=integration)

2. Install the integration from HACS.
3. Restart Home Assistant.
4. Go to **Settings → Devices & Services → Add Integration**.
5. Search for `victron vrm api` (or `vrm`).
6. Enter your Site ID, Token, and Instance IDs.

### Manual Installation

1. Download the [latest release](https://github.com/KingKongKent/VRM-API/releases).
2. Copy `custom_components/victron_vrm_api/` into your Home Assistant `config/custom_components/` directory.
3. Restart Home Assistant.
4. Go to **Settings → Devices & Services → Add Integration**.
5. Search for `victron vrm api` and configure.

---

## Configuration

All configuration is handled through the Home Assistant UI — no YAML configuration is supported.

### Config Flow Fields

| Field | Required | Example | Description |
| :--- | :---: | :--- | :--- |
| **Site ID** | Yes | `337075` | Your VRM Installation ID |
| **Token** | Yes | `cf2e981f...` | VRM API Bearer token |
| **Battery Instance IDs** | No | `288, 291` | Comma-separated battery instance IDs |
| **MultiPlus Instance IDs** | No | `291` | Comma-separated MultiPlus instance IDs |
| **PV Inverter Instance IDs** | No | `200, 201` | Comma-separated PV Inverter instance IDs |
| **Tank Instance IDs** | No | `300` | Comma-separated Tank instance IDs |
| **Solar Charger Instance IDs** | No | `289, 290` | Comma-separated Solar Charger instance IDs |

### Notes

- If an instance ID field is left empty (or set to `0`), that device type will **not** be created.
- Multiple instances per device type are separated by commas.
- **Reconfiguration** is supported — use the integration's **Reconfigure** button in HA to update credentials or instance IDs without removing the entry.

---

## Supported Devices & Sensors

### Device Overview

| Device Type | Sensors per Instance | Description |
| :--- | :---: | :--- |
| **Battery** | up to 39 | SOC, voltage, current, power, alarms, diagnostics |
| **MultiPlus** | up to 35 | AC/DC voltages, currents, power, ESS settings, diagnostics |
| **PV Inverter** | up to 17 | Per-phase voltage, current, power, energy yields |
| **Tank** | up to 6 | Level, capacity, remaining, type, status |
| **Solar Charger** | up to 16 | PV voltage/current, charge state, yields, diagnostics |
| **Overall Stats** | 16 | Solar yield, consumption, grid in/out for day/week/month/year |
| **System Overview** | 10 per device | Firmware, serial, connection info for all detected devices |
| **Total** | **134+** | Depends on your installation |

---

### Battery Sensors

| Sensor Name | VRM ID | Unit | Description |
| :--- | :---: | :---: | :--- |
| State of Charge | `51` | % | Battery SOC |
| Voltage | `47` | V | Battery voltage |
| Starter Battery Voltage | `48` | V | Starter battery voltage |
| Current | `49` | A | Battery current |
| Consumed Amphours | `50` | Ah | Consumed Ah |
| Time to Go | `52` | h | Time until empty |
| Battery Temperature | `115` | °C | Battery temperature |
| Minimum Cell Voltage | `173` | V | Min cell voltage (BMS) |
| Maximum Cell Voltage | `174` | V | Max cell voltage (BMS) |
| Mid Voltage | `64` | V | Mid-point voltage |
| Battery Power | *calc* | W | Calculated (V × A) |
| Battery Charge Cycles | `58` | — | Full charge cycle count |
| Battery to Consumers (Today) | `Bc` | kWh | Energy to load today |
| Battery to Grid (Today) | `Bg` | kWh | Energy to grid today |

#### Battery Alarms (up to 21 sensors)

| Sensor Name | VRM ID | Description |
| :--- | :---: | :--- |
| Low Voltage Alarm | `119` | Low voltage detected |
| High Voltage Alarm | `120` | High voltage detected |
| Low Starter-Voltage Alarm | `121` | Low starter voltage |
| High Starter-Voltage Alarm | `122` | High starter voltage |
| Low State-of-Charge Alarm | `123` | Low SOC |
| Low Battery Temperature Alarm | `124` | Temperature too low |
| High Battery Temperature Alarm | `125` | Temperature too high |
| Mid-Voltage Alarm | `126` | Mid-voltage anomaly |
| Low Fused-Voltage Alarm | `155` | Low fused voltage |
| High Fused-Voltage Alarm | `156` | High fused voltage |
| Fuse Blown Alarm | `157` | Fuse blown |
| High Internal-Temperature Alarm | `158` | Internal temperature alarm |
| Cell Imbalance Alarm | `286` | Cell imbalance detected |
| High Charge Current Alarm | `287` | Charge current too high |
| High Discharge Current Alarm | `288` | Discharge current too high |
| Internal Failure | `289` | Internal failure |
| High Charge Temperature Alarm | `459` | Charge temp too high |
| Low Charge Temperature Alarm | `460` | Charge temp too low |
| Low Cell Voltage | `522` | Low cell voltage |
| Charge Blocked | `739` | Charging blocked (BMS) |
| Discharge Blocked | `740` | Discharging blocked (BMS) |

#### Battery Diagnostics (7 sensors per instance)

| Sensor Name | VRM ID | Unit | Description |
| :--- | :---: | :---: | :--- |
| Deepest Discharge | `55` | Ah | Deepest discharge recorded |
| Last Discharge | `56` | Ah | Most recent discharge |
| Average Discharge | `57` | Ah | Average discharge depth |
| Total Ah Drawn | `60` | Ah | Lifetime Ah drawn |
| Minimum Voltage | `61` | V | Recorded minimum voltage |
| Maximum Voltage | `62` | V | Recorded maximum voltage |
| Time Since Last Full Charge | `63` | s | Seconds since last full charge |

---

### MultiPlus Sensors

| Sensor Name | VRM ID | Unit | Description |
| :--- | :---: | :---: | :--- |
| AC Input Frequency | `6` | Hz | AC input frequency |
| AC Input Voltage L1/L2/L3 | `8`/`9`/`10` | V | AC input voltage per phase |
| AC Input Current L1/L2/L3 | `11`/`12`/`13` | A | AC input current per phase |
| AC Input Power L1/L2/L3 | `17`/`18`/`19` | W | AC input power per phase |
| AC Output Voltage L1/L2/L3 | `20`/`21`/`22` | V | AC output voltage per phase |
| AC Output Frequency | `23` | Hz | AC output frequency |
| AC Output Current L1/L2/L3 | `14`/`15`/`16` | A | AC output current per phase |
| AC Output Power L1/L2/L3 | `29`/`30`/`31` | W | AC output power per phase |
| DC Bus Voltage | `32` | V | DC bus voltage |
| DC Bus Current | `33` | A | DC bus current |
| DC Bus Power | *calc* | W | Calculated (DC V × DC A) |
| Active Input Source | `35` | — | Grid/Generator/Shore |
| VE.Bus State | `40` | — | Operating state |
| Switch Position | `44` | — | Charger/Inverter/On/Off |
| Grid Setpoint | `242` | W | ESS grid setpoint target |
| SOC Limit | `243` | % | ESS minimum SOC limit |
| Active SOC Limit | `244` | % | ESS active SOC limit |
| MultiPlus Temperature | `521` | °C | Device temperature |
| Grid to Consumers (Today) | `Gc` | kWh | Energy from grid to load today |
| Grid to Battery (Today) | `Gb` | kWh | Energy from grid to battery today |

#### MultiPlus Diagnostics (4 sensors per instance)

| Sensor Name | VRM ID | Unit | Description |
| :--- | :---: | :---: | :--- |
| Active Input Current Limit | `27` | A | Active input current limit |
| VE.Bus Error | `41` | — | VE.Bus error code |
| Low Battery | `43` | — | Low battery warning |
| Charge State | `557` | — | Current charge state |

---

### PV Inverter Sensors

| Sensor Name | VRM ID | Unit | Description |
| :--- | :---: | :---: | :--- |
| L1/L2/L3 Voltage | `203`/`207`/`211` | V | Voltage per phase |
| L1/L2/L3 Current | `204`/`208`/`212` | A | Current per phase |
| L1/L2/L3 Power | `205`/`209`/`213` | W | Power per phase |
| L1/L2/L3 Energy | `206`/`210`/`214` | kWh | Energy yield per phase (total) |
| Status | `246` | — | Status code |
| PV to Consumers (Today) | `Pc` | kWh | Energy from PV to load today |
| PV to Battery (Today) | `Pb` | kWh | Energy from PV to battery today |
| PV to Grid (Today) | `Pg` | kWh | Energy from PV to grid today |
| PV Total Today | *calc* | kWh | Sum of Pc + Pb + Pg |

---

### Tank Sensors

| Sensor Name | VRM ID | Unit | Description |
| :--- | :---: | :---: | :--- |
| Capacity | `328` | m³ | Tank capacity |
| Type | `329` | — | Fluid type |
| Level | `330` | % | Fluid level percentage |
| Remaining | `331` | m³ | Remaining fluid volume |
| Status | `443` | — | Tank status |
| Custom Name | `638` | — | User-defined name |

---

### Solar Charger Sensors

| Sensor Name | VRM ID | Unit | Description |
| :--- | :---: | :---: | :--- |
| Battery Voltage | `81` | V | Battery voltage |
| PV Voltage | `82` | V | Solar panel voltage |
| Battery Temperature | `83` | °C | Battery temperature (external) |
| PV Current | `84` | A | Solar panel current |
| Charge State | `85` | — | Bulk / Absorption / Float |
| Error Code | `88` | — | Error code |
| Relay Status | `90` | — | Relay state |
| Yield Today | `94` | kWh | Energy yield today |
| Max Power Today | `95` | W | Maximum power today |
| Yield Yesterday | `96` | kWh | Energy yield yesterday |
| Battery Watts | `107` | W | Charging power to battery |

#### Solar Charger Diagnostics (5 sensors per instance)

| Sensor Name | VRM ID | Unit | Description |
| :--- | :---: | :---: | :--- |
| PV Voltage (diag) | `86` | V | PV voltage (alternate source) |
| Max Power Yesterday | `97` | W | Maximum power yesterday |
| Error Code (diag) | `98` | — | Error code (alternate source) |
| PV Power | `442` | W | Current PV power |
| MPPT State | `518` | — | MPPT tracker state |

---

### Overall Stats (16 sensors)

| Metric | Periods | Key |
| :--- | :--- | :--- |
| Total Solar Yield | Today / Week / Month / Year | `total_solar_yield` |
| Total Consumption | Today / Week / Month / Year | `total_consumption` |
| Grid Energy In | Today / Week / Month / Year | `grid_history_from` |
| Grid Energy Out | Today / Week / Month / Year | `grid_history_to` |

---

### System Overview (10 sensors per detected device)

| Sensor Name | Key | Description |
| :--- | :--- | :--- |
| Firmware | `firmwareVersion` | Device firmware version |
| Last Connection | `lastConnection` | Last connection timestamp |
| Product Name | `productName` | Device product name |
| Remote IP | `remoteOnLan` | Remote IP address |
| Connection Info | `connectionInformation` | Connection details |
| Auto Update | `autoUpdate` | Auto-update status |
| Battery Family | `batteryFamily` | Battery family type |
| Battery Manufacturer | `batteryManufacturer` | Battery manufacturer |
| Serial Number | `machineSerialNumber` | Device serial number |
| Instance ID | `instance` | Device instance ID |

---

## Architecture

### Repository Structure

```
custom_components/victron_vrm_api/
├── __init__.py          # Entry point — platform setup/teardown
├── config_flow.py       # UI-based configuration flow + reconfigure
├── const.py             # Constants, config keys, scan intervals
├── manifest.json        # HA integration manifest (version, domain, etc.)
├── sensor.py            # All sensor entities and data coordinators (~1200 lines)
└── translations/
    ├── en.json           # English UI strings
    └── de.json           # German UI strings
docs/                    # Screenshots for README
.github/
├── workflows/validate.yml  # HACS validation CI
└── ISSUE_TEMPLATE/         # GitHub issue templates
```

### Component Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                  Home Assistant                               │
│                                                               │
│  config_flow.py ──► __init__.py ──► sensor.py                │
│  (UI Setup)        (Entry Point)   (Coordinators + Entities) │
│                                         │                     │
│                              ┌──────────┤                     │
│                              ▼          ▼                     │
│                      system-overview  diagnostics             │
│                       (device list)  (timestamps)             │
│                              └────┬─────┘                     │
│                                   ▼                           │
│                        _build_instance_remap()                │
│                     {configured_id → live_id}                 │
│                                   │                           │
│                          VrmDataCoordinator                   │
│                         (one per endpoint)                    │
│                                   │                           │
│                     async_get_clientsession ──► VRM API       │
│                     (HA managed session)       (HTTPS)        │
└──────────────────────────────────────────────────────────────┘
```

### Key Classes

| Class | Base Class | Purpose |
| :--- | :--- | :--- |
| `VrmDataCoordinator` | `DataUpdateCoordinator` | Fetches data from one VRM API endpoint |
| `VrmBaseSensor` | `CoordinatorEntity` + `SensorEntity` | Abstract base for all sensors |
| `VrmBatterySummarySensor` | `VrmBaseSensor` | Battery summary widget data |
| `VrmBatteryAlarmSensor` | `VrmBaseSensor` | Battery alarm/warning states |
| `VrmBatteryPowerSensor` | `VrmBaseSensor` | Calculated battery power (V × A) |
| `VrmMultiStatusSensor` | `VrmBaseSensor` | MultiPlus status data |
| `VrmMultiPlusDCPowerSensor` | `VrmBaseSensor` | Calculated DC power (V × A) |
| `VrmPvInverterSensor` | `VrmBaseSensor` | PV Inverter status data |
| `VrmPvTotalTodaySensor` | `VrmBaseSensor` | Calculated PV total (Pc + Pb + Pg) |
| `VrmTankSensor` | `VrmBaseSensor` | Tank data |
| `VrmSolarChargerSensor` | `VrmBaseSensor` | Solar charger data |
| `VrmOverallStatsSensor` | `VrmBaseSensor` | Navigates nested stats dict via data path |
| `VrmSystemOverviewSensor` | `VrmBaseSensor` | System overview per-device fields |
| `VrmDiagnosticSensor` | `VrmBaseSensor` | Diagnostics endpoint data |

### Data Flow

1. **`async_setup_entry()`** in `sensor.py` creates one `VrmDataCoordinator` per API endpoint.
2. Each coordinator calls `_async_update_data()` on its scan interval.
3. The coordinator uses HA's managed `async_get_clientsession()` to make HTTPS requests to the VRM API.
4. Sensor entities (extending `CoordinatorEntity`) automatically update when their coordinator receives new data.
5. If a coordinator fails, HA's built-in retry mechanism schedules the next attempt at the normal interval.

---

## API Reference

### Base URL

```
https://vrmapi.victronenergy.com/v2/installations/{site_id}/
```

### Authentication

All requests include the header:

```
X-Authorization: Token {your_vrm_token}
```

### Endpoints Used

| Endpoint | Method | Response Key | Description |
| :--- | :---: | :--- | :--- |
| `overallstats` | GET | `records` | Overall energy statistics |
| `stats?type=kwh&interval=15mins` | GET | `records`, `totals` | kWh stats with energy flow totals (Bc, Bg, Gc, Gb, Pc, Pb, Pg) |
| `system-overview` | GET | `records` | Device metadata for all detected devices |
| `diagnostics` | GET | `records` | Comprehensive diagnostic data per device |
| `widgets/BatterySummary?instance={id}` | GET | `records` | Battery summary data |
| `widgets/HistoricData?instance={id}` | GET | `records` | Battery history (charge cycles, mid-voltage) |
| `widgets/BatteryMonitorWarningsAndAlarms?instance={id}` | GET | `records` | Battery alarms and warnings |
| `widgets/Status?instance={id}` | GET | `records` | MultiPlus status |
| `widgets/PVInverterStatus?instance={id}` | GET | `records` | PV Inverter status |
| `widgets/TankSummary?instance={id}` | GET | `records` | Tank summary |
| `widgets/SolarChargerSummary?instance={id}` | GET | `records` | Solar charger summary |

### Response Handling

- **HTTP 200**: Data parsed from JSON response.
- **HTTP 204**: No data available — sensor shows as unavailable (not an error).
- **HTTP 429**: Rate limited — increase scan intervals.
- **Other**: Raises `UpdateFailed` for HA to retry on next cycle.

---

## Scan Intervals

| Device Type | Interval | Rationale |
| :--- | :--- | :--- |
| Battery (summary, history, alarms) | **20 seconds** | Real-time monitoring |
| MultiPlus | **20 seconds** | Real-time monitoring |
| PV Inverter | **20 seconds** | Real-time monitoring |
| Solar Charger | **20 seconds** | Real-time monitoring |
| Tank | **60 seconds** | Slow-changing data |
| Overall Stats | **300 seconds** (5 min) | Aggregated data, less volatile |
| Energy Stats (kWh) | **300 seconds** (5 min) | Aggregated daily totals |
| Diagnostics | **300 seconds** (5 min) | Historical/diagnostic data |
| System Overview | **1200 seconds** (20 min) | Device metadata, rarely changes |

Intervals are defined in `const.py` and can be adjusted there if needed. Be mindful of VRM API rate limits.

---

## Error Handling

The integration uses several layers of error handling:

| Layer | Behavior |
| :--- | :--- |
| **HTTP errors** | Non-200/204 status raises `UpdateFailed`; HA retries at next interval |
| **Connection errors** | `aiohttp.ClientError` caught, raises `UpdateFailed` |
| **Timeout** | 15-second timeout via `aiohttp.ClientTimeout(total=15)` |
| **First refresh failure** | Each coordinator's initial refresh is wrapped in try/except — one failing device doesn't block others |
| **Missing data** | Calculated sensors (Power, PV Total) return `0.0` instead of erroring |
| **Session management** | Uses HA's managed `async_get_clientsession()` — no manual session lifecycle |

---

## Troubleshooting

### Sensors show "Unavailable"

1. **Verify credentials**: Check that your Site ID and Token are correct in the integration config.
2. **Check VRM Portal**: Ensure your installation is online and reporting data.
3. **Check HA logs**: Filter for `victron_vrm_api`:
   ```
   Settings → System → Logs → filter: victron_vrm_api
   ```
4. **Enable debug logging**: Add to `configuration.yaml`:
   ```yaml
   logger:
     logs:
       custom_components.victron_vrm_api: debug
   ```
5. **Restart HA**: After a HA update, restart to ensure the integration reloads properly.

### Sensors show stale values (e.g., stuck on "Absorption")

This can happen when VRM caches the `formattedValue` server-side. Since v1.6.0, enum values are resolved from `rawValue` via the `dataAttributeEnumValues` map. Ensure you are running v1.6.0 or later.

### Instance ID changed after firmware update or Cerbo restart

VRM may reassign device instance IDs (e.g., VE.Bus from 291 to 290). Since v1.6.0, the integration auto-detects this using diagnostics timestamps and remaps API calls to the new instance while keeping entity IDs stable. Check the HA log for:
```
VRM instance remap for multi: configured 291 → live 290
```
If the remap doesn't trigger, verify that both the old and new instances appear in your VRM system-overview.

### Error `429 Too Many Requests`

The VRM API is rate-limiting your requests. Increase scan intervals in `const.py`:
```python
DEFAULT_SCAN_INTERVAL_BATTERY = 30      # was 20
DEFAULT_SCAN_INTERVAL_MULTI = 30        # was 20
DEFAULT_SCAN_INTERVAL_OVERALL = 600     # was 300
```

### Sensors show "Unknown"

This usually means the VRM API returned data but the specific sensor ID was not present. This is expected for:
- 3-phase sensors on a 1-phase system
- ESS sensors on a non-ESS system
- Alarm sensors when no alarms are active

The integration uses **smart sensor creation** — sensors are only created when data is actually available (since v1.5.6).

### Integration won't load after HA update

This was fixed in **v1.5.9**. Ensure you're running the latest version. The fix addresses aiohttp compatibility with HA 2026.2.x:
- Uses HA's managed session instead of raw `aiohttp.ClientSession()`
- Uses `aiohttp.ClientTimeout(total=15)` instead of bare integer timeout

---

## Development Guide

### Setting Up a Dev Environment

```bash
# Clone the repository
git clone https://github.com/KingKongKent/VRM-API.git
cd VRM-API

# Create a virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/macOS

# Install dependencies for testing
pip install aiohttp paramiko
```

### Test Scripts

| Script | Purpose |
| :--- | :--- |
| `test_vrm_api.py` | Basic API connectivity test |
| `test_all_endpoints.py` | Pull data from all API endpoints |
| `test_pull_all_data.py` | Download and save full API data |
| `test_analyze_data.py` | Analyze captured API responses |
| `test_diagnostics_endpoint.py` | Test the diagnostics endpoint |
| `test_device_comparison.py` | Compare device data across captures |
| `test_final_comparison.py` | Final validation of data consistency |
| `test_sensor_values_table.py` | Display sensor values in table format |

### Adding a New Sensor to an Existing Device

1. Find the VRM data attribute ID (check captured data in `api_data_*/` or the VRM API).
2. Add the sensor definition to the appropriate config dictionary in `sensor.py`:
   ```python
   "sensor_key": ("data_id", "Display Name", SensorDeviceClass.X, SensorStateClass.Y, "unit", "mdi:icon"),
   ```
3. Update the sensor tables in `README.md` and this documentation.

### Adding a New Device Type

1. Add `CONF_*_INSTANCE` constant in `const.py`.
2. Add `DEFAULT_SCAN_INTERVAL_*` constant in `const.py`.
3. Update `config_flow.py` — add the new field to `DATA_SCHEMA`.
4. Add translations in `translations/en.json` and `translations/de.json`.
5. In `sensor.py`:
   - Create a sensor config dictionary.
   - Add coordinator setup in `async_setup_entry()`.
   - Create a sensor entity class extending `VrmBaseSensor`.
6. Bump version in `manifest.json`.

### Adding a New Language

1. Copy `translations/en.json` to `translations/<lang_code>.json`.
2. Translate all string values while keeping the JSON keys unchanged.

---

## Deployment

### Deploy to a Local HA Instance

See [DEPLOY_LOCAL.md](DEPLOY_LOCAL.md) for full details.

**Quick methods:**

```powershell
# Option 1: Use the deployment script
.\deploy_to_ha.ps1

# Option 2: SCP
scp -r custom_components/victron_vrm_api root@<HA_IP>:/config/custom_components/

# Option 3: Python SFTP (if SSH requires password and sshpass is unavailable)
# See deploy scripts in the repo
```

After deploying:
1. Restart Home Assistant (Settings → System → Restart).
2. Verify the integration loads without errors in Settings → Devices & Services.
3. Check Developer Tools → States and filter by `vrm` to see sensor values.

### Release Checklist

1. Update `manifest.json` version.
2. Commit changes with a descriptive message.
3. Tag the commit: `git tag v1.x.y`.
4. Push: `git push origin main --tags`.
5. Create a GitHub Release: `gh release create v1.x.y --title "v1.x.y" --notes "Description"`.
6. HACS will pick up the new release automatically.

---

## Changelog

### v1.6.0 — Instance auto-remap + enum resolution fix
- **Feature**: Automatic instance ID remap — when VRM reassigns a device instance (e.g., VE.Bus 291 → 290 after Cerbo restart), the integration detects this at startup using diagnostics timestamps and automatically queries the correct live instance. Dashboard entities stay stable under their original IDs.
- **Fix**: Enum values (Charge State, VE.Bus State, etc.) now resolve via `dataAttributeEnumValues` + `rawValue` instead of trusting VRM's `formattedValue`, which can be stale server-side. Fixes sensors stuck on "Absorption" when the actual state is "Float".
- Both fixes apply to all 5 device sensor classes: MultiPlus, PV Inverter, Tank, Solar Charger, and Diagnostics.

### v1.5.9 — Fix aiohttp compatibility with HA 2026.2.x
- **Fix**: Replace raw `aiohttp.ClientSession()` with HA's managed `async_get_clientsession()`.
- **Fix**: Use `aiohttp.ClientTimeout(total=15)` instead of bare integer timeout (required by aiohttp 3.11+).
- **Fix**: Broaden exception handling in coordinator first refresh to prevent silent failures.
- Added project documentation, deployment guide, and deploy script.

### v1.5.8 — Fix diagnostics endpoint + decimal precision
- Fix diagnostics endpoint parsing.
- Add decimal precision display for sensor values.

### v1.5.6 — Smart sensor creation
- Only create MultiPlus sensors when data is actually available.
- Prevents "Unknown" / "Unavailable" sensors on systems with fewer phases or devices.

### v1.5.5 — New MultiPlus sensors
- Add Active Input Source, Switch Position, Grid Setpoint, SOC Limits (ESS).

### v1.5.4 — Expanded sensor coverage
- Add MultiPlus L2/L3 phases, currents, frequencies.
- Add Solar Charger PV voltage/current, max power, error code.
- Add Battery mid-voltage sensor.

### v1.5.3 — Starter Battery + System Overview
- Add Starter Battery Voltage sensor.
- Add System Overview device with per-device metadata.

### v1.5.2 — HACS default repository
- HACS registration and validation.

---

## FAQ

**Q: Can I use this integration without HACS?**
A: Yes. Download the release ZIP and copy `custom_components/victron_vrm_api/` into your HA config directory manually.

**Q: How many API calls does this integration make?**
A: It depends on your configured devices. Each device type has its own coordinator with its own interval. For a typical setup with 2 batteries, 1 MultiPlus, and 2 solar chargers: approximately 10–12 API calls every 20 seconds for real-time data, plus 4–5 calls every 5 minutes for stats/diagnostics.

**Q: Does this work with the Victron local (Modbus/TCP) integration?**
A: Yes. This integration (cloud-based VRM API) can run alongside local Modbus integrations like `victron` (by @sfstar). They use different data sources and create separate entities.

**Q: Why do some sensors show "Unknown"?**
A: The VRM API may not return data for sensors that don't apply to your hardware (e.g., 3-phase sensors on a 1-phase system). Since v1.5.6, these sensors are no longer created.

**Q: Can I change the polling intervals?**
A: Yes. Edit the `DEFAULT_SCAN_INTERVAL_*` constants in `const.py`. Be careful not to set them too low to avoid VRM API rate limiting (HTTP 429).

**Q: Does this integration support writing/controlling devices?**
A: No. This integration is read-only (cloud polling). To control Victron devices, use a local Modbus integration.

---

## Contributing

1. Fork the repository.
2. Create a feature branch.
3. Follow existing code patterns and conventions.
4. Test with the provided test scripts and a local HA instance.
5. Submit a Pull Request with a clear description of changes.

For bug reports and feature requests, use the [GitHub Issue Tracker](https://github.com/KingKongKent/VRM-API/issues).

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

## Support

If you find this integration useful, consider supporting the project:

[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-donate-yellow.svg)](https://buymeacoffee.com/KingKongKent)
