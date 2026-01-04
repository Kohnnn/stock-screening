
from vnstock import listing
try:
    print("Fetching listing...")
    df = listing(source='SSI')
    if df is not None and not df.empty:
        print("Columns:", df.columns.tolist())
        print("First row:", df.iloc[0].to_dict())
    else:
        print("Empty DataFrame returned")
except Exception as e:
    print(f"Error: {e}")
