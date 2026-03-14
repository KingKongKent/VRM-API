"""Test script for VRM API - Local testing only.

Copy .env.example to .env and fill in your credentials before running.
"""
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

# CONFIGURATION — loaded from .env
TOKEN = os.environ["VRM_TOKEN"]
SITE_ID = os.environ["VRM_SITE_ID"]

# Optionally specify instance IDs to test
MULTI_INSTANCE = "257"
BATTERY_INSTANCE = "512"
SOLAR_CHARGER_INSTANCE = "279"

BASE_URL = f"https://vrmapi.victronenergy.com/v2/installations/{SITE_ID}/"
headers = {"X-Authorization": f"Token {TOKEN}"}

print("=" * 80)
print(f"TESTING INSTALLATION {SITE_ID}")
print("=" * 80)

# Test MultiPlus Status
print(f"\n1. MULTIPLUS STATUS (instance={MULTI_INSTANCE}):")
print("-" * 80)
resp = requests.get(f"{BASE_URL}widgets/Status?instance={MULTI_INSTANCE}", headers=headers, timeout=10)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    if "records" in data and "data" in data["records"]:
        actual_data = data["records"]["data"]
        print(f"\nAvailable Data IDs:")
        for data_id in sorted([k for k in actual_data.keys() if k.isdigit()], key=int):
            value_info = actual_data[data_id]
            value = value_info.get("valueFloat") or value_info.get("value") or value_info.get("nameEnum")
            print(f"  ID {data_id:>4}: {value}")
else:
    print(f"Error: {resp.text}")

# Test Battery Summary
print(f"\n2. BATTERY SUMMARY (instance={BATTERY_INSTANCE}):")
print("-" * 80)
resp = requests.get(f"{BASE_URL}widgets/BatterySummary?instance={BATTERY_INSTANCE}", headers=headers, timeout=10)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    if "records" in data and "data" in data["records"]:
        actual_data = data["records"]["data"]
        print(f"\nAvailable Data IDs:")
        for data_id in sorted([k for k in actual_data.keys() if k.isdigit()], key=int):
            value_info = actual_data[data_id]
            value = value_info.get("valueFloat") or value_info.get("value")
            print(f"  ID {data_id:>4}: {value}")

# Test Solar Charger Summary
print(f"\n3. SOLAR CHARGER SUMMARY (instance={SOLAR_CHARGER_INSTANCE}):")
print("-" * 80)
resp = requests.get(f"{BASE_URL}widgets/SolarChargerSummary?instance={SOLAR_CHARGER_INSTANCE}", headers=headers, timeout=10)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    if "records" in data and "data" in data["records"]:
        actual_data = data["records"]["data"]
        print(f"\nAvailable Data IDs:")
        for data_id in sorted([k for k in actual_data.keys() if k.isdigit()], key=int):
            value_info = actual_data[data_id]
            value = value_info.get("valueFloat") or value_info.get("value") or value_info.get("nameEnum")
            print(f"  ID {data_id:>4}: {value}")

# Test Overall Stats
print("\n4. OVERALL STATS:")
print("-" * 80)
resp = requests.get(f"{BASE_URL}overallstats", headers=headers, timeout=10)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    if "records" in data:
        records = data["records"]
        if "today" in records and "totals" in records["today"]:
            print("\nToday's totals:")
            for key, value in records["today"]["totals"].items():
                print(f"  {key}: {value}")
