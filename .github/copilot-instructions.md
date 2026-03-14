# Victron VRM API — Copilot Instructions

## Project
Home Assistant custom integration that polls the Victron VRM Portal API.
Domain: `victron_vrm_api` | Min HA: 2025.1 | Current: v1.6.0

## Repository Layout
```
custom_components/victron_vrm_api/   ← Integration source (shipped to users)
├── __init__.py          entry point, platform setup/teardown
├── config_flow.py       UI config flow + reconfigure
├── const.py             constants, config keys, scan intervals
├── manifest.json        HA manifest
├── sensor.py            all sensor entities & data coordinators (~1200 lines)
└── translations/        en.json, de.json
docs/                    screenshots, documentation, deployment notes
scripts/                 local deployment helpers (not shipped)
tests/                   API test/exploration scripts (not shipped)
```

## Key Rules
1. **Never hardcode tokens or secrets.** Test scripts load from `.env` via `python-dotenv`.
2. **`.env` is gitignored.** Only `.env.example` is committed.
3. **Only `custom_components/` ships to users** (via HACS or manual install). Everything else is dev-only.
4. Sensor additions follow the pattern in `sensor.py`: create a `SensorEntityDescription`, add to coordinator, create entity class if needed.
5. Config keys live in `const.py`. Scan intervals are there too.
6. All HTTP calls use `aiohttp` async with 15s timeout. Handle 200, 204, 429 status codes.
7. Smart sensor creation: only create a sensor entity if the VRM API actually returns data for it.
8. **Enum resolution**: Always resolve enum values via `dataAttributeEnumValues` + `rawValue` first — VRM's `formattedValue` can be stale server-side.
9. **Instance auto-remap**: On startup, system-overview + diagnostics are fetched to detect if VRM reassigned a device instance ID. Stale instances are detected by comparing per-record timestamps from diagnostics (`dbusServiceType` → category). Entity unique IDs stay pinned to the configured instance; only API URLs change.

## API Reference
- Base URL: `https://vrmapi.victronenergy.com/v2/installations/{site_id}/`
- Auth header: `X-Authorization: Token {token}`
- Endpoints: `widgets/BatterySummary`, `widgets/Status`, `widgets/SolarChargerSummary`, `widgets/PVInverterStatus`, `widgets/TankSummary`, `overallstats`, `system-overview`, `diagnostics`, `stats` (kWh)

## Conventions
- Python 3.12+, async/await throughout
- No YAML configuration — UI config flow only
- Version bump in `manifest.json`
- Changelog in `docs/documentation.md`
