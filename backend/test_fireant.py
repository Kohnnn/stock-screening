import requests
import json

def test_fireant():
    print("Testing FireAnt API...")
    
    # Common headers acting as a browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://fireant.vn/',
        'Origin': 'https://fireant.vn'
    }

    # Try to get basic symbol list or financial data
    # Endpoint often used: https://restv2.fireant.vn/symbols/list
    # Or financial: https://restv2.fireant.vn/symbols/{symbol}/financial-reports
    
    try:
        # Test 1: Get Symbol info for VNM
        url = "https://restv2.fireant.vn/symbols/VNM/profile"
        print(f"1. Calling {url} ...")
        resp = requests.get(url, headers=headers, timeout=10)
        
        if resp.status_code == 200:
            print("✅ Profile Success!")
            print(json.dumps(resp.json(), indent=2, ensure_ascii=False)[:300] + "...")
        else:
            print(f"❌ Profile Failed: {resp.status_code} - {resp.text}")

        # Test 2: Financial Reports (The main goal)
        # Type 1 = Balance Sheet, 2 = Income, 3 = Cash Flow? Need to verify.
        url = "https://restv2.fireant.vn/symbols/VNM/financial-reports?type=1&year=2023&quarter=4"
        print(f"\n2. Calling {url} ...")
        resp = requests.get(url, headers=headers, timeout=10)
        
        if resp.status_code == 200:
            print("✅ Financials Success!")
            print(json.dumps(resp.json(), indent=2, ensure_ascii=False)[:300] + "...")
        elif resp.status_code == 401:
             print("❌ Financials require Auth (401)")
        else:
            print(f"❌ Financials Failed: {resp.status_code}")

    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    test_fireant()
