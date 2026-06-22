"""Platform for sensor entities from Victron VRM."""
import asyncio
import logging
from datetime import timedelta, datetime, timezone
import aiohttp
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import slugify
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    DOMAIN,
    CONF_SITE_ID,
    CONF_TOKEN,
    CONF_BATTERY_INSTANCE,
    CONF_MULTI_INSTANCE, 
    CONF_PV_INVERTER_INSTANCE,
    CONF_TANK_INSTANCE,
    CONF_SOLAR_CHARGER_INSTANCE,
    CONF_RUNTIME_DISCOVERY,
    DEFAULT_SCAN_INTERVAL_BATTERY,
    DEFAULT_SCAN_INTERVAL_DISCOVERY,
    DEFAULT_SCAN_INTERVAL_OVERALL,
    DEFAULT_SCAN_INTERVAL_MULTI,
    DEFAULT_SCAN_INTERVAL_PV_INVERTER,
    DEFAULT_SCAN_INTERVAL_TANK,
    DEFAULT_SCAN_INTERVAL_SOLAR_CHARGER,
    DEFAULT_SCAN_INTERVAL_SYSTEM_OVERVIEW,
    RUNTIME_DISCOVERY_DISABLED,
)

_LOGGER = logging.getLogger(__name__)


# --- 1. VRM Data Coordinator ----------------------------------------------------
class VrmDataCoordinator(DataUpdateCoordinator):
    """Manages the fetching of VRM data for a single endpoint."""

    def __init__(self, hass: HomeAssistant, site_id: str, token: str, endpoint: str, name: str, interval: int):
        """Initialize the coordinator."""
        self.site_id = site_id
        self.token = token
        self.endpoint = endpoint
        self.base_url = "https://vrmapi.victronenergy.com/v2/installations/"

        super().__init__(
            hass,
            _LOGGER,
            name=name,
            update_interval=timedelta(seconds=interval),
        )

    async def _async_update_data(self):
        """Fetch data from API endpoint."""
        url = f"{self.base_url}{self.site_id}/{self.endpoint}"
        headers = {"X-Authorization": f"Token {self.token}"}
        timeout = aiohttp.ClientTimeout(total=15)

        try:
            session = async_get_clientsession(self.hass)
            async with session.get(url, headers=headers, timeout=timeout) as response:
                if response.status not in (200, 204):
                    _LOGGER.error("API error at %s: Status %d", self.endpoint, response.status)
                    raise UpdateFailed(f"API error at {self.endpoint}: Status {response.status}")

                if response.status == 204:
                    return None

                data = await response.json()

                # IMPORTANT: If 'totals' is present (for stats endpoint), return everything.
                if "totals" in data:
                    return data

                # IMPORTANT: Diagnostics endpoint needs full response with success + records
                if self.endpoint == "diagnostics":
                    return data

                # IMPORTANT: System Overview has a 'records' -> 'devices' structure
                if "records" in data and "devices" in data["records"]:
                    return data["records"]

                # Standard behavior for widgets:
                if "records" in data:
                    return data.get("records", {})

                return data

        except aiohttp.ClientError as err:
            _LOGGER.error("Connection error while fetching data for %s: %s", self.endpoint, err)
            raise UpdateFailed(f"Connection error: {err}")
        except Exception as err:
            _LOGGER.error("Unknown error while fetching data for %s: %s", self.endpoint, err)
            raise UpdateFailed(f"Unknown error: {err}")


# --- 2. Hilfsfunktion zur ID-Verarbeitung -----------------------------------------
def _parse_instance_ids(config_string: str) -> list[int]:
    """Parses a comma-separated string of instance IDs into a list of unique integers."""
    if not config_string:
        return []
    
    ids = set()
    for part in config_string.split(','):
        try:
            # Remove whitespace and try to convert
            instance_id = int(part.strip())
            # 0 is the default/disabled value, only add > 0
            if instance_id > 0:
                ids.add(instance_id)
        except ValueError:
            _LOGGER.warning("Invalid instance ID '%s' in configuration ignored.", part.strip())
            continue
    return sorted(list(ids))


# VRM device type IDs → internal category names
_VRM_DEVICE_TYPE_MAP = {
    1: "multi",          # VE.Bus System (MultiPlus / Quattro)
    2: "battery",        # Battery Monitor (BMV / SmartShunt)
    3: "pv_inverter",    # PV Inverter (Fronius, SMA, …)
    4: "solar_charger",  # Solar Charger (BlueSolar / SmartSolar MPPT)
    12: "tank",          # Tank sensor
}

# Diagnostics dbusServiceType → internal category (for freshness detection)
_VRM_DBUS_SERVICE_MAP = {
    "vebus": "multi",
    "battery": "battery",
    "solarcharger": "solar_charger",
    "pvinverter": "pv_inverter",
    "tank": "tank",
}

_TANK_DIAGNOSTIC_DATA_IDS = {"328", "329", "330", "331", "443", "638"}
_KNOWN_DEVICE_CATEGORIES = ("battery", "multi", "pv_inverter", "tank", "solar_charger")
_STATIC_DIAGNOSTIC_IDS_BY_CATEGORY = {
    "battery": {"55", "56", "57", "60", "61", "62", "63"},
    "solar_charger": {"86", "97", "98", "442", "518"},
    "multi": {"27", "41", "43", "557"},
    "tank": _TANK_DIAGNOSTIC_DATA_IDS,
}


def _resolve_enum_record_value(record: dict[str, Any]) -> Any:
    """Resolve a diagnostics record enum from rawValue before formattedValue."""
    raw = record.get("rawValue")
    enum_values = record.get("dataAttributeEnumValues")
    if enum_values and raw is not None:
        for entry in enum_values:
            if entry.get("valueEnum") == raw:
                return entry.get("nameEnum")
        return raw
    formatted = record.get("formattedValue")
    if formatted not in (None, ""):
        return formatted
    return raw


def _build_tank_info_from_diagnostics(diagnostics_data: dict | None) -> dict[int, dict[str, Any]]:
    """Build tank metadata from diagnostics records when system-overview omits tanks."""
    tank_info: dict[int, dict[str, Any]] = {}
    if not diagnostics_data:
        return tank_info

    for record in diagnostics_data.get("records", []):
        if record.get("dbusServiceType") != "tank":
            continue
        instance = record.get("instance")
        data_id = str(record.get("idDataAttribute"))
        if instance is None or data_id not in _TANK_DIAGNOSTIC_DATA_IDS:
            continue

        info = tank_info.setdefault(instance, {})
        value = _resolve_enum_record_value(record)
        if data_id == "329" and value:
            info["type_name"] = str(value)
        elif data_id == "638" and value:
            info["custom_name"] = str(value)

    for instance, info in tank_info.items():
        info["name"] = info.get("custom_name") or info.get("type_name") or f"Tank {instance}"

    return tank_info


def _diagnostic_record_exists(records: list[dict[str, Any]], data_id: str, instance: int) -> bool:
    """Return True when diagnostics has a record for this attribute and instance."""
    return any(
        str(record.get("idDataAttribute")) == data_id and record.get("instance") == instance
        for record in records
    )


def _build_freshness_map(diagnostics_data: dict | None) -> dict[str, dict[int, int]]:
    """Build {category: {instance_id: max_timestamp}} from diagnostics records."""
    freshness: dict[str, dict[int, int]] = {}
    if not diagnostics_data:
        return freshness
    records = diagnostics_data.get("records", [])
    for rec in records:
        svc = rec.get("dbusServiceType")
        if not svc:
            continue
        cat = _VRM_DBUS_SERVICE_MAP.get(svc)
        if not cat:
            continue
        inst = rec.get("instance")
        ts = rec.get("timestamp", 0) or 0
        if inst is not None:
            freshness.setdefault(cat, {})
            if ts > freshness[cat].get(inst, 0):
                freshness[cat][inst] = ts
    return freshness


def _build_instance_remap(
    system_overview_data: dict | None,
    diagnostics_data: dict | None,
    configured: dict[str, list[int]],
) -> dict[str, dict[int, int]]:
    """Map configured instance IDs to live ones using system-overview + diagnostics.

    Returns a nested dict {category: {configured_id: live_id}}.

    When VRM reassigns an instance ID, the OLD instance may still appear in
    system-overview (stale but listed).  To tell stale from active, we use
    per-record timestamps from the diagnostics endpoint:
      - If a configured ID is found live AND a *newer* instance of the same
        device type exists, the configured ID is remapped to the fresher one.
      - If diagnostics is unavailable, falls back to positional matching.
    """
    remap: dict[str, dict[int, int]] = {}

    if not system_overview_data or "devices" not in system_overview_data:
        for category, ids in configured.items():
            remap[category] = {cid: cid for cid in ids}
        return remap

    # Collect live instance IDs per category from system-overview
    live_by_category: dict[str, list[int]] = {}
    for device in system_overview_data["devices"]:
        dev_type = device.get("idDeviceType")
        dev_instance = device.get("instance")
        if dev_type is not None and dev_instance is not None:
            category = _VRM_DEVICE_TYPE_MAP.get(dev_type)
            if category:
                live_by_category.setdefault(category, []).append(dev_instance)

    for cat in live_by_category:
        live_by_category[cat] = sorted(live_by_category[cat])

    # Build per-instance freshness from diagnostics
    freshness = _build_freshness_map(diagnostics_data)

    for category, configured_ids in configured.items():
        cat_remap: dict[int, int] = {}
        live_ids = live_by_category.get(category, [])
        sorted_conf = sorted(configured_ids)
        cat_freshness = freshness.get(category, {})

        for i, cid in enumerate(sorted_conf):
            if cid in live_ids:
                # Configured ID exists in live list — but it might be stale.
                # Check if a *new* instance (not configured) has fresher data.
                if cat_freshness:
                    cid_ts = cat_freshness.get(cid, 0)
                    new_candidates = [
                        (lid, cat_freshness.get(lid, 0))
                        for lid in live_ids
                        if lid not in sorted_conf and cat_freshness.get(lid, 0) > cid_ts
                    ]
                    if new_candidates:
                        best_lid, best_ts = max(new_candidates, key=lambda x: x[1])
                        cat_remap[cid] = best_lid
                        _LOGGER.warning(
                            "VRM instance remap for %s: configured %d (ts %d) → "
                            "live %d (ts %d, fresher by %ds).",
                            category, cid, cid_ts, best_lid, best_ts, best_ts - cid_ts,
                        )
                    else:
                        cat_remap[cid] = cid
                else:
                    # No diagnostics — trust system-overview as-is
                    cat_remap[cid] = cid
            elif i < len(live_ids):
                cat_remap[cid] = live_ids[i]
                _LOGGER.warning(
                    "VRM instance ID changed for %s: configured %d → live %d. "
                    "Entities keep their original IDs; API calls use the new instance.",
                    category, cid, live_ids[i],
                )
            else:
                cat_remap[cid] = cid

        remap[category] = cat_remap

    return remap


