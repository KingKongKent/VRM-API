# Inventory — Victron VRM API for Home Assistant

> Last updated: 2026-05-17 | Version: **1.6.1**

## What Ships to Users

Only `custom_components/victron_vrm_api/` is distributed (via HACS or manual copy).

| File | Purpose |
| :--- | :--- |
| `__init__.py` | Integration entry point — platform setup, teardown, reload |
| `config_flow.py` | UI-based configuration flow + reconfigure support |
| `const.py` | Domain name, config keys, scan-interval defaults |
| `manifest.json` | HA integration manifest (version, dependencies, domain) |
| `sensor.py` | All sensor entities, data coordinators, API calls (~1200 lines) |
| `translations/en.json` | English UI strings |
| `translations/de.json` | German UI strings |

## Repository Structure

```
.
├── custom_components/victron_vrm_api/   ← shipped to users
│   ├── __init__.py
│   ├── config_flow.py
│   ├── const.py
│   ├── manifest.json
│   ├── sensor.py
│   └── translations/
│       ├── en.json
│       └── de.json
├── docs/                                ← documentation & screenshots
│   ├── documentation.md                 Full API reference & changelog
│   ├── architecture.md                  Runtime architecture and Mermaid diagram
│   ├── security.md                      Boundaries, pitfalls, and risk register
│   ├── Instructions.md                  Developer architecture guide
│   ├── DEPLOY_LOCAL.md                  Local deployment checklist
│   ├── sensor_v1.4_backup.py            Pre-diagnostics sensor.py backup
│   └── *.png                            Screenshots for README
├── scripts/                             ← developer utilities (not shipped)
│   ├── README.md                        Script boundary and safety rules
│   └── deploy_to_ha.ps1                 SCP / file-share deploy helper
├── tests/                               ← API test scripts (not shipped)
│   ├── test_vrm_api.py                  Basic API connectivity test
│   ├── test_all_endpoints.py            Full endpoint sweep
│   ├── test_analyze_data.py             Analyse captured JSON responses
│   ├── test_device_comparison.py        HA entity vs API data comparison
│   ├── test_diagnostics_endpoint.py     Diagnostics endpoint test
│   ├── test_final_comparison.py         Final validation
│   ├── test_pull_all_data.py            Download all API data to JSON
│   └── test_sensor_values_table.py      Pretty-print sensor values
├── api_data_*/                          ← captured API samples (gitignored)
├── .env.example                         ← credential template
├── .github/
│   ├── copilot-instructions.md          Copilot coding rules
│   ├── skills/                          Workspace maintenance skills
│   └── workflows/validate.yml           HACS validation CI
├── hacs.json                            HACS metadata
├── LICENSE                              Licence file
├── INVENTORY.md                         This file
└── README.md                            Project overview & quick start
```

## Supported Devices & Sensors (134+)

| Device Type | Sensors | Endpoint | Scan Interval |
| :--- | :---: | :--- | :--- |
| Battery | 35 | `widgets/BatterySummary`, `HistoricData`, alarms | 20 s |
| MultiPlus | 29 | `widgets/Status` | 20 s |
| PV Inverter | 16 | `widgets/PVInverterStatus` | 20 s |
| Tank | 6 | `widgets/TankSummary`, diagnostics fallback | 60 s |
| Solar Charger | 11 | `widgets/SolarChargerSummary`, diagnostics | 20 s |
| Overall Stats | 16 | `overallstats`, `stats` (kWh) | 300 s |
| System Overview | 10/dev | `system-overview` | 1200 s |
| Diagnostics | varies | `diagnostics` | 300 s |

## API Endpoints

Base: `https://vrmapi.victronenergy.com/v2/installations/{site_id}/`

| Endpoint | Returns |
| :--- | :--- |
| `widgets/BatterySummary?instance={id}` | Battery SOC, voltage, current, temperature |
| `widgets/BatteryMonitorWarningsAndAlarms?instance={id}` | 21 alarm/warning states |
| `widgets/Status?instance={id}` | MultiPlus AC/DC voltages, currents, powers |
| `widgets/SolarChargerSummary?instance={id}` | PV voltage, yield, charger state |
| `widgets/PVInverterStatus?instance={id}` | PV inverter per-phase data |
| `widgets/TankSummary?instance={id}` | Tank level, capacity, type |
| `diagnostics` tank records | Tank discovery and fallback values when tanks are absent from system-overview/widgets |
| `overallstats` | Total solar, consumption, grid in/out |
| `stats?type=kwh&start=…&end=…` | kWh statistics for Battery↔Grid/Consumer, PV |
| `system-overview` | Firmware, serial, product name per device |
| `diagnostics?count=100` | Extended device diagnostics |

## Secrets & Credentials

| Asset | Where | Protected |
| :--- | :--- | :---: |
| VRM API token | `.env` (local) | `.gitignore` |
| Site ID | `.env` (local) | `.gitignore` |
| User token in HA | `config_entries` (encrypted) | HA core |
| Template | `.env.example` (committed) | placeholders only |

## Boundary & Tracking Docs

| File | Purpose |
| :--- | :--- |
| [docs/architecture.md](docs/architecture.md) | Runtime flow, component responsibilities, API data flow, Mermaid diagram |
| [docs/security.md](docs/security.md) | Secret rules, pitfalls learned, review checklist, vulnerability/risk register |
| [scripts/README.md](scripts/README.md) | Explains why local deployment helpers are not shipped and usually ignored |
| [.github/skills/victron-vrm-maintenance/SKILL.md](.github/skills/victron-vrm-maintenance/SKILL.md) | Repeatable maintenance workflow for agents and future repo work |
