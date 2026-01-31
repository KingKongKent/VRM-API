"""Test script for installation 337075."""
import requests
import json

TOKEN = "cf2e981f964cd6020ed06c81dda8df1cf8154fc1353b7630dd320e8e243ca0c1"
SITE_ID = "337075"
BASE_URL = f"https://vrmapi.victronenergy.com/v2/installations/{SITE_ID}/"
headers = {"X-Authorization": f"Token {TOKEN}"}

print("=" * 80)
print(f"TESTING INSTALLATION {SITE_ID}")
print("=" * 80)

# Test MultiPlus Status - instance 257
print("\n1. MULTIPLUS STATUS (instance=257):")
print("-" * 80)
resp = requests.get(f"{BASE_URL}widgets/Status?instance=257", headers=headers, timeout=10)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    print(f"Response keys: {data.keys()}")
    if "records" in data:
        print(f"Records keys: {data['records'].keys()}")
        if "data" in data["records"]:
            actual_data = data["records"]["data"]
            print(f"Data keys: {list(actual_data.keys())[:20]}")  # First 20 keys
            print(f"\nAvailable Data IDs:")
            for data_id in sorted([k for k in actual_data.keys() if k.isdigit()], key=int):
                value_info = actual_data[data_id]
                value = value_info.get("valueFloat") or value_info.get("value") or value_info.get("nameEnum")
                print(f"  ID {data_id:>4}: {value}")
        else:
            print("No 'data' key in records")
    else:
        print("No 'records' key in response")
else:
    print(f"Error: {resp.text}")

# Test Battery Summary - instance 512
print("\n2. BATTERY SUMMARY (instance=512):")
print("-" * 80)
resp = requests.get(f"{BASE_URL}widgets/BatterySummary?instance=512", headers=headers, timeout=10)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    if "records" in data and "data" in data["records"]:
        actual_data = data["records"]["data"]
        print(f"\nAvailable Data IDs:")
        for data_id in sorted(actual_data.keys(), key=lambda x: int(x) if x.isdigit() else 999):
            if data_id in ["hasOldData", "secondsAgo"]:
                continue
            value_info = actual_data[data_id]
            value = value_info.get("valueFloat") or value_info.get("value")
            print(f"  ID {data_id:>4}: {value}")
    else:
        print("No data found")

# Test Solar Charger Summary - instance 279
print("\n3. SOLAR CHARGER SUMMARY (instance=279):")
print("-" * 80)
resp = requests.get(f"{BASE_URL}widgets/SolarChargerSummary?instance=279", headers=headers, timeout=10)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    if "records" in data and "data" in data["records"]:
        actual_data = data["records"]["data"]
        print(f"\nAvailable Data IDs:")
        for data_id in sorted(actual_data.keys(), key=lambda x: int(x) if x.isdigit() else 999):
            if data_id in ["hasOldData", "secondsAgo"]:
                continue
            value_info = actual_data[data_id]
            value = value_info.get("valueFloat") or value_info.get("value") or value_info.get("nameEnum")
            print(f"  ID {data_id:>4}: {value}")
    else:
        print("No data found")

# Test Overall Stats
print("\n4. OVERALL STATS:")
print("-" * 80)
resp = requests.get(f"{BASE_URL}overallstats", headers=headers, timeout=10)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    print(json.dumps(data, indent=2)[:1000])
