"""Inventory every value returned by the VRM endpoints for one installation.

Live mode reads VRM_TOKEN and VRM_SITE_ID from the environment or a local
.env file. Capture mode reads an existing ignored api_data_* directory.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BASE_URL = "https://vrmapi.victronenergy.com/v2/installations/{site_id}/"
MIN_REQUEST_INTERVAL = 0.35
DEVICE_TYPE_NAMES = {
    0: "Gateway",
    1: "VE.Bus System",
    2: "Battery Monitor",
    3: "Expansion I/O",
    4: "Solar Charger",
    5: "Tank",
    20: "Digital Input",
}
DEVICE_ENDPOINTS = {
    1: (("status", "widgets/Status?instance={instance}"),),
    2: (
        ("summary", "widgets/BatterySummary?instance={instance}"),
        ("history", "widgets/HistoricData?instance={instance}"),
        ("alarms", "widgets/BatteryMonitorWarningsAndAlarms?instance={instance}"),
    ),
    4: (("summary", "widgets/SolarChargerSummary?instance={instance}"),),
    5: (("summary", "widgets/TankSummary?instance={instance}"),),
}
CAPTURE_PATTERNS = {
    "system-overview": ("system_overview.json",),
    "diagnostics": ("diagnostics.json",),
    "overallstats": ("overallstats.json",),
    "stats": ("stats_kwh.json",),
}


def _display_value(value_data: Any) -> Any:
    """Return the best human-readable value without trusting stale enum text."""
    if not isinstance(value_data, dict):
        return value_data

    enum_value = value_data.get("valueEnum")
    enum_values = value_data.get("dataAttributeEnumValues") or []
    if enum_value is not None:
        for enum_entry in enum_values:
            if enum_entry.get("valueEnum") == enum_value:
                return enum_entry.get("nameEnum", enum_value)

    for key in ("valueFloat", "value", "nameEnum", "formattedValue"):
        value = value_data.get(key)
        if value not in (None, ""):
            return value
    return None


def _diagnostic_value(record: dict[str, Any]) -> Any:
    """Resolve a diagnostics value from raw enum data before formatted text."""
    raw_value = record.get("rawValue")
    for enum_entry in record.get("dataAttributeEnumValues") or []:
        if enum_entry.get("valueEnum") == raw_value:
            return enum_entry.get("nameEnum", raw_value)
    return record.get("formattedValue") or raw_value


class LiveClient:
    """Small rate-limited VRM client used only by this developer tool."""

    def __init__(self, site_id: str, token: str) -> None:
        self._base_url = BASE_URL.format(site_id=site_id)
        self._headers = {"X-Authorization": f"Token {token}"}
        self._last_request = 0.0

    def get(self, endpoint: str) -> dict[str, Any] | None:
        elapsed = time.monotonic() - self._last_request
        if elapsed < MIN_REQUEST_INTERVAL:
            time.sleep(MIN_REQUEST_INTERVAL - elapsed)

        request = Request(f"{self._base_url}{endpoint}", headers=self._headers)
        try:
            with urlopen(request, timeout=15) as response:
                self._last_request = time.monotonic()
                if response.status == 204:
                    return None
                return json.load(response)
        except HTTPError as error:
            self._last_request = time.monotonic()
            if error.code == 429:
                retry_after = max(float(error.headers.get("Retry-After", "1")), 1.0)
                time.sleep(retry_after)
                return self.get(endpoint)
            raise


def _load_local_env(path: Path = Path(".env")) -> None:
    """Load missing variables from a simple local dotenv file."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _records(payload: dict[str, Any] | None) -> Any:
    if not payload:
        return None
    return payload.get("records", payload)


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as file_handle:
        return json.load(file_handle)


def _capture_file(capture_dir: Path, device_type: int, instance: int, label: str) -> Path | None:
    prefixes = {
        1: "multiplus",
        2: "battery",
        4: "solar_charger",
        5: "tank",
    }
    suffixes = {
        "summary": "summary",
        "history": "history",
        "alarms": "alarms",
        "status": "status",
    }
    candidate = capture_dir / f"{prefixes[device_type]}_{instance}_{suffixes[label]}.json"
    return candidate if candidate.exists() else None


def _device_name(device: dict[str, Any]) -> str:
    return str(device.get("customName") or device.get("name") or device.get("productName") or "Unknown device")


def _widget_rows(payload: dict[str, Any] | None, source: str) -> list[dict[str, Any]]:
    records = _records(payload)
    if not isinstance(records, dict):
        return []
    data = records.get("data", {})
    rows = []
    for data_id, value_data in data.items():
        if not str(data_id).isdigit():
            continue
        rows.append(
            {
                "source": source,
                "id": str(data_id),
                "name": value_data.get("dataAttributeName") or value_data.get("description") or value_data.get("code") or "",
                "value": _display_value(value_data),
                "unit": value_data.get("unit") or value_data.get("unitOfMeasurement") or "",
            }
        )
    return rows


def _diagnostic_rows(payload: dict[str, Any] | None) -> dict[tuple[str, int], list[dict[str, Any]]]:
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    records = payload.get("records", []) if payload else []
    for record in records:
        service_type = str(record.get("dbusServiceType") or "gateway")
        instance = record.get("instance")
        if instance is None:
            instance = 0
        grouped[(service_type, int(instance))].append(
            {
                "source": "diagnostics",
                "id": str(record.get("idDataAttribute", "")),
                "name": record.get("dataAttributeName") or record.get("description") or record.get("code") or "",
                "value": _diagnostic_value(record),
                "unit": record.get("unit") or record.get("unitOfMeasurement") or "",
            }
        )
    return grouped


