import os
import sys
from pathlib import Path
import psycopg2

# Add the project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.core.config import settings

def migrate_is_active():
    db_url = settings.DATABASE_URL
    if not db_url.startswith("postgresql"):
        print("❌ This script is intended for PostgreSQL databases.")
        return

    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cur = conn.cursor()

        print("🔧 Adding 'is_active' column to 'users' table...")
        try:
            # Add column with default TRUE, so existing users remain active
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;")
            print("✅ Column added (or already exists).")
        except Exception as e:
            print(f"❌ Error adding column: {e}")

        cur.close()
        conn.close()
        print("\n🎉 Migration completed.")

    except Exception as e:
        print(f"\n❌ Database connection failed: {e}")

if __name__ == "__main__":
    migrate_is_active()
