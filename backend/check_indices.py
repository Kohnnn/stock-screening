
from vnstock import Vnstock
import pandas as pd

def check_indices():
    vn = Vnstock()
    # Try to find index list
    # The 'listing' class usually has methods for this
    try:
        # Some versions use other methods, checking popular ones
        print("Checking vnstock indices...")
        # Often this is hardcoded or specific function
        # Let's try fetching history for specific codes to see if they exist
        candidates = ['HNX', 'HNX30', 'HNXINDEX', 'UPCOM', 'UPCOMINDEX', 'VNINDEX', 'VN30']
        
        for code in candidates:
            try:
                print(f"Testing {code}...")
                df = vn.stock(symbol=code, source='VCI').quote.history(days=1)
                if df is not None and not df.empty:
                    print(f"  -> FOUND {code}: {df.iloc[0].to_dict()}")
                else:
                    print(f"  -> Empty result for {code}")
            except Exception as e:
                print(f"  -> Error fetching {code}: {e}")
                
    except Exception as e:
        print(f"Global error: {e}")

if __name__ == "__main__":
    check_indices()
