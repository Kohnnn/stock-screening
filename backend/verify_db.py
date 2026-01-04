import sqlite3
import pandas as pd

def verify():
    conn = sqlite3.connect('./data/vnstock_data.db')
    cursor = conn.cursor()
    
    symbols = ['FPT', 'NLG', 'DHG', 'VNM']
    print(f"Checking {symbols}...")
    
    for symbol in symbols:
        cursor.execute("SELECT symbol, gross_margin, net_margin, roe, pe_ratio FROM screener_metrics WHERE symbol = ?", (symbol,))
        row = cursor.fetchone()
    
        if row:
            print(f"✅ Found Screener Data for {symbol}:")
            print(f"  Gross Margin: {row[1]}")
            print(f"  Net Margin: {row[2]}")
            print(f"  ROE: {row[3]}")
            print(f"  PE: {row[4]}")
        else:
            print(f"❌ No screener data found for {symbol}")
    else:
        print(f"❌ No data found for {symbol}")
        
    conn.close()

if __name__ == "__main__":
    verify()