def _extract_live_instances(
    system_overview_data: dict | None,
    diagnostics_data: dict | None,
) -> dict[str, list[int]]:
    """Extract live instances by category from system-overview and diagnostics."""
    live_instances: dict[str, set[int]] = {category: set() for category in _KNOWN_DEVICE_CATEGORIES}

    if system_overview_data and "devices" in system_overview_data:
        for device in system_overview_data.get("devices", []):
            category = _VRM_DEVICE_TYPE_MAP.get(device.get("idDeviceType"))
            instance = device.get("instance")
            if category in live_instances and instance is not None:
                live_instances[category].add(instance)

    # Tanks can be missing from system-overview; discover them from diagnostics.
    for tank_instance in _build_tank_info_from_diagnostics(diagnostics_data).keys():
        live_instances["tank"].add(tank_instance)

    return {category: sorted(values) for category, values in live_instances.items()}


def _merge_discovered_instances(
    configured_instances: dict[str, list[int]],
    live_instances: dict[str, list[int]],
) -> dict[str, list[int]]:
    """Merge newly discovered live instances into configured instance lists."""
    merged: dict[str, list[int]] = {}
    for category in _KNOWN_DEVICE_CATEGORIES:
        configured = set(configured_instances.get(category, []))
        live = set(live_instances.get(category, []))
        discovered = sorted(live - configured)
        if discovered:
            _LOGGER.info(
                "Discovered VRM %s instance IDs from live data: %s",
                category,
                ", ".join(str(instance_id) for instance_id in discovered),
            )
        merged[category] = sorted(configured.union(live))
    return merged


def _serialize_instance_ids(instance_ids: list[int]) -> str:
    """Serialize sorted instance IDs to config string format."""
    return ", ".join(str(instance_id) for instance_id in sorted(instance_ids))


def _collect_known_diagnostic_ids(
    device_data: dict[str, dict[int, dict[str, Any]]],
    diagnostics_data: dict | None,
) -> dict[str, dict[int, set[str]]]:
    """Collect currently known diagnostics IDs for managed instances."""
    known: dict[str, dict[int, set[str]]] = {category: {} for category in _KNOWN_DEVICE_CATEGORIES}

    if not diagnostics_data:
        return known

    live_to_configured: dict[str, dict[int, int]] = {category: {} for category in _KNOWN_DEVICE_CATEGORIES}
    for category in _KNOWN_DEVICE_CATEGORIES:
        for configured_instance, data in device_data.get(category, {}).items():
            live_instance = data.get("live_instance", configured_instance)
            live_to_configured[category][live_instance] = configured_instance

    for record in diagnostics_data.get("records", []):
        category = _VRM_DBUS_SERVICE_MAP.get(record.get("dbusServiceType"))
        instance = record.get("instance")
        data_id = record.get("idDataAttribute")
        if category not in known or instance is None or data_id is None:
            continue

        configured_instance = live_to_configured.get(category, {}).get(instance)
        if configured_instance is None:
            continue

        known[category].setdefault(configured_instance, set()).add(str(data_id))

    return known


def _build_dynamic_diagnostic_entities(
    diagnostics_coord: "VrmDataCoordinator",
    site_id: str,
    diagnostics_data: dict | None,
    device_data: dict[str, dict[int, dict[str, Any]]],
    created_dynamic_keys: set[str],
) -> list[SensorEntity]:
    """Create sensors for diagnostics records that are not statically mapped."""
    entities: list[SensorEntity] = []
    if not diagnostics_data:
        return entities

    for record in diagnostics_data.get("records", []):
        category = _VRM_DBUS_SERVICE_MAP.get(record.get("dbusServiceType"))
        live_instance = record.get("instance")
        data_id = str(record.get("idDataAttribute"))
        if category not in device_data or live_instance is None or not data_id or data_id == "None":
            continue

        if data_id in _STATIC_DIAGNOSTIC_IDS_BY_CATEGORY.get(category, set()):
            continue

        configured_instance = None
        for instance_id, data in device_data.get(category, {}).items():
            if data.get("live_instance", instance_id) == live_instance:
                configured_instance = instance_id
                break

        if configured_instance is None:
            continue

        dynamic_key = f"{category}:{configured_instance}:{data_id}"
        if dynamic_key in created_dynamic_keys:
            continue

        data_name = record.get("dataAttributeName") or f"Diagnostic {data_id}"
        entities.append(
            VrmDiagnosticSensor(
                diagnostics_coord,
                site_id,
                f"diag_dynamic_{category}_{data_id}_{configured_instance}",
                data_id,
                live_instance,
                data_name,
                None,
                None,
                None,
                "mdi:chart-line",
                device_data[category][configured_instance]["device_info"],
            )
        )
        created_dynamic_keys.add(dynamic_key)

    return entities


