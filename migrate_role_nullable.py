#!/usr/bin/env python3
"""
Database migration script to allow null values in the users.role column
This is needed for Google OAuth users who haven't selected their role yet.
"""

import pymysql
import re
from config import settings

def parse_database_url(url):
    """Parse MySQL database URL into connection parameters"""
    # Format: mysql+pymysql://user:password@host:port/database
    pattern = r'mysql\+pymysql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)'
    match = re.match(pattern, url)
    if not match:
        raise ValueError(f"Invalid database URL format: {url}")
    
    return {
        'user': match.group(1),
        'password': match.group(2),
        'host': match.group(3),
        'port': int(match.group(4)),
        'database': match.group(5)
    }

def migrate_role_nullable():
    """Make the role column nullable in the users table"""
    
    # Parse database URL
    config = parse_database_url(settings.DATABASE_URL)
    
    # Connect to database
    connection = pymysql.connect(
        host=config['host'],
        port=config['port'],
        user=config['user'],
        password=config['password'],
        database=config['database'],
        charset='utf8mb4'
    )
    
    try:
        with connection.cursor() as cursor:
            # Check current column definition
            cursor.execute("""
                SELECT COLUMN_NAME, IS_NULLABLE, COLUMN_TYPE, COLUMN_DEFAULT
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'users' AND COLUMN_NAME = 'role'
            """, (config['database'],))
            
            current_def = cursor.fetchone()
            if current_def:
                print(f"Current role column definition:")
                print(f"  - Nullable: {current_def[1]}")
                print(f"  - Type: {current_def[2]}")
                print(f"  - Default: {current_def[3]}")
            
            # Make role column nullable
            print("\nUpdating role column to allow NULL values...")
            cursor.execute("""
                ALTER TABLE users 
                MODIFY COLUMN role ENUM('customer', 'chef') NULL
            """)
            
            # Verify the change
            cursor.execute("""
                SELECT COLUMN_NAME, IS_NULLABLE, COLUMN_TYPE, COLUMN_DEFAULT
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'users' AND COLUMN_NAME = 'role'
            """, (config['database'],))
            
            updated_def = cursor.fetchone()
            if updated_def:
                print(f"\nUpdated role column definition:")
                print(f"  - Nullable: {updated_def[1]}")
                print(f"  - Type: {updated_def[2]}")
                print(f"  - Default: {updated_def[3]}")
            
            connection.commit()
            print("\n✅ Migration successful! Role column now allows NULL values.")
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        connection.rollback()
        raise
    finally:
        connection.close()

if __name__ == "__main__":
    try:
        migrate_role_nullable()
    except Exception as e:
        print(f"Migration error: {e}")
        exit(1) 