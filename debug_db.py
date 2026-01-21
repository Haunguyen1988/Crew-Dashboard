import os
import sys

# Try to load env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from supabase import create_client
except ImportError:
    print("Error: 'supabase' package not found. Run: pip install supabase")
    sys.exit(1)

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("❌ Error: SUPABASE_URL or SUPABASE_KEY not set in .env")
    print("Please create a .env file with your credentials.")
    sys.exit(1)

print(f"Connecting to Supabase: {url}...")

try:
    client = create_client(url, key)
    print("✅ Client initialized.")
    
    # Check Tables
    tables = ['flights', 'ac_utilization', 'rolling_hours', 'crew_schedule']
    
    print("\n--- DATABASE STATUS ---")
    
    for table in tables:
        try:
            # Count rows
            # Note: head=True implies count only
            res = client.table(table).select("*", count='exact', head=True).execute()
            count = res.count
            print(f"📊 Table '{table}': {count} records")
            
            if count and count > 0:
                 # Show a sample
                 sample = client.table(table).select("*").limit(1).execute()
                 if sample.data:
                     print(f"   Sample: {sample.data[0].keys()}")
            
        except Exception as e:
            print(f"❌ Error query table '{table}': {str(e)}")
            print("   (Run the updated SQL script to fix RLS policies)")

except Exception as e:
    print(f"❌ Connection Failed: {str(e)}")
