
import asyncio
import sys
import os
import aiosqlite

async def main():
    db_path = "./backend/data/vnstock_data.db"
    if not os.path.exists(db_path):
        print(f"❌ DB not found: {db_path}")
        return

    async with aiosqlite.connect(db_path) as db:
        async with db.execute("SELECT COUNT(*) FROM stocks") as cursor:
            count = (await cursor.fetchone())[0]
            print(f"Total stocks: {count}")

        async with db.execute("SELECT COUNT(*) FROM stocks WHERE is_active=1") as cursor:
            active = (await cursor.fetchone())[0]
            print(f"Active stocks: {active}")

if __name__ == "__main__":
    asyncio.run(main())
