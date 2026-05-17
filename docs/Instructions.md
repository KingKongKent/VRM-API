# Instructions — Victron VRM API for Home Assistant

## Project Overview

This is a **Home Assistant custom integration** that connects to the [Victron VRM Portal](https://vrm.victronenergy.com/) API to pull real-time data from Victron Energy installations. It supports Battery, MultiPlus, PV Inverter, Tank, Solar Charger, Overall Stats, System Overview, and Diagnostics devices.

- **Domain**: `victron_vrm_api`
- **Integration type**: Hub (cloud polling)
- **Configuration**: UI-based config flow only (no YAML)
- **Minimum HA version**: 2025.1
- **Current version**: 1.6.1

---

## Repository Structure

```
custom_components/victron_vrm_api/   ← Integration source code
├── __init__.py                      ← Entry point, platform setup/teardown
├── config_flow.py                   ← UI configuration flow + reconfigure
├── const.py                         ← Constants, config keys, scan intervals
├── manifest.json                    ← HA integration manifest
├── sensor.py                        ← All sensor entities & data coordinators
└── translations/
    ├── en.json                      ← English UI strings
    └── de.json                      ← German UI strings
docs/                                ← Screenshots for README
├── architecture.md                  ← Runtime architecture and diagram
├── security.md                      ← Boundaries, pitfalls, risk register
.github/
├── workflows/validate.yml           ← HACS validation workflow
├── skills/                          ← Workspace maintenance skills
├── ISSUE_TEMPLATE/                  ← GitHub issue templates
└── FUNDING.yml                      ← Sponsorship config
scripts/                             ← Local helpers; not shipped
tests/                               ← API test/exploration scripts; not shipped
api_data_*/                          ← Captured API response samples; ignored
hacs.json                            ← HACS metadata
```

## Boundaries, Security, and Pitfalls

- Only `custom_components/victron_vrm_api/` ships to users.
- Never commit `.env`, real VRM tokens, HA tokens, SSH keys, local deployment targets, or private API captures.
- Use placeholders in docs. Do not include real-looking token examples.
- Token fields must use password selectors and reconfigure must not prefill saved tokens.
- Patch vulnerable behavior before documenting around it.
- Track repeated mistakes and vulnerabilities in [security.md](security.md).
- Keep architecture changes in [architecture.md](architecture.md).

Common pitfalls:

| Pitfall | Correct pattern |
| :--- | :--- |
| VRM `formattedValue` can be stale | Resolve enum/status values through raw enum data and `dataAttributeEnumValues` first |
| VRM can list stale and live instances together | Use diagnostics timestamps for instance auto-remap |
| Missing data can create noisy entities | Create sensors only when the API returns the attribute |
| Local deploy scripts can leak environment details | Keep them ignored or fully generic |
| Aggressive polling can cause HTTP 429 | Keep scan intervals conservative |

---

## Prerequisites

Before using or developing this integration you need:

1. **VRM Access Token** — Create at [VRM Portal → Preferences → Integrations → Access tokens](https://vrm.victronenergy.com/access-tokens). Keep this secret.
2. **Site ID** — Your VRM Installation ID, visible in the VRM Portal URL.
3. **Instance IDs** — Device instance numbers for Battery, MultiPlus, PV Inverter, Tank, and/or Solar Charger. Found in the VRM Portal device list (see `docs/vrm-api-description.png` for guidance).

---

## Installation

### Via HACS (Recommended)

1. Add this repository to HACS or use the [one-click add link](https://my.home-assistant.io/redirect/hacs_repository/?owner=KingKongKent&repository=VRM-API&category=integration).
2. Install the integration from HACS.
3. Go to **Settings → Devices & Services → Add Integration**.
4. Search for `victron vrm api` (or `vrm`).
5. Enter your Site ID, Token, and Instance IDs.

### Manual Installation

1. Download the latest release.
2. Copy the `custom_components/victron_vrm_api/` folder into your Home Assistant `config/custom_components/` directory.
3. Restart Home Assistant.
4. Go to **Settings → Devices & Services → Add Integration**.
5. Search for `victron vrm api` and configure.

---

## Configuration

All configuration is done through the Home Assistant UI. The config flow asks for:

| Field | Required | Description |
| :--- | :---: | :--- |
| **Site ID** | Yes | Your VRM Installation ID |
| **Token** | Yes | VRM API token; never commit a real value |
| **Battery Instance IDs** | No | Comma-separated (e.g., `512` or `288, 291`) |
| **MultiPlus Instance IDs** | No | Comma-separated (e.g., `257`) |
| **PV Inverter Instance IDs** | No | Comma-separated (e.g., `200, 201`) |
| **Tank Instance IDs** | No | Comma-separated (e.g., `300`) |
| **Solar Charger Instance IDs** | No | Comma-separated (e.g., `279, 288, 289`) |

- If an instance ID field is left empty (or `0`), that device type will not be created.
- You can add multiple instances per device type, separated by commas.
- Reconfiguration is supported via the integration's **Reconfigure** button.

---

## Architecture & Code Guide

### Entry Point (`__init__.py`)

- Registers the `sensor` platform only.
- `async_setup_entry()` stores config data in `hass.data[DOMAIN]` and forwards setup to `sensor.py`.
- `async_unload_entry()` cleanly removes data and unloads platforms.
- No YAML configuration support — config flow only.

### Config Flow (`config_flow.py`)

- `VictronVrmConfigFlow` handles initial setup and reconfiguration.
- Uses `CONF_SITE_ID` as the unique ID to prevent duplicate entries.
- On reconfigure, pre-fills current values in the form.

### Constants (`const.py`)

- `DOMAIN = "victron_vrm_api"`
- All `CONF_*` keys for config entries.
- Default scan intervals:
  - Battery / MultiPlus / PV Inverter / Solar Charger: **20 seconds**
  - Tank: **60 seconds**
  - Overall Stats: **300 seconds** (5 minutes)
  - System Overview: **1200 seconds** (20 minutes)

### Sensors (`sensor.py`)

This is the main file (~1200 lines) containing:

- **`VrmDataCoordinator`** — Extends `DataUpdateCoordinator`. Fetches data from VRM API endpoints. One coordinator per device/endpoint.
- **Sensor entity classes** — Use `CoordinatorEntity` pattern for efficient updates.
- **API Base URL**: `https://vrmapi.victronenergy.com/v2/installations/`
- **Authentication**: `X-Authorization: Token <token>` header.

#### Supported Device Types & Endpoints

| Device Type | API Endpoint | Sensors |
| :--- | :--- | :---: |
| Battery | `widgets/BatterySummary?instance=<id>` | 35 |
| MultiPlus | `widgets/...?instance=<id>` | 29 |
| PV Inverter | `widgets/...?instance=<id>` | 16 |
| Tank | `widgets/TankSummary?instance=<id>` + diagnostics fallback | 6 |
| Solar Charger | `widgets/...?instance=<id>` | 11 |
| Overall Stats | `stats` (totals for day/week/month/year) | 16 |
| System Overview | `system-overview` (all detected devices) | 10/device |
| Diagnostics | `diagnostics` | 28+ |

### Translations (`translations/`)

- `en.json` and `de.json` provide localized config flow labels and descriptions.
- To add a new language, create a new JSON file following the same structure.

---

## Development Workflow

### Local Testing

Several test scripts are provided in the repository root for exploring and validating VRM API responses:

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

### Deploying to a Local Home Assistant Instance

See [DEPLOY_LOCAL.md](DEPLOY_LOCAL.md) for detailed instructions. Quick summary:

```powershell
# Option 1: SCP
scp -r custom_components/victron_vrm_api root@<HA_IP>:/config/custom_components/

# Option 2: Use the deployment script
.\scripts\deploy_to_ha.ps1
```

After deploying, restart Home Assistant or reload the integration.

### Adding a New Sensor

1. Identify the VRM API data attribute ID (check VRM API docs or captured data in `api_data_*/`).
2. Add the sensor definition tuple to the appropriate `*_sensors_config` dictionary in `sensor.py`:
   ```python
   "sensor_key": ("data_id", "Display Name", SensorDeviceClass.X, SensorStateClass.Y, "unit", "mdi:icon"),
   ```
3. If adding a new device type or endpoint, create a new `VrmDataCoordinator` instance and corresponding sensor entity class.
4. Update `const.py` if new config keys or scan intervals are needed.
5. Update translations in `translations/en.json` and `translations/de.json`.
6. Update `README.md` sensor tables.

### Adding a New Device Type

1. Add a new `CONF_*_INSTANCE` constant in `const.py`.
2. Add a default scan interval constant in `const.py`.
3. Update `config_flow.py` to include the new field in `DATA_SCHEMA`.
4. Add translations for the new field.
5. In `sensor.py`, create:
   - A sensor config dictionary mapping keys to `(data_id, name, device_class, state_class, unit, icon)`.
   - A coordinator setup in `async_setup_entry()`.
   - Sensor entity creation logic.
6. Update `manifest.json` version.

---

## Versioning & Release

- Version is tracked in `manifest.json` (`"version": "x.y.z"`).
- Follow [Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH`.
- The HACS validation workflow (`.github/workflows/validate.yml`) runs automatically on push/PR.
- HACS metadata is in `hacs.json`.

---

## Key API Details

- **Base URL**: `https://vrmapi.victronenergy.com/v2/installations/{site_id}/`
- **Auth Header**: `X-Authorization: Token {token}`
- **Response format**: JSON with `records` or `totals` keys depending on endpoint.
- **Rate limiting**: Be mindful of VRM API rate limits — do not set scan intervals too low.
- **HTTP 204**: Returned when no data is available; handled gracefully by the coordinator.

---

## Troubleshooting

- **No sensors appearing**: Verify your Site ID, Token, and Instance IDs are correct. Check HA logs for API errors.
- **`429 Too Many Requests`**: Increase scan intervals in `const.py`.
- **Stale data**: Check VRM Portal to confirm your installation is online and reporting.
- **Reconfigure**: Use the integration's Reconfigure button in HA to update credentials or instance IDs without removing the integration.
- **Logs**: Filter Home Assistant logs for `victron_vrm_api` to see API errors and coordinator updates.

---

## Contributing

1. Fork the repository.
2. Create a feature branch.
3. Make changes following the existing code patterns.
4. Test with the provided test scripts and on a local HA instance.
5. Submit a Pull Request with a clear description of changes.

For feature requests, use the [GitHub Issue Template](https://github.com/KingKongKent/VRM-API/issues/new?template=feature_request.md).
