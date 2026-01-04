
"""
Collect company profiles from multiple sources (VCI, CafeF).
Since TCBS is blocking, we use alternative sources.
"""

import asyncio
from datetime import datetime
import sqlite3
import aiohttp
from loguru import logger
from vnstock import Vnstock, Company

# Priority stocks
PRIORITY_SYMBOLS = [
    "VCB", "VHM", "VIC", "FPT", "MBB", "TCB", "HPG", "VNM", "BID", "CTG",
    "GAS", "SAB", "VPB", "MWG", "MSN", "HDB", "ACB", "STB", "SSI", "VRE",
    "VJC", "PLX", "POW", "BCM", "GVR", "SHB", "TPB", "SSB", "VIB", "BVH"
]

async def collect_profiles_vci():
    """Collect company profiles using VCI source."""
    logger.info("👤 Starting profile collection using VCI source...")
    
    conn = sqlite3.connect("./data/vnstock_data.db")
    cursor = conn.cursor()
    
    # Ensure stock_profiles table exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_profiles (
            symbol TEXT PRIMARY KEY,
            short_name TEXT,
            company_name TEXT,
            exchange TEXT,
            industry TEXT,
            sector TEXT,
            company_type TEXT,
            established_date TEXT,
            charter_capital REAL,
            listing_date TEXT,
            issue_shares REAL,
            listed_shares REAL,
            website TEXT,
            phone TEXT,
            email TEXT,
            address TEXT,
            description TEXT,
            history TEXT,
            updated_at TEXT
        )
    """)
    conn.commit()
    
    collected = 0
    failed = 0
    
    for symbol in PRIORITY_SYMBOLS:
        try:
            # Try VCI source
            company = Company(symbol=symbol, source='VCI')
            overview = company.overview()
            
            if overview is not None and not overview.empty:
                row = overview.iloc[0] if len(overview) > 0 else {}
                
                cursor.execute("""
                    INSERT OR REPLACE INTO stock_profiles (
                        symbol, short_name, company_name, exchange, industry, sector,
                        company_type, established_date, charter_capital, listing_date,
                        issue_shares, listed_shares, website, phone, email, address,
                        description, history, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    symbol,
                    str(row.get('short_name', row.get('organ_short_name', '')))[:50],
                    str(row.get('company_name', row.get('organ_name', '')))[:200],
                    str(row.get('exchange', '')),
                    str(row.get('icb_name3', row.get('industry', '')))[:100],
                    str(row.get('icb_name2', row.get('sector', '')))[:100],
                    str(row.get('company_type', '')),
                    str(row.get('established_date', '')),
                    float(row.get('charter_capital', 0) or 0),
                    str(row.get('listing_date', '')),
                    float(row.get('issue_share', 0) or 0),
                    float(row.get('listed_share', 0) or 0),
                    str(row.get('website', ''))[:200],
                    str(row.get('phone', ''))[:50],
                    str(row.get('email', ''))[:100],
                    str(row.get('address', ''))[:300],
                    str(row.get('company_profile', row.get('organ_intro', '')))[:5000],
                    str(row.get('history', ''))[:2000],
                    datetime.now().isoformat()
                ))
                conn.commit()
                collected += 1
                logger.info(f"✅ {symbol}: Profile saved from VCI")
            else:
                failed += 1
                logger.warning(f"⚠️ {symbol}: No VCI profile data")
                
        except Exception as e:
            failed += 1
            logger.error(f"❌ {symbol}: {str(e)[:60]}")
        
        await asyncio.sleep(0.5)
    
    conn.close()
    logger.info(f"\n🏁 VCI Collection: {collected} collected, {failed} failed")
    return collected, failed


async def collect_profiles_cafef():
    """Collect company profiles from CafeF website."""
    logger.info("☕ Starting profile collection from CafeF...")
    
    conn = sqlite3.connect("./data/vnstock_data.db")
    cursor = conn.cursor()
    
    collected = 0
    failed = 0
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    async with aiohttp.ClientSession(headers=headers) as session:
        for symbol in PRIORITY_SYMBOLS:
            try:
                # CafeF company profile URL
                url = f"https://s.cafef.vn/hose/{symbol}.chn"
                
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        
                        # Basic parsing - extract company description from HTML
                        import re
                        
                        # Look for company description in meta tags or specific divs
                        desc_match = re.search(r'<meta name="description" content="([^"]+)"', html)
                        desc = desc_match.group(1) if desc_match else ''
                        
                        # Look for company name in title
                        title_match = re.search(r'<title>([^<]+)</title>', html)
                        title = title_match.group(1) if title_match else ''
                        
                        if desc or title:
                            # Update existing profile with CafeF data
                            cursor.execute("""
                                UPDATE stock_profiles SET
                                    description = COALESCE(NULLIF(?, ''), description)
                                WHERE symbol = ?
                            """, (desc[:5000], symbol))
                            
                            if cursor.rowcount == 0:
                                # Insert new if doesn't exist
                                cursor.execute("""
                                    INSERT OR IGNORE INTO stock_profiles 
                                    (symbol, company_name, description, updated_at)
                                    VALUES (?, ?, ?, ?)
                                """, (symbol, title[:200], desc[:5000], datetime.now().isoformat()))
                            
                            conn.commit()
                            collected += 1
                            logger.info(f"✅ {symbol}: CafeF profile updated")
                        else:
                            failed += 1
                            logger.warning(f"⚠️ {symbol}: No CafeF content")
                    else:
                        failed += 1
                        logger.warning(f"⚠️ {symbol}: CafeF status {resp.status}")
                        
            except Exception as e:
                failed += 1
                logger.error(f"❌ {symbol}: CafeF error - {str(e)[:40]}")
            
            await asyncio.sleep(0.5)
    
    conn.close()
    logger.info(f"\n☕ CafeF Collection: {collected} updated, {failed} failed")
    return collected, failed


async def main():
    """Run profile collection from all sources."""
    logger.info("=" * 60)
    logger.info("COMPANY PROFILE COLLECTION")
    logger.info("=" * 60)
    
    # Try VCI source first
    vci_collected, vci_failed = await collect_profiles_vci()
    
    # Supplement with CafeF
    cafef_collected, cafef_failed = await collect_profiles_cafef()
    
    logger.info("\n" + "=" * 60)
    logger.info(f"TOTAL: VCI={vci_collected}, CafeF={cafef_collected}")
    logger.info("=" * 60)
    
    # Check results
    conn = sqlite3.connect("./data/vnstock_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM stock_profiles WHERE description IS NOT NULL AND description != ''")
    with_desc = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM stock_profiles")
    total = cursor.fetchone()[0]
    conn.close()
    
    logger.info(f"📊 Profiles with description: {with_desc}/{total}")

if __name__ == "__main__":
    asyncio.run(main())
