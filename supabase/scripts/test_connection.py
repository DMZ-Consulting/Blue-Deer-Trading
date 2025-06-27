#!/usr/bin/env python3
"""
Simple script to test database connections
"""
import psycopg2
import os
import sys

def test_connection(name, url_env_var):
    url = os.getenv(url_env_var)
    if not url:
        print(f"❌ {name}: {url_env_var} environment variable not set")
        return False
    
    print(f"🔗 Testing {name} connection...")
    print(f"   URL: {url[:50]}...")  # Only show first 50 chars for security
    
    try:
        conn = psycopg2.connect(url)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        print(f"✅ {name}: Connection successful!")
        return True
        
    except Exception as e:
        print(f"❌ {name}: Connection failed - {e}")
        return False

def main():
    print("=== Database Connection Test ===\n")
    
    prod_ok = test_connection("Production", "PROD_DB_URL")
    preview_ok = test_connection("Preview", "PREVIEW_DB_URL")
    
    print("\n=== Results ===")
    if prod_ok and preview_ok:
        print("✅ Both connections working! You can run the data copy script.")
    else:
        print("❌ Some connections failed. Check your database URLs.")
        print("\n💡 Tips:")
        print("• Make sure you copied the full URI from Supabase dashboard")
        print("• The URL should start with 'postgresql://'")
        print("• Make sure the password is correct (no special characters need escaping)")
        print("• The hostname might be something like 'aws-0-us-west-1.pooler.supabase.com'")

if __name__ == "__main__":
    main() 