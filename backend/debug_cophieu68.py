"""Debug script to inspect cophieu68 HTML structure."""
import aiohttp
import asyncio
from bs4 import BeautifulSoup

async def debug():
    async with aiohttp.ClientSession() as session:
        async with session.get('https://www.cophieu68.vn/market/markets.php?vt=1&cP=1') as resp:
            html = await resp.text()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find data table
            tables = soup.find_all('table')
            for t in tables:
                if t.find('a', href=lambda x: x and 'quote/summary.php' in x):
                    rows = t.find_all('tr')
                    # Print header
                    header = rows[0].find_all(['td', 'th'])
                    print("HEADER:", [h.get_text(strip=True)[:15] for h in header])
                    
                    # Print first 3 data rows
                    print("\nDATA ROWS:")
                    for row in rows[1:4]:
                        cells = row.find_all(['td', 'th'])
                        print("---")
                        for i, c in enumerate(cells[:10]):
                            val = c.get_text(strip=True)[:50]
                            print(f"  [{i}]: {val}")
                    break

if __name__ == "__main__":
    asyncio.run(debug())
