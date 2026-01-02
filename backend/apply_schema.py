"""Apply the new database schema to create missing tables."""
import sqlite3
from pathlib import Path

def apply_schema():
    """Apply the schema updates to create new tables."""
    db_path = Path('data/vnstock_data.db')
    schema_path = Path('database_schema.sql')
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return False
    
    if not schema_path.exists():
        print(f"❌ Schema file not found: {schema_path}")
        return False
    
    print(f"📁 Database: {db_path}")
    print(f"📄 Schema: {schema_path}")
    
    # Read the schema
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema = f.read()
    
    # Connect and apply
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Execute the entire schema (CREATE IF NOT EXISTS will skip existing tables)
        cursor.executescript(schema)
        conn.commit()
        print("✅ Schema applied successfully!")
        
        # Verify new tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [r[0] for r in cursor.fetchall()]
        
        new_tables = ['data_update_tracker', 'dividend_history', 'company_ratings', 
                      'intraday_prices', 'market_indices']
        
        print("\nNew Tables Status:")
        for table in new_tables:
            exists = table in tables
            print(f"  {'✅' if exists else '❌'} {table}")
        
        return all(t in tables for t in new_tables)
        
    except Exception as e:
        print(f"❌ Error applying schema: {e}")
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    print("\n🔧 Applying Database Schema Updates\n")
    success = apply_schema()
    print(f"\n{'🎉 Complete!' if success else '⚠️ Check errors above'}")
