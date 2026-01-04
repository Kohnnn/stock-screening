
"""
Tag VN30 stocks with sector='VN30' for Smart Board display.
"""
import asyncio
from database import Database

VN30_SYMBOLS = [
    "ACB", "BCM", "BID", "BVH", "CTG", "FPT", "GAS", "GVR", "HDB", "HPG",
    "MBB", "MSN", "MWG", "PLX", "POW", "SAB", "SHB", "SSB", "SSI", "STB",
    "TCB", "TPB", "VCB", "VHM", "VIB", "VIC", "VJC", "VNM", "VPB", "VRE"
]

async def tag_vn30():
    db = Database("./data/vnstock_data.db")
    await db.initialize()
    
    # Create placeholders for the SQL
    placeholders = ','.join(['?' for _ in VN30_SYMBOLS])
    
    # First, add VN30 as a secondary tag (preserve original sector)
    # We'll create a new column or use a join table approach
    # For now, let's create stocks in VN30 sector view by using a dedicated query
    
    # Alternative: Update the API to handle VN30 specially
    # For quick fix, let's update stocks table to have is_vn30 flag
    
    async with db.connection() as conn:
        # Check if is_vn30 column exists
        cursor = await conn.execute("PRAGMA table_info(stocks)")
        columns = [row[1] for row in await cursor.fetchall()]
        
        if 'is_vn30' not in columns:
            print("Adding is_vn30 column...")
            await conn.execute("ALTER TABLE stocks ADD COLUMN is_vn30 INTEGER DEFAULT 0")
            await conn.commit()
        
        # Tag VN30 stocks
        await conn.execute(f"UPDATE stocks SET is_vn30 = 1 WHERE symbol IN ({placeholders})", VN30_SYMBOLS)
        await conn.commit()
        
        cursor = await conn.execute("SELECT COUNT(*) FROM stocks WHERE is_vn30 = 1")
        count = (await cursor.fetchone())[0]
        print(f"Tagged {count} stocks as VN30")

if __name__ == "__main__":
    asyncio.run(tag_vn30())
