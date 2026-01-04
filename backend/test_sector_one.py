
from vnstock import Vnstock
try:
    print("Testing single stock overview...")
    vn = Vnstock()
    stock = vn.stock(symbol='VCB', source='VCI')
    overview = stock.company.overview()
    print("Overview Data:")
    print(overview)
    if overview is not None and not overview.empty:
        print("Columns:", overview.columns.tolist())
        row = overview.iloc[0]
        print("Sector info:", row.get('icb_name2'), row.get('industry'), row.get('sector'))
except Exception as e:
    print(f"Error: {e}")
