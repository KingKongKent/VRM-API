"""Focused regression tests for VRM sensor discovery and value helpers."""

from __future__ import annotations

import importlib.util
import re
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "custom_components.victron_vrm_api"


class _CoordinatorEntity:
    def __init__(self, coordinator):
        self.coordinator = coordinator


class _DataUpdateCoordinator:
    def __init__(self, *args, **kwargs):
        self.data = None


class _SensorDeviceClass:
    BATTERY = "battery"
    CURRENT = "current"
    DATA_SIZE = "data_size"
    DURATION = "duration"
    ENERGY = "energy"
    FREQUENCY = "frequency"
    HUMIDITY = "humidity"
    POWER = "power"
    TEMPERATURE = "temperature"
    TIMESTAMP = "timestamp"
    VOLTAGE = "voltage"
    VOLUME = "volume"


class _SensorStateClass:
    MEASUREMENT = "measurement"
    TOTAL = "total"
    TOTAL_INCREASING = "total_increasing"


def _module(name: str, **attributes):
    module = types.ModuleType(name)
    for attribute, value in attributes.items():
        setattr(module, attribute, value)
    sys.modules[name] = module
    return module


def _load_sensor_module():
    for name in (
        "aiohttp",
        "homeassistant",
        "homeassistant.components",
        "homeassistant.components.sensor",
        "homeassistant.core",
        "homeassistant.config_entries",
        "homeassistant.helpers",
        "homeassistant.helpers.device_registry",
        "homeassistant.helpers.entity_registry",
        "homeassistant.helpers.entity_platform",
        "homeassistant.helpers.aiohttp_client",
        "homeassistant.helpers.update_coordinator",
        "homeassistant.util",
    ):
        sys.modules.pop(name, None)

    _module(
        "aiohttp",
        ClientError=OSError,
        ClientTimeout=lambda **kwargs: kwargs,
    )
    _module("homeassistant")
    _module("homeassistant.components")
    _module(
        "homeassistant.components.sensor",
        SensorEntity=type("SensorEntity", (), {}),
        SensorDeviceClass=_SensorDeviceClass,
        SensorStateClass=_SensorStateClass,
    )
    _module("homeassistant.core", HomeAssistant=type("HomeAssistant", (), {}))
    _module("homeassistant.config_entries", ConfigEntry=type("ConfigEntry", (), {}))
    helpers_module = _module("homeassistant.helpers")
    device_registry_module = _module(
        "homeassistant.helpers.device_registry",
        async_get=lambda hass: hass.device_registry,
    )
    entity_registry_module = _module(
        "homeassistant.helpers.entity_registry",
        async_get=lambda hass: hass.entity_registry,
    )
    helpers_module.device_registry = device_registry_module
    helpers_module.entity_registry = entity_registry_module
    _module(
        "homeassistant.helpers.entity_platform",
        AddEntitiesCallback=object,
    )
    _module(
        "homeassistant.helpers.aiohttp_client",
        async_get_clientsession=lambda hass: None,
    )
    _module(
        "homeassistant.helpers.update_coordinator",
        CoordinatorEntity=_CoordinatorEntity,
        DataUpdateCoordinator=_DataUpdateCoordinator,
        UpdateFailed=RuntimeError,
    )
    _module(
        "homeassistant.util",
        slugify=lambda value: re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_"),
    )

    package = types.ModuleType(PACKAGE)
    package.__path__ = [str(ROOT / "custom_components" / "victron_vrm_api")]
    sys.modules[PACKAGE] = package

    const_name = f"{PACKAGE}.const"
    const_spec = importlib.util.spec_from_file_location(
        const_name, ROOT / "custom_components" / "victron_vrm_api" / "const.py"
    )
    const_module = importlib.util.module_from_spec(const_spec)
    sys.modules[const_name] = const_module
    const_spec.loader.exec_module(const_module)

    sensor_name = f"{PACKAGE}.sensor"
    sensor_spec = importlib.util.spec_from_file_location(
        sensor_name, ROOT / "custom_components" / "victron_vrm_api" / "sensor.py"
    )
    sensor_module = importlib.util.module_from_spec(sensor_spec)
    sys.modules[sensor_name] = sensor_module
    sensor_spec.loader.exec_module(sensor_module)
    return sensor_module


