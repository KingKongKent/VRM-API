"""Test script to check available VRM API data."""
import aiohttp
import asyncio
import json

TOKEN = "cf2e981f964cd6020ed06c81dda8df1cf8154fc1353b7630dd320e8e243ca0c1"
BASE_URL = "https://vrmapi.victronenergy.com/v2/installations/"

async def test_api():
    """Test VRM API endpoints."""
    
    # First, get the list of installations
    headers = {"X-Authorization": f"Token {TOKEN}"}
    
    async with aiohttp.ClientSession() as session:
        # Get installations
        async with session.get(f"{BASE_URL[:-15]}users/me/installations", headers=headers) as response:
            if response.status == 200:
                installations = await response.json()
                print("=" * 80)
                print("YOUR INSTALLATIONS:")
                print("=" * 80)
                for inst in installations.get("records", []):
                    print(f"Site ID: {inst.get('idSite')}")
                    print(f"Name: {inst.get('name')}")
                    print()
                
                if installations.get("records"):
                    site_id = installations["records"][0]["idSite"]
                    print(f"\nTesting with Site ID: {site_id}")
                    print("=" * 80)
                    
                    # Test MultiPlus Status endpoint
                    endpoints = [
                        ("widgets/Status?instance=257", "MultiPlus Status"),
                        ("widgets/BatterySummary?instance=512", "Battery Summary"),
                        ("widgets/HistoricData?instance=512", "Battery History"),
                    ]
                    
                    for endpoint, name in endpoints:
                        print(f"\n{name} ({endpoint}):")
                        print("-" * 80)
                        url = f"{BASE_URL}{site_id}/{endpoint}"
                        async with session.get(url, headers=headers) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                if "data" in data:
                                    print(f"Available Data IDs:")
                                    for data_id in sorted(data["data"].keys(), key=lambda x: int(x) if x.isdigit() else 999):
                                        value_info = data["data"][data_id]
                                        value = value_info.get("valueFloat") or value_info.get("value") or value_info.get("nameEnum")
                                        print(f"  ID {data_id:>4}: {value}")
                                else:
                                    print(f"Response: {json.dumps(data, indent=2)[:500]}")
                            else:
                                print(f"Error: Status {resp.status}")

if __name__ == "__main__":
    asyncio.run(test_api())
