#!/usr/bin/env python3
"""
Script to check and fix enum data inconsistencies in the users table
"""

import pymysql
import re
from config import settings

def parse_database_url(url):
    """Parse MySQL database URL into connection parameters"""
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

def fix_enum_data():
    """Check and fix enum data in users table"""
    
    config = parse_database_url(settings.DATABASE_URL)
    
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
            print("Checking current role column definition...")
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
            
            # Check existing data
            print("\nChecking existing role values in database...")
            cursor.execute("SELECT DISTINCT role FROM users WHERE role IS NOT NULL")
            existing_roles = cursor.fetchall()
            print(f"Existing role values: {[row[0] for row in existing_roles]}")
            
            # Update any uppercase values to lowercase
            print("\nUpdating any uppercase role values to lowercase...")
            
            # Update CUSTOMER to customer
            cursor.execute("UPDATE users SET role = 'customer' WHERE role = 'CUSTOMER'")
            customer_updates = cursor.rowcount
            print(f"Updated {customer_updates} CUSTOMER records to customer")
            
            # Update CHEF to chef  
            cursor.execute("UPDATE users SET role = 'chef' WHERE role = 'CHEF'")
            chef_updates = cursor.rowcount
            print(f"Updated {chef_updates} CHEF records to chef")
            
            # Ensure enum definition is correct
            print("\nEnsuring enum definition is correct...")
            cursor.execute("""
                ALTER TABLE users 
                MODIFY COLUMN role ENUM('customer', 'chef') NULL
            """)
            
            # Verify final state
            print("\nVerifying final state...")
            cursor.execute("""
                SELECT COLUMN_NAME, IS_NULLABLE, COLUMN_TYPE, COLUMN_DEFAULT
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'users' AND COLUMN_NAME = 'role'
            """, (config['database'],))
            
            final_def = cursor.fetchone()
            if final_def:
                print(f"Final role column definition:")
                print(f"  - Nullable: {final_def[1]}")
                print(f"  - Type: {final_def[2]}")
                print(f"  - Default: {final_def[3]}")
            
            cursor.execute("SELECT DISTINCT role FROM users WHERE role IS NOT NULL")
            final_roles = cursor.fetchall()
            print(f"Final role values: {[row[0] for row in final_roles]}")
            
            connection.commit()
            print("\n✅ Enum data fix completed successfully!")
            
    except Exception as e:
        print(f"❌ Fix failed: {e}")
        connection.rollback()
        raise
    finally:
        connection.close()

if __name__ == "__main__":
    try:
        fix_enum_data()
    except Exception as e:
        print(f"Fix error: {e}")
        exit(1) 