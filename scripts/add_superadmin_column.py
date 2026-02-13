import os
import sys
from pathlib import Path
import psycopg2
from psycopg2 import sql

sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.core.config import settings

import argparse

def migrate_and_promote():
    parser = argparse.ArgumentParser(description="Add is_superadmin column and optionally promote a user.")
    parser.add_argument("--promote", help="Email of the user to promote to superadmin")
    parser.add_argument("--no-input", action="store_true", help="Run without interactive prompts (just add column)")
    args = parser.parse_args()

    db_url = settings.DATABASE_URL
    if not db_url.startswith("postgresql"):
        print("❌ This script is intended for PostgreSQL databases.")
        return

    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cur = conn.cursor()

        print("🔧 Adding 'is_superadmin' column to 'users' table...")
        try:
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_superadmin BOOLEAN DEFAULT FALSE;")
            print("✅ Column added (or already exists).")
        except Exception as e:
            print(f"❌ Error adding column: {e}")

        if not args.no_input and not args.promote:
            print("\n👥 Existing users:")
            cur.execute("SELECT email, is_superadmin FROM users;")
            users = cur.fetchall()
            if not users:
                print("   (No users found)")
            else:
                for u in users:
                    print(f"   - {u[0]} (is_superadmin: {u[1]})")

        email_to_promote = args.promote

        if not email_to_promote and not args.no_input:
            print("\n📢 Would you like to promote a user to Superadmin? (y/n)")
            choice = input().strip().lower()
            if choice == 'y':
                email_to_promote = input("📧 Enter the email of the user to promote: ").strip()

        if email_to_promote:
            cur.execute("SELECT id FROM users WHERE email = %s;", (email_to_promote,))
            user = cur.fetchone()
            
            if user:
                cur.execute("UPDATE users SET is_superadmin = TRUE WHERE email = %s;", (email_to_promote,))
                print(f"✅ User '{email_to_promote}' is now a Superadmin!")
            else:
                print(f"❌ User '{email_to_promote}' not found.")
        
        cur.close()
        conn.close()
        print("\n🎉 Migration completed.")

    except Exception as e:
        print(f"\n❌ Database connection failed: {e}")

if __name__ == "__main__":
    migrate_and_promote()