sensor = _load_sensor_module()


def _record(service, instance, data_id, raw_value, formatted_value=None, timestamp=100):
    return {
        "dbusServiceType": service,
        "instance": instance,
        "idDataAttribute": data_id,
        "rawValue": raw_value,
        "formattedValue": formatted_value,
        "timestamp": timestamp,
    }


class VrmSensorLogicTests(unittest.TestCase):
    def test_live_device_type_map_does_not_treat_expansion_io_as_pv(self):
        self.assertNotIn(3, sensor._VRM_DEVICE_TYPE_MAP)
        self.assertEqual(sensor._VRM_DEVICE_TYPE_MAP[5], "tank")

    def test_remap_preserves_identity_and_does_not_duplicate_targets(self):
        overview = {
            "devices": [
                {"idDeviceType": 2, "instance": instance} for instance in (202, 288, 289)
            ]
            + [{"idDeviceType": 1, "instance": 276}]
            + [{"idDeviceType": 4, "instance": instance} for instance in (288, 290)]
            + [{"idDeviceType": 5, "instance": instance} for instance in (24, 203)]
        }
        diagnostics = {
            "records": [
                _record("battery", 202, 47, 13.4),
                _record("battery", 288, 47, 13.5),
                _record("battery", 289, 47, 13.4),
                _record("battery", 291, 47, 0, timestamp=50),
                _record("vebus", 276, 40, 9),
                _record("vebus", 291, 40, 0, timestamp=50),
                _record("solarcharger", 288, 442, 100),
                _record("solarcharger", 290, 442, 100),
                _record("solarcharger", 289, 442, 0, timestamp=50),
                _record("tank", 24, 330, 25),
                _record("tank", 203, 330, 50),
            ]
        }
        configured = {
            "battery": [288, 291],
            "multi": [291],
            "pv_inverter": [],
            "tank": [203],
            "solar_charger": [289, 290],
        }

        remap = sensor._build_instance_remap(overview, diagnostics, configured)
        self.assertEqual(remap["battery"], {288: 288, 291: 289})
        self.assertEqual(remap["multi"], {291: 276})
        self.assertEqual(remap["solar_charger"], {289: 288, 290: 290})

        live = sensor._extract_live_instances(overview, diagnostics)
        merged = sensor._merge_discovered_instances(configured, live, remap)
        self.assertEqual(merged["battery"], [202, 288, 291])
        self.assertEqual(merged["multi"], [291])
        self.assertEqual(merged["solar_charger"], [289, 290])
        self.assertEqual(merged["tank"], [24, 203])

    def test_pv_current_uses_matching_solarcharger_records(self):
        coordinator = types.SimpleNamespace(
            data={
                "records": [
                    _record("system", 288, 442, 999),
                    _record("solarcharger", 288, 442, 102),
                    _record("solarcharger", 288, 86, 39.4),
                ]
            }
        )
        entity = sensor.VrmSolarPvCurrentSensor(
            coordinator,
            "site",
            "pv_current_288",
            288,
            "PV Current",
            {"name": "Solar Charger 288"},
        )
        self.assertEqual(entity.native_value, 2.59)

    def test_pv_current_rejects_zero_voltage(self):
        coordinator = types.SimpleNamespace(
            data={
                "records": [
                    _record("solarcharger", 288, 442, 102),
                    _record("solarcharger", 288, 86, 0),
                ]
            }
        )
        entity = sensor.VrmSolarPvCurrentSensor(
            coordinator,
            "site",
            "pv_current_288",
            288,
            "PV Current",
            {"name": "Solar Charger 288"},
        )
        self.assertIsNone(entity.native_value)

    def test_auxiliary_operational_entities_are_named_and_deduplicated(self):
        records = [
            _record("switch", 121, 1866, "DC/DC", "DC/DC"),
            _record("switch", 121, 1869, 1, "1"),
            _record("digitalinput", 110, 593, "Water Leak", "Water Leak"),
            _record("digitalinput", 110, 465, 0, "No alarm"),
            _record("digitalinput", 110, 466, 1, "High"),
            _record("digitalinput", 110, 467, 3, "3"),
            _record("digitalinput", 110, 468, 2, "Bilge pump"),
            _record("gateway", 101, 637, "Temp Lugar", "Temp Lugar"),
            _record("temperature", 101, 450, 22.4, "22.4 °C"),
            _record("temperature", 101, 920, 59.2, "59.2 %"),
            _record("gateway", 0, 558, 0, "Idle"),
            _record("system", 0, 113, 256, "256 W"),
        ]
        coordinator = types.SimpleNamespace(data={"records": records})
        created_keys = set()
        entities = sensor._build_auxiliary_diagnostic_entities(
            coordinator,
            "site",
            coordinator.data,
            created_keys,
            {"name": "VRM Site"},
        )

        self.assertEqual(len(entities), 9)
        self.assertEqual(
            {entity._attr_device_info["name"] for entity in entities},
            {"DC/DC", "Water Leak", "Temp Lugar", "VRM Site"},
        )
        self.assertEqual(
            sensor._build_auxiliary_diagnostic_entities(
                coordinator,
                "site",
                coordinator.data,
                created_keys,
                {"name": "VRM Site"},
            ),
            [],
        )

    def test_registry_cleanup_preserves_active_and_removes_empty_stale_device(self):
        active = types.SimpleNamespace(
            entity_id="sensor.active",
            config_entry_id="entry",
            platform="victron_vrm_api",
            unique_id="active-id",
            device_id="active-device",
        )
        obsolete = types.SimpleNamespace(
            entity_id="sensor.vrm_diagnostic_80",
            config_entry_id="entry",
            platform="victron_vrm_api",
            unique_id="old-diag-dynamic-id",
            device_id="stale-device",
        )
        unrelated = types.SimpleNamespace(
            entity_id="sensor.other",
            config_entry_id="other-entry",
            platform="other",
            unique_id="other-id",
            device_id="stale-device",
        )

        class EntityRegistry:
            def __init__(self):
                self.entities = {
                    active.entity_id: active,
                    obsolete.entity_id: obsolete,
                    unrelated.entity_id: unrelated,
                }
                self.save_scheduled = False

            def async_remove(self, entity_id):
                self.entities.pop(entity_id)

            def async_schedule_save(self):
                self.save_scheduled = True

        class DeviceRegistry:
            def __init__(self):
                self.devices = {
                    "active-device": types.SimpleNamespace(
                        id="active-device",
                        config_entries={"entry"},
                        identifiers={("victron_vrm_api", "active")},
                    ),
                    "empty-device": types.SimpleNamespace(
                        id="empty-device",
                        config_entries={"entry"},
                        identifiers={("victron_vrm_api", "stale")},
                    ),
                }
                self.save_scheduled = False

            def async_remove_device(self, device_id):
                self.devices.pop(device_id)

            def async_schedule_save(self):
                self.save_scheduled = True

        hass = types.SimpleNamespace(
            entity_registry=EntityRegistry(),
            device_registry=DeviceRegistry(),
        )
        entry = types.SimpleNamespace(entry_id="entry")

        sensor._cleanup_obsolete_registry_entries(hass, entry, {"active-id"})

        self.assertIn("sensor.active", hass.entity_registry.entities)
        self.assertIn("sensor.other", hass.entity_registry.entities)
        self.assertNotIn("sensor.vrm_diagnostic_80", hass.entity_registry.entities)
        self.assertTrue(hass.entity_registry.save_scheduled)
        self.assertIn("active-device", hass.device_registry.devices)
        self.assertNotIn("empty-device", hass.device_registry.devices)
        self.assertTrue(hass.device_registry.save_scheduled)


if __name__ == "__main__":
    unittest.main()