class VrmRuntimeDiscoveryCoordinator(DataUpdateCoordinator):
    """Detect newly added VRM devices and diagnostics IDs at runtime."""

    def __init__(
        self,
        hass: HomeAssistant,
        site_id: str,
        token: str,
        managed_instances: dict[str, set[int]],
        known_diagnostic_ids: dict[str, dict[int, set[str]]],
    ):
        """Initialize runtime discovery coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="VRM Runtime Discovery",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL_DISCOVERY),
        )
        self._managed_instances = managed_instances
        self._known_diagnostic_ids = known_diagnostic_ids
        self._system_overview_coord = VrmDataCoordinator(
            hass,
            site_id,
            token,
            "system-overview",
            "VRM Runtime Discovery System Overview",
            DEFAULT_SCAN_INTERVAL_DISCOVERY,
        )
        self._diagnostics_coord = VrmDataCoordinator(
            hass,
            site_id,
            token,
            "diagnostics",
            "VRM Runtime Discovery Diagnostics",
            DEFAULT_SCAN_INTERVAL_DISCOVERY,
        )

    async def _async_update_data(self):
        """Return newly discovered instances and diagnostics IDs."""
        await self._system_overview_coord.async_refresh()
        await self._diagnostics_coord.async_refresh()

        live_instances = _extract_live_instances(self._system_overview_coord.data, self._diagnostics_coord.data)
        new_instances: dict[str, list[int]] = {}
        for category in _KNOWN_DEVICE_CATEGORIES:
            managed = self._managed_instances.setdefault(category, set())
            discovered = sorted(set(live_instances.get(category, [])) - managed)
            if discovered:
                new_instances[category] = discovered
                managed.update(discovered)

        new_diagnostic_ids: dict[str, dict[int, list[str]]] = {}
        live_to_configured: dict[str, dict[int, int]] = {category: {} for category in _KNOWN_DEVICE_CATEGORIES}
        for category in _KNOWN_DEVICE_CATEGORIES:
            for configured_instance in self._managed_instances.get(category, set()):
                live_to_configured[category][configured_instance] = configured_instance

        records = self._diagnostics_coord.data.get("records", []) if self._diagnostics_coord.data else []
        for record in records:
            category = _VRM_DBUS_SERVICE_MAP.get(record.get("dbusServiceType"))
            instance = record.get("instance")
            data_id = record.get("idDataAttribute")
            if category not in _KNOWN_DEVICE_CATEGORIES or instance is None or data_id is None:
                continue
            if instance not in self._managed_instances.get(category, set()):
                continue

            known_for_instance = self._known_diagnostic_ids.setdefault(category, {}).setdefault(instance, set())
            data_id_str = str(data_id)
            if data_id_str in known_for_instance:
                continue

            known_for_instance.add(data_id_str)
            new_diagnostic_ids.setdefault(category, {}).setdefault(instance, []).append(data_id_str)

        return {
            "new_instances": new_instances,
            "new_diagnostic_ids": new_diagnostic_ids,
        }


# --- 3. Setup-Funktion -----------------------------------------------------------
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    """Set up VRM sensors from a config entry."""

    config_data = hass.data[DOMAIN][entry.entry_id]

    site_id = config_data[CONF_SITE_ID]
    token = config_data[CONF_TOKEN]
    
    # Instance IDs als String-Listen abrufen und parsen
    battery_instance_ids = _parse_instance_ids(config_data.get(CONF_BATTERY_INSTANCE, ""))
    multi_instance_ids = _parse_instance_ids(config_data.get(CONF_MULTI_INSTANCE, ""))
    pv_inverter_instance_ids = _parse_instance_ids(config_data.get(CONF_PV_INVERTER_INSTANCE, ""))
    configured_tank_instance_ids = _parse_instance_ids(config_data.get(CONF_TANK_INSTANCE, ""))
    tank_instance_ids = list(configured_tank_instance_ids)
    solar_charger_instance_ids = _parse_instance_ids(config_data.get(CONF_SOLAR_CHARGER_INSTANCE, ""))

    configured_instances = {
        "battery": battery_instance_ids,
        "multi": multi_instance_ids,
        "pv_inverter": pv_inverter_instance_ids,
        "tank": tank_instance_ids,
        "solar_charger": solar_charger_instance_ids,
    }
    
    
    # Define endpoints (static endpoints)
    overall_endpoint = "overallstats"
    stats_endpoint = "stats?type=kwh&interval=15mins"
    system_overview_endpoint = "system-overview"
    diagnostics_endpoint = "diagnostics" # NEW - comprehensive system data

    # Initialize coordinators (always present)
    overall_stats_coord = VrmDataCoordinator(
        hass, site_id, token, overall_endpoint, "VRM Overall Stats", DEFAULT_SCAN_INTERVAL_OVERALL
    )
    stats_coord = VrmDataCoordinator(
        hass, site_id, token, stats_endpoint, "VRM Energy Stats", DEFAULT_SCAN_INTERVAL_OVERALL
    )
    # Coordinator for System Overview
    system_overview_coord = VrmDataCoordinator(
        hass, site_id, token, system_overview_endpoint, "VRM System Overview", DEFAULT_SCAN_INTERVAL_SYSTEM_OVERVIEW
    )
    # NEW - Coordinator for Diagnostics (extended sensor data)
    diagnostics_coord = VrmDataCoordinator(
        hass, site_id, token, diagnostics_endpoint, "VRM Diagnostics", DEFAULT_SCAN_INTERVAL_OVERALL
    )

    # Dictionary to store coordinators and device info per instance ID
    device_data = {
        "battery": {},
        "multi": {},
        "pv_inverter": {},
        "tank": {},
        "solar_charger": {}
    }

    # Define the hub device (main device)
    hub_device_info = { 
        "identifiers": {(DOMAIN, site_id)},
        "name": f"VRM Site {site_id}",
        "manufacturer": "Victron VRM API",
        "model": "VRM Hub",
    }
    
    # Define the overall stats device
    overall_device_info = {
        "identifiers": {(DOMAIN, f"{site_id}_overall")},
        "name": "Stats Overall",
        "manufacturer": "Victron VRM API",
        "model": "Overall Statistics",
        "via_device": (DOMAIN, site_id),
    }

    # Define the System Overview device (the parent device under which all entities are grouped)
    system_overview_device_info = {
        "identifiers": {(DOMAIN, f"{site_id}_system_overview")},
        "name": "System Overview",
        "manufacturer": "Victron Energy",
        "model": "Device List",
        "via_device": (DOMAIN, site_id),
    }
    
    # Temporary list of all dynamic coordinators for initial refresh
    dynamic_coordinators = []

    # --- Fetch system-overview AND diagnostics FIRST to detect instance ID changes ---
    # Diagnostics provides per-record timestamps that let us distinguish stale
    # from active devices when VRM reassigns an instance ID.
    try:
        await system_overview_coord.async_refresh()
    except Exception as err:
        _LOGGER.warning("Could not fetch system overview for instance detection: %s", err)

    try:
        await diagnostics_coord.async_refresh()
    except Exception as err:
        _LOGGER.warning("Could not fetch diagnostics for instance detection: %s", err)

    live_instances = _extract_live_instances(system_overview_coord.data, diagnostics_coord.data)
    merged_instances = _merge_discovered_instances(configured_instances, live_instances)

    battery_instance_ids = merged_instances["battery"]
    multi_instance_ids = merged_instances["multi"]
    pv_inverter_instance_ids = merged_instances["pv_inverter"]
    tank_instance_ids = merged_instances["tank"]
    solar_charger_instance_ids = merged_instances["solar_charger"]

    diagnostics_tank_info = _build_tank_info_from_diagnostics(diagnostics_coord.data)

    instance_remap = _build_instance_remap(
        system_overview_coord.data,
        diagnostics_coord.data,
        {
            "battery": battery_instance_ids,
            "multi": multi_instance_ids,
            "pv_inverter": pv_inverter_instance_ids,
            "tank": tank_instance_ids,
            "solar_charger": solar_charger_instance_ids,
        },
    )

    # --- Initialize dynamic coordinators and device info per instance ---
    
    # 1. Batteries (extended with History and Alarms coordinator)
    for instance_id in battery_instance_ids:
        live_id = instance_remap.get("battery", {}).get(instance_id, instance_id)
        # Standard Battery Summary
        battery_endpoint = f"widgets/BatterySummary?instance={live_id}"
        coord_name = f"VRM Battery {instance_id} Summary"
        battery_summary_coord = VrmDataCoordinator(
            hass, site_id, token, battery_endpoint, coord_name, DEFAULT_SCAN_INTERVAL_BATTERY
        )
        dynamic_coordinators.append(battery_summary_coord)

        # History Data (for Charge Cycles)
        history_endpoint = f"widgets/HistoricData?instance={live_id}"
        history_coord_name = f"VRM Battery {instance_id} History"
        battery_history_coord = VrmDataCoordinator(
            hass, site_id, token, history_endpoint, history_coord_name, DEFAULT_SCAN_INTERVAL_BATTERY
        )
        dynamic_coordinators.append(battery_history_coord)
        
        # Alarms Data
        alarm_endpoint = f"widgets/BatteryMonitorWarningsAndAlarms?instance={live_id}"
        alarm_coord_name = f"VRM Battery {instance_id} Alarms"
        battery_alarm_coord = VrmDataCoordinator(
            hass, site_id, token, alarm_endpoint, alarm_coord_name, DEFAULT_SCAN_INTERVAL_BATTERY
        )
        dynamic_coordinators.append(battery_alarm_coord)

        device_data["battery"][instance_id] = {
            'coordinator': battery_summary_coord,
            'history_coordinator': battery_history_coord, 
            'alarm_coordinator': battery_alarm_coord,
            'live_instance': live_id,
            'device_info': {
                "identifiers": {(DOMAIN, f"{site_id}_battery_{instance_id}")},
                "name": f"Battery {instance_id}",
                "manufacturer": "Victron VRM API",
                "model": f"instance_id {instance_id}",
                "via_device": (DOMAIN, site_id),
            }
        }

    # 2. MultiPlus
    for instance_id in multi_instance_ids:
        live_id = instance_remap.get("multi", {}).get(instance_id, instance_id)
        multi_status_endpoint = f"widgets/Status?instance={live_id}"
        coord_name = f"VRM MultiPlus {instance_id} Status"
        multi_status_coord = VrmDataCoordinator(
            hass, site_id, token, multi_status_endpoint, coord_name, DEFAULT_SCAN_INTERVAL_MULTI
        )
        dynamic_coordinators.append(multi_status_coord)
        device_data["multi"][instance_id] = {
            'coordinator': multi_status_coord,
            'live_instance': live_id,
            'device_info': {
                "identifiers": {(DOMAIN, f"{site_id}_multiplus_{instance_id}")},
                "name": f"MultiPlus {instance_id}",
                "manufacturer": "Victron VRM API",
                "model": f"instance_id {instance_id}",
                "via_device": (DOMAIN, site_id),
            }
        }
        
    # 3. PV Inverter
    for instance_id in pv_inverter_instance_ids:
        live_id = instance_remap.get("pv_inverter", {}).get(instance_id, instance_id)
        pv_inverter_endpoint = f"widgets/PVInverterStatus?instance={live_id}"
        coord_name = f"VRM PV Inverter {instance_id} Status"
        pv_inverter_coord = VrmDataCoordinator(
            hass, site_id, token, pv_inverter_endpoint, coord_name, DEFAULT_SCAN_INTERVAL_PV_INVERTER
        )
        dynamic_coordinators.append(pv_inverter_coord)
        device_data["pv_inverter"][instance_id] = {
            'coordinator': pv_inverter_coord,
            'live_instance': live_id,
            'device_info': {
                "identifiers": {(DOMAIN, f"{site_id}_pvinverter_{instance_id}")},
                "name": f"PV Inverter {instance_id}",
                "manufacturer": "Victron VRM API",
                "model": f"instance_id {instance_id}",
                "via_device": (DOMAIN, site_id),
            }
        }

    # 4. Tank
    for instance_id in tank_instance_ids:
        live_id = instance_remap.get("tank", {}).get(instance_id, instance_id)
        tank_info = diagnostics_tank_info.get(instance_id, {})
        tank_name = tank_info.get("name") or f"Tank {instance_id}"
        tank_endpoint = f"widgets/TankSummary?instance={live_id}"
        coord_name = f"VRM Tank {instance_id} Summary"
        tank_coord = VrmDataCoordinator(
            hass, site_id, token, tank_endpoint, coord_name, DEFAULT_SCAN_INTERVAL_TANK
        )
        dynamic_coordinators.append(tank_coord)
        device_data["tank"][instance_id] = {
            'coordinator': tank_coord,
            'live_instance': live_id,
            'device_info': {
                "identifiers": {(DOMAIN, f"{site_id}_tank_{instance_id}")},
                "name": tank_name,
                "_unique_id_name": f"Tank {instance_id}",
                "manufacturer": "Victron VRM API",
                "model": tank_info.get("type_name") or f"instance_id {instance_id}",
                "via_device": (DOMAIN, site_id),
            }
        }

    # 5. Solar Charger
    for instance_id in solar_charger_instance_ids:
        live_id = instance_remap.get("solar_charger", {}).get(instance_id, instance_id)
        solar_charger_endpoint = f"widgets/SolarChargerSummary?instance={live_id}"
        coord_name = f"VRM Solar Charger {instance_id} Summary"
        solar_charger_coord = VrmDataCoordinator(
            hass, site_id, token, solar_charger_endpoint, coord_name, DEFAULT_SCAN_INTERVAL_SOLAR_CHARGER
        )
        dynamic_coordinators.append(solar_charger_coord)
        device_data["solar_charger"][instance_id] = {
            'coordinator': solar_charger_coord,
            'live_instance': live_id,
            'device_info': {
                "identifiers": {(DOMAIN, f"{site_id}_solarcharger_{instance_id}")},
                "name": f"Solar Charger {instance_id}",
                "manufacturer": "Victron VRM API",
                "model": f"instance_id {instance_id}",
                "via_device": (DOMAIN, site_id),
            }
        }
    
    # Execute initial refresh (system_overview_coord already fetched above)
    remaining_coordinators = [overall_stats_coord, stats_coord, diagnostics_coord] + dynamic_coordinators
    for coordinator in remaining_coordinators:
        try:
            await coordinator.async_config_entry_first_refresh()
        except Exception as err:
            _LOGGER.warning("Initial refresh of %s coordinator failed: %s", coordinator.name, err)

    runtime_state = hass.data[DOMAIN][entry.entry_id].setdefault("runtime", {})
    runtime_state["device_data"] = device_data
    runtime_state["diagnostics_coord"] = diagnostics_coord
    runtime_state["site_id"] = site_id
    runtime_state["managed_instances"] = {
        category: set(device_data.get(category, {}).keys())
        for category in _KNOWN_DEVICE_CATEGORIES
    }
    runtime_state["known_diagnostic_ids"] = _collect_known_diagnostic_ids(device_data, diagnostics_coord.data)
    runtime_state["dynamic_diagnostic_keys"] = set()
    runtime_state["reload_lock"] = asyncio.Lock()


    entities: list[SensorEntity] = []


    # --- 1. Battery Summary Sensoren ---
    battery_sensors_config = {
        "soc": ("51", "State of charge", SensorDeviceClass.BATTERY, SensorStateClass.MEASUREMENT, "%", "mdi:battery-50"),
        "voltage": ("47", "Voltage", SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, "V", "mdi:current-dc"),
        "starter_voltage": ("48", "Starter Battery Voltage", SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, "V", "mdi:car-battery"),
        "current": ("49", "Current", SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, "A", "mdi:current-dc"),
        "consumed": ("50", "Consumed Amphours", None, SensorStateClass.TOTAL_INCREASING, "Ah", "mdi:battery-alert-variant-outline"),
        "ttg": ("52", "Time to go", None, SensorStateClass.MEASUREMENT, "h", "mdi:timer-sand"),
        "mid_voltage": ("64", "Mid Voltage", SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, "V", "mdi:battery-medium"),
        "charge_cycles": ("58", "Charge Cycles", None, SensorStateClass.TOTAL_INCREASING, None, "mdi:battery-sync"),
    }
    
    power_sensor_key = "power"
    power_sensor_name = "Battery Power"

    for instance_id, data in device_data["battery"].items():
        summary_coord = data['coordinator']
        history_coord = data['history_coordinator']
        alarm_coord = data['alarm_coordinator']
        dev_info = data['device_info']
        
        # Standard summary sensors
        for key, (data_id, name, device_class, state_class, unit, icon) in battery_sensors_config.items():
            
            # IMPORTANT: Select the correct coordinator based on sensor type
            if key == "charge_cycles":
                active_coord = history_coord
            elif key == "mid_voltage":
                active_coord = history_coord
            else:
                active_coord = summary_coord

            # Check if data is available in the selected coordinator
            if active_coord.data and active_coord.data.get("data"):
                actual_data = active_coord.data.get("data", {})
                
                # Check if the specific ID exists in the data
                if data_id in actual_data:
                    entities.append(
                        VrmBatterySummarySensor(
                            active_coord, site_id, 
                            f"{key}_{instance_id}", 
                            data_id, 
                            name, # Friendly name without ID 
                            device_class, state_class, unit, icon, dev_info
                        )
                    )
        
        # Power sensor always uses summary coord
        if summary_coord.data:
            entities.append(
                VrmBatteryPowerSensor(
                    summary_coord, site_id, 
                    f"{power_sensor_key}_{instance_id}", 
                    power_sensor_name, 
                    dev_info
                )
            )
            
        # --- 1.1 Battery Alarm & Warning Sensors ---
        battery_alarms_config = {
            "119": ("Low voltage alarm", None, None, None, "mdi:battery-alert"),
            "120": ("High voltage alarm", None, None, None, "mdi:battery-alert"),
            "121": ("Low starter-voltage alarm", None, None, None, "mdi:car-battery"),
            "122": ("High starter-voltage alarm", None, None, None, "mdi:car-battery"),
            "123": ("Low state-of-charge alarm", None, None, None, "mdi:battery-low"),
            "124": ("Low battery temperature alarm", None, None, None, "mdi:thermometer-alert"),
            "125": ("High battery temperature alarm", None, None, None, "mdi:thermometer-alert"),
            "126": ("Mid-voltage alarm", None, None, None, "mdi:battery-alert"),
            "155": ("Low fused-voltage alarm", None, None, None, "mdi:fuse-alert"),
            "156": ("High fused-voltage alarm", None, None, None, "mdi:fuse-alert"),
            "157": ("Fuse blown alarm", None, None, None, "mdi:fuse-off"),
            "158": ("High internal-temperature alarm", None, None, None, "mdi:thermometer-alert"),
            "286": ("Cell Imbalance alarm", None, None, None, "mdi:battery-alert-variant"),
            "287": ("High charge current alarm", None, None, None, "mdi:current-dc"),
            "288": ("High discharge current alarm", None, None, None, "mdi:current-dc"),
            "289": ("Internal Failure", None, None, None, "mdi:alert-circle"),
            "459": ("High charge temperature alarm", None, None, None, "mdi:thermometer-alert"),
            "460": ("Low charge temperature alarm", None, None, None, "mdi:thermometer-alert"),
            "522": ("Low cell voltage", None, None, None, "mdi:battery-alert"),
            "739": ("Charge blocked", None, None, None, "mdi:battery-charging-off"),
            "740": ("Discharge blocked", None, None, None, "mdi:battery-off"),
        }
        
        if alarm_coord.data and alarm_coord.data.get("data"):
            alarm_data = alarm_coord.data.get("data", {})
            for data_id, (name, device_class, state_class, unit, icon) in battery_alarms_config.items():
                if data_id in alarm_data:
                    entities.append(
                        VrmBatteryAlarmSensor(
                            alarm_coord, site_id,
                            f"alarm_{data_id}_{instance_id}",
                            data_id,
                            name,
                            device_class,
                            state_class,
                            unit,
                            icon,
                            dev_info
                        )
                    )

    # --- 2. Battery Additional Stats Sensoren ---
    additional_stats = {
        "Bc": ("Battery to Consumers Today", SensorDeviceClass.ENERGY, "mdi:battery-arrow-down"),
        "Bg": ("Battery to Grid Today", SensorDeviceClass.ENERGY, "mdi:battery-arrow-down"), 
    }

    if stats_coord.data:
        for instance_id, data in device_data["battery"].items():
            dev_info = data['device_info']
            for json_key, (name, device_class, icon) in additional_stats.items():
                data_path = ["totals", json_key]
                entities.append(
                    VrmOverallStatsSensor(
                        stats_coord, site_id, f"stats_{json_key}_{instance_id}", data_path, name,
                        device_class, SensorStateClass.TOTAL_INCREASING, "kWh", icon, dev_info 
                    )
                )

    # --- 3. MultiPlus Status Sensoren ---
    multi_status_sensors_config = {
        "ac_in_frequency": ("6", "AC Input Frequency", SensorDeviceClass.FREQUENCY, SensorStateClass.MEASUREMENT, "Hz", "mdi:sine-wave"),
        "ac_in_voltage_l1": ("8", "AC Input Voltage L1", SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, "V", "mdi:transmission-tower"),
        "ac_in_voltage_l2": ("9", "AC Input Voltage L2", SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, "V", "mdi:transmission-tower"),
        "ac_in_voltage_l3": ("10", "AC Input Voltage L3", SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, "V", "mdi:transmission-tower"),
        "ac_in_current_l1": ("11", "AC Input Current L1", SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, "A", "mdi:current-ac"),
        "ac_in_current_l2": ("12", "AC Input Current L2", SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, "A", "mdi:current-ac"),
        "ac_in_current_l3": ("13", "AC Input Current L3", SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, "A", "mdi:current-ac"),
        "ac_in_power_l1": ("17", "AC Input Power L1", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, "W", "mdi:transmission-tower"),
        "ac_in_power_l2": ("18", "AC Input Power L2", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, "W", "mdi:transmission-tower"),
        "ac_in_power_l3": ("19", "AC Input Power L3", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, "W", "mdi:transmission-tower"),
        "ac_out_voltage_l1": ("20", "AC Output Voltage L1", SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, "V", "mdi:power-socket-eu"),
        "ac_out_voltage_l2": ("21", "AC Output Voltage L2", SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, "V", "mdi:power-socket-eu"),
        "ac_out_voltage_l3": ("22", "AC Output Voltage L3", SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, "V", "mdi:power-socket-eu"),
        "ac_out_frequency": ("23", "AC Output Frequency", SensorDeviceClass.FREQUENCY, SensorStateClass.MEASUREMENT, "Hz", "mdi:sine-wave"),
        "ac_out_current_l1": ("14", "AC Output Current L1", SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, "A", "mdi:current-ac"),
        "ac_out_current_l2": ("15", "AC Output Current L2", SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, "A", "mdi:current-ac"),
        "ac_out_current_l3": ("16", "AC Output Current L3", SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, "A", "mdi:current-ac"),
        "ac_out_power_l1": ("29", "AC Output Power L1", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, "W", "mdi:power-socket-eu"),
        "ac_out_power_l2": ("30", "AC Output Power L2", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, "W", "mdi:power-socket-eu"),
        "ac_out_power_l3": ("31", "AC Output Power L3", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, "W", "mdi:power-socket-eu"),
        "dc_voltage": ("32", "DC Bus Voltage", SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, "V", "mdi:current-dc"),
        "dc_current": ("33", "DC Bus Current", SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, "A", "mdi:current-dc"),
        "active_input": ("35", "Active Input Source", None, None, None, "mdi:power-plug"),
        "inverter_state": ("40", "VE.Bus State", None, None, None, "mdi:flash"),
        "switch_position": ("44", "Switch Position", None, None, None, "mdi:light-switch"),
        "grid_setpoint": ("242", "Grid Setpoint", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, "W", "mdi:transmission-tower-export"),
        "soc_limit": ("243", "SOC Limit", SensorDeviceClass.BATTERY, SensorStateClass.MEASUREMENT, "%", "mdi:battery-lock"),
        "active_soc_limit": ("244", "Active SOC Limit", SensorDeviceClass.BATTERY, SensorStateClass.MEASUREMENT, "%", "mdi:battery-lock-open"),
        "multi_temp": ("521", "MultiPlus Temperature", SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, "°C", "mdi:thermometer"),
    }
    
    multi_dc_power_key = "dc_power"
    multi_dc_power_name = "DC Bus Power"

    for instance_id, data in device_data["multi"].items():
        coord = data['coordinator']
        dev_info = data['device_info']
        if coord.data and coord.data.get("data"):
            actual_data = coord.data.get("data", {})
            for key, (data_id, name, device_class, state_class, unit, icon) in multi_status_sensors_config.items():
                if data_id in actual_data:
                    entities.append(
                        VrmMultiStatusSensor(
                            coord, site_id, f"{key}_{instance_id}", data_id, name, 
                            device_class, state_class, unit, icon, dev_info
                        )
                    )
            # Only add DC Power sensor if both voltage and current are available
            if "32" in actual_data and "33" in actual_data:
                entities.append(
                    VrmMultiPlusDCPowerSensor(
                        coord, site_id, f"{multi_dc_power_key}_{instance_id}", multi_dc_power_name, dev_info
                    )
                )

    # --- 3.5. MultiPlus Additional Stats Sensoren ---
    multi_additional_stats = {
        "Gc": ("Grid to Consumers Today", SensorDeviceClass.ENERGY, "mdi:transmission-tower"),
        "Gb": ("Grid to Battery Today", SensorDeviceClass.ENERGY, "mdi:battery-arrow-down"),
    }

    if stats_coord.data:
        for instance_id, data in device_data["multi"].items():
            dev_info = data['device_info']
            for json_key, (name, device_class, icon) in multi_additional_stats.items():
                data_path = ["totals", json_key]
                entities.append(
                    VrmOverallStatsSensor(
                        stats_coord, site_id, f"stats_{json_key}_{instance_id}", data_path, name,
                        device_class, SensorStateClass.TOTAL_INCREASING, "kWh", icon, dev_info
                    )
                )

    # --- 3.6. PV Inverter Additional Stats Sensoren ---
    pv_additional_stats = {
        "Pc": ("PV to Consumers Today", SensorDeviceClass.ENERGY, "mdi:solar-power-variant-outline"),
        "Pb": ("PV to Battery Today", SensorDeviceClass.ENERGY, "mdi:battery-arrow-down-outline"),
        "Pg": ("PV to Grid Today", SensorDeviceClass.ENERGY, "mdi:home-export-outline"),          
    }

    if stats_coord.data:
        for instance_id, data in device_data["pv_inverter"].items():
            dev_info = data['device_info']
            for json_key, (name, device_class, icon) in pv_additional_stats.items():
                data_path = ["totals", json_key]
                entities.append(
                    VrmOverallStatsSensor(
                        stats_coord, site_id, f"stats_{json_key}_{instance_id}", data_path, name,
                        device_class, SensorStateClass.TOTAL_INCREASING, "kWh", icon, dev_info 
                    )
                )
            entities.append(
                VrmPvTotalTodaySensor(
                    stats_coord, site_id, f"pv_total_today_{instance_id}", "PV Total Today", dev_info
                )
            )
        
    # --- 3.7. PV Inverter Sensoren Leistung ---
    pv_inverter_sensors_config = {
        "ac_voltage_l1": ("203", "L1 Voltage", SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, "V", "mdi:flash-triangle"),
        "ac_current_l1": ("204", "L1 Current", SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, "A", "mdi:current-ac"),
        "ac_power_l1":   ("205", "L1 Power",   SensorDeviceClass.POWER,   SensorStateClass.MEASUREMENT, "W", "mdi:solar-power"),
        "ac_energy_l1":  ("206", "L1 Energy",  SensorDeviceClass.ENERGY,  SensorStateClass.TOTAL_INCREASING, "kWh", "mdi:solar-panel"),
        "ac_voltage_l2": ("207", "L2 Voltage", SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, "V", "mdi:flash-triangle"),
        "ac_current_l2": ("208", "L2 Current", SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, "A", "mdi:current-ac"),
        "ac_power_l2":   ("209", "L2 Power",   SensorDeviceClass.POWER,   SensorStateClass.MEASUREMENT, "W", "mdi:solar-power"),
        "ac_energy_l2":  ("210", "L2 Energy",  SensorDeviceClass.ENERGY,  SensorStateClass.TOTAL_INCREASING, "kWh", "mdi:solar-panel"),
        "ac_voltage_l3": ("211", "L3 Voltage", SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, "V", "mdi:flash-triangle"),
        "ac_current_l3": ("212", "L3 Current", SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, "A", "mdi:current-ac"),
        "ac_power_l3":   ("213", "L3 Power",   SensorDeviceClass.POWER,   SensorStateClass.MEASUREMENT, "W", "mdi:solar-power"),
        "ac_energy_l3":  ("214", "L3 Energy",  SensorDeviceClass.ENERGY,  SensorStateClass.TOTAL_INCREASING, "kWh", "mdi:solar-panel"),
        "status_code":   ("246", "Status",     None,                     None,                          None, "mdi:list-status"),
    }

    for instance_id, data in device_data["pv_inverter"].items():
        coord = data['coordinator']
        dev_info = data['device_info']
        if coord.data and coord.data.get("data"):
            actual_data = coord.data.get("data", {})
            for key, (data_id, name, device_class, state_class, unit, icon) in pv_inverter_sensors_config.items():
                if data_id in actual_data:
                    entities.append(
                        VrmPvInverterSensor(
                            coord, site_id, f"{key}_{instance_id}", data_id, name, 
                            device_class, state_class, unit, icon, dev_info
                        )
                    )

    # --- 3.8. Tank Sensoren ---
    tank_sensors_config = {
        "level":     ("330", "Level",     None,                     SensorStateClass.MEASUREMENT, "%",  "mdi:cup-water"),
        "remaining": ("331", "Remaining", SensorDeviceClass.VOLUME, SensorStateClass.TOTAL, "m³", "mdi:cup-water"), 
        "capacity":  ("328", "Capacity",  SensorDeviceClass.VOLUME, SensorStateClass.TOTAL, "m³", "mdi:beaker"),      
        "status":    ("443", "Status",    None,                     None,                         None, "mdi:list-status"),
        "type":      ("329", "Type",      None,                     None,                         None, "mdi:information-outline"),
        "name":      ("638", "Custom Name", None,                   None,                         None, "mdi:tag-text"),
    }

    for instance_id, data in device_data["tank"].items():
        coord = data['coordinator']
        dev_info = data['device_info']
        live_id = data.get('live_instance', instance_id)
        tank_name = dev_info.get("name", f"Tank {instance_id}")
        actual_tank_data = coord.data.get("data", {}) if coord.data else {}
        diagnostics_records = diagnostics_coord.data.get("records", []) if diagnostics_coord.data else []

        for key, (data_id, name, device_class, state_class, unit, icon) in tank_sensors_config.items():
            sensor_name = f"{tank_name} {name}"
            if str(data_id) in actual_tank_data:
                entities.append(
                    VrmTankSensor(
                        coord, site_id, f"{key}_{instance_id}", data_id, sensor_name,
                        device_class, state_class, unit, icon, dev_info
                    )
                )
            elif _diagnostic_record_exists(diagnostics_records, str(data_id), live_id):
                entities.append(
                    VrmDiagnosticSensor(
                        diagnostics_coord, site_id, f"{key}_{instance_id}",
                        data_id, live_id, sensor_name, device_class, state_class, unit, icon, dev_info
                    )
                )

    # --- 3.9. Solar Charger Sensoren ---
    solar_charger_sensors_config = {
        "battery_voltage": ("81",  "Battery Voltage",   SensorDeviceClass.VOLTAGE,   SensorStateClass.MEASUREMENT,      "V",   "mdi:current-dc"),
        "pv_voltage":      ("82",  "PV Voltage",        SensorDeviceClass.VOLTAGE,   SensorStateClass.MEASUREMENT,      "V",   "mdi:solar-panel"),
        "battery_temp":    ("83",  "Battery Temperature", SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT,  "°C",  "mdi:thermometer"),
        "pv_current":      ("84",  "PV Current",        SensorDeviceClass.CURRENT,   SensorStateClass.MEASUREMENT,      "A",   "mdi:current-dc"),
        "charge_state":    ("85",  "Charge State",      None,                        None,                              None,  "mdi:solar-power"),
        "error_code":      ("88",  "Error Code",        None,                        None,                              None,  "mdi:alert-circle"),
        "relay_status":    ("90",  "Relay Status",      None,                        None,                              None,  "mdi:electric-switch"),
        "yield_today":     ("94",  "Yield Today",       SensorDeviceClass.ENERGY,    SensorStateClass.TOTAL_INCREASING, "kWh", "mdi:solar-power"),
        "max_power_today": ("95",  "Max Power Today",   SensorDeviceClass.POWER,     SensorStateClass.MEASUREMENT,      "W",   "mdi:solar-power-variant"),
        "yield_yesterday": ("96",  "Yield Yesterday",   SensorDeviceClass.ENERGY,    SensorStateClass.TOTAL_INCREASING, "kWh", "mdi:solar-panel"),
        "battery_watts":   ("107", "Battery Watts",     SensorDeviceClass.POWER,     SensorStateClass.MEASUREMENT,      "W",   "mdi:battery-charging-90"),
    }

    for instance_id, data in device_data["solar_charger"].items():
        coord = data['coordinator']
        dev_info = data['device_info']
        if coord.data and coord.data.get("data"):
            actual_sc_data = coord.data.get("data", {})
            for key, (data_id, name, device_class, state_class, unit, icon) in solar_charger_sensors_config.items():
                if str(data_id) in actual_sc_data:
                    entities.append(
                        VrmSolarChargerSensor(
                            coord, site_id, f"{key}_{instance_id}", data_id, name, 
                            device_class, state_class, unit, icon, dev_info
                        )
                    )

    # --- 4. Overall Stats Sensoren ---
    periods = ["today", "week", "month", "year"]
    metrics = {
        "total_solar_yield": ("Solar Yield", SensorDeviceClass.ENERGY, "mdi:solar-power"),
        "total_consumption": ("Consumption", SensorDeviceClass.ENERGY, "mdi:power-plug"),
        "grid_history_from": ("Grid Energy In", SensorDeviceClass.ENERGY, "mdi:transmission-tower"),
        "grid_history_to": ("Grid Energy Out", SensorDeviceClass.ENERGY, "mdi:home-export-outline"),
    }

    if overall_stats_coord.data:
        for period in periods:
            for metric_key, (metric_name, device_class, icon) in metrics.items():
                key = f"{period}_{metric_key}"
                name = f"{period.capitalize()} {metric_name}"
                data_path = [period, "totals", metric_key]
                entities.append(
                    VrmOverallStatsSensor(
                        overall_stats_coord, site_id, key, data_path, name, device_class,
                        SensorStateClass.TOTAL_INCREASING, 
                        "kWh", icon, overall_device_info 
                    )
                )

    # --- 5. System Overview Sensoren (KORRIGIERT: Gruppierung unter einem Gerät) ---
    if system_overview_coord.data and "devices" in system_overview_coord.data:
        devices_list = system_overview_coord.data.get("devices", [])
        
        # Konfiguration der Felder, die wir als Sensoren haben wollen
        overview_fields = {
            "firmwareVersion": ("Firmware", None, None, None, "mdi:chip"),
            "lastConnection": ("Last Connection", SensorDeviceClass.TIMESTAMP, None, None, "mdi:clock-check"),
            "productName": ("Product Name", None, None, None, "mdi:information"),
            "remoteOnLan": ("Remote IP", None, None, None, "mdi:ip-network"),
            "connectionInformation": ("Connection Info", None, None, None, "mdi:connection"),
            "autoUpdate": ("Auto Update", None, None, None, "mdi:update"),
            # HINZUGEFÜGTE FELDER:
            "batteryFamily": ("Battery Family", None, None, None, "mdi:battery-heart-variant"),
            "batteryManufacturer": ("Battery Manufacturer", None, None, None, "mdi:factory"),
            "machineSerialNumber": ("Serial Number", None, None, None, "mdi:barcode"),
            "instance": ("Instance ID", None, None, None, "mdi:identifier"),
        }

        for device in devices_list:
            # Try to find a unique ID to uniquely name entities
            # and to find the device in the API data array.
            dev_instance = device.get("instance")
            dev_identifier = device.get("identifier")
            dev_name = device.get("name", "Unknown Device")
            dev_custom_name = device.get("customName")
            
            # Determine the name for the sensor. We use the device name + field suffix
            final_name_prefix = dev_custom_name if dev_custom_name else dev_name
            
            # Determine unique ID for entity ID generation and recognition
            unique_ref = None
            if dev_instance is not None:
                # Important: Instance ID is only unique within the device type, 
                # so include device type ID
                current_type_id = device.get('idDeviceType')
                unique_ref = f"type{current_type_id}_inst{dev_instance}"
            elif dev_identifier:
                unique_ref = f"id_{dev_identifier}"
            else:
                # Fallback if neither instance nor identifier are present
                unique_ref = f"type_{device.get('idDeviceType')}_{slugify(dev_name)}"
            
            # **NO** separate device_info creation here! 
            # Instead use the parent `system_overview_device_info`.

            for field_key, (suffix, dev_class, state_class, unit, icon) in overview_fields.items():
                # The field must be present in the current device data dictionary
                if field_key in device:
                    entities.append(
                        VrmSystemOverviewSensor(
                            system_overview_coord,
                            site_id,
                            f"overview_{unique_ref}_{field_key}", # Unique ID Key
                            unique_ref, # Reference to find the device in the array
                            field_key, # Which field to read
                            f"{final_name_prefix} {suffix}", # Friendly name (e.g. "Cerbo GX Firmware")
                            dev_class,
                            state_class,
                            unit,
                            icon,
                            system_overview_device_info # <--- PARENT DEVICE IS USED HERE
                        )
                    )

    # --- 6. NEW: Diagnostics Sensors (Extended System Data) ---
    if diagnostics_coord.data and "records" in diagnostics_coord.data:
        diagnostics_records = diagnostics_coord.data["records"]
        
        # Useful battery diagnostics (history/stats not in widget)
        battery_diagnostics_config = {
            "55": ("Deepest discharge", SensorDeviceClass.ENERGY, "Ah", "mdi:battery-arrow-down"),
            "56": ("Last discharge", SensorDeviceClass.ENERGY, "Ah", "mdi:battery-minus"),
            "57": ("Average discharge", SensorDeviceClass.ENERGY, "Ah", "mdi:battery-50"),
            "60": ("Total Ah drawn", SensorDeviceClass.ENERGY, "Ah", "mdi:counter"),
            "61": ("Minimum voltage", SensorDeviceClass.VOLTAGE, "V", "mdi:battery-low"),
            "62": ("Maximum voltage", SensorDeviceClass.VOLTAGE, "V", "mdi:battery-high"),
            "63": ("Time since last full charge", None, "s", "mdi:clock-outline"),
        }
        
        # Solar charger diagnostics
        solar_diagnostics_config = {
            "86": ("PV Voltage", SensorDeviceClass.VOLTAGE, "V", "mdi:solar-panel"),
            "97": ("Max Power Yesterday", SensorDeviceClass.POWER, "W", "mdi:solar-power-variant"),
            "98": ("Error Code", None, None, "mdi:alert-circle"),
            "442": ("PV Power", SensorDeviceClass.POWER, "W", "mdi:solar-power"),
            "518": ("MPPT State", None, None, "mdi:state-machine"),
        }
        
        # MultiPlus diagnostics  
        multi_diagnostics_config = {
            "27": ("Active Input Current Limit", SensorDeviceClass.CURRENT, "A", "mdi:current-ac"),
            "41": ("VE.Bus Error", None, None, "mdi:alert-circle"),
            "43": ("Low Battery", None, None, "mdi:battery-alert"),
            "557": ("Charge State", None, None, "mdi:battery-charging"),
        }
        
        # Add battery diagnostics
        for instance_id, data in device_data["battery"].items():
            dev_info = data['device_info']
            live_id = data.get('live_instance', instance_id)
            for data_id, (name, device_class, unit, icon) in battery_diagnostics_config.items():
                # Find matching record in diagnostics (use live instance)
                for record in diagnostics_records:
                    if (str(record.get("idDataAttribute")) == data_id and 
                        record.get("instance") == live_id):
                        entities.append(
                            VrmDiagnosticSensor(
                                diagnostics_coord, site_id,
                                f"diag_{data_id}_{instance_id}",
                                data_id, live_id, name,
                                device_class, SensorStateClass.MEASUREMENT if device_class else None,
                                unit, icon, dev_info
                            )
                        )
                        break
        
        # Add solar charger diagnostics
        for instance_id, data in device_data["solar_charger"].items():
            dev_info = data['device_info']
            live_id = data.get('live_instance', instance_id)
            for data_id, (name, device_class, unit, icon) in solar_diagnostics_config.items():
                # Find matching record in diagnostics (use live instance)
                for record in diagnostics_records:
                    if (str(record.get("idDataAttribute")) == data_id and 
                        record.get("instance") == live_id):
                        entities.append(
                            VrmDiagnosticSensor(
                                diagnostics_coord, site_id,
                                f"diag_{data_id}_{instance_id}",
                                data_id, live_id, name,
                                device_class, SensorStateClass.MEASUREMENT if device_class else None,
                                unit, icon, dev_info
                            )
                        )
                        break
        
        # Add MultiPlus diagnostics
        for instance_id, data in device_data["multi"].items():
            dev_info = data['device_info']
            live_id = data.get('live_instance', instance_id)
            for data_id, (name, device_class, unit, icon) in multi_diagnostics_config.items():
                # Find matching record in diagnostics (use live instance)
                for record in diagnostics_records:
                    if (str(record.get("idDataAttribute")) == data_id and 
                        record.get("instance") == live_id):
                        entities.append(
                            VrmDiagnosticSensor(
                                diagnostics_coord, site_id,
                                f"diag_{data_id}_{instance_id}",
                                data_id, live_id, name,
                                device_class, SensorStateClass.MEASUREMENT if device_class else None,
                                unit, icon, dev_info
                            )
                        )
                        break

    entities.extend(
        _build_dynamic_diagnostic_entities(
            diagnostics_coord,
            site_id,
            diagnostics_coord.data,
            device_data,
            runtime_state["dynamic_diagnostic_keys"],
        )
    )

    async_add_entities(entities, True)

    if config_data.get(CONF_RUNTIME_DISCOVERY, "enabled") == RUNTIME_DISCOVERY_DISABLED:
        return

    entry_conf_key_by_category = {
        "battery": CONF_BATTERY_INSTANCE,
        "multi": CONF_MULTI_INSTANCE,
        "pv_inverter": CONF_PV_INVERTER_INSTANCE,
        "tank": CONF_TANK_INSTANCE,
        "solar_charger": CONF_SOLAR_CHARGER_INSTANCE,
    }

    runtime_discovery_coord = VrmRuntimeDiscoveryCoordinator(
        hass,
        site_id,
        token,
        runtime_state["managed_instances"],
        runtime_state["known_diagnostic_ids"],
    )
    runtime_state["runtime_discovery_coord"] = runtime_discovery_coord

    async def _process_runtime_discovery_update() -> None:
        async with runtime_state["reload_lock"]:
            data = runtime_discovery_coord.data or {}
            new_instances = data.get("new_instances", {})
            has_new_instances = any(new_instances.get(category) for category in _KNOWN_DEVICE_CATEGORIES)
            if has_new_instances:
                updated_data = dict(entry.data)
                for category, conf_key in entry_conf_key_by_category.items():
                    if category not in new_instances:
                        continue
                    current_ids = set(_parse_instance_ids(updated_data.get(conf_key, "")))
                    current_ids.update(new_instances[category])
                    updated_data[conf_key] = _serialize_instance_ids(sorted(current_ids))

                _LOGGER.info("Runtime discovery detected new instances. Reloading integration entry %s.", entry.entry_id)
                hass.config_entries.async_update_entry(entry, data=updated_data)
                hass.async_create_task(hass.config_entries.async_reload(entry.entry_id))
                return

            new_dynamic_entities = _build_dynamic_diagnostic_entities(
                diagnostics_coord,
                site_id,
                runtime_discovery_coord._diagnostics_coord.data,
                device_data,
                runtime_state["dynamic_diagnostic_keys"],
            )
            if new_dynamic_entities:
                _LOGGER.info("Runtime discovery adding %d new diagnostics sensors.", len(new_dynamic_entities))
                async_add_entities(new_dynamic_entities, True)

    def _runtime_discovery_listener() -> None:
        hass.async_create_task(_process_runtime_discovery_update())

    unsub_discovery = runtime_discovery_coord.async_add_listener(_runtime_discovery_listener)
    entry.async_on_unload(unsub_discovery)
    await runtime_discovery_coord.async_refresh()


# --- 5. Basisklasse für Sensoren -----------
class VrmBaseSensor(CoordinatorEntity, SensorEntity):
    """Basisklasse für alle VRM Sensoren."""
    def __init__(self, coordinator, site_id, key, name, device_class, state_class, unit, icon, device_info):
        super().__init__(coordinator)
        
        unique_id_name = device_info.get("_unique_id_name", device_info["name"])
        unique_slug = slugify(f"{unique_id_name}_{key}")
        # When the sensor is grouped under a parent device, the unique_id must be constructed differently 
        # to avoid conflicts (e.g. when multiple sensors have the same device_info name)
        # For System Overview sensors, the key is already assumed to be unique.
        self._attr_unique_id = f"vrm_v2_{site_id}_{unique_slug}"
        
        self._attr_name = name
        self.entity_id = f"sensor.vrm_{slugify(name)}"
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_device_info = {
            key: value for key, value in device_info.items() if key != "_unique_id_name"
        }
        
        # Set display precision based on device class and unit
        if device_class == SensorDeviceClass.VOLTAGE:
            self._attr_suggested_display_precision = 2
        elif device_class == SensorDeviceClass.CURRENT:
            self._attr_suggested_display_precision = 2
        elif device_class == SensorDeviceClass.POWER:
            self._attr_suggested_display_precision = 1
        elif device_class == SensorDeviceClass.ENERGY:
            self._attr_suggested_display_precision = 3
        elif device_class == SensorDeviceClass.FREQUENCY:
            self._attr_suggested_display_precision = 2
        elif device_class == SensorDeviceClass.TEMPERATURE:
            self._attr_suggested_display_precision = 1
        elif device_class == SensorDeviceClass.BATTERY:
            self._attr_suggested_display_precision = 1
        elif unit == "Ah":
            self._attr_suggested_display_precision = 2
        elif unit == "h":
            self._attr_suggested_display_precision = 1
        elif unit == "%":
            self._attr_suggested_display_precision = 1 

# --- 6. Battery Summary Sensor ---------------------------------------------------
class VrmBatterySummarySensor(VrmBaseSensor):
    """Represents a single value from the VRM Battery Summary data."""
    def __init__(self, coordinator, site_id, key, data_id, name, device_class, state_class, unit, icon, device_info):
        super().__init__(coordinator, site_id, key, name, device_class, state_class, unit, icon, device_info)
        self._data_id = data_id
    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        data = self.coordinator.data.get("data", {})
        attr = data.get(self._data_id, {})
        return attr.get("valueFloat")

# --- 6.1 Battery Alarm Sensor --------------------------------------------
class VrmBatteryAlarmSensor(VrmBaseSensor):
    """Represents a Battery Alarm Status (Text from Enum)."""
    def __init__(self, coordinator, site_id, key, data_id, name, device_class, state_class, unit, icon, device_info):
        super().__init__(coordinator, site_id, key, name, device_class, state_class, unit, icon, device_info)
        self._data_id = data_id

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        
        records_data = self.coordinator.data.get("data", {})
        specific_data = records_data.get(self._data_id, {})
        
        raw_value = None
        try:
            first_index = specific_data.get("0", {})
            raw_value = first_index.get("0")
        except (AttributeError, KeyError):
            return None

        if raw_value is None:
            return None

        enums = self.coordinator.data.get("enums", {})
        specific_enums = enums.get(self._data_id, {})
        
        human_readable = specific_enums.get(str(raw_value))
        if human_readable:
            return human_readable
        
        return raw_value

# --- 6.5. Calculated Battery Power Sensor --------------------------------------
class VrmBatteryPowerSensor(VrmBaseSensor):
    """Calculates Battery Power (Voltage * Current) from Battery Summary data."""
    
    VOLTAGE_DATA_ID = "47"
    CURRENT_DATA_ID = "49"

    def __init__(self, coordinator, site_id, key, name, device_info):
        super().__init__(
            coordinator, site_id, key, name, SensorDeviceClass.POWER,
            SensorStateClass.MEASUREMENT, "W", None, device_info
        )

    @property
    def native_value(self) -> float:
        if not self.coordinator.data:
            return 0.0
        data = self.coordinator.data.get("data", {})
        voltage = data.get(self.VOLTAGE_DATA_ID, {}).get("valueFloat")
        current = data.get(self.CURRENT_DATA_ID, {}).get("valueFloat")

        if voltage is None or current is None:
            return 0.0
        try:
            return round(voltage * current, 2) 
        except (TypeError, ValueError):
            return 0.0

# --- 6.6. Calculated MultiPlus DC Power Sensor --------------------------------------
class VrmMultiPlusDCPowerSensor(VrmBaseSensor):
    """Calculates MultiPlus DC Power (Voltage * Current) from Multi Status data."""
    
    VOLTAGE_DATA_ID = "32"
    CURRENT_DATA_ID = "33"

    def __init__(self, coordinator, site_id, key, name, device_info):
        super().__init__(
            coordinator, site_id, key, name, SensorDeviceClass.POWER,
            SensorStateClass.MEASUREMENT, "W", None, device_info
        )

    @property
    def native_value(self) -> float:
        if not self.coordinator.data:
            return 0.0
        data = self.coordinator.data.get("data", {})
        voltage = data.get(self.VOLTAGE_DATA_ID, {}).get("valueFloat")
        current = data.get(self.CURRENT_DATA_ID, {}).get("valueFloat")

        if voltage is None or current is None:
            return 0.0
        try:
            return round(voltage * current, 2) 
        except (TypeError, ValueError):
            return 0.0

# --- 6.7. Calculated PV Total Today Sensor --------------------------------------
class VrmPvTotalTodaySensor(VrmBaseSensor):
    """Calculates total PV energy produced today (Pc + Pb + Pg)."""
    
    PC_KEY = "Pc"
    PB_KEY = "Pb"
    PG_KEY = "Pg"

    def __init__(self, coordinator, site_id, key, name, device_info):
        super().__init__(
            coordinator, site_id, key, name, SensorDeviceClass.ENERGY,
            SensorStateClass.TOTAL_INCREASING, "kWh", "mdi:solar-power", device_info
        )

    @property
    def native_value(self) -> float:
        if not self.coordinator.data or "totals" not in self.coordinator.data:
            return 0.0
        
        totals = self.coordinator.data.get("totals", {})
        
        try:
            pc = float(totals.get(self.PC_KEY, 0.0))
            pb = float(totals.get(self.PB_KEY, 0.0))
            pg = float(totals.get(self.PG_KEY, 0.0))
        except (TypeError, ValueError):
            _LOGGER.warning("At least one PV value (Pc, Pb, Pg) is not available as a number.")
            return 0.0

        total_pv = pc + pb + pg
        
        return round(total_pv, 3)

# --- 7. Overall Stats Sensor -----------------------------------------------------
class VrmOverallStatsSensor(VrmBaseSensor):
    """Represents a single value from the VRM Overall Stats data."""
    def __init__(self, coordinator, site_id, key, data_path, name, device_class, state_class, unit, icon, device_info):
        super().__init__(coordinator, site_id, key, name, device_class, state_class, unit, icon, device_info)
        self._data_path = data_path
    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        value = self.coordinator.data
        try:
            for key in self._data_path:
                value = value[key]
            if isinstance(value, (int, float)):
                return value
            if isinstance(value, str):
                return float(value)
            return None
        except (KeyError, TypeError, ValueError):
            return 0.0 
            
# --- 8. MultiPlus Status Sensor ----------------------------------------------
class VrmMultiStatusSensor(VrmBaseSensor):
    """Represents a single value from the VRM MultiPlus Status data."""
    def __init__(self, coordinator, site_id, key, data_id, name, device_class, state_class, unit, icon, device_info):
        super().__init__(coordinator, site_id, key, name, device_class, state_class, unit, icon, device_info)
        self._data_id = data_id
    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        data = self.coordinator.data.get("data", {})
        data_item = data.get(self._data_id, {})
        if not data_item:
            return None

        # Enum attributes: resolve valueEnum through the enum map
        # (nameEnum / formattedValue can be stale on the VRM server)
        enum_values = data_item.get("dataAttributeEnumValues")
        value_enum = data_item.get("valueEnum")
        if enum_values and value_enum is not None:
            for entry in enum_values:
                if entry.get("valueEnum") == value_enum:
                    return entry["nameEnum"]

        value_float = data_item.get("valueFloat")
        if value_float is not None:
            return value_float
        value_enum_name = data_item.get("nameEnum")
        if value_enum_name is not None:
            return value_enum_name
        return data_item.get("value")

# --- 9. PV Inverter Sensor --------------------
class VrmPvInverterSensor(VrmBaseSensor):
    """Represents a single value from the VRM PV Inverter Status data."""
    def __init__(self, coordinator, site_id, key, data_id, name, device_class, state_class, unit, icon, device_info):
        super().__init__(coordinator, site_id, key, name, device_class, state_class, unit, icon, device_info)
        self._data_id = data_id
        
    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        data = self.coordinator.data.get("data", {})
        attr = data.get(self._data_id, {})
        if not attr:
            return None

        # Enum attributes: resolve valueEnum through the enum map
        enum_values = attr.get("dataAttributeEnumValues")
        value_enum_id = attr.get("valueEnum")
        if enum_values and value_enum_id is not None:
            for entry in enum_values:
                if entry.get("valueEnum") == value_enum_id:
                    return entry["nameEnum"]

        value_float = attr.get("valueFloat")
        if value_float is not None:
            return value_float
            
        value_enum = attr.get("nameEnum")
        if value_enum is not None:
            return value_enum
        return attr.get("value")

# --- 10. Tank Sensor ----------------------------------------------------------
class VrmTankSensor(VrmBaseSensor):
    """Represents a single value from the VRM Tank Status data."""
    def __init__(self, coordinator, site_id, key, data_id, name, device_class, state_class, unit, icon, device_info):
        super().__init__(coordinator, site_id, key, name, device_class, state_class, unit, icon, device_info)
        self._data_id = data_id
        
    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        data = self.coordinator.data.get("data", {})
        attr = data.get(str(self._data_id), {}) 
        if not attr:
            return None

        # Enum attributes: resolve valueEnum through the enum map
        enum_values = attr.get("dataAttributeEnumValues")
        value_enum_id = attr.get("valueEnum")
        if enum_values and value_enum_id is not None:
            for entry in enum_values:
                if entry.get("valueEnum") == value_enum_id:
                    return entry["nameEnum"]

        value_float = attr.get("valueFloat")
        if value_float is not None:
            return value_float
            
        value_enum = attr.get("nameEnum")
        if value_enum is not None:
            return value_enum
        return attr.get("value")

# --- 11. Solar Charger Sensor -------------------------------------------------
class VrmSolarChargerSensor(VrmBaseSensor):
    """Represents a single value from the VRM Solar Charger Status data."""
    def __init__(self, coordinator, site_id, key, data_id, name, device_class, state_class, unit, icon, device_info):
        super().__init__(coordinator, site_id, key, name, device_class, state_class, unit, icon, device_info)
        self._data_id = data_id
        
    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        data = self.coordinator.data.get("data", {})
        attr = data.get(str(self._data_id), {}) 
        if not attr:
            return None

        # Enum attributes: resolve valueEnum through the enum map
        enum_values = attr.get("dataAttributeEnumValues")
        value_enum_id = attr.get("valueEnum")
        if enum_values and value_enum_id is not None:
            for entry in enum_values:
                if entry.get("valueEnum") == value_enum_id:
                    return entry["nameEnum"]

        value_float = attr.get("valueFloat")
        if value_float is not None:
            return value_float
            
        value_enum = attr.get("nameEnum")
        if value_enum is not None:
            return value_enum
        return attr.get("value")

# --- 12. System Overview Sensor (NEU) ----------------------------------------
class VrmSystemOverviewSensor(VrmBaseSensor):
    """Represents a generic value from the System Overview data."""
    def __init__(self, coordinator, site_id, key, unique_ref, json_key, name, device_class, state_class, unit, icon, device_info):
        super().__init__(coordinator, site_id, key, name, device_class, state_class, unit, icon, device_info)
        self._unique_ref = unique_ref
        self._json_key = json_key

    @property
    def native_value(self):
        if not self.coordinator.data or "devices" not in self.coordinator.data:
            return None
            
        devices = self.coordinator.data["devices"]
        
        # We need to find the device in the list.
        # We use the unique_ref defined in setup (e.g. "type130_inst1")
        
        target_device = None
        for device in devices:
            dev_instance = device.get("instance")
            dev_identifier = device.get("identifier")
            dev_name = device.get("name", "Unknown")
            
            # Reconstruction of unique ref (must match the logic in setup)
            current_ref = None
            if dev_instance is not None:
                current_type_id = device.get('idDeviceType')
                current_ref = f"type{current_type_id}_inst{dev_instance}"
            elif dev_identifier:
                current_ref = f"id_{dev_identifier}"
            else:
                 current_ref = f"type_{device.get('idDeviceType')}_{slugify(dev_name)}"
                 
            if current_ref == self._unique_ref:
                target_device = device
                break
        
        if not target_device:
            return None
            
        value = target_device.get(self._json_key)
        
        # Special handling for timestamps
        if self.device_class == SensorDeviceClass.TIMESTAMP:
            if value is not None and isinstance(value, int):
                # Convert UNIX timestamp to datetime object with UTC timezone
                return datetime.fromtimestamp(value, tz=timezone.utc)
        
        # Value can be False, 0, None, String or Int. We return it unchanged.
        return value

# --- 13. NEW: Diagnostic Sensor (from diagnostics endpoint) -------------------
class VrmDiagnosticSensor(VrmBaseSensor):
    """Represents a sensor from the VRM diagnostics endpoint."""
    def __init__(self, coordinator, site_id, key, data_id, instance, name, device_class, state_class, unit, icon, device_info):
        super().__init__(coordinator, site_id, key, name, device_class, state_class, unit, icon, device_info)
        self._data_id = str(data_id)
        self._instance = instance

    @property
    def native_value(self):
        if not self.coordinator.data or "records" not in self.coordinator.data:
            return None
        
        records = self.coordinator.data["records"]
        
        # Find matching record by data_id and instance
        for record in records:
            if (str(record.get("idDataAttribute")) == self._data_id and 
                record.get("instance") == self._instance):
                
                raw = record.get("rawValue")

                # Enum attributes: resolve rawValue through the enum map
                # (formattedValue can be stale on the VRM server)
                enum_values = record.get("dataAttributeEnumValues")
                if enum_values and raw is not None:
                    for entry in enum_values:
                        if entry.get("valueEnum") == raw:
                            return entry["nameEnum"]
                    return raw

                # Numeric: try formattedValue first (includes unit)
                formatted = record.get("formattedValue")
                if formatted:
                    try:
                        return float(formatted.split()[0])
                    except (ValueError, IndexError):
                        return formatted
                
                # Fallback to rawValue
                if raw is not None:
                    return raw
                
                return None
        
        return None
