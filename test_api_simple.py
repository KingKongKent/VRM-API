"""Test script to check available VRM API data."""
import requests
import json

TOKEN = "cf2e981f964cd6020ed06c81dda8df1cf8154fc1353b7630dd320e8e243ca0c1"
BASE_URL = "https://vrmapi.victronenergy.com/v2/"

headers = {"X-Authorization": f"Token {TOKEN}"}

# Get installations
print("=" * 80)
print("GETTING YOUR INSTALLATIONS...")
print("=" * 80)

try:
    # Correct endpoint for installations list
    response = requests.get(f"{BASE_URL}users/me/installations", headers=headers, timeout=10)
    print(f"Response Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"API Response structure: {list(data.keys())}")
        
        # The correct response structure has 'records' at root level
        if 'records' in data:
            installations = data.get("records", [])
        else:
            # Fallback: maybe it's nested differently
            print(f"Full response: {json.dumps(data, indent=2)[:1000]}")
            installations = []
        
        if installations:
            for inst in installations:
                print(f"Site ID: {inst.get('idSite')}")
                print(f"Name: {inst.get('name')}")
                print()
            
            site_id = installations[0]["idSite"]
            print(f"\nUsing Site ID: {site_id}")
            print("=" * 80)
            
            # Test MultiPlus Status with instance 257
            print(f"\nMULTIPLUS STATUS (instance=257):")
            print("-" * 80)
            url = f"{BASE_URL}installations/{site_id}/widgets/Status?instance=257"
            resp = requests.get(url, headers=headers)
            print(f"Status Code: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                if "data" in data:
                    print(f"\nAvailable Data IDs in MultiPlus:")
                    for data_id in sorted(data["data"].keys(), key=lambda x: int(x) if x.isdigit() else 999):
                        value_info = data["data"][data_id]
                        value = value_info.get("valueFloat") or value_info.get("value") or value_info.get("nameEnum")
                        print(f"  ID {data_id:>4}: {value}")
                else:
                    print(f"Response: {json.dumps(data, indent=2)[:500]}")
            print()
            
            # Test Battery Summary with instance 512
            print(f"\nBATTERY SUMMARY (instance=512):")
            print("-" * 80)
            url = f"{BASE_URL}installations/{site_id}/widgets/BatterySummary?instance=512"
            resp = requests.get(url, headers=headers)
            print(f"Status Code: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                if "data" in data:
                    print(f"\nAvailable Data IDs in Battery:")
                    for data_id in sorted(data["data"].keys(), key=lambda x: int(x) if x.isdigit() else 999):
                        value_info = data["data"][data_id]
                        value = value_info.get("valueFloat") or value_info.get("value")
                        print(f"  ID {data_id:>4}: {value}")
            print()
    else:
        print(f"Error getting installations: {response.status_code}")
        print(f"Response Text: {response.text}")
except Exception as e:
    print(f"Exception occurred: {e}")
    import traceback
    traceback.print_exc()