def _format_row(row: dict[str, Any]) -> str:
    name = str(row["name"]).replace("|", "/") or "(unnamed)"
    value = str(row["value"]).replace("|", "/")
    unit = str(row["unit"]).replace("|", "/")
    return f"| {row['source']} | {row['id']} | {name} | {value} | {unit} |"


def build_report(
    system_overview: dict[str, Any] | None,
    diagnostics: dict[str, Any] | None,
    widget_payloads: dict[tuple[int, int, str], dict[str, Any] | None],
) -> str:
    """Build a complete Markdown inventory grouped by physical device."""
    overview_records = _records(system_overview) or {}
    devices = overview_records.get("devices", []) if isinstance(overview_records, dict) else []
    diagnostics_by_device = _diagnostic_rows(diagnostics)
    sections = ["# VRM Value Inventory", ""]

    matched_diagnostics: set[tuple[str, int]] = set()
    service_by_type = {
        0: "gateway",
        1: "vebus",
        2: "battery",
        3: "switch",
        4: "solarcharger",
        5: "tank",
        20: "digitalinput",
    }
    for device in sorted(devices, key=lambda item: (str(item.get("name", "")), int(item.get("instance") or 0))):
        device_type = int(device.get("idDeviceType") or 0)
        instance = int(device.get("instance") or 0)
        type_name = DEVICE_TYPE_NAMES.get(device_type, str(device.get("deviceType") or f"Device type {device_type}"))
        sections.extend(
            [
                f"## {_device_name(device)} [{instance}]",
                "",
                f"Type: {type_name} (idDeviceType {device_type})",
                "",
                "| Source | ID/key | Name | Value | Unit |",
                "| :--- | :--- | :--- | :--- | :--- |",
            ]
        )
        rows: list[dict[str, Any]] = []
        for (payload_type, payload_instance, label), payload in widget_payloads.items():
            if payload_type == device_type and payload_instance == instance:
                rows.extend(_widget_rows(payload, label))

        service_type = service_by_type.get(device_type)
        diagnostic_key = (service_type, instance) if service_type else None
        if diagnostic_key and diagnostic_key in diagnostics_by_device:
            rows.extend(diagnostics_by_device[diagnostic_key])
            matched_diagnostics.add(diagnostic_key)

        metadata_keys = (
            "firmwareVersion",
            "lastConnection",
            "productName",
            "connectionInformation",
            "autoUpdate",
            "batteryFamily",
            "batteryManufacturer",
            "instance",
        )
        rows.extend(
            {
                "source": "system-overview",
                "id": key,
                "name": key,
                "value": device[key],
                "unit": "",
            }
            for key in metadata_keys
            if key in device
        )
        sections.extend(_format_row(row) for row in rows)
        if not rows:
            sections.append("| - | - | No values returned | - | - |")
        sections.append("")

    remaining = {
        key: rows for key, rows in diagnostics_by_device.items() if key not in matched_diagnostics
    }
    for (service_type, instance), rows in sorted(remaining.items()):
        sections.extend(
            [
                f"## Diagnostics: {service_type} [{instance}]",
                "",
                "| Source | ID/key | Name | Value | Unit |",
                "| :--- | :--- | :--- | :--- | :--- |",
                *(_format_row(row) for row in rows),
                "",
            ]
        )
    return "\n".join(sections)


def _live_payloads(client: LiveClient) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict]:
    system_overview = client.get("system-overview")
    diagnostics = client.get("diagnostics")
    overview_records = _records(system_overview) or {}
    devices = overview_records.get("devices", []) if isinstance(overview_records, dict) else []
    widget_payloads = {}
    for device in devices:
        device_type = int(device.get("idDeviceType") or 0)
        instance = int(device.get("instance") or 0)
        for label, endpoint in DEVICE_ENDPOINTS.get(device_type, ()):
            widget_payloads[(device_type, instance, label)] = client.get(endpoint.format(instance=instance))
    return system_overview, diagnostics, widget_payloads


def _capture_payloads(capture_dir: Path) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict]:
    system_overview = _load_json(capture_dir / CAPTURE_PATTERNS["system-overview"][0])
    diagnostics = _load_json(capture_dir / CAPTURE_PATTERNS["diagnostics"][0])
    overview_records = _records(system_overview) or {}
    devices = overview_records.get("devices", []) if isinstance(overview_records, dict) else []
    widget_payloads = {}
    for device in devices:
        device_type = int(device.get("idDeviceType") or 0)
        instance = int(device.get("instance") or 0)
        for label, _endpoint in DEVICE_ENDPOINTS.get(device_type, ()):
            capture_file = _capture_file(capture_dir, device_type, instance, label)
            widget_payloads[(device_type, instance, label)] = _load_json(capture_file) if capture_file else None
    return system_overview, diagnostics, widget_payloads


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-dir", type=Path, help="Read an existing api_data_* capture instead of VRM")
    parser.add_argument("--output", type=Path, help="Write Markdown here instead of standard output")
    args = parser.parse_args()

    if args.capture_dir:
        payloads = _capture_payloads(args.capture_dir)
    else:
        _load_local_env()
        token = os.environ.get("VRM_TOKEN")
        site_id = os.environ.get("VRM_SITE_ID")
        if not token or not site_id:
            parser.error("live mode requires VRM_TOKEN and VRM_SITE_ID in the environment or .env")
        payloads = _live_payloads(LiveClient(site_id, token))

    report = build_report(*payloads)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()