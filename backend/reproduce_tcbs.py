from vnstock import Vnstock
import pandas as pd

def test_tcbs():
    print("Testing TCBS Screener...")
    try:
        stock = Vnstock().stock(source='VCI')
        params = {
            "filter": [{"key": "marketCap", "operator": ">", "value": 0}],
            "sort": [{"key": "marketCap", "value": "desc"}],
            "limit": 5,
            "page": 0
        }
        df = stock.screener.screener_data(params=params)
        if df is not None and not df.empty:
            print("✅ Success! Got data:")
            print(df[['ticker', 'marketCap', 'price']].head())
        else:
            print("❌ Failed: Returned empty or None")
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    test_tcbs()
