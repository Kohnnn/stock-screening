"""
Database Schema Migration Script

Adds missing columns to existing tables without data loss.
Run this when database schema has been updated.
"""
import sqlite3
from pathlib import Path


def get_existing_columns(cursor, table_name: str) -> set:
    """Get set of existing column names for a table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    return {row[1] for row in cursor.fetchall()}


def add_column_if_missing(cursor, table: str, column: str, col_type: str, existing: set):
    """Add a column if it doesn't exist."""
    if column not in existing:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
            print(f"  ✅ Added: {table}.{column}")
            return True
        except Exception as e:
            print(f"  ❌ Error adding {table}.{column}: {e}")
            return False
    else:
        print(f"  ⏭️  Exists: {table}.{column}")
        return False


def migrate_stock_prices(cursor):
    """Add missing columns to stock_prices table."""
    print("\n📊 Migrating stock_prices table...")
    
    existing = get_existing_columns(cursor, 'stock_prices')
    
    # Columns from database_schema.sql that may be missing
    columns_to_add = [
        ('book_value', 'REAL'),
        ('ps_ratio', 'REAL'),
        ('total_debt', 'REAL'),
        ('owner_equity', 'REAL'),
        ('total_assets', 'REAL'),
        ('debt_to_equity', 'REAL'),
        ('equity_to_assets', 'REAL'),
        ('cash', 'REAL'),
        ('foreign_ownership', 'REAL'),
        ('avg_volume_52w', 'INTEGER'),
        ('listed_shares', 'INTEGER'),
    ]
    
    added = 0
    for col_name, col_type in columns_to_add:
        if add_column_if_missing(cursor, 'stock_prices', col_name, col_type, existing):
            added += 1
    
    print(f"  📈 Added {added} new columns to stock_prices")
    return added


def migrate_stock_metrics(cursor):
    """Add missing columns to stock_metrics table."""
    print("\n📊 Migrating stock_metrics table...")
    
    existing = get_existing_columns(cursor, 'stock_metrics')
    
    # Columns that may be missing
    columns_to_add = [
        ('rel_strength_1m', 'REAL'),
        ('rel_strength_3m', 'REAL'),
        ('rel_strength_1y', 'REAL'),
        ('relative_strength_3d', 'REAL'),
    ]
    
    added = 0
    for col_name, col_type in columns_to_add:
        if add_column_if_missing(cursor, 'stock_metrics', col_name, col_type, existing):
            added += 1
    
    print(f"  📈 Added {added} new columns to stock_metrics")
    return added


def migrate_database():
    """Run all migrations."""
    db_path = Path(__file__).parent / 'data' / 'vnstock_data.db'
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return False
    
    print(f"📁 Database: {db_path}")
    print(f"📏 Size: {db_path.stat().st_size / 1024:.1f} KB")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cursor.fetchall()]
        print(f"📋 Tables: {', '.join(tables)}")
        
        # Run migrations
        total_added = 0
        total_added += migrate_stock_prices(cursor)
        total_added += migrate_stock_metrics(cursor)
        
        # Also run the full schema to create any missing tables
        schema_path = Path(__file__).parent / 'database_schema.sql'
        if schema_path.exists():
            print("\n📄 Applying full schema (for new tables)...")
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema = f.read()
            cursor.executescript(schema)
            print("  ✅ Schema applied")
        
        conn.commit()
        
        # Verify
        print("\n✅ Migration complete!")
        print(f"   Total columns added: {total_added}")
        
        # Show stock_prices structure
        cursor.execute("PRAGMA table_info(stock_prices)")
        cols = cursor.fetchall()
        print(f"\n📊 stock_prices now has {len(cols)} columns")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    print("\n🔧 VnStock Database Migration\n")
    print("=" * 50)
    success = migrate_database()
    print("=" * 50)
    print(f"\n{'🎉 Done!' if success else '⚠️ Check errors above'}\n")
